"""
High level game loop combining exploration and combat.

The `Game` class manages the world map, hero movement, random encounters and
transition into tactical combat.  It loads all graphical assets at startup
and passes them into the appropriate drawing functions.  The main loop is
event‑driven and uses Pygame to handle input and rendering.
"""

from __future__ import annotations

import os
import random
import json
import heapq
import logging
from functools import lru_cache
from typing import Dict, Optional, Tuple, List, Any, Type, Union, Set

import pygame
import audio
import constants
import theme
from graphics.scale import scale_surface, scale_with_anchor
from ui.inventory_screen import InventoryScreen
from loaders.asset_manager import AssetManager
from loaders.core import Context
from loaders.flora_loader import FloraLoader, PropInstance
from loaders.resources_loader import load_resources, ResourceDef
from loaders.biomes import BiomeCatalog, BiomeTileset, load_tileset
from loaders import units_loader
from loaders.scenario_loader import load_scenario
from tools.artifact_manifest import load_artifact_manifest
from tools.load_manifest import load_manifest
from events import dispatch as dispatch_event
from core.entities import (
    Hero,
    Army,
    EnemyHero,
    Unit,
    UnitStats,
    UnitCarrier,
    Item,
    HeroStats,
    SWORDSMAN_STATS,
    ARCHER_STATS,
    MAGE_STATS,
    CAVALRY_STATS,
    DRAGON_STATS,
    PRIEST_STATS,
    create_random_enemy_army,
    STARTING_ARTIFACTS,
    ARTIFACT_ICONS,
)
from core.world import WorldMap, generate_combat_map, init_biome_images, Tile
from core.faction import Faction
from graphics.spritesheet import load_sprite_sheet
from mapgen import generate_continent_map
from mapgen.continents import required_coast_images
from core.ai.faction_ai import FactionAI
from core.ai.creature_ai import CreatureAI
from core.buildings import Building, Town, create_building
from loaders.building_loader import BUILDINGS, get_surface
from ui.main_screen import MainScreen
from ui import dialogs
from state.event_bus import (
    EVENT_BUS,
    ON_SELECT_HERO,
    ON_RESOURCES_CHANGED,
    ON_TURN_END,
    ON_CAMERA_CHANGED,
    ON_ENEMY_DEFEATED,
    ON_INFO_MESSAGE,
)
from state.game_state import PlayerResources, GameState
from state.quests import QuestManager
from core import economy, auto_resolve


logger = logging.getLogger(__name__)

# Mapping from unit names to their statistics for serialisation
STATS_BY_NAME: Dict[str, UnitStats] = {
    SWORDSMAN_STATS.name: SWORDSMAN_STATS,
    ARCHER_STATS.name: ARCHER_STATS,
    MAGE_STATS.name: MAGE_STATS,
    CAVALRY_STATS.name: CAVALRY_STATS,
    DRAGON_STATS.name: DRAGON_STATS,
    PRIEST_STATS.name: PRIEST_STATS,
}



# Filenames for save slots
SAVE_SLOT_FILES = [f"save{i:02d}.json" for i in range(1, 4)]
PROFILE_SLOT_FILES = [f"save_profile{i:02d}.json" for i in range(1, 4)]
# Filename for a quick save
QUICK_SAVE_FILE = "quick_save.json"
QUICK_PROFILE_FILE = "quick_save_profile.json"

# Current version of the save file format.
SAVE_FORMAT_VERSION = 1

# Mapping from building names to their classes for serialisation
# Legacy mapping retained for save compatibility; only Town uses a custom class.
BUILDING_CLASSES: Dict[str, Type[Building]] = {"Town": Town}


# ---------------------------------------------------------------------------
# Pathfinding helpers
# ---------------------------------------------------------------------------


