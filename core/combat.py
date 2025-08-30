"""
Tactical combat implementation using Pygame.

The `Combat` class orchestrates a battle between the hero's army and an
enemy army on a grid.  Each unit takes a turn in order of initiative.
During the hero's turn, the player selects a unit, then chooses a square
to move to or an enemy to attack.  A basic AI controls enemy units.

This module does not import from `pygame.display` at import time; the game
loop should initialise Pygame and pass in the display surface.
"""

from __future__ import annotations

import os
import random
import sys
import copy
import math
from collections import deque
from dataclasses import dataclass
from typing import Callable, Deque, Dict, List, Optional, Tuple, Union
import json
from pathlib import Path

import pygame
import audio
import constants
import theme
from ui import combat_summary
from core import combat_ai, combat_render
from core.entities import Unit, UnitStats, apply_defence, ARTIFACT_CATALOG, Item, Hero
from core.status_effects import StatusEffect
from core import combat_rules
from core.fx import AnimatedFX, FXEvent, FXQueue, load_animation
from siege import Fortification, SiegeAction
try:  # flora support optional in tests
    from loaders.flora_loader import FloraLoader, PropInstance
except Exception:  # pragma: no cover
    FloraLoader = PropInstance = None  # type: ignore
from loaders.biomes import BiomeTileset
from loaders.asset_manager import AssetManager
# Battlefield definitions for background images and hero placement
from loaders.battlefield_loader import BattlefieldDef
# en haut de combat.py
from core.combat_screen import CombatHUD
from core.abilities import AbilityEngine, parse_abilities
from core.spell import (
    load_spells,
    cast_fireball,
    cast_chain_lightning,
    cast_heal,
    cast_ice_wall,
    Spell as SpellDef,
)
from core.faction import FactionDef
from ui.widgets.icon_button import IconButton
from core.vfx_manifest import get_vfx_entry

# Units with explicit hero/enemy image overrides. Other units default to an
# asset whose identifier matches ``UnitStats.name``.
UNIT_IMAGE_KEYS = {
    'Swordsman': {'hero': 'swordsman', 'enemy': 'swordsman'},
    'Archer': {'hero': 'archer', 'enemy': 'archer'},
    'Mage': {'hero': 'mage', 'enemy': 'mage'},
    'Priest': {'hero': 'priest', 'enemy': 'priest'},
    'Cavalry': {'hero': 'cavalry', 'enemy': 'cavalry'},
    'Dragon': {'hero': 'dragon', 'enemy': 'dragon'},

}

def _load_unit_spells() -> Dict[str, Dict[str, int]]:
    """Load unit spell definitions from JSON manifests.

    Each entry in ``assets/units/units.json`` and ``assets/units/creatures.json``
    may define an ``abilities`` mapping listing spells and their mana costs.  This
    function aggregates those into a single mapping keyed by unit name.
    """

    spells: Dict[str, Dict[str, int]] = {}
    base = Path(__file__).resolve().parent.parent / "assets" / "units"
    manifests = [
        (base / "units.json", "units", lambda n: n.replace("_", " ").title()),
        (base / "creatures.json", "creatures", lambda n: n),
    ]
    for path, key, transform in manifests:
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
        except Exception:
            continue
        for entry in data.get(key, []):
            abilities = entry.get("abilities")
            if not abilities:
                continue
            name = entry.get("name") or entry.get("id")
            if not name:
                continue
            spells[transform(name)] = {k: int(v) for k, v in abilities.items()}
    return spells


# Mapping of unit types to their spells and mana costs loaded from manifests
UNIT_SPELLS: Dict[str, Dict[str, int]] = _load_unit_spells()

# Slot -> (x, y) coordinates for hero formations
FORMATION_COORDS: Dict[str, List[Tuple[int, int]]] = {
    "serree": [
        (0, 0), (0, 2), (0, 4), (0, 6), (1, 1), (1, 3), (1, 5)
    ],
    "relachee": [
        (0, 0), (0, 2), (0, 4), (0, 6), (2, 1), (2, 3), (2, 5)
    ],
    "carree": [
        (0, 0), (0, 2), (1, 0), (1, 2), (2, 0), (2, 2), (0, 4)
    ],
}


def water_battlefield_template() -> List[List[str]]:
    """Return a combat grid filled entirely with water tiles.

    Naval battles take place on open water with no obstacles.  The returned
    template mirrors the standard combat grid dimensions and contains only the
    ``"ocean"`` biome.
    """

    return [
        ["ocean" for _ in range(constants.COMBAT_GRID_WIDTH)]
        for _ in range(constants.COMBAT_GRID_HEIGHT)
    ]

@dataclass
class CombatSpell:
    """Represents a spell that can be cast during combat."""

    name: str
    cost: int
    target: str
    effect: Callable[["Combat", Unit, Union[Unit, Tuple[int, int], Tuple[Unit, Tuple[int, int]]], int], None]


class CombatUnit(Unit):
    """Unit used during combat with support for temporary status effects."""

    def __init__(self, stats: UnitStats, count: int, side: str) -> None:  # noqa: D401
        super().__init__(stats, count, side)
        # ``base_stats`` keeps an unmodified copy so that temporary modifiers
        # can be reapplied cleanly each turn.
        self.base_stats: UnitStats = copy.deepcopy(stats)
        self.effects: List[StatusEffect] = []

    # ------------------------------------------------------------------
    def refresh_base_stats(self) -> None:
        """Refresh ``base_stats`` to match current ``stats``."""

        self.base_stats = copy.deepcopy(self.stats)

    # ------------------------------------------------------------------
    def add_effect(self, effect: StatusEffect) -> None:
        """Attach ``effect`` to this unit."""

        self.effects.append(effect)

    # ------------------------------------------------------------------
    def get_effect(self, name: str) -> StatusEffect | None:
        for eff in self.effects:
            if eff.name == name:
                return eff
        return None

    # ------------------------------------------------------------------
    def remove_effect(self, name: str) -> None:
        self.effects = [e for e in self.effects if e.name != name]


