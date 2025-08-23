"""
World map generation and rendering for the graphical Heroes‑like game.

The `WorldMap` encapsulates a grid of tiles that the hero can explore.  Tiles
may be passable grass, impassable obstacles, treasure chests or enemy
encounters.  This module also provides a `draw` method that renders the
current state of the world onto a Pygame surface using supplied images.
"""

from __future__ import annotations

import json
import logging
import os
import random
from enum import Enum, auto
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Set, TYPE_CHECKING, Sequence

try:  # pragma: no cover - pygame is only required for rendering
    import pygame
except ImportError:  # pragma: no cover
    pygame = None

import constants
from core.entities import (
    Unit,
    Hero,
    EnemyHero,
    FUMEROLLE_LIZARD_STATS,
    SHADOWLEAF_WOLF_STATS,
    BOAR_RAVEN_STATS,
    HURLOMBE_STATS,
    Army,
    UnitCarrier,
)
from core.buildings import create_building, Town, Building
from core import economy
from render.autotile import AutoTileRenderer
try:  # flora loader is optional for tests without pygame
    from loaders.flora_loader import FloraLoader, PropInstance
except Exception:  # pragma: no cover
    FloraLoader = PropInstance = None  # type: ignore
from loaders.biomes import BiomeCatalog
from .vision import compute_vision
from core.ai.creature_ai import (
    CreatureAI,
    CreatureBehavior,
    GuardianAI,
    RoamingAI,
)


logger = logging.getLogger(__name__)


# Type hints for optional flora integration
if TYPE_CHECKING:  # pragma: no cover
    from loaders.flora_loader import FloraLoader, PropInstance

# Mapping from unit names to image identifiers for enemy stacks
# Only creatures populate the world map; enemy hero armies still use the
# recruitable units defined elsewhere.
ENEMY_UNIT_IMAGES: Dict[str, str] = {
    FUMEROLLE_LIZARD_STATS.name: FUMEROLLE_LIZARD_STATS.name,
    SHADOWLEAF_WOLF_STATS.name: SHADOWLEAF_WOLF_STATS.name,
    BOAR_RAVEN_STATS.name: BOAR_RAVEN_STATS.name,
    HURLOMBE_STATS.name: HURLOMBE_STATS.name,
}

# Number of tiles grouped into a single flora chunk used for spatial indexing
FLORA_CHUNK_TILES = 32

# All known creature stats indexed by their unique name
CREATURE_STATS: Dict[str, "UnitStats"] = {
    FUMEROLLE_LIZARD_STATS.name: FUMEROLLE_LIZARD_STATS,
    SHADOWLEAF_WOLF_STATS.name: SHADOWLEAF_WOLF_STATS,
    BOAR_RAVEN_STATS.name: BOAR_RAVEN_STATS,
    HURLOMBE_STATS.name: HURLOMBE_STATS,
}


def _reset_town_counter() -> None:
    """Reset the town naming counter for a fresh game session."""
    Town._counter = 0


def _load_creatures_by_biome() -> Tuple[
    Dict[str, List[str]], Dict[str, Tuple[CreatureBehavior, int]]
]:
    """Load creature spawn data from ``assets/units/creatures.json``.

    Each entry provides the list of ``biomes`` it inhabits as well as optional
    ``behavior`` and ``guard_range`` fields.  Returns a tuple of two mappings:
    biome → creature ids and creature id → (behaviour, guard_range).
    Falls back to a default mapping if the manifest is missing or malformed.
    """

    path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__), "..", "assets", "units", "creatures.json"
        )
    )
    mapping: Dict[str, List[str]] = {}
    behaviour: Dict[str, Tuple[CreatureBehavior, int]] = {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, list):
            for entry in data:
                try:
                    cid = entry["id"]
                    for biome in entry.get("biomes", []):
                        mapping.setdefault(str(biome), []).append(cid)
                    beh = entry.get("behavior", "roamer")
                    try:
                        mode = CreatureBehavior(beh)
                    except ValueError:
                        mode = CreatureBehavior.ROAMER
                    guard = int(entry.get("guard_range", 3))
                    behaviour[cid] = (mode, guard)
                except Exception:
                    continue
    except Exception as exc:  # pragma: no cover - simple logging
        logger.warning("Failed to load creature manifest from %s: %s", path, exc)
    if mapping:
        return mapping, behaviour
    return (
        {
            "scarletia_echo_plain": ["boar_raven"],
            "scarletia_crimson_forest": ["shadowleaf_wolf", "hurlombe"],
            "mountain": ["hurlombe", "boar_raven"],
            "scarletia_volcanic": ["fumet_lizard"],
        },
        {
            "boar_raven": (CreatureBehavior.ROAMER, 2),
            "shadowleaf_wolf": (CreatureBehavior.ROAMER, 3),
            "fumet_lizard": (CreatureBehavior.ROAMER, 3),
            "hurlombe": (CreatureBehavior.GUARDIAN, 2),
        },
    )


CREATURES_BY_BIOME, CREATURE_BEHAVIOUR = _load_creatures_by_biome()
DEFAULT_ENEMY_UNITS: List[str] = [
    FUMEROLLE_LIZARD_STATS.name,
    SHADOWLEAF_WOLF_STATS.name,
    BOAR_RAVEN_STATS.name,
    HURLOMBE_STATS.name,
]



class Biome(Enum):
    """Possible terrain types for a tile."""
    GRASS = auto()
    FOREST = auto()
    DESERT = auto()
    MOUNTAIN = auto()
    HILLS = auto()
    SWAMP = auto()
    JUNGLE = auto()
    ICE = auto()
    COAST = auto()
    OCEAN = auto()