def heuristic(a: Tuple[int, int], b: Tuple[int, int]) -> int:
    """Return the Manhattan distance between two tiles."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


class _WorldView:
    """Lightweight adapter exposing camera info for widgets."""

    def __init__(self, game: "Game") -> None:
        self.game = game
        self.surface = pygame.Surface((1, 1))

    @property
    def cam_x(self) -> float:
        return -self.game.offset_x / self.game.zoom

    @property
    def cam_y(self) -> float:
        return -self.game.offset_y / self.game.zoom

    @property
    def zoom(self) -> float:
        return self.game.zoom

    def center_on(self, tile: Tuple[int, int]) -> None:
        tx, ty = tile
        rect = (
            self.game.main_screen.widgets.get("1")
            if getattr(self.game, "main_screen", None)
            else pygame.Rect(0, 0, self.surface.get_width(), self.surface.get_height())
        )
        px = (tx + 0.5) * constants.TILE_SIZE * self.game.zoom
        py = (ty + 0.5) * constants.TILE_SIZE * self.game.zoom
        self.game.offset_x = rect.width / 2 - px
        self.game.offset_y = rect.height / 2 - py
        self.game._clamp_offset(rect)
        EVENT_BUS.publish(ON_CAMERA_CHANGED, self.game.offset_x, self.game.offset_y, self.game.zoom)

class Game:
    def __init__(
        self,
        screen: pygame.Surface,
        map_file: Optional[str] = None,
        use_default_map: bool = True,
        slot: int = 0,
        map_size: str = constants.DEFAULT_MAP_SIZE,
        difficulty: str = constants.AI_DIFFICULTY,
        scenario: Optional[str] = None,
        player_name: str = "Joueur",
        player_colour: Tuple[int, int, int] = constants.BLUE,
        faction: Faction = Faction.RED_KNIGHTS,
        ai_names: Optional[List[str]] = None,
    ) -> None:
        self.screen = screen
        self.current_slot = slot
        self.map_size = map_size
        self.scenario = scenario
        self.player_name = player_name
        self.player_colour = player_colour
        self.faction = faction
        self.ai_names = ai_names or ["ordinateur"]
        constants.AI_DIFFICULTY = difficulty
        repo_root = os.path.dirname(os.path.dirname(__file__))
        self.assets = AssetManager(repo_root)

        search_paths = [os.path.join(repo_root, "assets")]
        extra = os.environ.get("FG_ASSETS_DIR")
        if extra:
            search_paths.append(extra)
        self.ctx = Context(repo_root=repo_root, search_paths=search_paths, asset_loader=self.assets)

        BiomeCatalog.load(self.ctx, "biomes/biomes.json")
        init_biome_images()
        self.load_assets()

        self.biome_tilesets: Dict[str, BiomeTileset] = {
            b.id: load_tileset(self.ctx, b, tile_size=constants.COMBAT_TILE_SIZE)
            for b in BiomeCatalog._biomes.values()
        }

        self.flora_loader = FloraLoader(self.ctx, tile_size=constants.TILE_SIZE)
        self.flora_loader.load_manifest("flora/flora.json")

        self.resources: Dict[str, ResourceDef] = load_resources(
            self.ctx, "resources/resources.json", tile_size=constants.TILE_SIZE
        )

        try:
            self.unit_defs = units_loader.load_units(self.ctx, "units/units.json")
        except Exception:
            self.unit_defs = {}
        # Initialise audio system and load sound effects
        audio.init()
        try:
            self.ap_font = theme.get_font(24) or pygame.font.Font(None, 24)
        except Exception:
            logger.exception("Failed to initialise action point font")
            self.ap_font = None
        # Create world map from file if provided; otherwise try to load a default file
        world_path: Optional[str] = None
        if map_file:
            world_path = map_file
        elif use_default_map:
            # Look for a default map in the maps folder
            default_path = os.path.join(os.path.dirname(__file__), 'maps', 'example_map.txt')
            if os.path.isfile(default_path):
                world_path = default_path
        if world_path and os.path.isfile(world_path):
            with open(world_path, "r", encoding="utf-8") as f:
                map_rows = [line.rstrip("\n") for line in f]
            self.world = WorldMap.from_file(world_path)
        else:
            # Fallback to procedurally generated continents using the chosen size
            width, height = constants.MAP_SIZE_PRESETS.get(
                self.map_size, constants.MAP_SIZE_PRESETS[constants.DEFAULT_MAP_SIZE]
            )
            # Generate only the first region's biomes using the new indexing
            map_rows = generate_continent_map(
                width,
                height,
                land_chance=0.55,
                smoothing_iterations=5,
                biome_chars="GFD",
            )
            self.world = WorldMap(map_data=map_rows)

            # Populate the world with additional features scaled to available land
            land_tiles = len(self.world._empty_land_tiles())
            treasure_count = max(1, land_tiles // 18)
            enemy_count = max(1, land_tiles // 18)
            self.world._place_treasures(treasure_count)
            self.world._generate_clusters(random, enemy_count)

        # Apply scenario specific data such as pre-placed units or objectives
        if self.scenario:
            scen_dir = os.path.join(repo_root, "scenarios")
            path = self.scenario
            if not os.path.isabs(path):
                path = os.path.join(scen_dir, path)
            if not path.endswith(".json"):
                path += ".json"
            try:
                self.scenario_data = load_scenario(path)
                for info in self.scenario_data.get("units", []):
                    stats = STATS_BY_NAME.get(info.get("type"))
                    if not stats:
                        continue
                    unit = Unit(stats, info.get("count", 1), owner="enemy")
                    x = info.get("x", 0)
                    y = info.get("y", 0)
                    if 0 <= y < self.world.height and 0 <= x < self.world.width:
                        tile = self.world.grid[y][x]
                        tile.enemy_units = (tile.enemy_units or []) + [unit]
                self.objectives = self.scenario_data.get("objectives", [])
            except Exception:
                self.scenario_data = {}
                self.objectives = []
        else:
            self.scenario_data = {}
            self.objectives = []

        self._rebuild_world_caches()

        # Reset pathfinding cache whenever a new map is generated or loaded
        self.invalidate_path_cache()

        # Neutral creature groups generated by the world
        self.creatures: List[CreatureAI] = list(getattr(self.world, "creatures", []))

        self.world.populate_flora(self.flora_loader)

        # Coastline overlays are now a fixed set of assets; load them all.
        self.load_additional_assets(
            [f"overlays/{img}" for img in required_coast_images()]
        )


        # Prepare renderer for terrain drawing
        self.world.init_renderer(
            self.assets, self.tile_variants, self.coast_edges, self.coast_corners
        )
            
        # Place hero at the town if available, otherwise at a random empty tile
        if self.world.hero_start:
            hx, hy = self.world.hero_start
        else:
            empty_tiles = self.world._empty_land_tiles()
            if not empty_tiles:
                # Ensure there is at least one valid spawn location
                land = [
                    (x, y)
                    for y, row in enumerate(self.world.grid)
                    for x, t in enumerate(row)
                    if (
                        (BiomeCatalog.get(t.biome).passable
                         if BiomeCatalog.get(t.biome)
                         else t.biome not in constants.IMPASSABLE_BIOMES)
                    )
                ]
                if not land:
                    land = [(0, 0)]
                    self.world.grid[0][0].biome = "scarletia_echo_plain"
                x, y = random.choice(land)
                tile = self.world.grid[y][x]
                tile.obstacle = False
                tile.treasure = None
                tile.enemy_units = None
                empty_tiles = [(x, y)]
            hx, hy = random.choice(empty_tiles)
        # Create hero with starting army
        starting_army = [
            Unit(SWORDSMAN_STATS, 22, 'hero'),
            Unit(ARCHER_STATS, 30, 'hero'),
            Unit(MAGE_STATS, 15, 'hero'),
            Unit(CAVALRY_STATS, 16, 'hero'),
            Unit(DRAGON_STATS, 5, 'hero'),
            Unit(PRIEST_STATS, 15, 'hero'),
        ]
        self.hero = Hero(
            hx,
            hy,
            starting_army,
            name=self.player_name,
            colour=self.player_colour,
            faction=self.faction,
        )
        hero_asset = self.assets.get("default_hero")
        if isinstance(hero_asset, dict):
            self.hero.portrait = hero_asset.get("portrait")
        self.hero.inventory.extend(STARTING_ARTIFACTS)
        # Quest system
        self.quest_manager = QuestManager(self)
        # Initialise vision for the starting player
        self._update_player_visibility()
        # Remember the player's starting town to detect loss later
        self.starting_town: Optional[Tuple[int, int]] = self.world.hero_town
        # Flag to avoid showing the game over screen multiple times
        self._game_over_shown = False
        # Track ownership of towns to handle victory conditions
        self._town_control_subscribed = False
        self._init_town_ownership()
        if not self._town_control_subscribed:
            EVENT_BUS.subscribe(ON_TURN_END, self._update_town_control)
            self._town_control_subscribed = True
        # High-level state container for UI widgets
        self.state = GameState(world=self.world, heroes=[self.hero])
        self.hero_idx = 0
        # ``active_actor`` tracks whichever hero or army is currently selected.
        # It defaults to the main hero and is updated via the ``ON_SELECT_HERO``
        # event whenever the user selects a different actor.
        self.active_actor: UnitCarrier = self.hero
        # Economy state mirrors world buildings and player resources
        self._econ_building_map: Dict[Building, economy.Building] = {}
        self.state.economy.players[0] = economy.PlayerEconomy()
        self.state.economy.players[1] = economy.PlayerEconomy()
        self._sync_economy_from_hero()
        for row in self.world.grid:
            for tile in row:
                if tile.building:
                    b = tile.building
                    econ_b = economy.Building(
                        id=getattr(b, "name", ""),
                        owner=getattr(b, "owner", None),
                        provides=dict(getattr(b, "income", {})),
                        growth_per_week=dict(getattr(b, "growth_per_week", {})),
                        stock=dict(getattr(b, "stock", {})),
                        level=getattr(b, "level", 1),
                        upgrade_cost=dict(getattr(b, "upgrade_cost", {})),
                        production_per_level=dict(getattr(b, "production_per_level", {})),
                    )
                    self.state.economy.buildings.append(econ_b)
                    self._econ_building_map[b] = econ_b
        # Enemy faction setup
        self.ai_player: Optional[FactionAI] = None
        self.enemy_heroes: List[EnemyHero] = []
        if self.world.enemy_town:
            ex, ey = self.world.enemy_town
            town_building = self.world.grid[ey][ex].building
            if isinstance(town_building, Town):
                self.ai_player = FactionAI(
                    town_building,
                    heroes=self.enemy_heroes,
                    economy=self.state.economy.players[1],
                )
        # Spawn the main enemy hero and sync economy
        self._spawn_enemy_heroes()
        # Select the default hero as the highest level hero available
        self.hero = max(self.state.heroes, key=lambda h: h.level)
        # Track current turn
        self.turn: int = 0
        # Prepare basic UI elements (layout calculated after main screen creation)
        # Clock for controlling frame rate
        self.clock = pygame.time.Clock()
        # Animation frame counter used for simple sprite animations
        self.anim_frame = 0
        # Zoom level for world map rendering.  Adjusted via mouse wheel as well.
        self.zoom = 1.0
        # Offset for panning the world view
        self.offset_x = 0
        self.offset_y = 0
        # Adapter exposing camera information for widgets
        self.world_renderer = _WorldView(self)
        # Drag state for mouse-driven panning
        # Queue of world coordinates to move through after a click
        self.move_queue: List[Tuple[int, int]] = []
        # Cached path for rendering movement arrows
        self.path: List[Tuple[int, int]] = []
        # Cumulative AP cost for each step in ``self.path``
        self.path_costs: List[int] = []
        self.path_target: Optional[Tuple[int, int]] = None
        # Pre-tinted arrow images used for path visualisation
        self.arrow_green: Optional[pygame.Surface] = None
        self.arrow_red: Optional[pygame.Surface] = None
        self._init_path_arrows()
        # Flag to signal returning to the main menu
        self.quit_to_menu = False
        # Available save slots (save01.json, save02.json, ...)
        base_dir = os.path.dirname(__file__)
        if self.scenario:
            scen_name = os.path.splitext(os.path.basename(self.scenario))[0]
            base_dir = os.path.join(base_dir, scen_name)
            os.makedirs(base_dir, exist_ok=True)
        self.save_slots = [os.path.join(base_dir, name) for name in SAVE_SLOT_FILES]
        self.profile_slots = [
            os.path.join(base_dir, name) for name in PROFILE_SLOT_FILES
        ]
        self.current_slot = max(0, min(self.current_slot, len(self.save_slots) - 1))
        self.default_save_path = self.save_slots[self.current_slot]
        self.default_profile_path = self.profile_slots[self.current_slot]
        # Queue of pending game events
        self.event_queue: List[Any] = []
        # Main UI screen controller
        self.main_screen = MainScreen(self)
        # The initial visibility update above occurred before the minimap was
        # constructed, so run it again now to populate fog-of-war data for the
        # newly created minimap.
        self._update_player_visibility()
        self.minimap_viewport: Optional[pygame.Rect] = None
        EVENT_BUS.subscribe(ON_CAMERA_CHANGED, self._update_minimap_viewport)
        EVENT_BUS.subscribe(ON_SELECT_HERO, self._on_select_hero)
        self.resources_bar = self.main_screen.resources_bar
        self._recalc_ui()
        # Set up initial hero selection
        panel = getattr(self.main_screen, "army_panel", None)
        if panel:
            panel.set_hero(self.hero)
        EVENT_BUS.publish(ON_SELECT_HERO, self.hero)
        self._update_minimap_viewport()

    def _recalc_ui(self) -> None:
        """Recalculate layout when the screen size changes."""

        self.main_screen.compute_layout(
            self.screen.get_width(), self.screen.get_height()
        )
        world_rect = self.main_screen.widgets.get(
            "1", pygame.Rect(0, 0, self.screen.get_width(), self.screen.get_height())
        )
        if self.world_renderer:
            self.world_renderer.surface = pygame.Surface((world_rect.width, world_rect.height))
        bottom = world_rect.y + world_rect.height
        self.ui_panel_rect = pygame.Rect(
            0,
            bottom,
            self.screen.get_width(),
            self.screen.get_height() - bottom,
        )
        self._update_minimap_viewport()

    def _update_minimap_viewport(self, *_: object) -> None:
        """Recalculate the minimap viewport rectangle."""
        minimap = getattr(self.main_screen, "minimap", None)
        rect = self.main_screen.widgets.get("4") if self.main_screen.widgets else None
        if minimap and rect:
            self.minimap_viewport = minimap.get_viewport_rect(rect)
        else:
            self.minimap_viewport = None

    def _notify(self, message: str) -> None:
        """Log ``message`` and publish it to the UI event bus."""
        logger.info(message)
        EVENT_BUS.publish(ON_INFO_MESSAGE, message)

    # ------------------------------------------------------------------ events
    def process_event_queue(self) -> None:
        """Dispatch and clear all queued game events.

        Events are simple dictionaries loaded from :mod:`events.events.json`
        and must contain a ``type`` key.  The registry defined in
        :mod:`events` maps these type strings to handler functions.
        """
        while self.event_queue:
            evt = self.event_queue.pop(0)
            try:
                dispatch_event(self, evt)
            except KeyError:
                logger.warning("Unknown event type: %s", evt.get("type"))

    def load_assets(self) -> None:
        """Load all images referenced in constants.  If a file is missing, skip it."""
        # Build a mapping of relative path -> full path by walking all
        # directories known to the asset manager.  Paths earlier in
        # ``search_paths`` take precedence, ensuring externally supplied assets
        # override those bundled with the repository.
        search_dirs = list(self.assets.search_paths)
        asset_paths: dict[str, str] = {}
        for directory in search_dirs:
            for root, _, files in os.walk(directory):
                for filename in files:
                    rel = os.path.relpath(os.path.join(root, filename), directory).replace(
                        os.sep, "/"
                    )
                    # Store paths using lowercase keys to make lookups
                    # case-insensitive across different filesystems
                    asset_paths.setdefault(rel.lower(), os.path.join(root, filename))
        self._asset_paths = asset_paths

        repo_root = self.ctx.repo_root
        
        base_images = [
            imgs[0] if isinstance(imgs, list) else imgs
            for imgs in constants.BIOME_BASE_IMAGES.values()
        ]
        grass_img = constants.BIOME_BASE_IMAGES.get("grass")
        if isinstance(grass_img, list):
            grass_img = grass_img[0]

        for img_name in base_images + [
            constants.IMG_OBSTACLE,
            constants.IMG_TREASURE,
            constants.IMG_HERO_PORTRAIT,
            constants.IMG_SKILL_COMBAT,
            constants.IMG_SKILL_MAGIC,

        ] + list(ARTIFACT_ICONS.values()):
            # Look up image paths using normalised lowercase keys for robustness
            key = img_name.replace(os.sep, "/").lower()
            path = asset_paths.get(key)
            if path and os.path.isfile(path):
                try:
                    image = pygame.image.load(path).convert_alpha()
                    # Resize images to tile sizes if needed
                    if img_name == grass_img:
                        # Grass tile used in both world and combat; keep pixels crisp
                        image = scale_surface(
                            image, (constants.TILE_SIZE, constants.TILE_SIZE), smooth=False
                        )
                    elif img_name in base_images:
                        # Base tiles used in both world and combat; pre-scale to tile size
                        image = pygame.transform.scale(
                            image, (constants.TILE_SIZE, constants.TILE_SIZE)
                        )
                    elif img_name in (
                        constants.IMG_OBSTACLE,
                        constants.IMG_TREASURE,
                    ):
                        # Map tiles are pixel art
                        image = scale_surface(
                            image, (constants.TILE_SIZE, constants.TILE_SIZE), smooth=False
                        )
                    self.assets[img_name] = image
                except Exception:
                    # If loading fails, ignore the image
                    pass
            else:
                # File not found; skip
                pass

        # Load legacy terrain tiles for backwards compatibility
        load_manifest(
            repo_root,
            os.path.join("assets", "terrain", "legacy.json"),
            self.assets,
        )

        # Load visual effects declared in assets/vfx/vfx.json
        load_manifest(
            repo_root,
            os.path.join("assets", "vfx", "vfx.json"),
            self.assets,
        )

        # Load artifact icons declared in assets/artifacts.json
        self.artifacts_manifest = load_artifact_manifest(repo_root, self.assets)

        # Load unit and creature sprites declared in assets/units/*.json
        self.unit_shadow_baked: Dict[str, bool] = {}
        for fname in ["units.json", "creatures.json"]:
            manifest_path = os.path.join(repo_root, "assets", "units", fname)
            if not os.path.isfile(manifest_path):
                continue
            try:
                with open(manifest_path, "r", encoding="utf-8") as f:
                    entries = json.load(f)
            except Exception:
                continue
            for entry in entries:
                try:
                    self.unit_shadow_baked[entry["id"]] = bool(entry.get("shadow_baked", False))
                    surf = self.assets.get(entry["image"])
                    surf = scale_surface(
                        surf,
                        (constants.COMBAT_TILE_SIZE, constants.COMBAT_TILE_SIZE),
                        smooth=True,
                    )
                    self.assets[entry["id"]] = surf
                except Exception:
                    continue

        # Load hero portraits and map icons declared in assets/units/heroes.json
        heroes_path = os.path.join(repo_root, "assets", "units", "heroes.json")
        if os.path.isfile(heroes_path):
            try:
                with open(heroes_path, "r", encoding="utf-8") as f:
                    entries = json.load(f)
                for entry in entries:
                    try:
                        portrait = self.assets.get(entry.get("portrait", ""))
                        icon_info = entry.get("icon", {})
                        icon_surf = self.assets.get(icon_info.get("image", ""))
                        size = icon_info.get("scale", constants.TILE_SIZE)
                        icon_surf = scale_surface(icon_surf, (size, size), smooth=True)
                        self.assets[entry["id"]] = {
                            "portrait": portrait,
                            "icon": {
                                "surface": icon_surf,
                                "anchor": tuple(icon_info.get("anchor", (0, 0))),
                            },
                        }
                    except Exception:
                        continue
            except Exception:
                pass

        # Load resource icons declared in assets/resources/resources.json
        resources_path = os.path.join(
            repo_root, "assets", "resources", "resources.json"
        )
        self.resource_defs: Dict[str, ResourceDef] = load_resources(
            resources_path, self.assets, constants.TILE_SIZE
        )

        # Load building sprites declared in the building manifest
        for asset in BUILDINGS.values():
            try:
                surf, scale = get_surface(asset, self.assets, constants.TILE_SIZE)
            except Exception:
                continue

            path = asset.file_list()[0]
            name, _ = os.path.splitext(path)

            if surf is self.assets._fallback:
                msg = f"Missing building asset {path} for {asset.id}"
                if os.environ.get("FG_DEBUG_ASSETS"):
                    raise FileNotFoundError(msg)
                logger.warning(msg)

            self.assets[asset.id] = surf
            self.assets[path] = surf
            self.assets[name] = surf
            asset.scale = scale

        # Discover tile variants and coastline overlays
        tile_variants: Dict[str, List[str]] = {
            biome: (names if isinstance(names, list) else [names])
            for biome, names in constants.BIOME_BASE_IMAGES.items()
        }
        variant_files: List[str] = [
            fname for files in tile_variants.values() for fname in files
        ]

        coast_edges: Dict[str, str] = {
            d: f"overlays/mask_{d}.png" for d in ("n", "e", "s", "w")
        }
        coast_corners: Dict[str, str] = {
            c: f"overlays/mask_{c}.png" for c in ("ne", "nw", "se", "sw")
        }
        overlay_files: List[str] = list(coast_edges.values()) + list(
            coast_corners.values()
        )

        if variant_files or overlay_files:
            self.load_additional_assets(variant_files + overlay_files)

        self.tile_variants = tile_variants
        self.coast_edges = coast_edges
        self.coast_corners = coast_corners

        # Load overlay sprites declared in assets/overlays/overlays.json
        overlays_path = os.path.join(
            repo_root, "assets", "overlays", "overlays.json"
        )
        if os.path.isfile(overlays_path):
            try:
                with open(overlays_path, "r", encoding="utf-8") as f:
                    entries = json.load(f)
                overlay_files = [e.get("image") for e in entries if e.get("image")]
                if overlay_files:
                    self.load_additional_assets(overlay_files)
                for entry in entries:
                    oid = entry.get("id")
                    img = entry.get("image")
                    if not oid or not img:
                        continue
                    surf = self.assets.get(img)
                    if surf:
                        if oid in {
                            "highlight",
                            "active_unit",
                            "melee_range",
                            "ranged_range",
                        }:
                            surf = scale_surface(
                                surf,
                                (
                                    constants.COMBAT_TILE_SIZE,
                                    constants.COMBAT_TILE_SIZE,
                                ),
                                smooth=True,
                            )
                        self.assets[oid] = surf
            except Exception:
                pass

        # Load unit sprites from a combined sprite sheet if available
        sheet_path = asset_paths.get("units.png")
        if sheet_path and os.path.isfile(sheet_path):
            try:
                frames = load_sprite_sheet(sheet_path, constants.COMBAT_TILE_SIZE, constants.COMBAT_TILE_SIZE)
                self.assets["units"] = frames
                # Map unit names to frame indices
                self.assets["unit_frames"] = {
                    "swordsman": (0, 0),
                    "archer": (1, 1),
                    "mage": (2, 2),
                }
            except Exception:
                pass


    def load_additional_assets(self, filenames: List[str]) -> None:
        """Load extra image files into ``self.assets``.

        Filenames are looked up in the previously discovered asset paths and
        scaled to the standard tile size.  Missing files are silently ignored
        to keep asset loading robust in constrained environments.
        """
        for img_name in filenames:
            # Asset paths are stored with normalised lowercase keys
            key = img_name.replace(os.sep, "/").lower()
            path = (
                self._asset_paths.get(key)
                if hasattr(self, "_asset_paths")
                else None
            )
            if path and os.path.isfile(path):
                try:
                    image = pygame.image.load(path).convert_alpha()
                    image, _ = scale_with_anchor(
                        image, (constants.TILE_SIZE, constants.TILE_SIZE), smooth=False
                    )
                    self.assets[img_name] = image
                    continue
                except Exception:
                    pass
            # If file missing or loading failed, store a placeholder surface so
            # callers can still reference the image by name.
            try:
                placeholder = pygame.Surface(
                    (constants.TILE_SIZE, constants.TILE_SIZE), pygame.SRCALPHA
                )
            except Exception:
                placeholder = None
            self.assets[img_name] = placeholder


    # ------------------------------------------------------------------
    # Movement and path handling
    # ------------------------------------------------------------------
    def _init_path_arrows(self) -> None:
        """Prepare tinted arrow surfaces for path visualisation."""
        base = self.assets.get("move_arrow")
        if base:
            try:
                w, h = base.get_size()
                scale = (constants.TILE_SIZE * 0.6) / max(w, h)
                new_w = max(1, int(w * scale))
                new_h = max(1, int(h * scale))
                scaled = pygame.transform.scale(base, (new_w, new_h))
                canvas = pygame.Surface((constants.TILE_SIZE, constants.TILE_SIZE), pygame.SRCALPHA)
                canvas.blit(
                    scaled,
                    ((constants.TILE_SIZE - new_w) // 2, (constants.TILE_SIZE - new_h) // 2),
                )
                base = canvas
            except Exception:
                base = None
        if not base:
            base = pygame.Surface((constants.TILE_SIZE, constants.TILE_SIZE), pygame.SRCALPHA)
            if hasattr(pygame.draw, "polygon"):
                pygame.draw.polygon(
                    base,
                    (255, 255, 255),
                    [
                        (constants.TILE_SIZE // 4, constants.TILE_SIZE // 2),
                        (constants.TILE_SIZE * 3 // 4, constants.TILE_SIZE // 4),
                        (constants.TILE_SIZE * 3 // 4, constants.TILE_SIZE * 3 // 4),
                    ],
                )
            else:
                base.fill((255, 255, 255))
        if not hasattr(base, "copy"):
            self.arrow_green = base
            self.arrow_red = base
            return
        # Green arrow
        green = base.copy()
        try:
            green.fill((0, 255, 0, 255), special_flags=pygame.BLEND_RGBA_MULT)
        except Exception:
            pass
        self.arrow_green = green
        # Red arrow
        red = base.copy()
        try:
            red.fill((255, 0, 0, 255), special_flags=pygame.BLEND_RGBA_MULT)
        except Exception:
            pass
        self.arrow_red = red

    def _draw_hero_sprite(self, surface: pygame.Surface, pos: Tuple[int, int]) -> None:
        """Draw the hero sprite at ``pos`` on ``surface``."""
        hx, hy = pos
        hero = self.assets.get("default_hero")
        if isinstance(hero, dict):
            # New hero assets store the world-map icon under the "icon" key;
            # older assets may still provide a direct surface/anchor pair.
            icon = hero.get("icon") if isinstance(hero.get("icon"), dict) else None
            if icon and isinstance(icon.get("surface"), pygame.Surface):
                surf = icon["surface"]
                ax, ay = icon.get("anchor", (0, 0))
                surface.blit(
                    surf, (hx * constants.TILE_SIZE - ax, hy * constants.TILE_SIZE - ay)
                )
                return
            if "surface" in hero and "anchor" in hero:
                surf, (ax, ay) = hero["surface"], hero["anchor"]
                surface.blit(
                    surf, (hx * constants.TILE_SIZE - ax, hy * constants.TILE_SIZE - ay)
                )
                return
        pygame.draw.circle(
            surface,
            self.player_colour,
            (
                hx * constants.TILE_SIZE + constants.TILE_SIZE // 2,
                hy * constants.TILE_SIZE + constants.TILE_SIZE // 2,
            ),
            constants.TILE_SIZE // 3,
        )

    def invalidate_path_cache(self) -> None:
        """Clear cached paths. Should be called when the map changes."""
        try:
            self._compute_path_cached.cache_clear()  # type: ignore[attr-defined]
        except AttributeError:
            pass

    def _pathfinding_state_key(self) -> Tuple[Tuple[int, int], ...]:
        """Return a hashable representation of units affecting pathfinding."""
        positions: Set[Tuple[int, int]] = set()
        hero = getattr(self, "hero", None)
        if hero:
            positions.add((hero.x, hero.y))
        state = getattr(self, "state", None)
        if state:
            positions.update((h.x, h.y) for h in getattr(state, "heroes", []))
        positions.update((a.x, a.y) for a in getattr(self.world, "player_armies", []))
        positions.update((e.x, e.y) for e in self.enemy_heroes)
        for y, row in enumerate(self.world.grid):
            for x, tile in enumerate(row):
                if tile.enemy_units:
                    positions.add((x, y))
        return tuple(sorted(positions))

    @lru_cache(maxsize=256)
    def _compute_path_cached(
        self,
        start: Tuple[int, int],
        goal: Tuple[int, int],
        avoid_enemies: bool = True,
        frontier_limit: Optional[int] = None,
        state_key: Tuple[Tuple[int, int], ...] = (),
    ) -> Optional[Tuple[Tuple[int, int], ...]]:
        """Internal A* search returning a tuple of path coordinates."""
        if start == goal:
            return ()

        frontier: List[Tuple[int, Tuple[int, int]]] = [(0, start)]
        came_from: Dict[Tuple[int, int], Optional[Tuple[int, int]]] = {start: None}
        cost_so_far: Dict[Tuple[int, int], int] = {start: 0}
        actor = getattr(self, "active_actor", getattr(self, "hero", None))

        while frontier:
            _, (x, y) = heapq.heappop(frontier)
            if (x, y) == goal:
                break
            for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                nx, ny = x + dx, y + dy
                if not self.world.in_bounds(nx, ny):
                    continue
                tile = self.world.grid[ny][nx]
                if not tile.is_passable() and (nx, ny) != goal:
                    continue
                if (nx, ny) != goal:
                    # Avoid stepping onto friendly units or heroes
                    occupied = False
                    if isinstance(actor, Hero):
                        state = getattr(self, "state", None)
                        if state and any(
                            h is not actor and h.x == nx and h.y == ny
                            for h in getattr(state, "heroes", [])
                        ):
                            occupied = True
                        if any(
                            a.x == nx and a.y == ny
                            for a in getattr(self.world, "player_armies", [])
                        ):
                            occupied = True
                    else:
                        if (
                            getattr(self, "hero", None)
                            and self.hero is not actor
                            and self.hero.x == nx
                            and self.hero.y == ny
                        ):
                            occupied = True
                        if any(
                            a is not actor and a.x == nx and a.y == ny
                            for a in getattr(self.world, "player_armies", [])
                        ):
                            occupied = True
                    if occupied:
                        continue
                if avoid_enemies and (nx, ny) != goal:
                    if tile.enemy_units:
                        continue
                    if any(e.x == nx and e.y == ny for e in self.enemy_heroes):
                        continue
                biome = BiomeCatalog.get(tile.biome)
                if getattr(tile, "road", False):
                    step_cost = constants.ROAD_COST
                else:
                    step_cost = biome.terrain_cost if biome else 1
                new_cost = cost_so_far[(x, y)] + step_cost
                if (nx, ny) not in cost_so_far or new_cost < cost_so_far[(nx, ny)]:
                    cost_so_far[(nx, ny)] = new_cost
                    priority = new_cost + heuristic((nx, ny), goal)
                    heapq.heappush(frontier, (priority, (nx, ny)))
                    if frontier_limit is not None and len(frontier) > frontier_limit:
                        return None
                    came_from[(nx, ny)] = (x, y)
        else:
            return None

        path: List[Tuple[int, int]] = []
        cur = goal
        while cur != start:
            path.append(cur)
            cur = came_from.get(cur)
            if cur is None:
                return None
        path.reverse()
        return tuple(path)

    def compute_path(
        self,
        start: Tuple[int, int],
        goal: Tuple[int, int],
        avoid_enemies: bool = True,
        frontier_limit: Optional[int] = None,
    ) -> Optional[List[Tuple[int, int]]]:
        """Compute a path using the A* algorithm.

        When ``avoid_enemies`` is ``True`` tiles occupied by enemy stacks or
        enemy heroes are treated as impassable unless they are the goal tile.
        Movement cost is derived from the destination tile's biome.
        ``frontier_limit`` limits the search space to avoid endless searches.
        """
        state_key = self._pathfinding_state_key()
        result = self._compute_path_cached(
            start, goal, avoid_enemies, frontier_limit, state_key
        )
        return list(result) if result is not None else None

    def handle_world_click(self, pos: Tuple[int, int]) -> None:
        """Convert a screen click into a world path and enqueue movement."""
        world_rect = None
        if hasattr(self, "main_screen") and self.main_screen.widgets:
            world_rect = self.main_screen.widgets.get("1")
        if world_rect:
            if not world_rect.collidepoint(pos):
                return
        else:
            if pos[1] >= getattr(self.ui_panel_rect, "y", 0):
                return
        mx = int(
            (pos[0] - (world_rect.x if world_rect else 0) - self.offset_x)
            / (constants.TILE_SIZE * self.zoom)
        )
        my = int(
            (pos[1] - (world_rect.y if world_rect else 0) - self.offset_y)
            / (constants.TILE_SIZE * self.zoom)
        )
        if not self.world.in_bounds(mx, my):
            return
        def calc_costs(p: List[Tuple[int, int]]) -> List[int]:
            costs: List[int] = []
            total = 0
            for x, y in p:
                tile = self.world.grid[y][x]
                biome = BiomeCatalog.get(tile.biome)
                if getattr(tile, "road", False):
                    step_cost = constants.ROAD_COST
                else:
                    step_cost = biome.terrain_cost if biome else 1
                total += step_cost
                costs.append(total)
            return costs

        actor = getattr(self, "active_actor", self.hero)
        if self.path and not self.move_queue and self.path_target == (mx, my):
            path = self.compute_path((actor.x, actor.y), (mx, my))
            if path is None:
                path = self.compute_path((actor.x, actor.y), (mx, my), avoid_enemies=False)
            if path is None:
                self.move_queue = []
                self.path = []
                self.path_costs = []
                self.path_target = None
            else:
                self.path = path
                self.path_costs = calc_costs(path)
                self.move_queue = path.copy()
            return
        path = self.compute_path((actor.x, actor.y), (mx, my))
        if path is None:
            path = self.compute_path((actor.x, actor.y), (mx, my), avoid_enemies=False)
        if path is None:
            self.move_queue = []
            self.path = []
            self.path_costs = []
            self.path_target = None
        else:
            self.move_queue = []
            self.path = path
            self.path_costs = calc_costs(path)
            self.path_target = (mx, my)

    def hover_probe(self, x: int, y: int) -> Optional[Tuple[str, str]]:
        """Return information about the world element under the cursor.

        The result is a tuple ``(name, type)`` where ``type`` is one of
        ``"enemy"``, ``"building"``, ``"treasure"``, ``"resource"`` or
        ``"tile"``.  ``None`` is returned if the position is outside the world
        view.
        """
        world_rect = None
        if hasattr(self, "main_screen") and self.main_screen.widgets:
            world_rect = self.main_screen.widgets.get("1")
        if world_rect:
            if not world_rect.collidepoint((x, y)):
                return None
        else:
            if y >= getattr(self.ui_panel_rect, "y", 0):
                return None
        mx = int(
            (x - (world_rect.x if world_rect else 0) - self.offset_x)
            / (constants.TILE_SIZE * self.zoom)
        )
        my = int(
            (y - (world_rect.y if world_rect else 0) - self.offset_y)
            / (constants.TILE_SIZE * self.zoom)
        )
        if not self.world.in_bounds(mx, my):
            return None
        tile = self.world.grid[my][mx]
        if tile.building:
            return tile.building.name, "building"
        if tile.enemy_units:
            strongest = max(tile.enemy_units, key=lambda u: u.stats.max_hp)
            return strongest.stats.name, "enemy"
        if tile.treasure is not None:
            return "Treasure", "treasure"
        if tile.resource:
            return tile.resource.capitalize(), "resource"
        return tile.biome.capitalize(), "tile"

    def update_movement(self) -> None:
        """Advance hero movement along the queued path."""
        actor = getattr(self, "active_actor", self.hero)
        if not self.move_queue or actor.ap <= 0:
            return
        nx, ny = self.move_queue[0]
        dx = nx - actor.x
        dy = ny - actor.y
        self.try_move_hero(dx, dy)
        if (actor.x, actor.y) == (nx, ny):
            self.move_queue.pop(0)
            if self.path:
                self.path.pop(0)
            if self.path_costs:
                self.path_costs.pop(0)
        else:
            # Movement blocked
            self.move_queue = []
            self.path = []
            self.path_costs = []
        if not self.move_queue and not self.path:
            self.path_target = None



    def run(self) -> None:
        """Main game loop handling exploration and combat."""
        self.quit_to_menu = False
        running = True
        while running and not self.quit_to_menu:
            self._check_starting_town_owner()
            for event in pygame.event.get():
                # Allow the UI controller to handle common interactions first
                if self.main_screen.handle_event(event):
                    continue

                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        quit_to_menu, self.screen = self.open_pause_menu()
                        if quit_to_menu:
                            self.quit_to_menu = True
                    elif event.key in (pygame.K_UP, pygame.K_w):
                        self.try_move_hero(0, -1)
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        self.try_move_hero(0, 1)
                    elif event.key in (pygame.K_LEFT, pygame.K_a):
                        self.try_move_hero(-1, 0)
                    elif event.key in (pygame.K_RIGHT, pygame.K_d):
                        self.try_move_hero(1, 0)
                    elif event.key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
                        # Zoom in via keyboard
                        self._adjust_zoom(
                            0.25,
                            (
                                self.screen.get_width() // 2,
                                self.screen.get_height() // 2,
                            ),
                        )
                    elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                        # Zoom out via keyboard
                        self._adjust_zoom(
                            -0.25,
                            (
                                self.screen.get_width() // 2,
                                self.screen.get_height() // 2,
                            ),
                        )
                    elif event.key == pygame.K_t:
                        # End turn and reset action points
                        self.end_turn()
                    elif event.key == pygame.K_h:
                        # Heal ability
                        self.hero_heal()
                    elif event.key == pygame.K_F5:
                        # Quick save
                        self.save_game(
                            self.default_save_path, self.default_profile_path
                        )
                    elif event.key == pygame.K_F9:
                        # Quick load
                        self.load_game(
                            self.default_save_path, self.default_profile_path
                        )
                    elif event.key == pygame.K_i:
                        # Open hero inventory and skill tree
                        if self.show_inventory():
                            self.quit_to_menu = True
                    elif event.key == pygame.K_u:
                        self.open_town()
                    elif event.key == pygame.K_1:
                        self.hero.choose_skill('strength')
                    elif event.key == pygame.K_2:
                        self.hero.choose_skill('wisdom')
                    elif event.key == pygame.K_3:
                        self.hero.choose_skill('tactics')
                    elif event.key == pygame.K_4:
                        self.hero.choose_skill('logistics')
                    elif event.key == pygame.K_F11:
                        pygame.display.toggle_fullscreen()
                        self.screen = pygame.display.get_surface()
                        self._recalc_ui()

                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button in (1, 2):
                        self.handle_world_click(event.pos)
            # Advance queued movement then draw world
            self.update_movement()
            self.screen.fill(theme.PALETTE["background"])
            dirty = [self.draw_world(self.anim_frame)]
            # Overlay generic UI panels and collect their dirty rects
            dirty.extend(self.main_screen.draw(self.screen))
            pygame.display.update(dirty)
            dt = self.clock.tick(constants.FPS) / 1000.0
            self.main_screen.turn_bar.update(dt)
            self.anim_frame = (self.anim_frame + 1) % 60
        if not self.quit_to_menu:
            pygame.quit()

    def _adjust_zoom(self, delta: float, pivot: Tuple[int, int]) -> None:
        """Change zoom level keeping a pivot point stable."""
        old_zoom = self.zoom
        self.zoom = max(0.5, min(2.0, self.zoom + delta))
        if self.zoom == old_zoom:
            return
        px, py = pivot
        # Reposition offset so that the zoom occurs around the pivot
        scale = self.zoom / old_zoom
        self.offset_x = px - (px - self.offset_x) * scale
        self.offset_y = py - (py - self.offset_y) * scale
        world_rect = None
        if hasattr(self, "main_screen") and self.main_screen.widgets:
            world_rect = self.main_screen.widgets.get("1")
        if world_rect:
            self._clamp_offset(world_rect)
        EVENT_BUS.publish(ON_CAMERA_CHANGED, self.offset_x, self.offset_y, self.zoom)

    def _clamp_offset(self, world_rect: pygame.Rect) -> None:
        """Keep the camera offset within the bounds of ``world_rect``."""
        map_w = int(self.world.width * constants.TILE_SIZE * self.zoom)
        map_h = int(self.world.height * constants.TILE_SIZE * self.zoom)
        min_x = min(world_rect.width - map_w, 0)
        min_y = min(world_rect.height - map_h, 0)
        self.offset_x = max(min(self.offset_x, 0), min_x)
        self.offset_y = max(min(self.offset_y, 0), min_y)

    def _check_starting_town_owner(self) -> None:
        """Show game over screen if the starting town changes owner."""
        if getattr(self, "_game_over_shown", False):
            return
        start = getattr(self, "starting_town", None)
        if not start:
            return
        x, y = start
        tile = self.world.grid[y][x]
        town = tile.building
        if isinstance(town, Town) and town.owner != 0:
            self._game_over_shown = True
            self._show_game_over()

    def _show_game_over(self) -> None:
        """Display a simple game over summary and return to the main menu."""
        heading_font = theme.get_font(48) or pygame.font.SysFont(None, 48)
        font = theme.get_font(24) or pygame.font.SysFont(None, 24)
        ok_rect = pygame.Rect(
            self.screen.get_width() // 2 - 40, self.screen.get_height() - 60, 80, 40
        )
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.quit_to_menu = True
                    return
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if ok_rect.collidepoint(event.pos):
                        from ui.menu import main_menu

                        self.screen = main_menu(self.screen)
                        self.quit_to_menu = True
                        return
            self.screen.fill(theme.PALETTE["background"])
            heading = heading_font.render("Game Over", True, theme.PALETTE["text"])
            self.screen.blit(
                heading,
                heading.get_rect(center=(self.screen.get_width() // 2, 40)),
            )
            lines = [
                f"Jours joués : {getattr(self, 'turn', 0)}",
                f"Niveau du héros : {self.hero.level}",
            ]
            for i, line in enumerate(lines):
                surf = font.render(line, True, theme.PALETTE["text"])
                self.screen.blit(
                    surf,
                    surf.get_rect(
                        center=(self.screen.get_width() // 2, 80 + i * 30)
                    ),
                )
            pygame.draw.rect(self.screen, theme.PALETTE["accent"], ok_rect)
            pygame.draw.rect(
                self.screen, theme.PALETTE["text"], ok_rect, theme.FRAME_WIDTH
            )
            ok_txt = font.render("OK", True, theme.PALETTE["text"])
            self.screen.blit(ok_txt, ok_txt.get_rect(center=ok_rect.center))
            pygame.display.flip()

    def _show_victory(self) -> None:
        """Display a simple victory summary and return to the main menu."""
        heading_font = theme.get_font(48) or pygame.font.SysFont(None, 48)
        font = theme.get_font(24) or pygame.font.SysFont(None, 24)
        ok_rect = pygame.Rect(
            self.screen.get_width() // 2 - 40, self.screen.get_height() - 60, 80, 40
        )
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.quit_to_menu = True
                    return
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if ok_rect.collidepoint(event.pos):
                        from ui.menu import main_menu

                        self.screen = main_menu(self.screen)
                        self.quit_to_menu = True
                        return
            self.screen.fill(theme.PALETTE["background"])
            heading = heading_font.render("Victory!", True, theme.PALETTE["text"])
            self.screen.blit(
                heading,
                heading.get_rect(center=(self.screen.get_width() // 2, 40)),
            )
            lines = [
                f"Jours joués : {getattr(self, 'turn', 0)}",
                f"Niveau du héros : {self.hero.level}",
            ]
            for i, line in enumerate(lines):
                surf = font.render(line, True, theme.PALETTE["text"])
                self.screen.blit(
                    surf,
                    surf.get_rect(
                        center=(self.screen.get_width() // 2, 80 + i * 30)
                    ),
                )
            pygame.draw.rect(self.screen, theme.PALETTE["accent"], ok_rect)
            pygame.draw.rect(
                self.screen, theme.PALETTE["text"], ok_rect, theme.FRAME_WIDTH
            )
            ok_txt = font.render("OK", True, theme.PALETTE["text"])
            self.screen.blit(ok_txt, ok_txt.get_rect(center=ok_rect.center))
            pygame.display.flip()

    def _init_town_ownership(self) -> None:
        """Initialise ownership tracking for all towns on the map."""
        towns_attr = getattr(self.world, "towns", None)
        towns = towns_attr() if callable(towns_attr) else towns_attr
        self._initial_town_owners = (
            {t: getattr(t, "owner", None) for t in towns} if towns else {}
        )
        self._enemy_town_counters = {
            t: 0 for t, owner in self._initial_town_owners.items() if owner != 0
        }
        self._victory_shown = False

    def _update_town_control(self, *_: object) -> None:
        """Increment or reset control counters for enemy towns and check victory."""
        if not getattr(self, "_enemy_town_counters", None) or self._victory_shown:
            return
        for town in self._enemy_town_counters:
            if town.owner == 0:
                self._enemy_town_counters[town] += 1
            else:
                self._enemy_town_counters[town] = 0
        if self._enemy_town_counters and all(
            count >= 7 for count in self._enemy_town_counters.values()
        ):
            self._victory_shown = True
            self._show_victory()

    def _on_select_hero(self, hero: UnitCarrier) -> None:
        """Update internal state when a hero or army is selected."""

        # Track the active actor separately from the roster hero so that
        # selecting an army does not disturb hero cycling logic.
        self.active_actor = hero
        if isinstance(hero, Hero) and hero in getattr(self.state, "heroes", []):
            self.hero = hero
            self.hero_idx = self.state.heroes.index(hero)
        panel = getattr(self.main_screen, "army_panel", None)
        if panel:
            try:
                panel.set_hero(hero)
            except Exception:
                pass
        # Clear any queued movement so paths don't transfer between actors
        self.move_queue = []
        self.path = []
        self.path_costs = []
        self.path_target = None
        self._publish_resources()

    def _publish_resources(self) -> None:
        """Broadcast the player's current resources."""
        res_dict = getattr(self.hero, "resources", {})
        for key in ("wood", "stone", "crystal"):
            res_dict.setdefault(key, 0)
        if not hasattr(self.hero, "resources"):
            self.hero.resources = res_dict  # type: ignore[attr-defined]
        res = PlayerResources(
            gold=getattr(self.hero, "gold", 0),
            wood=res_dict["wood"],
            stone=res_dict["stone"],
            crystal=res_dict["crystal"],
        )
        EVENT_BUS.publish(ON_RESOURCES_CHANGED, res)
        bar = getattr(self, "resources_bar", None)
        if bar:
            bar.set_resources(res)

    def _sync_economy_from_hero(self) -> None:
        """Copy the hero's current resources into the economy state."""
        if not hasattr(self, "state") or not hasattr(self.state, "economy"):
            return
        pe = self.state.economy.players.setdefault(0, economy.PlayerEconomy())
        pe.resources["gold"] = getattr(self.hero, "gold", 0)
        for res in ("wood", "stone", "crystal"):
            pe.resources[res] = self.hero.resources.get(res, 0)

    def _sync_hero_from_economy(self) -> None:
        """Update the hero's resources from the economy state."""
        if not hasattr(self, "state") or not hasattr(self.state, "economy"):
            return
        pe = self.state.economy.players.get(0)
        if not pe:
            return
        self.hero.gold = pe.resources.get("gold", 0)
        for res in ("wood", "stone", "crystal"):
            self.hero.resources[res] = pe.resources.get(res, 0)

    def _is_tile_free(self, x: int, y: int) -> bool:
        """Return ``True`` if tile ``(x, y)`` has no blocking features or units."""
        if not hasattr(self, "world"):
            return False
        tile = self.world.grid[y][x]
        if not tile.is_passable():
            return False
        if (
            tile.obstacle
            or tile.treasure is not None
            or tile.enemy_units is not None
            or tile.resource is not None
            or tile.building is not None
        ):
            return False
        if hasattr(self, "hero") and (self.hero.x, self.hero.y) == (x, y):
            return False
        for enemy in getattr(self, "enemy_heroes", []):
            if (enemy.x, enemy.y) == (x, y):
                return False
        for army in getattr(getattr(self, "world", None), "player_armies", []):
            if (army.x, army.y) == (x, y):
                return False
        return True

    def _update_caches_for_tile(self, x: int, y: int) -> None:
        """Update cached tile lists after a change at ``(x, y)``."""
        if not hasattr(self, "world"):
            return
        tile = self.world.grid[y][x]
        if not hasattr(self, "resource_tiles"):
            self.resource_tiles = set()
        if tile.resource:
            self.resource_tiles.add((x, y))
        else:
            self.resource_tiles.discard((x, y))

        if not hasattr(self, "treasure_tiles"):
            self.treasure_tiles = set()
        if tile.treasure is not None:
            self.treasure_tiles.add((x, y))
        else:
            self.treasure_tiles.discard((x, y))

        if not hasattr(self, "neutral_buildings"):
            self.neutral_buildings = set()
        if tile.building and getattr(tile.building, "owner", None) != 1:
            self.neutral_buildings.add((x, y))
        else:
            self.neutral_buildings.discard((x, y))

        if not hasattr(self, "free_tiles"):
            self.free_tiles = set()
        if self._is_tile_free(x, y):
            self.free_tiles.add((x, y))
        else:
            self.free_tiles.discard((x, y))

    def _rebuild_world_caches(self) -> None:
        """Recompute lists of resources, treasures, buildings and free tiles."""
        self.resource_tiles: Set[Tuple[int, int]] = set()
        self.neutral_buildings: Set[Tuple[int, int]] = set()
        self.treasure_tiles: Set[Tuple[int, int]] = set()
        self.free_tiles: Set[Tuple[int, int]] = set()
        if not hasattr(self, "world"):
            return
        for y, row in enumerate(self.world.grid):
            for x, _ in enumerate(row):
                self._update_caches_for_tile(x, y)

    def add_hero(self, hero: Hero) -> None:
        """Add a new hero to the player's roster."""
        self.state.heroes.append(hero)
        if hasattr(self, "main_screen"):
            self.main_screen.hero_list.set_heroes(self.state.heroes)
        self._update_player_visibility()

    def select_hero(self, hero: Hero) -> None:
        """Select ``hero`` as the active hero and publish the event."""

        EVENT_BUS.publish(ON_SELECT_HERO, hero)

    def try_move_hero(self, dx: int, dy: int) -> None:
        """Move the currently selected actor (hero or army)."""

        actor = getattr(self, "active_actor", self.hero)
        if isinstance(actor, Hero):
            self._try_move_hero(dx, dy)
        else:
            self._try_move_army(dx, dy, actor)
        self._cleanup_armies()

    def _try_move_army(self, dx: int, dy: int, actor: Army) -> None:
        """Movement logic for independent armies."""

        if actor.ap <= 0:
            self._notify("No action points left. End your turn to restore them (press T).")
            return
        nx, ny = actor.x + dx, actor.y + dy
        if not self.world.in_bounds(nx, ny):
            return
        # Check collisions with hero or allied armies
        if nx == getattr(self.hero, "x", -1) and ny == getattr(self.hero, "y", -1):
            current = self.hero
            self.hero = actor  # type: ignore[assignment]
            self.open_hero_exchange(current)
            self.hero = current  # type: ignore[assignment]
            return
        for other in getattr(self.world, "player_armies", []):
            if other is not actor and other.x == nx and other.y == ny:
                current = self.hero
                self.hero = actor  # type: ignore[assignment]
                self.open_hero_exchange(other)
                self.hero = current  # type: ignore[assignment]
                return
        tile = self.world.grid[ny][nx]
        biome = BiomeCatalog.get(tile.biome)
        step_cost = constants.ROAD_COST if getattr(tile, "road", False) else (
            biome.terrain_cost if biome else 1
        )
        if actor.ap < step_cost:
            return
        if tile.building and isinstance(tile.building, Town) and not tile.building.passable:
            actor.ap -= step_cost
            econ_state = getattr(self.state, "economy", None) if hasattr(self, "state") else None
            econ_b = getattr(self, "_econ_building_map", {}).get(tile.building)
            if self._capture_tile(nx, ny, tile, self.hero, 0, econ_state, econ_b):
                self._publish_resources()
            self.open_town(tile.building, actor, town_pos=(nx, ny))
            return
        if not tile.is_passable():
            return
        prev_x, prev_y = actor.x, actor.y
        actor.x, actor.y = nx, ny
        actor.ap -= step_cost
        # Enemy encounter
        if tile.enemy_units:
            if not getattr(self, "screen", None):
                hero_wins, _, heroes, enemies = auto_resolve.resolve(actor.units, tile.enemy_units)
                for unit, res in zip(actor.units, heroes):
                    unit.count = res.count
                    unit.current_hp = res.current_hp
                actor.units[:] = [u for u in actor.units if u.count > 0]
                if hero_wins:
                    tile.enemy_units = None
                    self.refresh_army_list()
                else:
                    actor.x, actor.y = prev_x, prev_y
                    actor.ap += step_cost
                    self.refresh_army_list()
                    return
            else:
                self._notify("An enemy army blocks your path!")
                choice = self.prompt_combat_choice(tile.enemy_units, actor.units)
                if getattr(self, "quit_to_menu", False):
                    return
                if choice == "flee":
                    actor.x, actor.y = prev_x, prev_y
                    actor.ap += step_cost
                    return
                if choice == "auto":
                    hero_wins, _, heroes, enemies = auto_resolve.resolve(actor.units, tile.enemy_units)
                    for unit, res in zip(actor.units, heroes):
                        unit.count = res.count
                        unit.current_hp = res.current_hp
                    actor.units[:] = [u for u in actor.units if u.count > 0]
                    if hasattr(actor, "update_portrait"):
                        actor.update_portrait()
                    if hero_wins:
                        tile.enemy_units = None
                    else:
                        actor.x, actor.y = prev_x, prev_y
                        actor.ap += step_cost
                        self.refresh_army_list()
                        return
                else:
                    from core.combat import Combat
                    combat_map, flora = generate_combat_map(
                        self.world,
                        actor.x,
                        actor.y,
                        constants.COMBAT_GRID_WIDTH,
                        constants.COMBAT_GRID_HEIGHT,
                    )
                    combat = Combat(
                        self.screen,
                        self.assets,
                        actor.units,
                        tile.enemy_units,
                        hero_mana=0,
                        hero_spells={},
                        combat_map=combat_map,
                        flora_props=flora,
                        flora_loader=self.world.flora_loader,
                        biome_tilesets=self.biome_tilesets,
                        biome=tile.biome,
                        num_obstacles=random.randint(1, 3),
                        unit_shadow_baked=self.unit_shadow_baked,
                        hero=None,
                    )
                    audio.play_sound('attack')
                    hero_wins, _ = combat.run()
                    for unit, result in zip(actor.units, combat.hero_units):
                        unit.count = result.count
                        unit.current_hp = result.current_hp
                    actor.units[:] = [u for u in actor.units if u.count > 0]
                    if hasattr(actor, "update_portrait"):
                        actor.update_portrait()
                    if hero_wins:
                        tile.enemy_units = None
                    else:
                        actor.x, actor.y = prev_x, prev_y
                        actor.ap += step_cost
                        self.refresh_army_list()
                        return
                self.refresh_army_list()
                if not actor.units:
                    return
        # Capture passable or neutral buildings
        if tile.building:
            econ_state = getattr(self.state, "economy", None) if hasattr(self, "state") else None
            econ_b = getattr(self, "_econ_building_map", {}).get(tile.building)
            if self._capture_tile(self.hero.x, self.hero.y, tile, self.hero, 0, econ_state, econ_b):
                self._publish_resources()
            if isinstance(tile.building, Town):
                self.open_town(tile.building, actor, town_pos=(nx, ny))
            else:
                choice = self.prompt_building_interaction(tile.building)
                if choice == "take" and tile.building.owner != 0:
                    if self._capture_tile(self.hero.x, self.hero.y, tile, self.hero, 0, econ_state, econ_b):
                        self._publish_resources()
        # Treasure collection
        if tile.treasure is not None:
            treasure = tile.treasure
            choice = self.prompt_treasure_choice(treasure)
            if choice == "gold":
                amount = random.randint(*treasure["gold"])
                self.hero.gold += amount
                tile.treasure = None
                self._notify(f"You found a treasure chest with {amount} gold!")
            elif choice == "exp":
                amount = random.randint(*treasure["exp"])
                self.hero.gain_exp(amount)
                tile.treasure = None
                self._notify(f"You gained {amount} experience from the treasure!")
            else:
                self._notify("You leave the treasure untouched.")
            self._update_caches_for_tile(nx, ny)
            self._publish_resources()
        # Resource collection
        if tile.resource:
            res = tile.resource
            self.hero.resources[res] += 5
            tile.resource = None
            self._notify(f"You gather some {res}.")
            self._update_caches_for_tile(nx, ny)
            self._publish_resources()
        # Update fog of war after movement
        self._update_player_visibility(actor)

    def _cleanup_armies(self) -> None:
        """Remove empty armies and update the hero list."""

        armies = getattr(self.world, "player_armies", [])
        armies[:] = [a for a in armies if a.units]
        hero_list = getattr(getattr(self, "main_screen", None), "hero_list", None)
        if hero_list:
            heroes = list(getattr(self.state, "heroes", []))
            hero_list.set_heroes(heroes + armies)

    def refresh_army_list(self) -> None:
        """Regenerate the hero list from heroes and player armies."""
        self._cleanup_armies()

    def _update_player_visibility(self, primary: UnitCarrier | None = None) -> None:
        """Recalculate fog of war including all controlled armies.

        ``primary`` if provided is updated first to ensure the visibility matrix
        is reset for the moving actor before merging in other units.
        """
        actors: list[UnitCarrier] = []
        if primary is not None:
            actors.append(primary)
        if hasattr(self, "state") and hasattr(self.state, "heroes"):
            actors.extend(list(self.state.heroes))
        elif primary is None:
            actors.append(self.hero)
        actors.extend(getattr(self.world, "player_armies", []))
        seen: set[int] = set()
        first = True
        for actor in actors:
            ident = id(actor)
            if ident in seen:
                continue
            if not self.world.in_bounds(actor.x, actor.y):
                continue
            self.world.update_visibility(0, actor, reset=first)
            seen.add(ident)
            first = False

        for town in getattr(self.world, "towns", []):
            if getattr(town, "owner", None) != 0:
                continue
            ox, oy = getattr(town, "origin", (0, 0))
            for dx, dy in getattr(town, "footprint", [(0, 0)]):
                tx, ty = ox + dx, oy + dy
                self.world.reveal(0, tx, ty, radius=2)

        minimap = getattr(getattr(self, "main_screen", None), "minimap", None)
        if minimap:
            vis = self.world.visible.get(0)
            exp = self.world.explored.get(0)
            if vis:
                fog = [
                    [not vis[y][x] and not (exp[y][x] if exp else False) for x in range(len(vis[0]))]
                    for y in range(len(vis))
                ]
                minimap.set_fog(fog)
            minimap.invalidate()

    def _try_move_hero(self, dx: int, dy: int) -> None:
        """Attempt to move hero on the map; handle encounters and collisions."""
        # Check if hero has action points available
        if self.hero.ap <= 0:
            self._notify("No action points left. End your turn to restore them (press T).")
            return
        prev_x, prev_y = self.hero.x, self.hero.y
        nx = self.hero.x + dx
        ny = self.hero.y + dy
        if not self.world.in_bounds(nx, ny):
            return
        state = getattr(self, "state", None)
        if state:
            others = list(getattr(state, "heroes", []))
            others.extend(getattr(self.world, "player_armies", []))
            for other in others:
                if other is not self.hero and other.x == nx and other.y == ny:
                    self.open_hero_exchange(other)
                    return
        tile = self.world.grid[ny][nx]
        biome = BiomeCatalog.get(tile.biome)
        if getattr(tile, "road", False):
            step_cost = constants.ROAD_COST
        else:
            step_cost = biome.terrain_cost if biome else 1
        if self.hero.ap < step_cost:
            self._notify("No action points left. End your turn to restore them (press T).")
            return
        if tile.building and not tile.building.passable:
            # Interact with the building without moving onto its tile
            self.hero.ap -= step_cost
            if tile.building.garrison:
                enemy = EnemyHero(nx, ny, tile.building.garrison)
                engaged = self.combat_with_enemy_hero(enemy, initiated_by="hero")
                if not engaged:
                    self.hero.ap += step_cost
                    return
                tile.building.garrison = [u for u in enemy.army if u.count > 0]
                if tile.building.garrison:
                    if not self.hero.alive():
                        self.hero.ap += step_cost
                    return
            adjacent_enemy = self.world.adjacent_enemy_hero(
                nx, ny, getattr(self, "enemy_heroes", [])
            )
            if adjacent_enemy:
                engaged = self.combat_with_enemy_hero(adjacent_enemy, initiated_by="hero")
                if not engaged:
                    self.hero.ap += step_cost
                    return
                if adjacent_enemy in self.enemy_heroes:
                    if not self.hero.alive():
                        self.hero.ap += step_cost
                    return
            if isinstance(tile.building, Town):
                town = tile.building
                if town.owner != 0:
                    econ_state = getattr(self.state, "economy", None) if hasattr(self, "state") else None
                    econ_b = getattr(self, "_econ_building_map", {}).get(town)
                    if self._capture_tile(nx, ny, tile, self.hero, 0, econ_state, econ_b):
                        self._publish_resources()
                self.open_town(town, town_pos=(nx, ny))
            else:
                choice = self.prompt_building_interaction(tile.building)
                if choice == "take" and tile.building.owner != 0:
                    econ_state = getattr(self.state, "economy", None) if hasattr(self, "state") else None
                    econ_b = getattr(self, "_econ_building_map", {}).get(tile.building)
                    if self._capture_tile(nx, ny, tile, self.hero, 0, econ_state, econ_b):
                        self._publish_resources()
            return
        if not tile.is_passable():
            return
        # Move hero
        self.hero.x = nx
        self.hero.y = ny
        audio.play_sound('move')
        # Update free tile cache for old and new positions
        self._update_caches_for_tile(prev_x, prev_y)
        self._update_caches_for_tile(self.hero.x, self.hero.y)
        # Consume action points based on terrain or road
        self.hero.ap -= step_cost
        # Check enemy hero encounter
        for enemy in list(self.enemy_heroes):
            if enemy.x == self.hero.x and enemy.y == self.hero.y:
                self._notify("An enemy hero blocks your path!")
                engaged = self.combat_with_enemy_hero(enemy, initiated_by="hero")
                if not engaged:
                    # Flee: revert position and AP
                    self.hero.x = prev_x
                    self.hero.y = prev_y
                    self.hero.ap += step_cost
                elif not self.hero.alive():
                    # Defeat: retreat and restore spent action points
                    self.hero.x = prev_x
                    self.hero.y = prev_y
                    self.hero.ap += step_cost
                return
        # Check enemy encounter on tile
        if tile.enemy_units:
            self._notify("An enemy army blocks your path!")
            choice = self.prompt_combat_choice(tile.enemy_units)
            if self.quit_to_menu:
                return
            if choice == "flee":
                self.hero.x = prev_x
                self.hero.y = prev_y
                self.hero.ap += 1
                return
            if choice == "auto":
                hero_wins, exp_gained, heroes, enemies = auto_resolve.resolve(
                    self.hero.army, tile.enemy_units
                )
                for unit, res in zip(self.hero.army, heroes):
                    unit.count = res.count
                    unit.current_hp = res.current_hp
                self.hero.army = [u for u in self.hero.army if u.count > 0]
                self.hero.mana = self.hero.max_mana
                self.hero.gain_exp(exp_gained)
                auto_resolve.show_summary(
                    self.screen, heroes, enemies, hero_wins, exp_gained, self.hero
                )
                if hero_wins:
                    self._notify("You are victorious!")
                    audio.play_sound('victory')
                    EVENT_BUS.publish(
                        ON_ENEMY_DEFEATED, [u.stats.name for u in tile.enemy_units]
                    )
                    tile.enemy_units = None
                    if not self.hero.alive():
                        self._notify("All your units have perished.  Game over.")
                        self.hero.army = []
                else:
                    self._notify("You have been defeated!")
                    self.hero.army = []
                    # Retreat to previous position
                    self.hero.x = prev_x
                    self.hero.y = prev_y
                    self.hero.ap += step_cost
                    return
            else:
                # Begin combat; pass hero's mana and reset afterwards
                from core.combat import Combat
                combat_map, flora = generate_combat_map(
                    self.world,
                    self.hero.x,
                    self.hero.y,
                    constants.COMBAT_GRID_WIDTH,
                    constants.COMBAT_GRID_HEIGHT,
                )
                combat = Combat(
                    self.screen,
                    self.assets,
                    self.hero.army,
                    tile.enemy_units,
                    hero_mana=self.hero.mana,
                    hero_spells=self.hero.spells,
                    combat_map=combat_map,
                    flora_props=flora,
                    flora_loader=self.world.flora_loader,
                    biome_tilesets=self.biome_tilesets,
                    biome=tile.biome,
                    num_obstacles=random.randint(1, 3),
                    unit_shadow_baked=self.unit_shadow_baked,
                    hero=self.hero,
                )
                audio.play_sound('attack')
                hero_wins, exp_gained = combat.run()
                if combat.exit_to_menu:
                    self.quit_to_menu = True
                    return
                # Sync surviving hero units with combat results
                for unit, result in zip(self.hero.army, combat.hero_units):
                    unit.count = result.count
                    unit.current_hp = result.current_hp
                # Remove stacks that were wiped out
                self.hero.army = [u for u in self.hero.army if u.count > 0]
                # After battle, reset hero mana and award experience
                self.hero.mana = self.hero.max_mana
                self.hero.gain_exp(exp_gained)
                if hero_wins:
                    self._notify("You are victorious!")
                    audio.play_sound('victory')
                    EVENT_BUS.publish(ON_ENEMY_DEFEATED, [u.stats.name for u in tile.enemy_units])
                    tile.enemy_units = None
                    if not self.hero.alive():
                        self._notify("All your units have perished.  Game over.")
                        self.hero.army = []
                else:
                    self._notify("You have been defeated!")
                    self.hero.army = []
                    # Retreat to previous position
                    self.hero.x = prev_x
                    self.hero.y = prev_y
                    self.hero.ap += step_cost
                    return
        if tile.building and tile.building.garrison:
            enemy = EnemyHero(nx, ny, tile.building.garrison)
            engaged = self.combat_with_enemy_hero(enemy, initiated_by="hero")
            if not engaged:
                self.hero.x = prev_x
                self.hero.y = prev_y
                self.hero.ap += step_cost
                return
            tile.building.garrison = [u for u in enemy.army if u.count > 0]
            if tile.building.garrison:
                if not self.hero.alive():
                    self.hero.x = prev_x
                    self.hero.y = prev_y
                    self.hero.ap += step_cost
                return
        # Capture unguarded building if present after moving
        if tile.building:
            econ_state = getattr(self.state, "economy", None) if hasattr(self, "state") else None
            econ_b = getattr(self, "_econ_building_map", {}).get(tile.building)
            if self._capture_tile(self.hero.x, self.hero.y, tile, self.hero, 0, econ_state, econ_b):
                self._publish_resources()
            if getattr(tile.building, "owner", None) == 0:
                from ui import building_info

                building_info.open_panel(
                    self.screen, tile.building, self.clock, self.hero, econ_b
                )
        # Collect flora
        prop = getattr(self.world, "collectibles", {}).get((self.hero.x, self.hero.y))
        if prop:
            loader = getattr(self.world, "flora_loader", None)
            asset = loader.assets.get(prop.asset_id) if loader else None
            if asset and asset.collectible:
                qty = asset.collectible.get("qty", [1, 1])
                amount = random.randint(qty[0], qty[1])
                item = Item(
                    id=prop.asset_id,
                    name=prop.asset_id,
                    slot=None,
                    rarity="common",
                    icon="",
                    stackable=True,
                    qty=amount,
                    modifiers=HeroStats(0, 0, 0, 0, 0, 0, 0, 0, 0),
                )
                self.hero.inventory.append(item)
            to_remove = [pos for pos, p in self.world.collectibles.items() if p is prop]
            for pos in to_remove:
                self.world.collectibles.pop(pos, None)
            if prop in self.world.flora_props:
                self.world.flora_props.remove(prop)
                self.world.invalidate_prop_chunk(prop)
        # Check treasure
        if tile.treasure is not None:
            treasure = tile.treasure
            choice = self.prompt_treasure_choice(treasure)
            if choice == "gold":
                amount = random.randint(*treasure["gold"])
                self.hero.gold += amount
                tile.treasure = None
                self._notify(f"You found a treasure chest with {amount} gold!")
            elif choice == "exp":
                amount = random.randint(*treasure["exp"])
                self.hero.gain_exp(amount)
                tile.treasure = None
                self._notify(f"You gained {amount} experience from the treasure!")
            else:
                self._notify("You leave the treasure untouched.")
            self._update_caches_for_tile(self.hero.x, self.hero.y)
            self._publish_resources()
        # Check loose resource deposit
        if tile.resource:
            res = tile.resource
            self.hero.resources[res] += 5
            tile.resource = None
            self._notify(f"You gather some {res}.")
            self._update_caches_for_tile(self.hero.x, self.hero.y)
            self._publish_resources()
        # Update fog of war after movement
        self._update_player_visibility(self.hero)
        # otherwise just move

    def prompt_combat_choice(self, enemy_units, army_units=None) -> str:
        """Display a prompt asking whether to engage in combat or auto-resolve.

        Returns "fight", "auto" or "flee". Setting ``self.quit_to_menu`` to ``True``
        indicates the menu should be opened.
        """
        font = theme.get_font(32) or pygame.font.SysFont(None, 32)
        btn_font = theme.get_font(28) or pygame.font.SysFont(None, 28)
        dialog_rect = pygame.Rect(0, 0, 420, 260)
        dialog_rect.center = (
            self.screen.get_width() // 2,
            self.screen.get_height() // 2,
        )
        fight_text = btn_font.render("Enter Combat", True, theme.PALETTE["text"])
        auto_text = btn_font.render("Auto-resolve", True, theme.PALETTE["text"])
        flee_text = btn_font.render("Flee", True, theme.PALETTE["text"])
        button_w = dialog_rect.width - 40
        button_h = fight_text.get_height() + 10
        fight_rect = pygame.Rect(0, 0, button_w, button_h)
        auto_rect = pygame.Rect(0, 0, button_w, button_h)
        flee_rect = pygame.Rect(0, 0, button_w, button_h)
        fight_rect.center = (dialog_rect.centerx, dialog_rect.centery + 40)
        auto_rect.center = (dialog_rect.centerx, fight_rect.bottom + button_h // 2 + 10)
        flee_rect.center = (dialog_rect.centerx, auto_rect.bottom + button_h // 2 + 10)

        pred_h_loss, pred_e_loss, pred_exp = auto_resolve.preview(
            army_units or self.hero.army, enemy_units
        )
        preview_lines = [
            f"Allied losses ~{pred_h_loss:.0f}",
            f"Enemy losses ~{pred_e_loss:.0f}",
            f"XP ~{pred_exp:.0f}",
        ]
        line_height = button_h
        self.screen.fill(theme.PALETTE["background"])
        self.draw_world(self.anim_frame)
        background = self.screen.copy()
        dim = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        dim.fill((*theme.PALETTE["background"], 200))
        def draw() -> None:
            self.screen.blit(background, (0, 0))
            self.screen.blit(dim, (0, 0))
            pygame.draw.rect(self.screen, theme.PALETTE["panel"], dialog_rect)
            pygame.draw.rect(
                self.screen, theme.PALETTE["accent"], dialog_rect, theme.FRAME_WIDTH
            )
            msg = font.render(
                "An enemy army blocks your path!", True, theme.PALETTE["text"]
            )
            msg_rect = msg.get_rect(center=(dialog_rect.centerx, dialog_rect.y + 60))
            self.screen.blit(msg, msg_rect)
            for i, line in enumerate(preview_lines):
                surf = btn_font.render(line, True, theme.PALETTE["text"])
                pos_y = dialog_rect.y + 110 + i * line_height
                self.screen.blit(surf, surf.get_rect(center=(dialog_rect.centerx, pos_y)))
            for rect, text in (
                (fight_rect, fight_text),
                (auto_rect, auto_text),
                (flee_rect, flee_text),
            ):
                pygame.draw.rect(self.screen, theme.PALETTE["accent"], rect)
                pygame.draw.rect(
                    self.screen, theme.PALETTE["text"], rect, theme.FRAME_WIDTH
                )
                self.screen.blit(text, text.get_rect(center=rect.center))
        return dialogs.run_dialog(
            self.screen,
            self.clock,
            draw,
            [(fight_rect, "fight"), (auto_rect, "auto"), (flee_rect, "flee")],
            "flee",
            on_escape=lambda: setattr(self, "quit_to_menu", True),
        )

    def prompt_building_interaction(self, building: Building) -> str:
        """Display a prompt for interacting with ``building``."""
        if isinstance(building, Town):
            return "take"
        # When the player already owns the building, open the info panel instead
        if getattr(building, "owner", None) == 0:
            from ui import building_info

            econ_b = getattr(self, "_econ_building_map", {}).get(building)
            building_info.open_panel(
                self.screen, building, self.clock, self.hero, econ_b
            )
            return "leave"

        font = theme.get_font(32) or pygame.font.SysFont(None, 32)
        btn_font = theme.get_font(28) or pygame.font.SysFont(None, 28)
        dialog_rect = pygame.Rect(0, 0, 420, 220)
        dialog_rect.center = (
            self.screen.get_width() // 2,
            self.screen.get_height() // 2,
        )
        take_text = btn_font.render("Prendre", True, theme.PALETTE["text"])
        leave_text = btn_font.render("Laisser", True, theme.PALETTE["text"])
        button_w = max(take_text.get_width(), leave_text.get_width()) + 20
        button_h = take_text.get_height() + 10
        take_rect = pygame.Rect(0, 0, button_w, button_h)
        leave_rect = pygame.Rect(0, 0, button_w, button_h)
        take_rect.center = (dialog_rect.centerx - button_w // 2, dialog_rect.centery + 50)
        leave_rect.center = (dialog_rect.centerx + button_w // 2, dialog_rect.centery + 50)
        self.screen.fill(theme.PALETTE["background"])
        self.draw_world(self.anim_frame)
        background = self.screen.copy()
        dim = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        dim.fill((*theme.PALETTE["background"], 200))
        def draw() -> None:
            self.screen.blit(background, (0, 0))
            self.screen.blit(dim, (0, 0))
            pygame.draw.rect(self.screen, theme.PALETTE["panel"], dialog_rect)
            pygame.draw.rect(
                self.screen, theme.PALETTE["accent"], dialog_rect, theme.FRAME_WIDTH
            )
            msg = font.render(building.name, True, theme.PALETTE["text"])
            msg_rect = msg.get_rect(center=(dialog_rect.centerx, dialog_rect.y + 60))
            self.screen.blit(msg, msg_rect)
            for rect, text in ((take_rect, take_text), (leave_rect, leave_text)):
                pygame.draw.rect(self.screen, theme.PALETTE["accent"], rect)
                pygame.draw.rect(
                    self.screen, theme.PALETTE["text"], rect, theme.FRAME_WIDTH
                )
                self.screen.blit(text, text.get_rect(center=rect.center))
        return dialogs.run_dialog(
            self.screen,
            self.clock,
            draw,
            [(take_rect, "take"), (leave_rect, "leave")],
            "leave",
            on_escape=lambda: setattr(self, "quit_to_menu", True),
        )

    def prompt_treasure_choice(self, treasure: Dict[str, Tuple[int, int]]) -> str:
        """Display a prompt for choosing a treasure reward."""
        font = theme.get_font(32) or pygame.font.SysFont(None, 32)
        btn_font = theme.get_font(28) or pygame.font.SysFont(None, 28)
        dialog_rect = pygame.Rect(0, 0, 420, 220)
        dialog_rect.center = (
            self.screen.get_width() // 2,
            self.screen.get_height() // 2,
        )
        gold_text = btn_font.render("Gold", True, theme.PALETTE["text"])
        exp_text = btn_font.render("Experience", True, theme.PALETTE["text"])
        leave_text = btn_font.render("Leave", True, theme.PALETTE["text"])
        button_w = max(gold_text.get_width(), exp_text.get_width(), leave_text.get_width()) + 20
        button_h = gold_text.get_height() + 10
        gold_rect = pygame.Rect(0, 0, button_w, button_h)
        exp_rect = pygame.Rect(0, 0, button_w, button_h)
        leave_rect = pygame.Rect(0, 0, button_w, button_h)
        gold_rect.center = (
            dialog_rect.centerx - button_w,
            dialog_rect.centery + 50,
        )
        exp_rect.center = (dialog_rect.centerx, dialog_rect.centery + 50)
        leave_rect.center = (
            dialog_rect.centerx + button_w,
            dialog_rect.centery + 50,
        )
        self.screen.fill(theme.PALETTE["background"])
        self.draw_world(self.anim_frame)
        background = self.screen.copy()
        dim = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        dim.fill((*theme.PALETTE["background"], 200))
        def draw() -> None:
            self.screen.blit(background, (0, 0))
            self.screen.blit(dim, (0, 0))
            pygame.draw.rect(self.screen, theme.PALETTE["panel"], dialog_rect)
            pygame.draw.rect(
                self.screen, theme.PALETTE["accent"], dialog_rect, theme.FRAME_WIDTH
            )
            msg = font.render(
                "You found a treasure chest!", True, theme.PALETTE["text"]
            )
            msg_rect = msg.get_rect(center=(dialog_rect.centerx, dialog_rect.y + 60))
            self.screen.blit(msg, msg_rect)
            for rect, text in (
                (gold_rect, gold_text),
                (exp_rect, exp_text),
                (leave_rect, leave_text),
            ):
                pygame.draw.rect(self.screen, theme.PALETTE["accent"], rect)
                pygame.draw.rect(
                    self.screen, theme.PALETTE["text"], rect, theme.FRAME_WIDTH
                )
                self.screen.blit(text, text.get_rect(center=rect.center))
        return dialogs.run_dialog(
            self.screen,
            self.clock,
            draw,
            [(gold_rect, "gold"), (exp_rect, "exp"), (leave_rect, "leave")],
            "leave",
            on_escape=lambda: setattr(self, "quit_to_menu", True),
        )

    def draw_world(self, frame: int) -> pygame.Rect:
        """Draw the world map and UI to the screen.

        Returns the rectangle updated on the main surface so the caller can use
        it as part of a dirty-rects rendering strategy.
        """
        world_rect = self.main_screen.widgets["1"]
        # Clear screen
        self.screen.fill(constants.BLACK, world_rect)
        # Render world to an offscreen surface so we can scale and pan it
        map_surface = pygame.Surface(
            (self.world.width * constants.TILE_SIZE, self.world.height * constants.TILE_SIZE)
        )
        state = getattr(self, "state", None)
        heroes = list(getattr(state, "heroes", [getattr(self, "hero", None)]))
        heroes = [h for h in heroes if h is not None]
        armies = list(getattr(self.world, "player_armies", []))
        overlay = self.world.draw(
            map_surface,
            self.assets,
            heroes,
            armies,
            self.active_actor,
            frame,
        )
        blend = getattr(pygame, "BLEND_RGBA_ADD", 0)

        # Draw planned movement path arrows before drawing units
        if self.path:
            actor = getattr(self, "active_actor", self.hero)
            prev = (actor.x, actor.y)
            costs = getattr(self, "path_costs", [])
            for i, (x, y) in enumerate(self.path):
                cost = costs[i] if i < len(costs) else i + 1
                dx = x - prev[0]
                dy = y - prev[1]
                angle = 0
                if dx == 1:
                    angle = 0
                elif dx == -1:
                    angle = 180
                elif dy == 1:
                    angle = -90
                elif dy == -1:
                    angle = 90
                img = self.arrow_green if cost <= actor.ap else self.arrow_red
                if img:
                    rot = pygame.transform.rotate(img, angle)
                    try:
                        overlay.blit(
                            rot,
                            (x * constants.TILE_SIZE, y * constants.TILE_SIZE),
                            special_flags=blend,
                        )
                    except TypeError:
                        overlay.blit(
                            rot,
                            (x * constants.TILE_SIZE, y * constants.TILE_SIZE),
                        )
                prev = (x, y)
            if self.path:
                if costs:
                    remaining = actor.ap - costs[-1]
                else:
                    remaining = actor.ap - len(self.path)
                if self.ap_font:
                    try:
                        try:
                            txt = self.ap_font.render(
                                str(max(0, remaining)), True, constants.WHITE, None
                            )
                        except TypeError:
                            txt = self.ap_font.render(
                                str(max(0, remaining)), True, constants.WHITE
                            )
                    except Exception:
                        logger.exception("Failed to render action point text")
                        txt = None
                    if txt:
                        if hasattr(txt, "convert_alpha"):
                            txt = txt.convert_alpha()
                        overlay.blit(
                            txt,
                            (
                                self.path[-1][0] * constants.TILE_SIZE + 4,
                                self.path[-1][1] * constants.TILE_SIZE + 4,
                            ),
                        )

        try:
            map_surface.blit(overlay, (0, 0), special_flags=blend)
        except TypeError:
            map_surface.blit(overlay, (0, 0))
            
        # Draw enemy heroes above arrows
        for enemy in getattr(self, "enemy_heroes", []):
            pygame.draw.circle(
                map_surface,
                constants.RED,
                (
                    enemy.x * constants.TILE_SIZE + constants.TILE_SIZE // 2,
                    enemy.y * constants.TILE_SIZE + constants.TILE_SIZE // 2,
                ),
                constants.TILE_SIZE // 3,
            )
        if self.zoom != 1.0:
            w = int(map_surface.get_width() * self.zoom)
            h = int(map_surface.get_height() * self.zoom)
            map_surface = pygame.transform.smoothscale(map_surface, (w, h))
        # Blit the (potentially scaled) map using the current offset
        self.screen.set_clip(world_rect)
        self.screen.blit(
            map_surface, (world_rect.x + self.offset_x, world_rect.y + self.offset_y)
        )
        self.screen.set_clip(None)
        return world_rect

    def end_turn(self) -> None:
        """Cycle to the next hero or end the day when all have acted."""
        # Clear any pending movement when ending the turn to avoid actors
        # unintentionally continuing another unit's path.
        self.move_queue = []
        self.path = []
        self.path_costs = []
        self.path_target = None
        state = getattr(self, "state", None)
        if not state:
            self._notify("End of turn. Your action points are restored.")
            for row in self.world.grid:
                for tile in row:
                    building = tile.building
                    if building and getattr(building, "owner", None) == 0:
                        for res, amount in getattr(building, "income", {}).items():
                            self.hero.resources[res] = self.hero.resources.get(res, 0) + amount
            self.hero.reset_ap()
            for army in getattr(self.world, "player_armies", []):
                if hasattr(army, "reset_ap"):
                    army.reset_ap()
            self.active_actor = self.hero
            self.turn = getattr(self, "turn", 0) + 1
            EVENT_BUS.publish(ON_TURN_END, self.turn)
            self._publish_resources()
            self.refresh_army_list()
            self._update_player_visibility()
            try:
                audio.play_sound('end_turn')
            except Exception:  # pragma: no cover
                pass
            self._run_ai_turn()
            return

        idx = getattr(self, "hero_idx", 0)
        if idx < len(state.heroes) - 1:
            # Select next hero in roster
            self.hero_idx = idx + 1
            self.hero = state.heroes[self.hero_idx]
            self.active_actor = self.hero
            EVENT_BUS.publish(ON_SELECT_HERO, self.hero)
            self._publish_resources()
            self.refresh_army_list()
            return
        self._notify("End of day. All heroes' action points are restored.")
        if hasattr(self, "state") and hasattr(self.state, "next_day"):
            self._sync_economy_from_hero()
            self.state.next_day()
            self._sync_hero_from_economy()
        else:
            for row in self.world.grid:
                for tile in row:
                    building = tile.building
                    if building and getattr(building, "owner", None) == 0:
                        for res, amount in getattr(building, "income", {}).items():
                            self.hero.resources[res] = self.hero.resources.get(res, 0) + amount
        for h in state.heroes:
            h.reset_ap()
        for army in getattr(self.world, "player_armies", []):
            if hasattr(army, "reset_ap"):
                army.reset_ap()
        self.turn = getattr(self, "turn", 0) + 1
        EVENT_BUS.publish(ON_TURN_END, self.turn)
        self._publish_resources()
        self.refresh_army_list()
        self._update_player_visibility()
        try:
            audio.play_sound('end_turn')
        except Exception:  # pragma: no cover
            pass
        self._run_ai_turn()
        # Start new day with first hero
        if state.heroes:
            self.hero_idx = 0
            self.hero = state.heroes[0]
            self.active_actor = self.hero
            EVENT_BUS.publish(ON_SELECT_HERO, self.hero)

    def move_enemies_randomly(self) -> None:
        """Update neutral creature groups using their AI behaviour."""
        hero_pos = (self.hero.x, self.hero.y)
        hero_strength = sum(u.count for u in self.hero.army)
        creatures = getattr(self, "creatures", [])
        for ai in list(creatures):
            ai.update(self.world, hero_pos, hero_strength)
            tile = self.world.grid[ai.y][ai.x]
            if tile.enemy_units is None:
                creatures.remove(ai)

    def _run_ai_turn(self) -> None:
        """Execute AI recruitment and movement for the turn."""
        if getattr(self, "ai_player", None):
            self._spawn_enemy_heroes()
        self.move_enemies_randomly()
        self.move_enemy_heroes()
        EVENT_BUS.publish(ON_TURN_END, self.turn)

    def _capture_tile(
        self,
        x: int,
        y: int,
        tile: Tile,
        hero: Hero,
        new_owner: int,
        econ_state: Optional[economy.GameEconomyState] = None,
        econ_building: Optional[economy.Building] = None,
    ) -> bool:
        """Capture ``tile`` and handle special cases such as enemy towns."""

        captured = tile.capture(hero, new_owner, econ_state, econ_building)
        if captured:
            self._update_caches_for_tile(x, y)
            if (
                new_owner == 0
                and isinstance(tile.building, Town)
                and self.world.enemy_town == (x, y)
            ):
                self.world.enemy_town = None
                if getattr(self, "ai_player", None) and self.ai_player.town is tile.building:
                    self.ai_player.town = None
        return captured

    def _spawn_enemy_heroes(self, count: int = 1) -> None:
        """Spawn or reinforce the enemy faction's heroes."""
        if not getattr(self, "ai_player", None) or not getattr(self, "state", None):
            return

        if self.world.enemy_town:
            tx, ty = self.world.enemy_town
            town_tile = self.world.grid[ty][tx]
            if not town_tile.building or getattr(town_tile.building, "owner", None) != 1:
                return

        # Spawn the main hero near the enemy town if none exists
        if not self.ai_player.heroes and self.world.enemy_town:
            ex, ey = self.world.enemy_town
            offsets = [(-1, 0), (1, 0), (0, -1), (0, 1), (0, 0)]
            candidates: List[Tuple[int, int]] = []
            if self.world.enemy_start:
                candidates.append(self.world.enemy_start)
            candidates.extend((ex + dx, ey + dy) for dx, dy in offsets)
            for sx, sy in candidates:
                if not self.world.in_bounds(sx, sy):
                    continue
                tile = self.world.grid[sy][sx]
                if (
                    tile.is_passable()
                    and tile.treasure is None
                    and tile.enemy_units is None
                    and tile.building is None
                ):
                    army = create_random_enemy_army()
                    hero = EnemyHero(sx, sy, army)
                    self.ai_player.heroes.append(hero)
                    self._update_caches_for_tile(sx, sy)
                    break
        else:
            # Periodically recruit units from owned buildings' garrisons
            ai_buildings = [b for b in self.state.economy.buildings if b.owner == 1]
            for hero in self.ai_player.heroes:
                for b in ai_buildings:
                    if not b.garrison:
                        continue
                    for unit_id, amount in list(b.garrison.items()):
                        stats = STATS_BY_NAME.get(unit_id)
                        if not stats or amount <= 0:
                            continue
                        hero.army.append(Unit(stats, amount, "enemy"))
                        b.garrison[unit_id] = 0

    def move_enemy_heroes(self) -> None:
        """Move each enemy hero one step toward the hero or nearest resource."""
        heroes: List[EnemyHero] = []
        ai_heroes = getattr(getattr(self, "ai_player", None), "heroes", None)
        if ai_heroes:
            heroes.extend(ai_heroes)
        if getattr(self, "enemy_heroes", None) and self.enemy_heroes is not ai_heroes:
            heroes.extend(self.enemy_heroes)
        if not heroes:
            return
        from . import exploration_ai

        for enemy in list(heroes):
            step = exploration_ai.compute_enemy_step(self, enemy, constants.AI_DIFFICULTY)
            if not step:
                continue
            sx, sy = step
            tile = self.world.grid[sy][sx]
            if tile.building and isinstance(tile.building, Town) and not tile.building.passable:
                biome = BiomeCatalog.get(tile.biome)
                step_cost = (
                    constants.ROAD_COST
                    if getattr(tile, "road", False)
                    else (biome.terrain_cost if biome else 1)
                )
                if enemy.ap >= step_cost:
                    garrison = getattr(tile.building, "garrison", None)
                    defenders = bool(garrison)
                    if not defenders:
                        adjacent = [(sx + dx, sy + dy) for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]]
                        if (self.hero.x, self.hero.y) in adjacent:
                            defenders = True
                        else:
                            for army in getattr(self.world, "player_armies", []):
                                if (army.x, army.y) in adjacent:
                                    defenders = True
                                    break
                    if defenders:
                        continue
                    enemy.ap -= step_cost
                    econ_state = getattr(self.state, "economy", None) if hasattr(self, "state") else None
                    econ_b = getattr(self, "_econ_building_map", {}).get(tile.building)
                    try:
                        self._capture_tile(sx, sy, tile, enemy, 1, econ_state, econ_b)
                    except Exception:
                        pass
                continue
            old_x, old_y = enemy.x, enemy.y
            enemy.x, enemy.y = sx, sy
            self._update_caches_for_tile(old_x, old_y)
            self._update_caches_for_tile(enemy.x, enemy.y)
            tile = self.world.grid[enemy.y][enemy.x]
            # Capture uncontrolled buildings
            if tile.building and getattr(tile.building, "owner", None) != 1:
                econ_state = getattr(self.state, "economy", None) if hasattr(self, "state") else None
                econ_b = getattr(self, "_econ_building_map", {}).get(tile.building)
                try:
                    self._capture_tile(enemy.x, enemy.y, tile, enemy, 1, econ_state, econ_b)
                except Exception:
                    pass
            # Collect loose resources
            if tile.resource:
                res = tile.resource
                enemy.resources[res] = enemy.resources.get(res, 0) + 5
                ai_econ = getattr(getattr(self, "ai_player", None), "economy", None)
                if ai_econ:
                    ai_econ.resources[res] = ai_econ.resources.get(res, 0) + 5
                tile.resource = None
                self._update_caches_for_tile(enemy.x, enemy.y)
            if tile.treasure is not None:
                tile.treasure = None
                self._update_caches_for_tile(enemy.x, enemy.y)
            if enemy.x == self.hero.x and enemy.y == self.hero.y:
                self.combat_with_enemy_hero(enemy, initiated_by="enemy")

    def combat_with_enemy_hero(self, enemy: EnemyHero, initiated_by: str) -> bool:
        """Handle combat between the player and an enemy hero.

        Returns ``True`` if combat occurred, ``False`` if the player fled.
        ``initiated_by`` should be ``"hero"`` when the player moves onto the
        enemy tile and ``"enemy"`` when the enemy hero moves onto the player.
        """
        if initiated_by == "hero":
            choice = self.prompt_combat_choice(enemy.army)
            if self.quit_to_menu:
                return False
            if choice == "flee":
                return False
            if choice == "auto":
                hero_wins, exp_gained, heroes, enemies = auto_resolve.resolve(self.hero.army, enemy.army)
                for unit, res in zip(self.hero.army, heroes):
                    unit.count = res.count
                    unit.current_hp = res.current_hp
                self.hero.army = [u for u in self.hero.army if u.count > 0]
                enemy.army = enemies
                self.hero.mana = self.hero.max_mana
                self.hero.gain_exp(exp_gained)
                if hero_wins:
                    if enemy in self.enemy_heroes:
                        self.enemy_heroes.remove(enemy)
                        self._update_caches_for_tile(enemy.x, enemy.y)
                    self._notify("You defeated the enemy hero!")
                    EVENT_BUS.publish(ON_ENEMY_DEFEATED, ["EnemyHero"])
                else:
                    self._notify("You have been defeated!")
                    self.hero.army = []
                return True
        from core.combat import Combat
        tile = self.world.grid[self.hero.y][self.hero.x]
        combat_map, flora = generate_combat_map(
            self.world,
            self.hero.x,
            self.hero.y,
            constants.COMBAT_GRID_WIDTH,
            constants.COMBAT_GRID_HEIGHT,
        )
        combat = Combat(
            self.screen,
            self.assets,
            self.hero.army,
            enemy.army,
            hero_mana=self.hero.mana,
            hero_spells=self.hero.spells,
            combat_map=combat_map,
            flora_props=flora,
            flora_loader=self.world.flora_loader,
            biome_tilesets=self.biome_tilesets,
            biome=tile.biome,
            num_obstacles=random.randint(1, 3),
            unit_shadow_baked=self.unit_shadow_baked,
            hero=self.hero,
        )
        audio.play_sound("attack")
        hero_wins, exp_gained = combat.run()
        if combat.exit_to_menu:
            self.quit_to_menu = True
            return False
        for unit, result in zip(self.hero.army, combat.hero_units):
            unit.count = result.count
            unit.current_hp = result.current_hp
        self.hero.army = [u for u in self.hero.army if u.count > 0]
        enemy.army = [u for u in combat.enemy_units if u.count > 0]
        self.hero.mana = self.hero.max_mana
        self.hero.gain_exp(exp_gained)
        if hero_wins:
            if enemy in self.enemy_heroes:
                self.enemy_heroes.remove(enemy)
                self._update_caches_for_tile(enemy.x, enemy.y)
            self._notify("You defeated the enemy hero!")
            EVENT_BUS.publish(ON_ENEMY_DEFEATED, ["EnemyHero"])
        else:
            self._notify("You have been defeated!")
            self.hero.army = []
        return True

    def open_pause_menu(self) -> Tuple[bool, pygame.Surface]:
        from ui.menu import pause_menu  # local import to avoid circular

        return pause_menu(self.screen, self)

    def show_inventory(self) -> bool:
        """Display the hero's inventory and skill tree.

        Returns ``True`` if the player chose to open the main menu.
        """
        screen = InventoryScreen(
            self.screen, self.assets, self.hero, self.clock, self.open_pause_menu
        )
        quit_to_menu, self.screen = screen.run()
        return quit_to_menu

    def open_town(
        self,
        town: Optional[Town] = None,
        army: Optional[Army] = None,
        town_pos: Optional[Tuple[int, int]] = None,
    ) -> None:
        """Open a town management screen or selection overlay.

        If ``town`` is provided, the detailed :class:`TownScreen` is opened
        directly for that town, optionally using ``army`` as the visiting
        army.  Otherwise a :class:`TownOverlay` listing all player-owned towns
        is displayed.
        """

        if town is not None:
            if army is None and town_pos is not None and getattr(self, "hero", None):
                tx, ty = town_pos
                if (
                    abs(self.hero.x - tx) <= 1
                    and abs(self.hero.y - ty) <= 1
                ):
                    army = self.hero
            try:  # pragma: no cover - allow running without package context
                from .ui.town_screen import TownScreen
            except ImportError:  # pragma: no cover
                from ui.town_screen import TownScreen
            screen = TownScreen(self.screen, self, town, army, None, town_pos)
            run = getattr(screen, "run", None)
            if callable(run):
                run()
            return

        try:  # pragma: no cover - allow running without package context
            from .ui.town_overlay import TownOverlay
        except ImportError:  # pragma: no cover
            from ui.town_overlay import TownOverlay

        world = getattr(self, "world", None)
        towns_attr = getattr(world, "towns", [])
        if callable(towns_attr):
            towns = [t for t in towns_attr() if getattr(t, "owner", None) == 0]
        else:
            towns = [t for t in towns_attr if getattr(t, "owner", None) == 0]
        if not towns:
            print("No town available")
            self._notify("No town available")
            return

        overlay = TownOverlay(self.screen, self, towns)
        running = True
        while running:
            for event in pygame.event.get():
                result = overlay.handle_event(event)
                if result is True:
                    running = False
                elif result:
                    try:  # pragma: no cover - allow running without package context
                        from .ui.town_screen import TownScreen
                    except ImportError:  # pragma: no cover
                        from ui.town_screen import TownScreen

                    # ``TownOverlay`` may return either a ``Town`` instance or a
                    # ``(Town, (x, y))`` tuple containing the town and its
                    # coordinates.  Extract both pieces accordingly.
                    town_obj: Town
                    town_pos: Optional[Tuple[int, int]] = None
                    army: Optional[Army] = None

                    if isinstance(result, tuple) and len(result) == 2 and isinstance(result[0], Town):
                        town_obj, town_pos = result
                    else:
                        town_obj = result
                        finder = getattr(getattr(self, "world", None), "find_building_pos", None)
                        if callable(finder):
                            town_pos = finder(town_obj)

                    if (
                        town_pos is not None
                        and getattr(self, "hero", None)
                    ):
                        tx, ty = town_pos
                        if abs(self.hero.x - tx) <= 1 and abs(self.hero.y - ty) <= 1:
                            army = self.hero

                    screen = TownScreen(self.screen, self, town_obj, army, None, town_pos)
                    run = getattr(screen, "run", None)
                    if callable(run):
                        run()
                    running = False
            overlay.draw()
            pygame.display.flip()
            self.clock.tick(constants.FPS)

    def open_hero_exchange(self, other: Union[Hero, Army]) -> None:
        """Open the unit exchange screen between the active hero and ``other``."""
        try:  # pragma: no cover
            from .ui.hero_exchange_screen import HeroExchangeScreen
        except ImportError:  # pragma: no cover
            from ui.hero_exchange_screen import HeroExchangeScreen
        screen = HeroExchangeScreen(self.screen, self.hero, other, self.clock)
        screen.run()

    def open_options(self) -> None:
        """Open the options menu allowing volume and graphics changes."""
        try:  # pragma: no cover - allow running without package context
            from .ui.options_menu import options_menu
        except ImportError:  # pragma: no cover
            from ui.options_menu import options_menu
        self.screen = options_menu(self.screen)

    def hero_heal(self) -> None:
        """Heal ability: restore some HP to the top creature of each stack. Costs one AP."""
        if self.hero.ap <= 0:
            self._notify("You have no action points to heal.")
            return
        healed_any = False
        for unit in self.hero.army:
            if unit.is_alive and unit.current_hp < unit.stats.max_hp:
                unit.current_hp = min(unit.stats.max_hp, unit.current_hp + 5)
                healed_any = True
        if healed_any:
            self._notify("You cast heal, restoring some health to your units.")
            self.hero.ap -= 1
        else:
            self._notify("All your units are at full health. Heal not needed.")

    # ------------------------------------------------------------------
    # Saving and loading
    # ------------------------------------------------------------------

    def _unit_to_dict(self, unit: Unit) -> Dict[str, Any]:
        return {
            "name": unit.stats.name,
            "count": unit.count,
            "current_hp": unit.current_hp,
            "side": unit.side,
            "attack_bonus": unit.attack_bonus,
            "initiative_bonus": unit.initiative_bonus,
        }

    def _unit_from_dict(self, data: Dict[str, Any]) -> Unit:
        stats = STATS_BY_NAME[data["name"]]
        unit = Unit(stats, data["count"], data.get("side", "hero"))
        unit.current_hp = data.get("current_hp", stats.max_hp)
        unit.attack_bonus = data.get("attack_bonus", 0)
        unit.initiative_bonus = data.get("initiative_bonus", 0)
        return unit

    def _serialize_state(self) -> Dict[str, Any]:
        hero_data = {
            "x": self.hero.x,
            "y": self.hero.y,
            "gold": self.hero.gold,
            "mana": self.hero.mana,
            "ap": self.hero.ap,
            "max_ap": self.hero.max_ap,
            "name": self.hero.name,
            "colour": list(self.hero.colour),
            "faction": self.hero.faction.value,
            "resources": self.hero.resources,
            "army": [self._unit_to_dict(u) for u in self.hero.army],
            "inventory": [self._unit_to_dict(u) for u in self.hero.inventory],
            "equipment": {
                slot: self._unit_to_dict(u)
                for slot, u in self.hero.equipment.items()
            },
            "skill_tree": self.hero.skill_tree,
        }
        enemy_data: List[Dict[str, Any]] = []
        for enemy in getattr(self, "enemy_heroes", []):
            enemy_data.append(
                {
                    "x": enemy.x,
                    "y": enemy.y,
                    "army": [self._unit_to_dict(u) for u in enemy.army],
                }
            )
        player_armies: List[Dict[str, Any]] = []
        for army in getattr(self.world, "player_armies", []):
            player_armies.append(
                {
                    "x": army.x,
                    "y": army.y,
                    "ap": army.ap,
                    "max_ap": army.max_ap,
                    "units": [self._unit_to_dict(u) for u in army.units],
                }
            )
        tiles: List[List[Dict[str, Any]]] = []
        for row in self.world.grid:
            row_data: List[Dict[str, Any]] = []
            for tile in row:
                t: Dict[str, Any] = {
                    "biome": tile.biome,
                    "obstacle": tile.obstacle,
                }
                if tile.treasure is not None:
                    t["treasure"] = tile.treasure
                if tile.enemy_units:
                    t["enemy_units"] = [self._unit_to_dict(u) for u in tile.enemy_units]
                if tile.building:
                    t["building"] = {
                        "id": tile.building.image,
                        "owner": tile.building.owner,
                        "level": getattr(tile.building, "level", 1),
                    }
                    if tile.building.garrison:
                        t["building"]["garrison"] = [
                            self._unit_to_dict(u) for u in tile.building.garrison
                        ]
                row_data.append(t)
            tiles.append(row_data)
        world_data = {
            "width": self.world.width,
            "height": self.world.height,
            "tiles": tiles,
            "flora_props": [
                {
                    "asset_id": p.asset_id,
                    "biome": p.biome,
                    "tile_xy": list(p.tile_xy),
                    "variant": p.variant,
                }
                for p in getattr(self.world, "flora_props", [])
            ],
        }
        return {
            "version": SAVE_FORMAT_VERSION,
            "map_size": getattr(self, "map_size", constants.DEFAULT_MAP_SIZE),
            "scenario": getattr(self, "scenario", None),
            "hero": hero_data,
            "world": world_data,
            "player_armies": player_armies,
            "enemy_heroes": enemy_data,
            "event_queue": getattr(self, "event_queue", []),
            "objectives": getattr(self, "objectives", []),
            "starting_town": getattr(self, "starting_town", None),
        }

    def _upgrade_save(self, data: Dict[str, Any], version: int) -> Dict[str, Any]:
        """Upgrade a save file in-place to the current format."""
        if version < 1:
            data["version"] = SAVE_FORMAT_VERSION
        return data

    def _load_state(self, data: Dict[str, Any]) -> None:
        hero_info = data["hero"]
        colour = tuple(
            hero_info.get("colour", getattr(self, "player_colour", constants.BLUE))
        )
        faction_val = hero_info.get("faction", Faction.RED_KNIGHTS.value)
        faction = Faction(faction_val) if isinstance(faction_val, str) else faction_val
        hero = Hero(
            hero_info["x"],
            hero_info["y"],
            [],
            name=hero_info.get("name", getattr(self, "player_name", "Hero")),
            colour=colour,
            faction=faction,
        )
        self.player_name = hero.name
        self.player_colour = hero.colour
        self.faction = hero.faction
        hero.gold = hero_info.get("gold", 0)
        hero.mana = hero_info.get("mana", 3)
        hero.ap = hero_info.get("ap", hero.max_ap)
        hero.max_ap = hero_info.get("max_ap", hero.max_ap)
        hero.army = [self._unit_from_dict(u) for u in hero_info.get("army", [])]
        hero.inventory = [
            self._unit_from_dict(u) for u in hero_info.get("inventory", [])
        ]
        hero.equipment = {
            slot: self._unit_from_dict(u)
            for slot, u in hero_info.get("equipment", {}).items()
        }
        hero.resources = hero_info.get("resources", hero.resources)
        hero.skill_tree = hero_info.get("skill_tree", hero.skill_tree)
        hero.apply_bonuses_to_army()

        world_info = data["world"]
        width = world_info["width"]
        height = world_info["height"]
        world = WorldMap(width=width, height=height, num_obstacles=0, num_treasures=0, num_enemies=0)
        for y, row in enumerate(world_info["tiles"]):
            for x, tile_data in enumerate(row):
                tile = world.grid[y][x]
                tile.biome = tile_data.get("biome", "scarletia_echo_plain")
                tile.obstacle = tile_data.get("obstacle", False)
                treasure = tile_data.get("treasure")
                if isinstance(treasure, dict):
                    gold = treasure.get("gold")
                    exp = treasure.get("exp")
                    if isinstance(gold, list):
                        treasure["gold"] = tuple(gold)
                    if isinstance(exp, list):
                        treasure["exp"] = tuple(exp)
                tile.treasure = treasure
                enemies = tile_data.get("enemy_units")
                tile.enemy_units = [self._unit_from_dict(u) for u in enemies] if enemies else None
                building_info = tile_data.get("building")
                if building_info:
                    bid = building_info.get("id")
                    building: Building | None = None
                    if bid == "town":
                        building = Town()
                    else:
                        key = bid
                        if key not in BUILDINGS:
                            key = os.path.basename(os.path.dirname(bid)) if "/" in bid else os.path.splitext(bid)[0]
                        if key in BUILDINGS:
                            building = create_building(key)
                    if building:
                        building.owner = building_info.get("owner")
                        building.level = building_info.get("level", 1)
                        if getattr(building, "production_per_level", {}):
                            building.income = {
                                res: val * building.level
                                for res, val in building.production_per_level.items()
                            }
                        garrison_info = building_info.get("garrison")
                        if garrison_info:
                            building.garrison = [
                                self._unit_from_dict(u) for u in garrison_info
                            ]
                        tile.building = building
        flora_infos = world_info.get("flora_props", [])
        world.flora_props = []
        world.collectibles = {}
        loader = getattr(self, "flora_loader", None)
        if loader:
            for info in flora_infos:
                asset = loader.assets.get(info["asset_id"])
                if not asset:
                    continue
                x, y = info.get("tile_xy", [0, 0])
                rect_world = pygame.Rect(
                    x * loader.tile,
                    y * loader.tile,
                    asset.footprint[0] * loader.tile,
                    asset.footprint[1] * loader.tile,
                )
                prop = PropInstance(
                    info["asset_id"],
                    info.get("biome", ""),
                    (x, y),
                    info.get("variant", 0),
                    asset.footprint,
                    asset.anchor_px,
                    asset.passable,
                    asset.occludes,
                    rect_world,
                )
                world.flora_props.append(prop)
                if asset.type == "collectible":
                    fw, fh = asset.footprint
                    for yy in range(y, y + fh):
                        for xx in range(x, x + fw):
                            world.collectibles[(xx, yy)] = prop
            world._build_flora_prop_index()
        self.hero = hero
        self.world = world
        self.map_size = data.get("map_size", constants.DEFAULT_MAP_SIZE)
        self.scenario = data.get("scenario")
        self.objectives = data.get("objectives", [])
        self.world.player_armies = []
        for info in data.get("player_armies", []):
            units = [self._unit_from_dict(u) for u in info.get("units", [])]
            army = Army(info["x"], info["y"], units, ap=info.get("ap", 0), max_ap=info.get("max_ap", 0))
            self.world.player_armies.append(army)
        self.enemy_heroes = []
        for info in data.get("enemy_heroes", []):
            army = [self._unit_from_dict(u) for u in info.get("army", [])]
            self.enemy_heroes.append(EnemyHero(info["x"], info["y"], army))
        self.event_queue = data.get("event_queue", [])
        st = data.get("starting_town")
        self.starting_town = tuple(st) if isinstance(st, list) else self.world.hero_town
        self._game_over_shown = False
        # Recreate minimal state container used by the UI and reset selection
        self.state = GameState(world=self.world, heroes=[self.hero] + self.world.player_armies)
        self.hero_idx = 0
        self.active_actor = self.hero
        self._econ_building_map = {}
        self.state.economy.players[0] = economy.PlayerEconomy()
        self._sync_economy_from_hero()
        for row in self.world.grid:
            for tile in row:
                if tile.building:
                    b = tile.building
                    econ_b = economy.Building(
                        id=getattr(b, "name", ""),
                        owner=getattr(b, "owner", None),
                        provides=dict(getattr(b, "income", {})),
                        growth_per_week=dict(getattr(b, "growth_per_week", {})),
                        stock=dict(getattr(b, "stock", {})),
                        level=getattr(b, "level", 1),
                        upgrade_cost=dict(getattr(b, "upgrade_cost", {})),
                        production_per_level=dict(getattr(b, "production_per_level", {})),
                    )
                    self.state.economy.buildings.append(econ_b)
                    self._econ_building_map[b] = econ_b
        self._init_town_ownership()
        if not getattr(self, "_town_control_subscribed", False):
            EVENT_BUS.subscribe(ON_TURN_END, self._update_town_control)
            self._town_control_subscribed = True

    def save_game(self, path: str, profile_path: str | None = None) -> None:
        """Serialise the current game state to JSON files.

        The main game state is written to ``path`` while the hero's inventory,
        equipment and skill tree are stored separately in ``profile_path``.
        """
        data = self._serialize_state()
        hero = data["hero"]
        profile = {
            key: hero.get(key, {})
            for key in ("inventory", "equipment", "skill_tree")
        }
        hero.pop("inventory", None)
        hero.pop("equipment", None)
        hero.pop("skill_tree", None)
        if profile_path is None:
            base = os.path.dirname(path)
            prefix = os.path.splitext(os.path.basename(path))[0]
            digits = ''.join(filter(str.isdigit, prefix))
            name = f"save_profile{digits}.json" if digits else "save_profile.json"
            profile_path = os.path.join(base, name)
        with open(profile_path, "w", encoding="utf-8") as f:
            json.dump(profile, f)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)

    def quick_save(self) -> None:
        """Convenience wrapper saving to the predefined quick-save slot."""
        base = os.path.dirname(__file__)
        if self.scenario:
            scen_name = os.path.splitext(os.path.basename(self.scenario))[0]
            base = os.path.join(base, scen_name)
        path = os.path.join(base, QUICK_SAVE_FILE)
        profile = os.path.join(base, QUICK_PROFILE_FILE)
        self.save_game(path, profile)

    def quick_load(self) -> None:
        """Load the quick-save file if it exists."""

        base = os.path.dirname(__file__)
        if self.scenario:
            scen_name = os.path.splitext(os.path.basename(self.scenario))[0]
            base = os.path.join(base, scen_name)
        path = os.path.join(base, QUICK_SAVE_FILE)
        profile = os.path.join(base, QUICK_PROFILE_FILE)
        if os.path.exists(path):
            self.load_game(path, profile)

    def load_game(self, path: str, profile_path: str | None = None) -> None:
        """Load game state from JSON files."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if profile_path is None:
            base = os.path.dirname(path)
            prefix = os.path.splitext(os.path.basename(path))[0]
            digits = ''.join(filter(str.isdigit, prefix))
            name = f"save_profile{digits}.json" if digits else "save_profile.json"
            profile_path = os.path.join(base, name)
        if os.path.exists(profile_path):
            with open(profile_path, "r", encoding="utf-8") as f:
                profile = json.load(f)
            data.setdefault("hero", {}).update(profile)
        version = data.get("version", 0)
        if version < SAVE_FORMAT_VERSION:
            data = self._upgrade_save(data, version)
        self._load_state(data)
