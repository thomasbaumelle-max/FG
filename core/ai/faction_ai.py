from __future__ import annotations

"""Simple faction AI controller.

This module defines :class:`FactionAI`, a small dataclass used by the game to
represent an enemy faction.  It keeps track of the faction's main town, the
heroes it controls and the associated economy data.  A :class:`FactionAI`
instance acts as the entry point for higher level behaviour such as town
management, unit recruitment and strategic movement across the world map.
"""

from dataclasses import dataclass, field
import logging
from typing import Iterable, List, Optional, Tuple

from core.buildings import Building, Town
from core.entities import EnemyHero
from core import economy


logger = logging.getLogger(__name__)


@dataclass
class FactionAI:
    """Container representing an AI‑controlled faction.

    The faction AI is responsible for high level decisions including:

    * gestion des villes possédées par la faction ;
    * recrutement et renforcement des héros ennemis ;
    * déplacements stratégiques des armées contrôlées par l'ordinateur.
    """

    town: Optional[Town]
    heroes: List[EnemyHero] = field(default_factory=list)
    economy: economy.PlayerEconomy = field(default_factory=economy.PlayerEconomy)

    # ------------------------------------------------------------------
    # High level decision helpers
    # ------------------------------------------------------------------
    def _find_nearest_mine(
        self, world, hero: EnemyHero, radius: int = 5
    ) -> Optional[Tuple[int, int]]:
        """Return coordinates of the closest capturable mine.

        The search is limited to a ``radius`` around ``hero`` to keep the
        operation inexpensive.  Mines are identified as any building providing
        income (``building.income``) that is not already owned by the enemy
        faction (owner ``1``).
        """

        best: Optional[Tuple[int, int]] = None
        best_dist = radius + 1
        vis = getattr(world, "visible", {}).get(1)
        for y in range(max(0, hero.y - radius), min(world.height, hero.y + radius + 1)):
            for x in range(max(0, hero.x - radius), min(world.width, hero.x + radius + 1)):
                if vis and not vis[y][x]:
                    continue
                tile = world.grid[y][x]
                b = getattr(tile, "building", None)
                if not isinstance(b, Building):
                    continue
                if not getattr(b, "income", None) or getattr(b, "owner", None) == 1:
                    continue
                dist = abs(x - hero.x) + abs(y - hero.y)
                if dist < best_dist:
                    best_dist = dist
                    best = (x, y)
        return best

    def _can_recruit(self) -> bool:
        """Return ``True`` if any owned building has units to recruit."""

        for b in getattr(self.economy, "buildings", []):
            if b.owner == 1 and getattr(b, "garrison", None):
                return True
        return False

    def _town_threatened(
        self, world, player_heroes: Optional[Iterable[object]] = None, radius: int = 5
    ) -> bool:
        """Return ``True`` if the faction town is threatened by player units."""

        if not self.town:
            return False
        # Locate town coordinates on the world grid
        town_pos: Optional[Tuple[int, int]] = None
        for y, row in enumerate(world.grid):
            for x, tile in enumerate(row):
                if tile.building is self.town:
                    town_pos = (x, y)
                    break
            if town_pos:
                break
        if town_pos is None:
            return False

        tx, ty = town_pos
        heroes = list(player_heroes or [])
        default_hero = getattr(world, "hero", None)
        if default_hero is not None and default_hero not in heroes:
            heroes.append(default_hero)

        vis = getattr(world, "visible", {}).get(1)
        for hero in heroes:
            hx, hy = getattr(hero, "x", 0), getattr(hero, "y", 0)
            if vis and not vis[hy][hx]:
                continue
            if abs(hx - tx) + abs(hy - ty) <= radius:
                return True
        return False

    def update_visibility(self, world) -> None:
        """Recompute fog-of-war information for the faction."""

        heroes = list(self.heroes)
        if heroes:
            first = True
            for hero in heroes:
                world.update_visibility(1, hero, reset=first)
                first = False
        else:
            ensure = getattr(world, "_ensure_player_fog", None)
            if ensure:
                ensure(1)
                vis = world.visible[1]
                for row in vis:
                    for i in range(len(row)):
                        row[i] = False

        towns_attr = getattr(world, "towns", None)
        towns = towns_attr() if callable(towns_attr) else towns_attr
        for town in towns or []:
            if getattr(town, "owner", None) != 1:
                continue
            loc = None
            for y, row in enumerate(world.grid):
                for x, tile in enumerate(row):
                    if tile.building is town:
                        loc = (x, y)
                        break
                if loc:
                    break
            if loc:
                ox, oy = loc
            else:
                ox, oy = getattr(town, "origin", (0, 0))
            for dx, dy in getattr(town, "footprint", [(0, 0)]):
                world.reveal(1, ox + dx, oy + dy, radius=2)

    # ------------------------------------------------------------------
    # Town management
    # ------------------------------------------------------------------
    def build_in_town(self) -> None:
        """Attempt to construct the next available structure in ``self.town``.

        Structures are prioritised by type: unit dwellings are built first in
        tier order (T1→T7) followed by utility buildings such as markets or
        magic schools.  Construction is skipped if the faction cannot afford the
        associated ``cost`` or if the town has already built something today.
        """

        town = self.town
        if not town or town.built_today:
            return

        structures = getattr(town, "structures", {})
        if not structures:
            return

        ui_order = list(getattr(town, "ui_order", structures.keys()))
        ordered: List[str] = []
        for sid in ui_order:
            info = structures.get(sid, {})
            if sid in town.built_structures:
                continue
            dwelling = info.get("dwelling", {}) if isinstance(info, dict) else {}
            if isinstance(dwelling, dict) and dwelling:
                ordered.append(sid)
        for sid in ui_order:
            if sid not in ordered and sid not in town.built_structures:
                ordered.append(sid)

        for sid in ordered:
            info = structures.get(sid, {})
            cost = town.structure_cost(sid)
            if not economy.can_afford(self.economy, cost):
                continue
            hero = self.heroes[0] if self.heroes else EnemyHero(0, 0, [])
            if town.build_structure(sid, hero, self.economy):
                dwelling = info.get("dwelling", {}) if isinstance(info, dict) else {}
                if isinstance(dwelling, dict) and dwelling:
                    desc = ", ".join(
                        f"+{amt} {uid.lower()}/sem" for uid, amt in dwelling.items()
                    )
                else:
                    desc = "utility"
                logger.info("Build %s: %s, coût OK", sid.replace("_", " "), desc)
                break

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def choose_strategy(self, game_or_world) -> str:
        """Return the current high level strategy for the faction.

        The decision hierarchy is as follows:

        1. Capture nearby mines not owned by the faction.
        2. Recruit units from owned buildings.
        3. Defend the faction town if the enemy is close to it.
        4. Harass the player (default fallback).

        ``game_or_world`` may either be the :class:`~core.game.Game` instance
        or the underlying :class:`~core.world.WorldMap`.
        """

        world = getattr(game_or_world, "world", game_or_world)
        hero = self.heroes[0] if self.heroes else None
        if hero and self._find_nearest_mine(world, hero) is not None:
            return "capture_mine"
        if self._can_recruit():
            return "recruit"
        player_hero = getattr(game_or_world, "hero", None)
        if self._town_threatened(world, [player_hero] if player_hero else None):
            return "defend"
        return "harass"


__all__ = ["FactionAI"]