# Mapping from biome names to asset names and fallback colours used when
# rendering tiles.  Populated from :class:`BiomeCatalog` so new biomes from the
# manifest automatically become available.
BIOME_IMAGES: Dict[str, Tuple[str, Tuple[int, int, int]]] = {}


def init_biome_images() -> None:
    """(Re)build :data:`BIOME_IMAGES` from :class:`BiomeCatalog`."""

    images: Dict[str, Tuple[str, Tuple[int, int, int]]] = {}
    for biome in BiomeCatalog._biomes.values():
        paths = constants.BIOME_BASE_IMAGES.get(biome.id, [""])
        base = paths[0] if isinstance(paths, list) else paths
        images[biome.id] = (base, biome.colour)
    images.update(
        {
            "mountain": (
                constants.BIOME_BASE_IMAGES.get("mountain", [""])[0],
                constants.GREY,
            ),
            "hills": (
                constants.BIOME_BASE_IMAGES.get("hills", [""])[0],
                constants.GREY,
            ),
            "swamp": (
                constants.BIOME_BASE_IMAGES.get("swamp", [""])[0],
                constants.GREEN,
            ),
            "jungle": (
                constants.BIOME_BASE_IMAGES.get("jungle", [""])[0],
                constants.GREEN,
            ),
            "ice": (
                constants.BIOME_BASE_IMAGES.get("ice", [""])[0],
                constants.WHITE,
            ),
            "ocean": (
                constants.BIOME_BASE_IMAGES.get("ocean", [""])[0],
                constants.BLUE,
            ),
        }
    )
    # Ensure placeholder entries for core Scarletiа biomes even if the catalog
    # has not been loaded yet (e.g. in unit tests using ``WorldMap`` directly).
    images.setdefault(
        "scarletia_echo_plain",
        (constants.BIOME_BASE_IMAGES.get("grass", [""])[0], constants.GREEN),
    )
    images.setdefault(
        "scarletia_crimson_forest",
        (constants.BIOME_BASE_IMAGES.get("forest", [""])[0], constants.GREEN),
    )
    images.setdefault(
        "scarletia_volcanic",
        (constants.BIOME_BASE_IMAGES.get("desert", [""])[0], constants.YELLOW),
    )
    global BIOME_IMAGES
    BIOME_IMAGES = images


# Initialise mapping with whatever is currently loaded in the catalogue.  The
# game refreshes this after loading the manifest.
init_biome_images()


def generate_combat_map(
    world: "WorldMap", x: int, y: int, width: int = 8, height: int = 6
) -> Tuple[List[List[str]], List["PropInstance"]]:
    """Create a biome grid for combat based on the world map.

    The returned grid has ``width``×``height`` cells and initially copies the
    biome of the source tile ``(x, y)``.  If the source tile borders a
    different biome, the second biome is mixed in using a simple checkerboard
    pattern.  Decorative flora props are generated using the world's existing
    ``flora_loader`` when available.
    """

    origin_biome = world.grid[y][x].biome
    grid = [[origin_biome for _ in range(width)] for _ in range(height)]

    neighbours: Set[str] = set()
    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        nx, ny = x + dx, y + dy
        if 0 <= nx < world.width and 0 <= ny < world.height:
            neighbours.add(world.grid[ny][nx].biome)

    neighbours.discard("ocean")
    secondary = next((b for b in neighbours if b != origin_biome), None)
    if "ocean" in {origin_biome, secondary}:
        fill = secondary if origin_biome == "ocean" else origin_biome
        if fill:
            grid = [[fill for _ in range(width)] for _ in range(height)]
    elif secondary:
        for yy in range(height):
            for xx in range(width):
                if (xx + yy) % 2:
                    grid[yy][xx] = secondary

    flora_props: List["PropInstance"] = []
    loader = getattr(world, "flora_loader", None)
    if loader:
        tags = [["" for _ in range(width)] for _ in range(height)]
        allowed: Dict[str, List[str]] = {}
        for biome_id in {cell for row in grid for cell in row}:
            biome = BiomeCatalog.get(biome_id)
            if biome and biome.flora:
                allowed[biome_id] = biome.flora
        flora_props = loader.autoplace(grid, tags, 0, allowed if allowed else None)

    return grid, flora_props

# Mapping from single-character codes in map files to biome names.  Certain
# biomes such as ``mountain`` and ``ocean`` are intrinsically impassable.
BIOME_CHAR_MAP = {
    "G": "scarletia_echo_plain",
    "F": "scarletia_crimson_forest",
    "D": "scarletia_volcanic",
    "M": "mountain",
    "H": "hills",
    "S": "swamp",
    "J": "jungle",
    "I": "ice",
    "R": "river",
    "W": "ocean",
    "O": "ocean",  # backward compatibility
}
BIOME_CHARS = set(BIOME_CHAR_MAP.keys())