class Combat:
    """Represents a single combat encounter."""
    # --- Exposer les constantes attendues par le HUD comme attributs de classe
    UNIT_SPELLS = UNIT_SPELLS
    UNIT_IMAGE_KEYS = UNIT_IMAGE_KEYS

    def __init__(
        self,
        screen: pygame.Surface,
        assets: AssetManager,
        hero_units: List[Unit],
        enemy_units: List[Unit],
        hero_mana: int = 3,
        hero_spells: Optional[Dict[str, int]] = None,
        combat_map: Optional[List[List[str]]] = None,
        flora_props: Optional[List["PropInstance"]] = None,
        flora_loader: Optional["FloraLoader"] = None,
        biome_tilesets: Optional[Dict[str, BiomeTileset]] = None,
        battlefield: Optional[BattlefieldDef] = None,
        num_obstacles: int = 0,
        unit_shadow_baked: Optional[Dict[str, bool]] = None,
        hero: Optional["Hero"] = None,
        hero_faction: Optional[FactionDef] = None,
        fortification: Optional[Fortification] = None,
        siege_actions: Optional[List[SiegeAction]] = None,
    ) -> None:
        self.screen = screen
        self.assets = assets
        # Create deep copies of units for combat so exploration state is preserved
        self.hero_units: List[CombatUnit] = [self.copy_unit(u) for u in hero_units]
        self.enemy_units: List[CombatUnit] = [self.copy_unit(u) for u in enemy_units]
        # Track initial enemy count to award experience
        self._initial_enemy_count = sum(u.count for u in self.enemy_units)
        self.units: List[CombatUnit] = self.hero_units + self.enemy_units
        self.hero_faction = hero_faction
        if hero_faction:
            for u in self.hero_units:
                for tag in hero_faction.unit_tags.get(u.stats.name, []):
                    if tag not in u.tags:
                        u.tags.append(tag)
                for stat, mod in hero_faction.doctrine.items():
                    if hasattr(u.stats, stat):
                        setattr(u.stats, stat, getattr(u.stats, stat) + mod)
            for rule in hero_faction.army_synergies:
                tag = rule.get("tag")
                min_count = int(rule.get("min", 0))
                morale = int(rule.get("morale", 0))
                if tag:
                    count = sum(1 for u in self.hero_units if tag in u.tags)
                    if count >= min_count:
                        for u in self.hero_units:
                            u.stats.morale += morale
        # --- Spells and abilities runtime ---
        self.spell_defs: Dict[str, SpellDef] = load_spells(os.path.join("assets", "spells", "spells.json"))
        self.ability_engine = AbilityEngine()
        self._rt_by_unit: dict[Unit, any] = {}
        self.spellbooks: Dict[Unit, Dict[str, SpellDef]] = {}
        uid = 0
        for u in self.units:
            specs = parse_abilities(getattr(u.stats, "abilities", []))
            self._rt_by_unit[u] = self.ability_engine.init_unit(uid, specs)
            book: Dict[str, SpellDef] = {}
            for sp in specs:
                sdef = self.spell_defs.get(sp.name)
                if sdef and not sdef.passive:
                    book[sdef.id] = sdef
            self.spellbooks[u] = book
            uid += 1
        for rt in self._rt_by_unit.values():
            self.ability_engine.on_battle_start(rt)

        # Finalise base stats after all modifiers have been applied
        for u in self.units:
            if isinstance(u, CombatUnit):
                u.refresh_base_stats()

        # --- HUD ---
        self.hud = CombatHUD()
        # Stack of active overlays (topmost drawn last)
        self.overlays: list = []
        # Grid representation; None or Unit
        self.grid: List[List[Optional[Unit]]] = [
            [None for _ in range(constants.COMBAT_GRID_WIDTH)]
            for _ in range(constants.COMBAT_GRID_HEIGHT)
        ]
        self.place_units()
        # Turn order
        self.turn_order: List[Unit] = []
        self.reset_turn_order()
        self.current_index: int = 0
        # Currently selected hero unit (only valid during hero's turn)
        self.selected_unit: Optional[Unit] = None
        # Action chosen by the player during the hero's turn
        self.selected_action: Optional[str] = None
        # Icon buttons for combat actions, populated during render.draw()
        self.action_buttons: Dict[str, IconButton] = {}
        # When casting a spell, store the caster and wait for target selection
        self.casting_spell: bool = False
        self.spell_caster: Optional[Unit] = None
        self.selected_spell: Optional[Spell] = None
        self.teleport_unit: Optional[Unit] = None
        self.hero_mana: int = hero_mana
        self.hero_spells: Dict[str, int] = hero_spells or {}
        # Battlefield definition provides background image and hero placement
        self.battlefield = battlefield or BattlefieldDef("default", "", (0, 0))
        self.combat_map: List[List[str]] = combat_map or [
            [self.battlefield.id for _ in range(constants.COMBAT_GRID_WIDTH)]
            for _ in range(constants.COMBAT_GRID_HEIGHT)
        ]
        # --- Siege mechanics ---
        self.fortification = fortification
        self.pending_siege_actions: List[SiegeAction] = siege_actions or []
        if self.pending_siege_actions:
            self.resolve_siege_actions()
        self.flora_loader = flora_loader
        self.flora_props: List["PropInstance"] = flora_props or []
        self.biome_tilesets = biome_tilesets or {}
        self.obstacles: set[tuple[int, int]] = set()
        self.unit_shadow_baked = unit_shadow_baked or {}
        # Flag to indicate user requested the main menu
        self.exit_to_menu = False
        self.hero_colour = getattr(hero, "colour", constants.BLUE)
        # Define available spells
        self.spells: Dict[str, CombatSpell] = {
            "Heal": CombatSpell("Heal", 1, "ally", self.spell_heal),
            "Buff": CombatSpell("Buff", 1, "ally", self.spell_buff),
            "Fireball": CombatSpell("Fireball", 1, "cell", self.spell_fireball),
            "Teleport": CombatSpell("Teleport", 1, "ally_cell", self.spell_teleport),
            "Chain Lightning": CombatSpell("Chain Lightning", 2, "cell", self.spell_chain_lightning),
            "Ice Wall": CombatSpell("Ice Wall", 1, "cell", self.spell_ice_wall),
            "Focus": CombatSpell("Focus", 1, "ally", self.spell_focus),
            "Shield Block": CombatSpell("Shield Block", 1, "ally", self.spell_shield_block),
            "Charge": CombatSpell("Charge", 1, "ally", self.spell_charge),
            "Dragon Breath": CombatSpell("Dragon Breath", 2, "cell", self.spell_dragon_breath),
        }
        self.spells_by_name: Dict[str, CombatSpell] = self.spells
        # Compute pixel dimensions of the combat grid for a hexagonal layout.
        # When a battlefield background image is available, derive the hex size
        # from that image so the grid fits nicely with lateral margins.
        self._battlefield_bg: Optional[pygame.Surface] = None
        if getattr(self.battlefield, "image", ""):
            try:
                self._battlefield_bg = pygame.image.load(self.battlefield.image).convert_alpha()
            except Exception:
                self._battlefield_bg = None

        cols = constants.COMBAT_GRID_WIDTH
        rows = constants.COMBAT_GRID_HEIGHT
        self.hex_width = constants.COMBAT_HEX_SIZE
        self.hex_height = int(self.hex_width * math.sqrt(3) / 2)
        self.grid_pixel_width = int(
            self.hex_width + (cols - 1) * self.hex_width * 3 / 4
        )
        self.grid_pixel_height = int(
            self.hex_height * rows + self.hex_height / 2
        )
        # Offset and zoom/pan state
        self.offset_x = 10
        self.offset_y = 10
        self.zoom = 1.0
        self._dragging = False
        # Automatic control flag and button
        self.auto_mode: bool = False
        self.auto_button: Optional[IconButton] = None
        self._auto_resolve_done: bool = False
        # Damage statistics for post battle summary
        self.damage_stats: Dict[Unit, Dict[str, int]] = {
            u: {"dealt": 0, "taken": 0} for u in self.units
        }
        # Combat log messages
        self.log: List[str] = []
        # Active ice walls on the grid with remaining duration
        self.ice_walls: Dict[Tuple[int, int], int] = {}
        if num_obstacles:
            self.generate_obstacles(num_obstacles)
        # Queue for transient visual effects
        self.fx_queue = FXQueue()
        # Load hit effect sprite sheets (explosions, sparks)
        self._hit_effect_sprites: Dict[str, List[pygame.Surface]] = {}
        for _kind in ("explosion", "spark"):
            frames = load_animation(self.assets, f"vfx/{_kind}", constants.COMBAT_TILE_SIZE, constants.COMBAT_TILE_SIZE)
            self._hit_effect_sprites[_kind] = frames
        # Reference to hero for awarding loot
        self.hero = hero
        self.loot: List[Item] = []

    # ------------------------------------------------------------------
    # Siege resolution
    # ------------------------------------------------------------------

    def resolve_siege_actions(self) -> None:
        """Apply any queued siege actions against the fortification."""

        for action in list(self.pending_siege_actions):
            action.resolve()
        self.pending_siege_actions.clear()

    # ------------------------------------------------------------------
    # Experience calculation
    # ------------------------------------------------------------------

    def experience_gained(self) -> int:
        """Calculate experience based on defeated enemy creatures."""
        remaining = sum(u.count for u in self.enemy_units if u.is_alive)
        defeated = self._initial_enemy_count - remaining
        return max(0, defeated * 10)

    def generate_loot(self) -> List[Item]:
        """Generate artifact loot based on enemy strength."""
        power = sum(u.count * (u.stats.attack_min + u.stats.attack_max) for u in self.enemy_units)
        if power > 120:
            rarities = {"legendary": 0.1, "rare": 0.3, "uncommon": 0.4, "common": 0.2}
        elif power > 60:
            rarities = {"rare": 0.3, "uncommon": 0.5, "common": 0.2}
        elif power > 30:
            rarities = {"uncommon": 0.6, "common": 0.4}
        else:
            rarities = {"common": 1.0}
        candidates = [a for a in ARTIFACT_CATALOG if a.rarity in rarities]
        if not candidates:
            return []
        weights = [rarities[a.rarity] for a in candidates]
        chosen = random.choices(candidates, weights=weights, k=1)[0]
        return [copy.deepcopy(chosen)]

    @staticmethod
    def copy_unit(unit: Unit) -> CombatUnit:
        """Return a copy of a unit with identical stats and state."""

        new_unit = CombatUnit(copy.deepcopy(unit.stats), unit.count, unit.side)
        new_unit.current_hp = unit.current_hp
        new_unit.attack_bonus = unit.attack_bonus
        new_unit.tags = list(unit.tags)
        new_unit.refresh_base_stats()
        return new_unit

    def get_unit_image(self, unit: Unit, size: Tuple[int, int]) -> Optional[pygame.Surface]:
        """Return a surface for the unit scaled to ``size`` if available."""
        img: Optional[pygame.Surface] = None
        # Look up an explicit mapping for this unit and side.  If none exists,
        # fall back to using the unit's ``stats.name`` directly which matches
        # the identifier used when loading creature assets.
        key = UNIT_IMAGE_KEYS.get(unit.stats.name, {}).get(unit.side, unit.stats.name)
        img = self.assets.get(key)
        if img is None:
            frames = self.assets.get(unit.stats.sheet)
            if isinstance(frames, list) and frames:
                start, _ = (
                    unit.stats.hero_frames if unit.side == "hero" else unit.stats.enemy_frames
                )
                if 0 <= start < len(frames):
                    img = frames[start]
        if img and img.get_size() != size:
            if hasattr(pygame.transform, "smoothscale"):
                img = pygame.transform.smoothscale(img, size)
            else:
                img = pygame.transform.scale(img, size)
        return img

    def add_log(self, msg: str) -> None:
        """Append a message to the combat log."""
        self.log.append(msg)

    def log_damage(self, attacker: Unit, defender: Unit, dmg: int) -> None:
        """Record damage dealt and taken for statistics."""
        self.damage_stats.setdefault(attacker, {"dealt": 0, "taken": 0})
        self.damage_stats.setdefault(defender, {"dealt": 0, "taken": 0})
        self.damage_stats[attacker]["dealt"] += dmg
        self.damage_stats[defender]["taken"] += dmg

    def show_spellbook(self) -> None:
        """Display the hero's spellbook overlay."""
        try:  # pragma: no cover - allow running without package context
            from ui.spellbook_overlay import SpellbookOverlay
        except ImportError:  # pragma: no cover
            from .ui.spellbook_overlay import SpellbookOverlay  # type: ignore
        # Defer drawing and event handling to the main loop via overlay stack
        self.overlays.append(SpellbookOverlay(self.screen, self))

    def show_stats(self) -> None:
        """Display a summary of combat damage for all units."""
        heading_font = theme.get_font(36) or pygame.font.SysFont(None, 36)
        font = theme.get_font(24) or pygame.font.SysFont(None, 24)

        overlay = combat_summary.build_overlay(self.screen)
        panel_rect = overlay()
        ok_rect = pygame.Rect(0, 0, 80, 40)
        ok_rect.center = (panel_rect.centerx, panel_rect.bottom - 40)

        # Determine battle outcome for heading and message
        hero_alive = any(u.is_alive for u in self.hero_units)
        enemy_alive = any(u.is_alive for u in self.enemy_units)
        victory = hero_alive and not enemy_alive
        heading_text = "Victoire" if victory else "Défaite"
        experience = self.experience_gained()
        total_damage = sum(stats["dealt"] for stats in self.damage_stats.values())
        loot_items: List[Item] = []
        if victory and self.hero is not None:
            if not self.loot:
                self.loot = self.generate_loot()
                for item in self.loot:
                    self.hero.inventory.append(item)
            loot_items = self.loot

        # Determine images for the header zone.  Show the hero portrait if
        # available, otherwise fall back to the strongest surviving unit on
        # each side.
        img_size = (64, 64)

        def strongest_unit(units: List[Unit]) -> Optional[Unit]:
            alive = [u for u in units if u.is_alive]
            if not alive:
                return None
            return max(alive, key=lambda u: u.stats.attack_max)

        hero_image: Optional[pygame.Surface] = None
        if self.hero and getattr(self.hero, "portrait", None):
            portrait = self.hero.portrait
            if isinstance(portrait, pygame.Surface):
                hero_image = portrait
            else:
                hero_image = self.assets.get(portrait)
            if hero_image and hero_image.get_size() != img_size:
                if hasattr(pygame.transform, "smoothscale"):
                    hero_image = pygame.transform.smoothscale(hero_image, img_size)
                else:
                    hero_image = pygame.transform.scale(hero_image, img_size)
        if hero_image is None:
            unit = strongest_unit(self.hero_units)
            if unit:
                hero_image = self.get_unit_image(unit, img_size)

        enemy_image: Optional[pygame.Surface] = None
        unit = strongest_unit(self.enemy_units)
        if unit:
            enemy_image = self.get_unit_image(unit, img_size)

        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if ok_rect.collidepoint(event.pos):
                        return

            # Background and panel
            overlay()

            # Header zone with portraits
            header_height = img_size[1] + 40
            heading_surf = heading_font.render(
                heading_text, True, theme.PALETTE["text"]
            )
            self.screen.blit(
                heading_surf,
                heading_surf.get_rect(
                    center=(panel_rect.centerx, panel_rect.y + header_height // 2)
                ),
            )
            if hero_image:
                self.screen.blit(
                    hero_image,
                    (panel_rect.x + 20, panel_rect.y + header_height // 2 - img_size[1] // 2),
                )
            if enemy_image:
                self.screen.blit(
                    enemy_image,
                    (
                        panel_rect.right - 20 - img_size[0],
                        panel_rect.y + header_height // 2 - img_size[1] // 2,
                    ),
                )

            # Reward and experience section
            msg_lines = [
                f"Expérience gagnée : {experience}",
                f"Dégâts totaux infligés : {total_damage}",
            ]
            if loot_items:
                names = ", ".join(item.name for item in loot_items)
                msg_lines.append(f"Butin : {names}")
            msg_y = panel_rect.y + header_height + 20
            for i, line in enumerate(msg_lines):
                msg_surf = font.render(line, True, theme.PALETTE["text"])
                self.screen.blit(
                    msg_surf,
                    msg_surf.get_rect(
                        center=(panel_rect.centerx, msg_y + i * 30)
                    ),
                )

            # Column headings
            left_x = panel_rect.x + 50
            right_x = panel_rect.centerx + 50
            header_y = msg_y + len(msg_lines) * 30 + 40
            ally_title = font.render("Alliés", True, theme.PALETTE["text"])
            enemy_title = font.render("Ennemis", True, theme.PALETTE["text"])
            self.screen.blit(ally_title, (left_x, header_y - 30))
            self.screen.blit(enemy_title, (right_x, header_y - 30))
            columns = [("Unité", 60), ("Infligés", 220), ("Subis", 300)]
            for text, offset in columns:
                surf = font.render(text, True, theme.PALETTE["text"])
                self.screen.blit(surf, (left_x + offset, header_y))
                self.screen.blit(surf, (right_x + offset, header_y))

            def truncate(text: str, max_width: int) -> str:
                while font.size(text)[0] > max_width and len(text) > 0:
                    text = text[:-1]
                if font.size(text)[0] > max_width and len(text) > 3:
                    text = text[:-3] + "..."
                return text

            name_width = 150

            # Rows for each side
            y_left = header_y + 40
            for unit in self.hero_units:
                stats = self.damage_stats.get(unit, {"dealt": 0, "taken": 0})
                img = self.get_unit_image(unit, (32, 32))
                if img:
                    self.screen.blit(img, (left_x, y_left))
                name = truncate(unit.stats.name, name_width)
                dealt = font.render(str(stats["dealt"]), True, theme.PALETTE["text"])
                taken = font.render(str(stats["taken"]), True, theme.PALETTE["text"])
                self.screen.blit(font.render(name, True, theme.PALETTE["text"]), (left_x + 60, y_left))
                self.screen.blit(dealt, (left_x + 220, y_left))
                self.screen.blit(taken, (left_x + 300, y_left))
                y_left += 40

            y_right = header_y + 40
            for unit in self.enemy_units:
                stats = self.damage_stats.get(unit, {"dealt": 0, "taken": 0})
                img = self.get_unit_image(unit, (32, 32))
                if img:
                    self.screen.blit(img, (right_x, y_right))
                name = truncate(unit.stats.name, name_width)
                dealt = font.render(str(stats["dealt"]), True, theme.PALETTE["text"])
                taken = font.render(str(stats["taken"]), True, theme.PALETTE["text"])
                self.screen.blit(font.render(name, True, theme.PALETTE["text"]), (right_x + 60, y_right))
                self.screen.blit(dealt, (right_x + 220, y_right))
                self.screen.blit(taken, (right_x + 300, y_right))
                y_right += 40

            # OK button
            pygame.draw.rect(self.screen, theme.PALETTE["accent"], ok_rect)
            pygame.draw.rect(
                self.screen, theme.PALETTE["text"], ok_rect, theme.FRAME_WIDTH
            )
            ok_text = font.render("OK", True, theme.PALETTE["text"])
            self.screen.blit(ok_text, ok_text.get_rect(center=ok_rect.center))
            pygame.display.flip()

    def place_units(self) -> None:
        """Place hero and enemy units on their starting positions."""
        # Clear grid
        for y in range(constants.COMBAT_GRID_HEIGHT):
            for x in range(constants.COMBAT_GRID_WIDTH):
                self.grid[y][x] = None

        # Hero formation
        hero_obj = getattr(self, "hero", None)
        formation = getattr(hero_obj, "formation", "serree")
        coords = FORMATION_COORDS.get(formation, FORMATION_COORDS["serree"])
        for idx, unit in enumerate(self.hero_units):
            if idx >= len(coords):
                break
            x, y = coords[idx]
            if 0 <= x < constants.COMBAT_GRID_WIDTH and 0 <= y < constants.COMBAT_GRID_HEIGHT:
                if self.grid[y][x] is None:
                    self.grid[y][x] = unit
                    unit.x = x
                    unit.y = y

        # Enemy uses tight formation mirrored horizontally
        enemy_coords = [
            (constants.COMBAT_GRID_WIDTH - 1 - x, y) for x, y in FORMATION_COORDS["serree"]
        ]
        for idx, unit in enumerate(self.enemy_units):
            if idx >= len(enemy_coords):
                break
            x, y = enemy_coords[idx]
            if 0 <= x < constants.COMBAT_GRID_WIDTH and 0 <= y < constants.COMBAT_GRID_HEIGHT:
                if self.grid[y][x] is None:
                    self.grid[y][x] = unit
                    unit.x = x
                    unit.y = y

    def reset_turn_order(self) -> None:
        """Initialise a new round by sorting units by initiative and resetting acted flag."""
        self.turn_order = [u for u in self.units if u.is_alive]
        random.shuffle(self.turn_order)
        self.turn_order.sort(key=lambda u: u.initiative, reverse=True)
        for u in self.turn_order:
            u.acted = False
        combat_rules.start_round_reset_retaliations(self.turn_order)
        self.current_index = 0

    def _rt(self, unit: Unit):
        return self._rt_by_unit.get(unit)

    def _apply_effects(self, effects: list[dict], source: Optional[Unit] = None) -> None:
        for e in effects or []:
            t = e.get("type")
            if t == "fx":
                # Image clé -> assets ; position en grille convertie en pixels
                key = e.get("asset")
                pos = e.get("pos")
                if key and pos:
                    self.show_effect(key, pos)
            elif t == "projectile":
                key = e.get("asset")
                src = e.get("from"); dst = e.get("to")
                if key and src and dst:
                    self.animate_projectile(key, src, dst)
            elif t == "status":
                unit = self._find_unit_by_id(e.get("target"))
                if unit:
                    self.add_status(
                        unit,
                        e.get("status", ""),
                        e.get("duration", 1),
                        e.get("modifiers"),
                        e.get("icon"),
                    )
            elif t == "heal":
                u = self._find_unit_by_id(e.get("target"))
                if u:
                    u.current_hp = min(u.stats.max_hp, u.current_hp + int(e.get("value",0)))
            elif t == "damage":
                u = self._find_unit_by_id(e.get("target"))
                if u:
                    attacker = source or self.turn_order[self.current_index]
                    self.resolve_damage(attacker, u, int(e.get("value",0)), e.get("element","magic"))
            elif t == "knockback":
                u = self._find_unit_by_id(e.get("target"))
                if u:
                    nx, ny = u.x + int(e.get("dx",0)), u.y + int(e.get("dy",0))
                    if 0 <= nx < constants.COMBAT_GRID_WIDTH and 0 <= ny < constants.COMBAT_GRID_HEIGHT:
                        if self.grid[ny][nx] is None:
                            self.move_unit(u, nx, ny)
            elif t == "spawn":
                if e.get("entity") == "ice_wall":
                    pos = e.get("pos")
                    if pos:
                        self.ice_walls[tuple(pos)] = 2

    def _find_unit_by_id(self, unit_id: int) -> Optional[Unit]:
        # nos unités n'ont pas d'ID global : on retombe sur “unit_id” == index d'init
        try:
            return self.units[unit_id]
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Spells
    # ------------------------------------------------------------------

    def get_spell(self, name: str) -> Spell:
        return self.spells_by_name[name]

    def start_spell(self, caster: Unit, name: str) -> bool:
        """Prepare ``caster`` to cast the spell ``name``.

        This validates that the unit knows the spell and that the hero has
        sufficient mana in the appropriate pool.  On success the combat state is updated so that the
        next click will select the spell target.
        ``True`` is returned if casting can begin, otherwise ``False``.
        """

        if name not in UNIT_SPELLS.get(caster.stats.name, {}) and name not in self.hero_spells:
            return False
        spell = self.get_spell(name)
        is_unit_spell = name in UNIT_SPELLS.get(caster.stats.name, {})
        if is_unit_spell:
            if caster.mana < spell.cost:
                return False
        else:
            if self.hero_mana < spell.cost:
                return False
        self.casting_spell = True
        self.spell_caster = caster
        self.selected_spell = spell
        self.teleport_unit = None
        return True

    def cast_spell(
        self, spell: Spell, caster: Unit, target: Union[Unit, Tuple[int, int], Tuple[Unit, Tuple[int, int]]]
    ) -> None:
        """Resolve a spell, consuming mana and applying its effect."""
        is_unit_spell = spell.name in UNIT_SPELLS.get(caster.stats.name, {})
        if is_unit_spell:
            if caster.mana < spell.cost:
                return
            level = self.hero_spells.get(spell.name, 1)
            spell.effect(caster, target, level)
            caster.mana -= spell.cost
        else:
            if self.hero_mana < spell.cost:
                return
            level = self.hero_spells.get(spell.name, 1)
            spell.effect(caster, target, level)
            self.hero_mana -= spell.cost
        # Trigger hit effect on target position for damaging spells
        if spell.name in {"Fireball", "Chain Lightning", "Dragon Breath"}:
            impact: Optional[Tuple[int, int]] = None
            if isinstance(target, Unit):
                impact = (target.x, target.y)
            elif isinstance(target, tuple):
                if isinstance(target[0], Unit) and isinstance(target[1], tuple):
                    impact = target[1]
                elif len(target) == 2 and isinstance(target[0], int):
                    impact = target  # direct cell target
            if impact:
                self.show_hit_effect(impact, "explosion")
        self.casting_spell = False
        self.spell_caster = None
        self.selected_spell = None
        self.teleport_unit = None

    # Generic resolution helpers

    def resolve_damage(self, attacker: Unit, defender: Unit, dmg: int, element: str) -> None:
        rt_def = self._rt(defender)
        if rt_def:
            new_dmg, eff, info = self.ability_engine.modify_incoming_damage(
                rt_def, dmg, element, is_melee=False, tile_biome=None
            )
            self._apply_effects(eff)
            if info.get("miss"):
                self.log_damage(attacker, defender, 0)
                return
            dmg = new_dmg
        adjusted = apply_defence(dmg, defender, "magic")
        self.log_damage(attacker, defender, adjusted)
        defender.take_damage(adjusted)
        self.show_hit_effect((defender.x, defender.y), "explosion")
        if not defender.is_alive:
            self.remove_unit_from_grid(defender)

    def damage_area(
        self, caster: Unit, center: Tuple[int, int], radius: int, dmg: int, element: str
    ) -> None:
        cx, cy = center
        for x in range(cx - radius, cx + radius + 1):
            for y in range(cy - radius, cy + radius + 1):
                if 0 <= x < constants.COMBAT_GRID_WIDTH and 0 <= y < constants.COMBAT_GRID_HEIGHT:
                    unit = self.grid[y][x]
                    if unit and unit.side != caster.side:
                        self.resolve_damage(caster, unit, dmg, element)

    def add_status(
        self,
        unit: CombatUnit,
        status: str,
        turns: int,
        modifiers: Optional[Dict[str, int]] | None = None,
        icon: Optional[str] | None = None,
    ) -> None:
        """Attach a :class:`StatusEffect` to ``unit``."""

        effect = StatusEffect(status, turns, modifiers or {}, icon or f"status_{status}")
        unit.add_effect(effect)

    def get_status(self, unit: CombatUnit, status: str) -> int:
        eff = unit.get_effect(status)
        return eff.duration if eff else 0

    def consume_status(self, unit: CombatUnit, status: str) -> None:
        unit.remove_effect(status)

    def apply_status_effects(self, unit: CombatUnit) -> None:
        if not unit.effects:
            return

        # Reset stats to baseline before applying modifiers
        unit.stats = copy.deepcopy(unit.base_stats)
        for effect in list(unit.effects):
            for attr, mod in effect.modifiers.items():
                if hasattr(unit.stats, attr):
                    setattr(unit.stats, attr, getattr(unit.stats, attr) + mod)
            if effect.name == "burn":
                self.log_damage(unit, unit, 5)
                unit.take_damage(5)
                if not unit.is_alive:
                    self.remove_unit_from_grid(unit)
            effect.duration -= 1
            if effect.duration <= 0:
                unit.effects.remove(effect)

    def resolve_attack(self, attacker: Unit, defender: Unit, attack_type: str) -> int:
        # Orientation and distance for flanking
        dx = defender.x - attacker.x
        dy = defender.y - attacker.y
        direction = (
            0 if dx == 0 else (1 if dx > 0 else -1),
            0 if dy == 0 else (1 if dy > 0 else -1),
        )
        attacker.facing = direction
        dist = self.hex_distance((attacker.x, attacker.y), (defender.x, defender.y))
        flank = combat_rules.flanking_bonus(attacker, defender)

        blocked: set[Tuple[int, int]] = set(self.obstacles) | set(self.ice_walls)
        for u in self.units:
            if not u.is_alive:
                continue
            if u is attacker or u is defender:
                continue
            blocked.add((u.x, u.y))
        result = combat_rules.compute_damage(
            attacker,
            defender,
            attack_type=attack_type,
            distance=dist,
            obstacles=blocked,
        )
        base = result["value"]
        luck_mul = result.get("luck", 1.0)
        if luck_mul > 1.0:
            self.add_log(f"Lucky strike by {attacker.stats.name}!")
            self.show_effect("luck_fx", (attacker.x, attacker.y))
        elif luck_mul < 1.0:
            self.add_log(f"Unlucky hit by {attacker.stats.name}.")
            self.show_effect("luck_fx", (attacker.x, attacker.y))
        if flank > 1.0:
            print("Flanking attack!")

        # Sortants (bonus charge, etc.)
        rt_att = self._rt(attacker)
        if rt_att:
            base, eff_o = self.ability_engine.modify_outgoing_damage(rt_att, base, {"attack_type": attack_type})
            self._apply_effects(eff_o)

        # Entrants (évasion, résistances…)
        rt_def = self._rt(defender)
        info = {}
        if rt_def:
            new_dmg, eff_i, info = self.ability_engine.modify_incoming_damage(
                rt_def,
                base,
                dmg_type=("magic" if attack_type == "spell" else "physical"),
                is_melee=(attack_type == "melee"),
                tile_biome=None,
            )
            self._apply_effects(eff_i)
            if info.get("miss"):
                self.log_damage(attacker, defender, 0)
                return 0
            base = new_dmg

        # Bouclier / focus via statuts
        if attack_type == 'ranged' and self.get_status(attacker, 'focus'):
            base *= 2
            self.consume_status(attacker, 'focus')
        if attack_type == 'melee' and self.get_status(defender, 'shield_block'):
            self.consume_status(defender, 'shield_block')
            self.log_damage(attacker, defender, 0)
            return 0

        # Apply damage
        self.log_damage(attacker, defender, base)
        defender_id = self.units.index(defender)
        defender.take_damage(base)
        self.show_hit_effect((defender.x, defender.y), "spark")
        dead = not defender.is_alive
        if dead:
            self.remove_unit_from_grid(defender)

        # Defender now faces attacker
        defender.facing = (-direction[0], -direction[1])

        # Réaction on-hit
        if attack_type == 'melee' and rt_def:
            eff = self.ability_engine.on_attacked_by_melee(rt_def, self.units.index(attacker))
            self._apply_effects(eff)

        # On-kill
        if dead and rt_att:
            eff = self.ability_engine.on_kill(rt_att, defender_id)
            self._apply_effects(eff)

        # Retaliation
        if attack_type == 'melee' and defender.is_alive and combat_rules.can_retaliate(defender):
            ret = combat_rules.compute_damage(defender, attacker, attack_type='melee')
            ret_dmg = ret["value"]
            luck_r = ret.get("luck", 1.0)
            if luck_r > 1.0:
                self.add_log(f"Lucky strike by {defender.stats.name}!")
            elif luck_r < 1.0:
                self.add_log(f"Unlucky hit by {defender.stats.name}.")
            self.log_damage(defender, attacker, ret_dmg)
            attacker.take_damage(ret_dmg)
            self.show_hit_effect((attacker.x, attacker.y), "spark")
            if not attacker.is_alive:
                self.remove_unit_from_grid(attacker)
            combat_rules.consume_retaliation(defender)
            defender.facing = (-direction[0], -direction[1])

        if self.get_status(attacker, 'charge'):
            self.consume_status(attacker, 'charge')
        return base


    # Spell effect implementations

    def spell_heal(self, caster: Unit, target: Unit, level: int) -> None:
        spell = self.spell_defs.get("heal")
        if not spell:
            return
        target_id = self.units.index(target)
        effects = cast_heal(spell, level, target_id)
        if caster.stats.name == "Priest" and effects:
            effects[0]["value"] = 100
        self._apply_effects(effects, caster)
        st = self._rt(caster)
        if st and "heal" in st.ability_states:
            st.ability_states["heal"].cooldown = st.ability_states["heal"].cooldown_max

    def spell_buff(self, _: Unit, target: Unit, level: int) -> None:
        target.attack_bonus += 2 * level

    def spell_fireball(self, caster: Unit, pos: Tuple[int, int], level: int) -> None:
        x, y = pos
        self.animate_projectile("fireball", (caster.x, caster.y), pos)
        dmg = 30 * level
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                tx, ty = x + dx, y + dy
                if 0 <= tx < constants.COMBAT_GRID_WIDTH and 0 <= ty < constants.COMBAT_GRID_HEIGHT:
                    unit = self.grid[ty][tx]
                    if unit and unit.side != caster.side:
                        self.resolve_damage(caster, unit, dmg, 'fire')
                        if not unit.is_alive:
                            self.remove_unit_from_grid(unit)
        st = self._rt(caster)
        if st and "fireball" in st.ability_states:
            st.ability_states["fireball"].cooldown = st.ability_states["fireball"].cooldown_max

    def spell_teleport(self, _: Unit, data: Tuple[Unit, Tuple[int, int]], level: int) -> None:  # noqa: ARG002
        unit, (x, y) = data
        if 0 <= x < constants.COMBAT_GRID_WIDTH and 0 <= y < constants.COMBAT_GRID_HEIGHT:
            if self.grid[y][x] is None and (x, y) not in self.obstacles:
                self.move_unit(unit, x, y)

    def spell_chain_lightning(self, caster: Unit, pos: Tuple[int, int], level: int) -> None:
        dmg = 25 * level
        self.animate_projectile("chain_lightning", (caster.x, caster.y), pos)
        self.damage_area(caster, pos, 1, dmg, 'shock')
        st = self._rt(caster)
        if st and "chain_lightning" in st.ability_states:
            st.ability_states["chain_lightning"].cooldown = st.ability_states["chain_lightning"].cooldown_max

    def spell_ice_wall(self, caster: Unit, pos: Tuple[int, int], level: int) -> None:  # noqa: ARG002
        spell = self.spell_defs.get("ice_wall")
        if not spell:
            return
        length = int(spell.data.get("wall_length", 3))
        line = [(pos[0] + i, pos[1]) for i in range(length)]
        effects = cast_ice_wall(spell, line, self.fx_queue, self.assets)
        self._apply_effects(effects, caster)
        st = self._rt(caster)
        if st and "ice_wall" in st.ability_states:
            st.ability_states["ice_wall"].cooldown = st.ability_states["ice_wall"].cooldown_max

    def spell_focus(self, _: Unit, target: Unit, level: int) -> None:  # noqa: ARG002
        self.show_effect("focus", (target.x, target.y))
        self.add_status(target, 'focus', 1)

    def spell_shield_block(self, _: Unit, target: Unit, level: int) -> None:  # noqa: ARG002
        self.show_effect("shield_block", (target.x, target.y))
        self.add_status(target, 'shield_block', 1)

    def spell_charge(self, caster: Unit, target: Unit, level: int) -> None:  # noqa: ARG002
        self.show_effect("charge", (target.x, target.y))
        self.add_status(target, 'charge', 1)

    def spell_dragon_breath(self, caster: Unit, pos: Tuple[int, int], level: int) -> None:
        dmg = 40 * level
        self.animate_projectile("dragon_breath", (caster.x, caster.y), pos)
        cx, cy = pos
        for x in range(cx - 3, cx + 4):
            for y in range(cy - 3, cy + 4):
                if 0 <= x < constants.COMBAT_GRID_WIDTH and 0 <= y < constants.COMBAT_GRID_HEIGHT:
                    unit = self.grid[y][x]
                    if unit and unit.side != caster.side:
                        self.resolve_damage(caster, unit, dmg, 'fire')
                        self.add_status(unit, 'burn', 2)

    def advance_turn(self) -> None:
        """Advance to the next unit's turn, starting a new round if necessary."""
        unit = self.turn_order[self.current_index]
        # Handle morale effects
        if unit.skip_turn:
            unit.acted = True
            unit.skip_turn = False
        if unit.acted and unit.extra_turns > 0:
            self.show_effect("morale_fx", (unit.x, unit.y))
            unit.extra_turns -= 1
            unit.acted = False
            return

        # Decrement ice wall durations
        for pos in list(self.ice_walls):
            self.ice_walls[pos] -= 1
            if self.ice_walls[pos] <= 0:
                del self.ice_walls[pos]

        self.current_index += 1
        # Skip dead units and those that have already acted
        while self.current_index < len(self.turn_order) and (
            not self.turn_order[self.current_index].is_alive
            or self.turn_order[self.current_index].acted
        ):
            self.current_index += 1
        if self.current_index >= len(self.turn_order):
            # End of round: start a new round
            self.reset_turn_order()

    def apply_passive_abilities(self, unit: Unit) -> None:
        """Apply passive abilities that trigger at the start of the unit's turn."""
        self.apply_status_effects(unit)
        if "passive_heal" in unit.stats.abilities:
            allies = self.hero_units if unit.side == "hero" else self.enemy_units
            for ally in allies:
                if ally.is_alive and ally.current_hp < ally.stats.max_hp:
                    ally.current_hp = min(ally.stats.max_hp, ally.current_hp + 5)
                    break

    def check_morale(self, unit: Unit) -> None:
        """Apply morale effects to a unit at the start of its turn."""
        outcome = combat_rules.roll_morale(unit.stats.morale)
        if outcome > 0:
            unit.extra_turns = 1
            self.add_log(f"{unit.stats.name} is inspired and gains an extra action!")
        elif outcome < 0:
            unit.skip_turn = True
            self.add_log(f"{unit.stats.name} falters and loses its action!")
            self.show_effect("morale_fx", (unit.x, unit.y))

    def get_available_actions(self, unit: Unit) -> List[str]:
        """Return the list of action identifiers available to ``unit``."""
        actions = ["move", "melee"]
        costs = UNIT_SPELLS.get(unit.stats.name, {})
        min_cost = min(costs.values()) if costs else None
        can_cast_unit = min_cost is not None and unit.mana >= min_cost
        if unit.stats.name == "Mage":
            if can_cast_unit:
                actions.append("spell")
        else:
            if unit.stats.attack_range > unit.stats.min_range:
                actions.append("ranged")
            if can_cast_unit:
                actions.append("spell")
        actions.append("wait")
        return actions

    # ------------------------------------------------------------------
    def use_ability(self) -> None:
        """Attempt to use the current unit's special ability or spell."""
        if not self.turn_order:
            return
        unit = self.turn_order[self.current_index]
        spells = self.UNIT_SPELLS.get(unit.stats.name, {})
        if not spells:
            return
        if len(spells) == 1:
            name, cost = next(iter(spells.items()))
            if unit.mana >= cost:
                self.start_spell(unit, name)
                unit.acted = True
                self.advance_turn()
                self.selected_action = None
                self.selected_unit = None
        else:
            self.selected_unit = unit
            self.selected_action = "spell"

    def swap_positions(self) -> None:
        """Swap the selected unit with another friendly unit if possible."""
        src = self.selected_unit
        if src is None:
            self.selected_unit = self.turn_order[self.current_index]
            return
        target: Optional[Unit] = None
        for u in self.hero_units:
            if u is not src and u.is_alive:
                target = u
                break
        if not target:
            return
        sx, sy = src.x, src.y
        tx, ty = target.x, target.y
        self.grid[sy][sx], self.grid[ty][tx] = self.grid[ty][tx], self.grid[sy][sx]
        src.x, src.y, target.x, target.y = tx, ty, sx, sy
        self.selected_unit = None
        self.selected_action = None

    def flee(self) -> None:
        """End the combat as a loss for the hero side."""
        for u in self.hero_units:
            u.count = 0
        self.add_log("The hero flees!")
        audio.play_sound('defeat')
        self.exit_to_menu = True

    def surrender(self) -> None:
        """Surrender the battle, counting as a defeat."""
        if self.hero:
            self.hero.gold = self.hero.gold // 2
            for res in self.hero.resources:
                self.hero.resources[res] = self.hero.resources[res] // 2
        self.add_log("The hero surrenders!")
        audio.play_sound('defeat')
        self.exit_to_menu = True

    def auto_resolve(self) -> None:
        """Resolve the battle automatically using the auto-resolve module."""
        from . import auto_resolve as ar

        hero_wins, exp, heroes, enemies = ar.resolve(self.hero_units, self.enemy_units)
        for src, res in zip(self.hero_units, heroes):
            src.count = res.count
            src.current_hp = res.current_hp
        for src, res in zip(self.enemy_units, enemies):
            src.count = res.count
            src.current_hp = res.current_hp
        ar.show_summary(self.screen, heroes, enemies, hero_wins, exp, self.hero)
        if hero_wins:
            audio.play_sound('victory')
        else:
            audio.play_sound('defeat')
        self._auto_resolve_done = True

    def auto_combat(self) -> None:
        """Enable automatic combat where AI controls the hero army."""
        self.auto_mode = True
        self.add_log("Auto-combat engaged")

    def select_next_unit(self) -> None:
        """Select the next friendly unit that has not acted yet."""
        if not self.hero_units:
            return
        start = 0
        if self.selected_unit and self.selected_unit in self.hero_units:
            start = (self.hero_units.index(self.selected_unit) + 1) % len(self.hero_units)
        for i in range(len(self.hero_units)):
            u = self.hero_units[(start + i) % len(self.hero_units)]
            if u.is_alive and not u.acted:
                self.selected_unit = u
                self.selected_action = None
                break


    def run(self) -> Tuple[bool, int]:
        """
        Run the combat event loop.

        Returns a tuple ``(hero_wins, experience)`` where ``experience``
        is the amount of experience earned from defeated enemies.
        This method blocks until the battle concludes.
        """
        clock = pygame.time.Clock()
        running = True
        frame = 0
        while running:
            # Check victory conditions
            hero_alive = any(u.is_alive for u in self.hero_units)
            enemy_alive = any(u.is_alive for u in self.enemy_units)
            if not hero_alive:
                if not self._auto_resolve_done:
                    audio.play_sound('defeat')
                    self.show_stats()
                return False, self.experience_gained()
            if not enemy_alive:
                # Award loot even when the post-battle stats screen is skipped
                if self.hero is not None:
                    if not self.loot:
                        self.loot = self.generate_loot()
                    for item in self.loot:
                        self.hero.inventory.append(item)
                if not self._auto_resolve_done:
                    audio.play_sound('victory')
                    self.show_stats()
                return True, self.experience_gained()
            # Get current unit
            if self.current_index >= len(self.turn_order):
                self.reset_turn_order()
            current_unit = self.turn_order[self.current_index]
            # If unit is dead skip
            if not current_unit.is_alive or current_unit.acted:
                self.advance_turn()
                continue

            # Hook début de tour (abilities)
            rt = self._rt(current_unit)
            if rt:
                self.ability_engine.on_turn_start(rt)
            self.apply_passive_abilities(current_unit)
            self.check_morale(current_unit)
            if current_unit.skip_turn:
                self.advance_turn()
                continue
            if self.auto_mode:
                for event in pygame.event.get():
                    if self.overlays:
                        if event.type == pygame.QUIT:
                            pygame.quit()
                            sys.exit()
                        elif self.overlays[-1].handle_event(event):
                            self.overlays.pop()
                        continue
                    if event.type == pygame.QUIT:
                        pygame.quit()
                        sys.exit()
                    elif event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE:
                            self.exit_to_menu = True
                            return False, self.experience_gained()
                        elif event.key == pygame.K_h:
                            self.auto_mode = False
                        elif event.key == pygame.K_s:
                            self.show_spellbook()
                    elif event.type == pygame.MOUSEBUTTONDOWN:
                        if (
                            event.button == 1
                            and self.auto_button
                            and self.auto_button.collidepoint(event.pos)
                        ):
                            self.auto_mode = False
                if self.overlays:
                    combat_render.draw(self, frame)
                    for overlay in self.overlays:
                        overlay.draw()
                    pygame.display.flip()
                    clock.tick(constants.FPS)
                    frame = (frame + 1) % 60
                    continue
                if self.auto_mode and current_unit.side == 'hero':
                    combat_ai.allied_ai_turn(self, current_unit)
                    current_unit.acted = True
                    self.advance_turn()
                    combat_render.draw(self, frame)
                    for overlay in self.overlays:
                        overlay.draw()
                    pygame.display.flip()
                    pygame.time.wait(200)
                    clock.tick(constants.FPS)
                    frame = (frame + 1) % 60
                    continue
            if current_unit.side == 'hero' and self.selected_unit is not current_unit:
                self.selected_unit = current_unit
                self.selected_action = None
                self.casting_spell = False
                self.spell_caster = None
                self.selected_spell = None
                self.teleport_unit = None
            for event in pygame.event.get():
                if self.overlays:
                    if event.type == pygame.QUIT:
                        pygame.quit()
                        sys.exit()
                    elif self.overlays[-1].handle_event(event):
                        self.overlays.pop()
                    continue
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.exit_to_menu = True
                        return False, self.experience_gained()
                    plus = (
                        getattr(pygame, "K_PLUS", 0),
                        getattr(pygame, "K_EQUALS", 0),
                        getattr(pygame, "K_KP_PLUS", 0),
                    )
                    minus = (
                        getattr(pygame, "K_MINUS", 0),
                        getattr(pygame, "K_KP_MINUS", 0),
                    )
                    if event.key in plus:
                        self._adjust_zoom(0.25, (
                            self.screen.get_width() // 2,
                            self.screen.get_height() // 2,
                        ))
                    elif event.key in minus:
                        self._adjust_zoom(-0.25, (
                            self.screen.get_width() // 2,
                            self.screen.get_height() // 2,
                        ))
                    elif event.key == pygame.K_s:
                        self.show_spellbook()
                    elif current_unit.side == 'hero':
                        if event.key == pygame.K_SPACE:
                            current_unit.acted = True
                            self.advance_turn()
                            self.selected_unit = None
                            self.selected_action = None
                            break
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 3:
                        mx, my = event.pos
                        cell = self.pixel_to_cell(mx, my)
                        opened = False
                        if cell is not None:
                            cx, cy = cell
                            unit = self.grid[cy][cx]
                            if unit and getattr(unit, "is_alive", False):
                                try:  # pragma: no cover - lazy import for tests
                                    from ui.unit_info_overlay import UnitInfoOverlay
                                except Exception:  # pragma: no cover
                                    from .ui.unit_info_overlay import UnitInfoOverlay  # type: ignore
                                self.overlays.append(UnitInfoOverlay(self.screen, unit))
                                opened = True
                        if not opened:
                            self._dragging = True
                    elif event.button == 4:
                        self._adjust_zoom(0.25, event.pos)
                    elif event.button == 5:
                        self._adjust_zoom(-0.25, event.pos)
                    elif event.button == 1 and current_unit.side == 'hero':
                        if combat_render.handle_button_click(self, current_unit, event.pos):
                            continue
                        mx, my = event.pos
                        cell = self.pixel_to_cell(mx, my)
                        if cell is None:
                            continue
                        cx, cy = cell
                        if self.casting_spell and self.spell_caster and self.selected_spell:
                            spell = self.selected_spell
                            if spell.target == "ally":
                                target_unit = self.grid[cy][cx]
                                if target_unit and target_unit.side == self.spell_caster.side:
                                    self.cast_spell(spell, self.spell_caster, target_unit)
                                    current_unit.acted = True
                                    self.advance_turn()
                                    self.selected_action = None
                                    break
                                else:
                                    print("Invalid target for spell")
                            elif spell.target == "cell":
                                self.cast_spell(spell, self.spell_caster, (cx, cy))
                                current_unit.acted = True
                                self.advance_turn()
                                self.selected_action = None
                                break
                            elif spell.target == "ally_cell":
                                if self.teleport_unit is None:
                                    unit = self.grid[cy][cx]
                                    if unit and unit.side == self.spell_caster.side:
                                        self.teleport_unit = unit
                                        print("Select destination")
                                    else:
                                        print("Select friendly unit to teleport")
                                else:
                                    if self.grid[cy][cx] is None:
                                        self.cast_spell(
                                            spell, self.spell_caster, (self.teleport_unit, (cx, cy))
                                        )
                                        current_unit.acted = True
                                        self.advance_turn()
                                        self.selected_action = None
                                        break
                                    else:
                                        print("Destination occupied")
                            continue
                        if not self.selected_action:
                            print("Choose an action first.")
                            continue
                        if self.selected_action == 'move':
                            x0, y0 = self.selected_unit.x, self.selected_unit.y
                            dist = self.hex_distance((x0, y0), (cx, cy))
                            move_speed = self.selected_unit.stats.speed
                            if 'charge' in self.selected_unit.stats.abilities:
                                move_speed *= 2
                            if 'flying' in self.selected_unit.stats.abilities:
                                move_speed = (
                                    constants.COMBAT_GRID_WIDTH + constants.COMBAT_GRID_HEIGHT
                                )
                            if (
                                self.grid[cy][cx] is None
                                and (cx, cy) not in self.ice_walls
                                and dist <= move_speed
                            ):
                                path = combat_rules.blocking_squares((x0, y0), (cx, cy))
                                path.append((cx, cy))
                                total_time = dist * 0.3
                                step_time = total_time / len(path) if path else 0.0
                                print(f"Moving {self.selected_unit.stats.name} to {(cx, cy)}")
                                for nx, ny in path:
                                    self.move_unit(self.selected_unit, nx, ny, duration=step_time)
                                    elapsed = 0.0
                                    while elapsed < step_time:
                                        combat_render.draw(self, frame)
                                        for overlay in self.overlays:
                                            overlay.draw()
                                        pygame.display.flip()
                                        dt = clock.tick(constants.FPS) / 1000.0
                                        frame = (frame + 1) % 60
                                        elapsed += dt

                                if self.get_status(self.selected_unit, 'charge'):
                                    # allow attack after move
                                    self.selected_action = None
                                else:
                                    self.selected_unit.acted = True
                                    self.selected_unit = None
                                    self.selected_action = None
                                    self.advance_turn()
                            else:
                                print("Invalid destination")
                        elif self.selected_action in ('melee', 'ranged'):
                            target_unit = self.grid[cy][cx]
                            if target_unit and target_unit.side == 'enemy':
                                dist = abs(cx - self.selected_unit.x) + abs(cy - self.selected_unit.y)
                                if (
                                    self.selected_action == 'melee' and dist == 1
                                ) or (
                                    self.selected_action == 'ranged'
                                    and self.selected_unit.stats.min_range <= dist <= self.selected_unit.stats.attack_range
                                ):
                                    attack_type = 'melee' if self.selected_action == 'melee' else 'ranged'
                                    self.animate_attack(self.selected_unit, target_unit, attack_type)
                                    dmg = self.resolve_attack(self.selected_unit, target_unit, attack_type)
                                    print(
                                        f"{self.selected_unit.stats.name} attacks {target_unit.stats.name} for {dmg} damage!"
                                    )
                                    if (
                                        "multi_shot" in self.selected_unit.stats.abilities
                                        and target_unit.is_alive
                                    ):
                                        self.animate_attack(
                                            self.selected_unit, target_unit, attack_type
                                        )
                                        dmg2 = self.resolve_attack(
                                            self.selected_unit, target_unit, attack_type
                                        )
                                        print(
                                            f"{self.selected_unit.stats.name} performs a second attack for {dmg2} damage!",
                                        )
                                    if not target_unit.is_alive:
                                        print(f"Enemy {target_unit.stats.name} is defeated!")
                                        self.remove_unit_from_grid(target_unit)
                                    self.selected_unit.acted = True
                                    self.selected_unit = None
                                    self.selected_action = None
                                    self.advance_turn()
                                else:
                                    print("Target out of range")
                            else:
                                print("No enemy unit there")
                        elif self.selected_action == 'spell':
                            print("Select a spell with the keyboard")
                elif event.type == pygame.MOUSEBUTTONUP:
                    if event.button == 3:
                        self._dragging = False
                elif event.type == pygame.MOUSEMOTION:
                    if self._dragging:
                        dx, dy = event.rel
                        self.offset_x += dx
                        self.offset_y += dy
                elif event.type == pygame.MOUSEWHEEL:
                    self._adjust_zoom(event.y * 0.25, pygame.mouse.get_pos())
            if self.overlays:
                combat_render.draw(self, frame)
                for overlay in self.overlays:
                    overlay.draw()
                pygame.display.flip()
                clock.tick(constants.FPS)
                frame = (frame + 1) % 60
                continue
            if current_unit.side != 'hero':
                combat_ai.enemy_ai_turn(self, current_unit)
                current_unit.acted = True
                self.advance_turn()
            # draw battle each iteration
            combat_render.draw(self, frame)
            for overlay in self.overlays:
                overlay.draw()
            pygame.display.flip()
            clock.tick(constants.FPS)
            frame = (frame + 1) % 60
        # Should never reach here
        return True, self.experience_gained()

    def _adjust_zoom(self, delta: float, pivot: Tuple[int, int]) -> None:
        """Change zoom level keeping a pivot point stable."""
        old_zoom = self.zoom
        self.zoom = max(0.5, min(2.0, self.zoom + delta))
        if self.zoom == old_zoom:
            return
        px, py = pivot
        scale = self.zoom / old_zoom
        self.offset_x = px - (px - self.offset_x) * scale
        self.offset_y = py - (py - self.offset_y) * scale

    def pixel_to_cell(self, px: int, py: int) -> Optional[Tuple[int, int]]:
        """Convert pixel coordinates to grid cell coordinates."""
        # Adjust for the grid's offset and current zoom before converting
        # pixel coordinates to grid indices.  If the click lands outside the
        # grid, ``None`` is returned so the event can be ignored.
        px = (px - self.offset_x) / self.zoom
        py = (py - self.offset_y) / self.zoom
        if px < 0 or py < 0:
            return None
        col = int(px // (self.hex_width * 3 / 4))
        row_offset = self.hex_height / 2 if col % 2 else 0
        row = int((py - row_offset) // self.hex_height)
        if 0 <= col < constants.COMBAT_GRID_WIDTH and 0 <= row < constants.COMBAT_GRID_HEIGHT:
            return col, row
        return None

    def cell_rect(self, x: int, y: int) -> pygame.Rect:
        w = int(self.hex_width * self.zoom)
        h = int(self.hex_height * self.zoom)
        px = int(self.offset_x + x * w * 3 / 4)
        py = int(self.offset_y + y * h + (h / 2 if x % 2 else 0))
        return pygame.Rect(px, py, w, h)

    @staticmethod
    def offset_to_axial(x: int, y: int) -> Tuple[int, int]:
        q = x
        r = y - (x - (x & 1)) // 2
        return q, r

    @staticmethod
    def axial_to_offset(q: int, r: int) -> Tuple[int, int]:
        x = q
        y = r + (q - (q & 1)) // 2
        return x, y

    def hex_neighbors(self, x: int, y: int) -> List[Tuple[int, int]]:
        q, r = self.offset_to_axial(x, y)
        directions = [(1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1)]
        neighbors: List[Tuple[int, int]] = []
        for dq, dr in directions:
            nq, nr = q + dq, r + dr
            nx, ny = self.axial_to_offset(nq, nr)
            if 0 <= nx < constants.COMBAT_GRID_WIDTH and 0 <= ny < constants.COMBAT_GRID_HEIGHT:
                neighbors.append((nx, ny))
        return neighbors

    def hex_distance(self, a: Tuple[int, int], b: Tuple[int, int]) -> int:
        aq, ar = self.offset_to_axial(*a)
        bq, br = self.offset_to_axial(*b)
        return int((abs(aq - bq) + abs(ar - br) + abs(aq + ar - bq - br)) / 2)

    def generate_obstacles(self, count: int) -> None:
        """Randomly place impassable obstacles on the grid."""
        attempts = 0
        while len(self.obstacles) < count and attempts < count * 10:
            x = random.randint(2, constants.COMBAT_GRID_WIDTH - 3)
            y = random.randint(1, constants.COMBAT_GRID_HEIGHT - 2)
            attempts += 1
            if self.grid[y][x] is None:
                self.obstacles.add((x, y))

    def has_line_of_sight(self, x1: int, y1: int, x2: int, y2: int) -> bool:
        """Return ``True`` if no obstacles block the path between two cells."""
        start = self.offset_to_axial(x1, y1)
        end = self.offset_to_axial(x2, y2)
        steps = self.hex_distance((x1, y1), (x2, y2))
        if steps == 0:
            return True

        def axial_to_cube(q: int, r: int) -> Tuple[int, int, int]:
            return q, r, -q - r

        def cube_lerp(a: Tuple[float, float, float], b: Tuple[float, float, float], t: float) -> Tuple[float, float, float]:
            return (
                a[0] + (b[0] - a[0]) * t,
                a[1] + (b[1] - a[1]) * t,
                a[2] + (b[2] - a[2]) * t,
            )

        def cube_round(c: Tuple[float, float, float]) -> Tuple[int, int, int]:
            rx, ry, rz = round(c[0]), round(c[1]), round(c[2])
            x_diff, y_diff, z_diff = abs(rx - c[0]), abs(ry - c[1]), abs(rz - c[2])
            if x_diff > y_diff and x_diff > z_diff:
                rx = -ry - rz
            elif y_diff > z_diff:
                ry = -rx - rz
            else:
                rz = -rx - ry
            return rx, ry, rz

        a_cube = axial_to_cube(*start)
        b_cube = axial_to_cube(*end)
        for i in range(1, steps):
            t = i / steps
            cube = cube_round(cube_lerp(a_cube, b_cube, t))
            q, r, _ = cube
            ox, oy = self.axial_to_offset(q, r)
            if (ox, oy) in self.obstacles or (ox, oy) in self.ice_walls:
                return False
        return True

    def move_unit(self, unit: Unit, x: int, y: int, duration: float = 0.0) -> None:
        """Move a unit to the specified cell on the grid.

        When ``duration`` is greater than zero an animation is queued using
        :class:`~core.fx.FXQueue` to interpolate the unit sprite from its
        previous cell to the new destination over the given time.
        """
        # Remove from old position
        old_x, old_y = unit.x, unit.y
        if old_x is not None and old_y is not None:
            # Animate the transition before actually moving the unit on the grid
            if duration > 0:
                start_rect = self.cell_rect(old_x, old_y)
                end_rect = self.cell_rect(x, y)
                if hasattr(pygame, "math"):
                    start_pos = pygame.math.Vector2(start_rect.center)
                    end_pos = pygame.math.Vector2(end_rect.center)
                else:
                    start_pos = start_rect.center
                    end_pos = end_rect.center
                img = self.get_unit_image(unit, start_rect.size)
                if img is not None:
                    velocity = (
                        (end_pos[0] - start_pos[0]) / duration,
                        (end_pos[1] - start_pos[1]) / duration,
                    ) if not hasattr(pygame, "math") else (end_pos - start_pos) / duration
                    event = FXEvent(img, start_pos, duration, z=50, velocity=velocity)
                    self.fx_queue.add(event)
            self.grid[old_y][old_x] = None
        # Place at new position
        self.grid[y][x] = unit
        unit.x = x
        unit.y = y
        if old_x is not None and old_y is not None:
            dx = x - old_x
            dy = y - old_y
            if dx or dy:
                unit.facing = (
                    0 if dx == 0 else (1 if dx > 0 else -1),
                    0 if dy == 0 else (1 if dy > 0 else -1),
                )
        audio.play_sound('move')
        # ability runtime: track moved tiles
        rt = self._rt(unit)
        if rt:
            rt.moved_tiles_this_turn += 1


    def remove_unit_from_grid(self, unit: Unit) -> None:
        """Remove ``unit`` from all combat structures.

        Prior to this change dead stacks were merely cleared from the grid and
        left inside the various unit lists.  This could lead to "ghost" piles
        lingering in ``self.units``/``turn_order`` after they had been defeated.
        The helper now removes the unit from the grid, the global unit
        collection, the side specific lists and the current turn order.
        """
        if unit.x is not None and unit.y is not None:
            self.grid[unit.y][unit.x] = None

        # Prune from master list and side lists
        if unit in self.units:
            self.units.remove(unit)
        if unit in self.hero_units:
            self.hero_units.remove(unit)
        if unit in self.enemy_units:
            self.enemy_units.remove(unit)

        # Ensure the unit cannot act again this round
        if unit in self.turn_order:
            idx = self.turn_order.index(unit)
            self.turn_order.remove(unit)
            if idx <= self.current_index and self.current_index > 0:
                self.current_index -= 1

    def animate_projectile(
        self, image_key: str, start: Tuple[int, int], end: Tuple[int, int]
    ) -> None:
        """Animate a projectile travelling from ``start`` to ``end``.

        ``start`` and ``end`` are grid coordinates.  If the required image is
        not present in ``self.assets`` the animation silently does nothing so
        tests and headless environments can run without the asset files.
        """
        img = self.assets.get(image_key)
        if img is None:
            return
        tile = int(constants.COMBAT_TILE_SIZE * self.zoom)
        w, h = img.get_size()
        scale = min(tile / w, tile / h, 1.0)
        if scale != 1.0 and hasattr(pygame, "transform"):
            img = pygame.transform.smoothscale(img, (int(w * scale), int(h * scale)))

        start_rect = self.cell_rect(*start)
        end_rect = self.cell_rect(*end)
        duration = 10 / constants.FPS
        if hasattr(pygame, "math"):
            start_pos = pygame.math.Vector2(start_rect.center)
            end_pos = pygame.math.Vector2(end_rect.center)
            velocity = (end_pos - start_pos) / duration
        else:
            start_pos = start_rect.center
            end_pos = end_rect.center
            velocity = (
                (end_pos[0] - start_pos[0]) / duration,
                (end_pos[1] - start_pos[1]) / duration,
            )
        event = FXEvent(img, start_pos, duration, z=100, velocity=velocity)
        self.fx_queue.add(event)

    def show_hit_effect(self, pos: Tuple[int, int], kind: str) -> None:
        """Display a transient hit effect (explosion or spark)."""
        frames = self._hit_effect_sprites.get(kind)
        if not frames:
            return
        rect = self.cell_rect(*pos)
        w, h = frames[0].get_size()
        scale = min(rect.width / w, rect.height / h, 1.0)
        if scale != 1.0 and hasattr(pygame, "transform"):
            frames = [pygame.transform.smoothscale(f, (int(w * scale), int(h * scale))) for f in frames]
        center = rect.center
        img_pos = pygame.math.Vector2(center) if hasattr(pygame, "math") else center
        frame_time = 1 / constants.FPS
        duration = frame_time * len(frames)
        event = AnimatedFX(pos=img_pos, duration=duration, frames=frames, frame_time=frame_time, z=200)
        self.fx_queue.add(event)

    def show_effect(self, image_key: str, pos: Tuple[int, int]) -> None:
        """Display a static or animated effect image on the grid."""
        entry = get_vfx_entry(image_key)
        frame_time = entry.get("frame_time", 1 / constants.FPS) if entry else 1 / constants.FPS
        fw = entry.get("frame_width", constants.COMBAT_TILE_SIZE) if entry else constants.COMBAT_TILE_SIZE
        fh = entry.get("frame_height", constants.COMBAT_TILE_SIZE) if entry else constants.COMBAT_TILE_SIZE
        sheet = self.assets.get(image_key)
        fallback = getattr(self.assets, "_fallback", None)
        if sheet is fallback:
            frames = [sheet]
        else:
            frames = load_animation(self.assets, image_key, fw, fh)
            if not frames:
                return
        rect = self.cell_rect(*pos)
        if hasattr(frames[0], "get_size"):
            w, h = frames[0].get_size()
            scale = min(self.hex_width / w, self.hex_height / h)
            if scale != 1.0 and hasattr(pygame, "transform"):
                frames = [
                    pygame.transform.smoothscale(f, (int(w * scale), int(h * scale)))
                    for f in frames
                ]
        if hasattr(rect, "center"):
            center = rect.center
        else:
            center = (rect.x + rect.width // 2, rect.y + rect.height // 2)
        img_pos = pygame.math.Vector2(center) if hasattr(pygame, "math") else center
        duration = frame_time * len(frames)
        if len(frames) > 1:
            event = AnimatedFX(pos=img_pos, duration=duration, frames=frames, frame_time=frame_time, z=100)
        else:
            event = FXEvent(frames[0], img_pos, duration, z=100)
        self.fx_queue.add(event)

    def animate_attack(self, attacker: Unit, target: Unit, attack_type: str) -> None:
        """Trigger a visual effect for ranged or magical attacks."""
        audio.play_sound('attack')
        if attack_type != "ranged":
            return
        if attacker.stats.name == "Archer":
            self.animate_projectile(
                "arrow", (attacker.x, attacker.y), (target.x, target.y)
            )
        elif attacker.stats.name == "Mage":
            self.animate_projectile(
                "fireball", (attacker.x, attacker.y), (target.x, target.y)
            )

                
    def reachable_squares(self, unit: Unit) -> List[Tuple[int, int]]:
        """Return a list of cells within movement range that are empty."""
        reachable: List[Tuple[int, int]] = []
        if "flying" in unit.stats.abilities:
            for y in range(constants.COMBAT_GRID_HEIGHT):
                for x in range(constants.COMBAT_GRID_WIDTH):
                    if (
                        self.grid[y][x] is None
                        and (x, y) not in self.ice_walls
                        and (x, y) not in self.obstacles
                    ):
                        reachable.append((x, y))
            return reachable

        move_speed = unit.stats.speed
        if "charge" in unit.stats.abilities:
            move_speed *= 2

        start = (unit.x, unit.y)
        queue: Deque[Tuple[Tuple[int, int], int]] = deque([(start, 0)])
        visited = {start}
        while queue:
            (cx, cy), dist = queue.popleft()
            for nx, ny in self.hex_neighbors(cx, cy):
                if (nx, ny) in visited:
                    continue
                if self.grid[ny][nx] is not None:
                    continue
                if (nx, ny) in self.obstacles or (nx, ny) in self.ice_walls:
                    continue
                ndist = dist + 1
                if ndist <= move_speed:
                    reachable.append((nx, ny))
                    visited.add((nx, ny))
                    queue.append(((nx, ny), ndist))
        return reachable

    def attackable_squares(self, unit: Unit, action: str) -> List[Tuple[int, int]]:
        """Return cells that could be targeted with the given attack action."""
        squares: List[Tuple[int, int]] = []
        if action == "melee":
            for nx, ny in self.hex_neighbors(unit.x, unit.y):
                if (nx, ny) not in self.obstacles and (nx, ny) not in self.ice_walls:
                    squares.append((nx, ny))
            return squares

        for y in range(constants.COMBAT_GRID_HEIGHT):
            for x in range(constants.COMBAT_GRID_WIDTH):
                if (x, y) in self.obstacles or (x, y) in self.ice_walls:
                    continue
                dist = self.hex_distance((unit.x, unit.y), (x, y))
                if (
                    unit.stats.min_range <= dist <= unit.stats.attack_range
                    and self.has_line_of_sight(unit.x, unit.y, x, y)
                ):
                    squares.append((x, y))
        return squares