@dataclass(slots=True)
class Tile:
    """Represents a single map tile.

    Only dynamic attributes are stored on the ``Tile`` instance itself.  Static
    per‑tile data such as the biome type and obstacle flag are kept in the
    parent :class:`WorldMap` as separate arrays for better cache locality and
    reduced memory usage.
    """

    world: "WorldMap"
    x: int
    y: int
    treasure: Optional[Dict[str, Tuple[int, int]]] = None
    enemy_units: Optional[List[Unit]] = None
    # Optional strategic resource deposit present on this tile
    resource: Optional[str] = None
    # Optional building such as a mine or sawmill
    building: Optional['Building'] = None
    owner: Optional[int] = None

    @property
    def biome(self) -> str:
        return self.world.biomes[self.y][self.x]

    @biome.setter
    def biome(self, value: str) -> None:  # pragma: no cover - trivial
        self.world.biomes[self.y][self.x] = value

    @property
    def obstacle(self) -> bool:
        return self.world.obstacles[self.y][self.x]

    @obstacle.setter
    def obstacle(self, value: bool) -> None:  # pragma: no cover - trivial
        self.world.obstacles[self.y][self.x] = value

    def capture(
        self,
        hero: "Hero",
        new_owner: int,
        econ_state: Optional["economy.GameEconomyState"] = None,
        econ_building: Optional["economy.Building"] = None,
    ) -> bool:
        if self.building and not self.building.garrison and self.building.owner != new_owner:
            self.building.interact(hero)
            self.building.owner = new_owner
            self.owner = new_owner
            if econ_state and econ_building:
                economy.capture_building(
                    econ_state,
                    econ_building,
                    new_owner,
                    getattr(self.building, "level", 1),
                )
                if new_owner != 1:
                    econ_building.garrison.clear()
            return True
        return False

    def is_passable(self) -> bool:
        """Return ``True`` if the tile can be entered by units."""
        biome = BiomeCatalog.get(self.biome)
        passable = (
            biome.passable if biome is not None else self.biome not in constants.IMPASSABLE_BIOMES
        )
        if self.building and not getattr(self.building, "passable", True):
            return False
        return passable and not self.obstacle


class WorldMap:
    """
    Generates and draws the exploration map.  A world map can either be
    procedurally generated with random placement of obstacles, treasures and
    enemies, or loaded from a text representation where each character
    describes the contents of a tile.  Use the `from_file` class method to
    construct a map from a file.
    """
    def __init__(
        self,
        width: Optional[int] = None,
        height: Optional[int] = None,
        num_obstacles: int = 0,
        num_treasures: int = 0,
        num_enemies: int = 0,
        num_resources: float = 7.5,
        num_buildings: int = 0,
        map_data: Optional[List[str]] = None,
        size_range: Tuple[int, int] = constants.WORLD_SIZE_RANGE,
        biome_weights: Optional[Dict[str, float]] = None,
    ) -> None:
        _reset_town_counter()
        self.hero_start: Optional[Tuple[int, int]] = None
        self.enemy_start: Optional[Tuple[int, int]] = None
        # Track town locations separately from hero spawn positions
        self.hero_town: Optional[Tuple[int, int]] = None
        self.enemy_town: Optional[Tuple[int, int]] = None
        self.starting_area: Optional[Tuple[int, int, int]] = None
        self.enemy_starting_area: Optional[Tuple[int, int, int]] = None
        # Neutral creature groups present on the map
        self.creatures: List[CreatureAI] = []

        if map_data:
            parsed_rows = [self._parse_row(row) for row in map_data]
            self.height = len(parsed_rows)
            self.width = max(len(r) for r in parsed_rows) if parsed_rows else 0
        else:
            if width is None:
                width = random.randint(*size_range)
            if height is None:
                height = random.randint(*size_range)
            self.width = width
            self.height = height

        # Arrays storing invariant per-tile data
        self.biomes: List[List[str]] = [
            ["scarletia_echo_plain" for _ in range(self.width)]
            for _ in range(self.height)
        ]
        self.obstacles: List[List[bool]] = [
            [False for _ in range(self.width)] for _ in range(self.height)
        ]
        # Grid of tile objects referencing the above arrays
        self.grid: List[List[Tile]] = [
            [Tile(self, x, y) for x in range(self.width)] for y in range(self.height)
        ]

        if map_data:
            self._load_from_parsed_data(parsed_rows)
            self._create_starting_area()

        total_tiles = max(1, self.width * self.height)
        if num_resources > 1:
            if num_resources > 100:
                self.resource_density = (num_resources / total_tiles) * 100
            else:
                self.resource_density = num_resources
        else:
            self.resource_density = num_resources * 100

        if not map_data:
            self._assign_biomes(biome_weights)
            self._place_obstacles(num_obstacles)
            self._place_treasures(num_treasures)
            self._generate_clusters(random, num_enemies)
            if self.resource_density > 0:
                self._scatter_resources(random)
            self._place_buildings(num_buildings)
        else:
            if self.resource_density > 0:
                self._scatter_resources(random)
            if num_buildings:
                self._place_resources()

        # Per-player fog of war state. ``visible`` marks tiles currently seen,
        # while ``explored`` remembers tiles that have ever been seen.  Entries
        # are created lazily for players when updating visibility.
        self.visible: Dict[int, List[List[bool]]] = {}
        self.explored: Dict[int, List[List[bool]]] = {}

        # Armies controlled by the player that roam the world map
        self.player_armies: List[Army] = []

        # Data used by the autotile renderer
        self.biome_grid: List[List[str]] = []
        self.water_map: List[List[bool]] = []
        self.renderer: Optional[AutoTileRenderer] = None
        self._build_render_maps()
        # Create a basic autotile renderer so ``WorldRenderer`` can always draw
        # terrain using texture files instead of solid colours.
        self.renderer = AutoTileRenderer(None, constants.TILE_SIZE)
        for biome, variants in constants.BIOME_BASE_IMAGES.items():
            self.renderer.register_biome(biome, variants)

        # Optional flora decorations populated via FloraLoader
        self.flora_loader: Optional[FloraLoader] = None
        self.flora_props: List[PropInstance] = []
        self.collectibles: Dict[Tuple[int, int], PropInstance] = {}
        self.flora_prop_chunks: Dict[Tuple[int, int], List[PropInstance]] = {}

    def _place_obstacles(self, count: int) -> None:
        """Randomly place a number of impassable obstacles."""
        tiles = self._empty_land_tiles()
        for x, y in random.sample(tiles, k=min(count, len(tiles))):
            self.grid[y][x].obstacle = True

    def _build_render_maps(self) -> None:
        """Prepare biome and water lookup grids for the renderer."""
        self.biome_grid = self.biomes
        self.water_map = [
            [biome in {"ocean", "river"} for biome in row] for row in self.biomes
        ]

    # ------------------------------------------------------------------
    #def populate_flora(self, loader: "FloraLoader", rng_seed: Optional[int] = None) -> None:
    #    """Populate decorative flora using ``loader``.

     #   ``rng_seed`` allows deterministic placement.  Generated props are stored
     #   on the instance for later rendering.
     #   """
     #   seed = rng_seed if rng_seed is not None else random.randint(0, 1_000_000)
     #   self.flora_loader = loader
     #   self.flora_props = loader.autoplace(self.biome_grid, None, rng_seed=seed)
    
    def populate_flora(self, loader: Optional[FloraLoader], rng_seed: int = 0) -> None:
        """Automatically place flora props on the map.

        ``loader`` is a :class:`FloraLoader` instance responsible for
        generating ``PropInstance`` objects.  ``rng_seed`` seeds the random
        placement.
        """
        if loader is None:
            return
        self.flora_loader = loader

        tags_grid: List[List[str]] = []
        for y, row in enumerate(self.grid):
            tag_row: List[str] = []
            for x, tile in enumerate(row):
                if self.water_map[y][x]:
                    tag_row.append("water")
                elif (
                    tile.obstacle
                    or tile.building is not None
                    or tile.treasure is not None
                    or tile.enemy_units is not None
                    or tile.resource is not None
                ):
                    tag_row.append("obstacle")
                else:
                    tag_row.append("")
            tags_grid.append(tag_row)

        # Limiter optionnellement certains biomes à leur propre flore déclarée
        allowed_flora: Dict[str, List[str]] = {}
        for biome_id in {tile.biome for row in self.grid for tile in row}:
            biome = BiomeCatalog.get(biome_id)
            if biome and biome.flora:
                allowed_flora[biome_id] = biome.flora

        self.flora_props = loader.autoplace(
            self.biome_grid, tags_grid, rng_seed, allowed_flora if allowed_flora else None
        )
        self.collectibles = {}
        for prop in self.flora_props:
            if loader.assets.get(prop.asset_id) and loader.assets[prop.asset_id].type == "collectible":
                x0, y0 = prop.tile_xy
                fw, fh = prop.footprint
                for yy in range(y0, y0 + fh):
                    for xx in range(x0, x0 + fw):
                        self.collectibles[(xx, yy)] = prop
            if not prop.passable:
                x0, y0 = prop.tile_xy
                fw, fh = prop.footprint
                for yy in range(y0, y0 + fh):
                    for xx in range(x0, x0 + fw):
                        self.grid[yy][xx].obstacle = True

        self._build_flora_prop_index()

    def _build_flora_prop_index(self) -> None:
        """Rebuild the spatial index for ``flora_props``."""
        chunk_px = FLORA_CHUNK_TILES * constants.TILE_SIZE
        self.flora_prop_chunks = {}
        for prop in self.flora_props:
            rect = getattr(prop, "rect_world", None)
            if not rect or not hasattr(rect, "x"):
                continue
            x0 = rect.x
            y0 = rect.y
            x1 = x0 + rect.width
            y1 = y0 + rect.height
            cx0 = x0 // chunk_px
            cy0 = y0 // chunk_px
            cx1 = (x1 - 1) // chunk_px
            cy1 = (y1 - 1) // chunk_px
            for cy in range(cy0, cy1 + 1):
                for cx in range(cx0, cx1 + 1):
                    self.flora_prop_chunks.setdefault((cx, cy), []).append(prop)

    def invalidate_prop_chunk(self, prop: PropInstance) -> None:
        """Rebuild the chunk(s) containing ``prop`` in the flora index."""
        rect = getattr(prop, "rect_world", None)
        if not rect or not hasattr(rect, "x"):
            return
        chunk_px = FLORA_CHUNK_TILES * constants.TILE_SIZE
        x0 = rect.x
        y0 = rect.y
        x1 = x0 + rect.width
        y1 = y0 + rect.height
        cx0 = x0 // chunk_px
        cy0 = y0 // chunk_px
        cx1 = (x1 - 1) // chunk_px
        cy1 = (y1 - 1) // chunk_px
        for cy in range(cy0, cy1 + 1):
            for cx in range(cx0, cx1 + 1):
                key = (cx, cy)
                chunk_left = cx * chunk_px
                chunk_top = cy * chunk_px
                chunk_right = chunk_left + chunk_px
                chunk_bottom = chunk_top + chunk_px
                props: List[PropInstance] = []
                for p in self.flora_props:
                    r2 = getattr(p, "rect_world", None)
                    if not r2 or not hasattr(r2, "x"):
                        continue
                    px0 = r2.x
                    py0 = r2.y
                    px1 = px0 + r2.width
                    py1 = py0 + r2.height
                    if (
                        px0 < chunk_right
                        and px1 > chunk_left
                        and py0 < chunk_bottom
                        and py1 > chunk_top
                    ):
                        props.append(p)
                if props:
                    self.flora_prop_chunks[key] = props
                else:
                    self.flora_prop_chunks.pop(key, None)

    def _ensure_player_fog(self, player_id: int) -> None:
        """Initialise fog of war matrices for ``player_id`` if missing."""
        if player_id not in self.visible:
            self.visible[player_id] = [
                [False for _ in range(self.width)] for _ in range(self.height)
            ]
            self.explored[player_id] = [
                [False for _ in range(self.width)] for _ in range(self.height)
            ]

    def update_visibility(
        self, player_id: int, actor: UnitCarrier, *, reset: bool = True
    ) -> None:
        """Recalculate which tiles ``player_id`` can currently see.

        ``actor`` is the viewer whose vision is taken into account. Visible
        tiles are recomputed using :func:`compute_vision`. When ``reset`` is
        ``True`` the existing visibility matrix is cleared before applying the
        new tiles allowing callers to accumulate vision from multiple actors by
        calling this method repeatedly with ``reset=False`` for subsequent
        actors. Newly seen tiles are also marked as explored.
        """
        self._ensure_player_fog(player_id)
        vis = self.visible[player_id]
        if reset:
            for row in vis:
                for i in range(len(row)):
                    row[i] = False
        tiles = compute_vision(self, actor)
        expl = self.explored[player_id]
        for x, y in tiles:
            vis[y][x] = True
            expl[y][x] = True

    def reveal(self, player_id: int, x: int, y: int, radius: int = 2) -> None:
        """Mark tiles in a square ``radius`` around ``(x, y)`` as seen."""
        self._ensure_player_fog(player_id)
        vis = self.visible[player_id]
        expl = self.explored[player_id]
        for yy in range(max(0, y - radius), min(self.height, y + radius + 1)):
            for xx in range(max(0, x - radius), min(self.width, x + radius + 1)):
                vis[yy][xx] = True
                expl[yy][xx] = True

    def _can_place_building(self, x: int, y: int, building: "Building") -> bool:
        """Return ``True`` if ``building`` fits at ``(x, y)``."""
        for dx, dy in building.footprint:
            xx, yy = x + dx, y + dy
            if not self.in_bounds(xx, yy):
                return False
            tile = self.grid[yy][xx]
            if (
                tile.obstacle
                or tile.treasure is not None
                or tile.enemy_units is not None
                or tile.resource is not None
                or tile.building is not None
            ):
                return False
        return True

    def _stamp_building(self, x: int, y: int, building: "Building") -> None:
        """Place ``building`` at ``(x, y)`` marking all tiles in its footprint."""
        building.origin = (x, y)
        for dx, dy in building.footprint:
            xx, yy = x + dx, y + dy
            if self.in_bounds(xx, yy):
                tile = self.grid[yy][xx]
                tile.building = building
                if not building.passable:
                    tile.obstacle = True

    def _assign_biomes(self, weights: Optional[Dict[str, float]] = None) -> None:
        """Randomly assign a biome to every tile.

        ``weights`` is a mapping of biome name to relative weight, allowing a
        caller to favour certain terrains when generating the map.
        """
        if weights is None:
            weights = constants.DEFAULT_BIOME_WEIGHTS
        biomes = list(weights.keys())
        probs = list(weights.values())
        for row in self.grid:
            for tile in row:
                tile.biome = random.choices(biomes, probs)[0]

    def _empty_land_tiles(self) -> List[Tuple[int, int]]:
        """Return coordinates of land tiles without any features.

        Tiles considered are those whose biome is passable and do not already
        contain an obstacle, treasure or enemy.  This helper avoids infinite
        placement loops when the map has little or no free land available.
        """
        coords: List[Tuple[int, int]] = []
        for y, row in enumerate(self.grid):
            for x, tile in enumerate(row):
                biome = BiomeCatalog.get(tile.biome)
                passable = (
                    biome.passable if biome is not None else tile.biome not in constants.IMPASSABLE_BIOMES
                )
                if (
                    passable
                    and not tile.obstacle
                    and tile.treasure is None
                    and tile.enemy_units is None
                    and tile.resource is None
                    and tile.building is None
                ):
                    coords.append((x, y))
        return coords

    def _adjacent_free_tile(self, x: int, y: int) -> Optional[Tuple[int, int]]:
        """Return a free passable tile adjacent to ``(x, y)`` if any.

        Considers the four cardinal directions and returns the first coordinate
        that is in bounds, passable and without buildings, treasures or enemy
        units.  Returns ``None`` if no such tile exists.
        """

        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = x + dx, y + dy
            if not self.in_bounds(nx, ny):
                continue
            tile = self.grid[ny][nx]
            if (
                tile.is_passable()
                and tile.building is None
                and tile.treasure is None
                and tile.enemy_units is None
            ):
                return (nx, ny)
        return None

    def adjacent_enemy_hero(
        self, x: int, y: int, enemies: Sequence[EnemyHero]
    ) -> Optional[EnemyHero]:
        """Return an enemy hero adjacent to ``(x, y)`` if one exists.

        Checks the four cardinal directions around the provided coordinates
        and returns the first enemy hero whose position matches.  Returns
        ``None`` when no enemy hero is adjacent.
        """

        for enemy in enemies:
            if abs(enemy.x - x) + abs(enemy.y - y) == 1:
                return enemy
        return None

    def _find_continents(self) -> List[List[Tuple[int, int]]]:
        """Return lists of coordinates for each landmass.

        Tiles considered part of a continent are those that are not ocean.
        Coast tiles are treated as land so buildings can appear on shorelines.
        """
        visited: Set[Tuple[int, int]] = set()
        continents: List[List[Tuple[int, int]]] = []
        for y in range(self.height):
            for x in range(self.width):
                if (x, y) in visited:
                    continue
                tile = self.grid[y][x]
                if tile.biome == "ocean":
                    continue
                queue = [(x, y)]
                visited.add((x, y))
                cells: List[Tuple[int, int]] = []
                while queue:
                    cx, cy = queue.pop()
                    cells.append((cx, cy))
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        nx, ny = cx + dx, cy + dy
                        if not self.in_bounds(nx, ny) or (nx, ny) in visited:
                            continue
                        ntile = self.grid[ny][nx]
                        if ntile.biome == "ocean":
                            continue
                        visited.add((nx, ny))
                        queue.append((nx, ny))
                continents.append(cells)
        return continents

    def init_renderer(
        self,
        assets: Dict[str, pygame.Surface],
        biome_variants: Dict[str, List[str]],
        coast_edges: Dict[str, str],
        coast_corners: Dict[str, str],
    ) -> None:
        """Initialise the autotile renderer with terrain and coast overlays."""
        self.renderer = AutoTileRenderer(assets, constants.TILE_SIZE)
        for biome, variants in biome_variants.items():
            self.renderer.register_biome(biome, variants)
        self.renderer.set_coast_overlays(coast_edges, coast_corners)

    def _place_treasures(self, count: int) -> None:
        """Place treasures with biome-dependent probabilities."""
        if count <= 0:
            return
        chances = {
            "scarletia_echo_plain": 0.05,
            "scarletia_crimson_forest": 0.03,
            "scarletia_volcanic": 0.04,
            "mountain": 0.02,
            "ocean": 0.0,
        }

        candidates = self._empty_land_tiles()
        random.shuffle(candidates)
        placed = 0
        for x, y in candidates:
            tile = self.grid[y][x]
            if random.random() < chances.get(tile.biome, 0.1):
                tile.treasure = {"gold": (25, 150), "exp": (40, 80)}
                placed += 1
                if placed >= count:
                    break

    def _create_enemy_army_for_biome(self, biome: str) -> List[Unit]:
        """Generate an enemy army themed to the given biome."""

        creature_names = CREATURES_BY_BIOME.get(biome, DEFAULT_ENEMY_UNITS)
        num_stacks = random.randint(1, 3)
        units: List[Unit] = []
        for _ in range(num_stacks):
            name = random.choice(creature_names)
            stats = CREATURE_STATS.get(name, FUMEROLLE_LIZARD_STATS)
            count = random.randint(5, 12)
            units.append(Unit(stats, count, side="enemy"))
        return units

    def _generate_clusters(self, rng: random.Random, enemy_count: int) -> None:
        """Generate resource/building clusters and attach creature guards."""

        if enemy_count <= 0:
            return
        # approximate Poisson-disc sampling by enforcing minimum distance
        radius = max(4, min(self.width, self.height) // 5)
        points: List[Tuple[int, int]] = []
        attempts = 0
        while len(points) < max(1, enemy_count // 2) and attempts < 2000:
            x = rng.randrange(self.width)
            y = rng.randrange(self.height)
            if any(abs(px - x) + abs(py - y) < radius for px, py in points):
                attempts += 1
                continue
            tile = self.grid[y][x]
            if tile.biome in constants.IMPASSABLE_BIOMES or not tile.is_passable():
                attempts += 1
                continue
            points.append((x, y))
            attempts += 1

        for x, y in points:
            tile = self.grid[y][x]
            # scatter a small cluster of resources around the centre
            resources = [
                ("wood", 5),
                ("stone", 5),
                ("crystal", 2),
                ("gold", 1),
            ]
            ids, weights = zip(*resources)
            for dx in range(-1, 2):
                for dy in range(-1, 2):
                    tx, ty = x + dx, y + dy
                    if not self.in_bounds(tx, ty):
                        continue
                    ttile = self.grid[ty][tx]
                    if ttile.is_passable() and ttile.resource is None and ttile.building is None:
                        if rng.random() < 0.5:
                            ttile.resource = rng.choices(ids, weights)[0]

            # attempt to place a small building at the centre
            building_ids = ["sawmill", "mine", "crystal_mine"]
            b = create_building(rng.choice(building_ids))
            if self._can_place_building(x, y, b):
                self._stamp_building(x, y, b)

            # guardian stack at cluster centre
            units = self._create_enemy_army_for_biome(tile.biome)
            tile.enemy_units = units
            cid = units[0].stats.name
            mode, guard = CREATURE_BEHAVIOUR.get(cid, (CreatureBehavior.ROAMER, 3))
            if mode is CreatureBehavior.GUARDIAN:
                ai = GuardianAI(x, y, units, guard)
            else:
                ai = RoamingAI(x, y, units, guard)
            self.creatures.append(ai)

        # spawn roaming stacks near frontiers
        edge_tiles = [
            (x, y)
            for y in range(self.height)
            for x in range(self.width)
            if x < 2 or y < 2 or x >= self.width - 2 or y >= self.height - 2
        ]
        rng.shuffle(edge_tiles)
        needed = max(0, enemy_count - len(points))
        placed = 0
        for x, y in edge_tiles:
            tile = self.grid[y][x]
            if not tile.is_passable() or tile.enemy_units is not None:
                continue
            units = self._create_enemy_army_for_biome(tile.biome)
            tile.enemy_units = units
            cid = units[0].stats.name
            _, guard = CREATURE_BEHAVIOUR.get(cid, (CreatureBehavior.ROAMER, 3))
            ai = RoamingAI(x, y, units, guard)
            self.creatures.append(ai)
            placed += 1
            if placed >= needed:
                break

    def _scatter_resources(self, rng: random.Random) -> None:
        """Lightweight pass to sprinkle solo resource piles."""

        resources = [
            ("wood", 5),
            ("stone", 5),
            ("crystal", 2),
            ("gold", 1),
            ("treasure", 1),
        ]
        ids, weights = zip(*resources)

        for y, row in enumerate(self.grid):
            for x, tile in enumerate(row):
                if tile.biome in constants.IMPASSABLE_BIOMES:
                    continue
                if (
                    tile.obstacle
                    or tile.building is not None
                    or tile.treasure is not None
                    or tile.enemy_units is not None
                    or tile.resource is not None
                ):
                    continue
                chance = self.resource_density / 100.0
                if rng.random() < chance:
                    tile.resource = rng.choices(ids, weights)[0]

    def _create_starting_area(self) -> None:
        """Create starting zones for player 0 and the enemy player."""
        if self.width < 5 or self.height < 5:
            return

        def carve_area(x0: int, y0: int, size: int, owner: int) -> None:
            biome = "scarletia_echo_plain"
            for yy in range(y0, y0 + size):
                for xx in range(x0, x0 + size):
                    tile = self.grid[yy][xx]
                    tile.biome = biome
                    tile.obstacle = False
                    tile.treasure = None
                    tile.enemy_units = None
                    tile.resource = None
                    tile.building = None
            area_coords = [
                (x, y)
                for y in range(y0, y0 + size)
                for x in range(x0, x0 + size)
            ]
            coords = area_coords.copy()
            random.shuffle(coords)
            town = Town()
            placed = False
            while coords:
                tx, ty = coords.pop()
                if self._can_place_building(tx, ty, town):
                    self._stamp_building(tx, ty, town)
                    town.owner = owner
                    if owner == 0:
                        self.hero_town = (tx, ty)
                        spawn = self._adjacent_free_tile(tx, ty)
                        if spawn:
                            self.hero_start = spawn
                        else:
                            self.hero_start = (tx, ty)
                            logger.error("No free tile around player town at %s,%s", tx, ty)
                    else:
                        self.enemy_town = (tx, ty)
                        spawn = self._adjacent_free_tile(tx, ty)
                        if spawn:
                            self.enemy_start = spawn
                        else:
                            self.enemy_start = (tx, ty)
                            logger.error("No free tile around enemy town at %s,%s", tx, ty)
                    placed = True
                    break
            if not placed:
                fallback_coords = [
                    c for c in area_coords if self.grid[c[1]][c[0]].building is None
                ]
                if fallback_coords:
                    tx, ty = random.choice(fallback_coords)
                    self._stamp_building(tx, ty, town)
                    town.owner = owner
                    if owner == 0:
                        self.hero_town = (tx, ty)
                        spawn = self._adjacent_free_tile(tx, ty)
                        if spawn:
                            self.hero_start = spawn
                        else:
                            self.hero_start = (tx, ty)
                            logger.error("No free tile around player town at %s,%s", tx, ty)
                    else:
                        self.enemy_town = (tx, ty)
                        spawn = self._adjacent_free_tile(tx, ty)
                        if spawn:
                            self.enemy_start = spawn
                        else:
                            self.enemy_start = (tx, ty)
                            logger.error("No free tile around enemy town at %s,%s", tx, ty)
                coords = [
                    c for c in area_coords if self.grid[c[1]][c[0]].building is None
                ]
            for bid in ("mine", "crystal_mine", "sawmill"):
                building = create_building(bid)
                while coords:
                    bx, by = coords.pop()
                    if self._can_place_building(bx, by, building):
                        self._stamp_building(bx, by, building)
                        if owner == 1:
                            building.owner = 1
                        if random.random() < 0.5:
                            building.garrison = self._create_enemy_army_for_biome(
                                biome
                            )
                        break

        # Player 0 starting area on largest continent
        continents = self._find_continents()
        if continents:
            largest = max(continents, key=len)
            xs = [x for x, _ in largest]
            ys = [y for _, y in largest]
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)
            max_size = min(max_x - min_x + 1, max_y - min_y + 1)
            size = random.randint(5, min(10, max_size)) if max_size >= 5 else max_size
            x0 = random.randint(min_x, max_x - size + 1)
            y0 = random.randint(min_y, max_y - size + 1)
        else:
            size = random.randint(5, 10)
            x0, y0 = 0, 0
            size = min(size, self.width, self.height)
        if size * size < 4:
            return

        carve_area(x0, y0, size, owner=0)
        self.starting_area = (x0, y0, size)

        # Enemy area placed away from player start
        min_dist = size + 5
        for _ in range(100):
            ex = random.randint(0, max(0, self.width - size))
            ey = random.randint(0, max(0, self.height - size))
            if abs(ex - x0) >= min_dist or abs(ey - y0) >= min_dist:
                break
        else:
            ex, ey = (max(0, self.width - size), max(0, self.height - size))

        carve_area(ex, ey, size, owner=1)
        self.enemy_starting_area = (ex, ey, size)

    def _place_resources(self, per_biome_counts: Optional[Dict[str, int]] = None) -> None:
        """Distribute resource-producing buildings based on biomes."""
        biome_buildings = {
            "scarletia_crimson_forest": "sawmill",
            "mountain": "mine",
            "scarletia_volcanic": "crystal_mine",
        }

        if per_biome_counts is None:
            per_biome_counts = {}

        continents = self._find_continents()
        for continent in continents:
            for biome, bid in biome_buildings.items():
                candidates = [
                    (x, y)
                    for (x, y) in continent
                    if self.grid[y][x].biome == biome
                ]
                if not candidates:
                    continue
                random.shuffle(candidates)
                count = per_biome_counts.get(biome, 1)
                placed = 0
                for x, y in candidates:
                    building = create_building(bid)
                    if self._can_place_building(x, y, building):
                        self._stamp_building(x, y, building)
                        placed += 1
                        if placed >= count:
                            break


    def _place_buildings(self, count: int) -> None:
        """Place simple buildings depending on biome."""
        building_map = {
            "scarletia_echo_plain": "farm",
            "scarletia_crimson_forest": "sawmill",
            "mountain": "mine",
            "scarletia_volcanic": "pyramid",
        }
        if count <= 0:
            return
        candidates = [
            (x, y)
            for y, row in enumerate(self.grid)
            for x, tile in enumerate(row)
            if not tile.obstacle
            and tile.treasure is None
            and tile.enemy_units is None
            and tile.resource is None
            and tile.building is None
        ]
        random.shuffle(candidates)
        placed = 0
        for x, y in candidates:
            tile = self.grid[y][x]
            btype = building_map.get(tile.biome)
            if not btype:
                continue
            building = create_building(btype)
            if self._can_place_building(x, y, building):
                self._stamp_building(x, y, building)
                placed += 1
                if placed >= count:
                    break


    @property
    def towns(self) -> List[Town]:
        """List all towns present on the map without duplicates."""
        towns: List[Town] = []
        seen: Set[Town] = set()
        for row in self.grid:
            for tile in row:
                building = tile.building
                if isinstance(building, Town) and building not in seen:
                    towns.append(building)
                    seen.add(building)
        return towns


    def find_building_pos(self, building: Building) -> Optional[Tuple[int, int]]:
        """Search ``self.grid`` for ``building`` and return its coordinates.

        Parameters
        ----------
        building: Building
            The building instance to locate on the world map.

        Returns
        -------
        Optional[Tuple[int, int]]
            ``(x, y)`` coordinates if the building is found, otherwise ``None``.
        """

        for y, row in enumerate(self.grid):
            for x, tile in enumerate(row):
                if tile.building is building:
                    return (x, y)
        return None


    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def _parse_row(self, row: str) -> List[Tuple[str, str]]:
        """Split a map row into `(biome, feature)` tokens.

        The map uses a two-character system where each tile is encoded by a
        biome character (``G``, ``F``, ``H``, ``D``, ``M``, ``S``, ``J``, ``I``
        or ``W``/``O``) optionally followed by a feature symbol
        (``#``, ``T``, ``E`` or ``.``).  If a feature symbol is omitted the tile
        is assumed to be empty.  For backward compatibility a single character
        row using only feature symbols is also supported, in which case the
        biome defaults to ``G`` (grass).
        """
        tokens: List[Tuple[str, str]] = []
        i = 0
        while i < len(row):
            biome = "G"
            feature = "."
            ch = row[i]
            if ch in BIOME_CHARS:
                biome = ch
                i += 1
                if i < len(row):
                    feature = row[i]
                    i += 1
            else:
                feature = ch
                i += 1
            tokens.append((biome, feature))
        return tokens

    def _load_from_parsed_data(self, rows: List[List[Tuple[str, str]]]) -> None:
        """Populate the grid from already parsed `(biome, feature)` rows."""
        for y, row in enumerate(rows):
            for x, (biome_char, feature) in enumerate(row):
                tile = self.grid[y][x]
                tile.biome = BIOME_CHAR_MAP.get(
                    biome_char, "scarletia_echo_plain"
                )
                if feature == '#':
                    tile.obstacle = True
                elif feature == 'T':
                    tile.treasure = {"gold": (25, 150), "exp": (40, 80)}
                elif feature == 'E':
                    tile.enemy_units = self._create_enemy_army_for_biome(tile.biome)
                # '.' or any other char leaves the tile empty

    @classmethod
    def from_file(cls, path: str) -> 'WorldMap':
        """Create a world map from a text file.

        Each tile is represented by a biome character (``G`` grass, ``F``
        forest, ``H`` hills, ``D`` desert, ``M`` mountain, ``S`` swamp,
        ``J`` jungle, ``I`` ice and ``W``/``O`` water) optionally
        followed by a feature symbol (``#`` obstacle, ``T`` treasure, ``E``
        enemy, ``.`` empty).  Older one-character maps that only contain feature
        symbols remain supported and default to grass.
        """
        _reset_town_counter()
        with open(path, 'r', encoding='utf-8') as f:
            lines = [line.rstrip('\n') for line in f]
        return cls(width=0, height=0, map_data=lines)

    def draw(
        self,
        surface: pygame.Surface,
        assets: dict[str, pygame.Surface],
        heroes: Optional[Sequence[UnitCarrier]],
        armies: Optional[Sequence[UnitCarrier]],
        selected: Optional[UnitCarrier],
        frame: int = 0,
        player_colour: Tuple[int, int, int] = constants.BLUE,
    ) -> pygame.Surface:
        """Draw the world map onto ``surface`` using the layered renderer.

        Returns a separate overlay surface on which callers may draw movement
        paths or other highlights.  The ``assets`` dictionary must contain
        surfaces keyed by the names defined in :mod:`constants`.  The ``frame``
        argument is accepted for backward compatibility but currently unused.
        """
        try:
            from .render.world_renderer import WorldRenderer
        except ImportError:  # pragma: no cover
            from render.world_renderer import WorldRenderer

        renderer = WorldRenderer(assets, player_colour=player_colour)
        renderer.world = self
        renderer.surface = surface
        overlay = renderer._draw_layers(
            surface,
            heroes or [],
            armies if armies is not None else getattr(self, "player_armies", []),
            selected,
        )
        return overlay

