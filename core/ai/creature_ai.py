"""Behaviour for neutral creature stacks roaming the world map."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import random
from typing import List, Tuple

from core.entities import Unit


class CreatureBehavior(Enum):
    """High level behaviour modes for neutral stacks."""

    GUARDIAN = "guardian"
    ROAMER = "roamer"
    ERRATIC = "erratic"


@dataclass
class CreatureAI:
    """Base AI controller for a neutral group of creatures.

    Sub-classes implement behaviour specific ``update`` methods.  ``spawn`` keeps
    track of the original location so that guardians can respect their guard
    range and roamers know their patrol origin.
    """

    x: int
    y: int
    units: List[Unit]
    behavior: CreatureBehavior
    spawn: Tuple[int, int] = field(init=False)

    def __post_init__(self) -> None:  # pragma: no cover - trivial
        self.spawn = (self.x, self.y)

    def _strength(self) -> int:
        return sum(u.count for u in self.units)

    def update(self, world, hero_pos: Tuple[int, int], hero_strength: int) -> None:
        raise NotImplementedError


@dataclass
class GuardianAI(CreatureAI):
    """Stationary guards that only react within ``guard_range``."""

    guard_range: int = 0

    def __init__(self, x: int, y: int, units: List[Unit], guard_range: int = 0):
        super().__init__(x, y, units, CreatureBehavior.GUARDIAN)
        self.guard_range = guard_range

    def update(self, world, hero_pos: Tuple[int, int], hero_strength: int) -> None:
        if not self.units:
            return
        hx, hy = hero_pos
        dist = abs(hx - self.x) + abs(hy - self.y)
        if dist > self.guard_range:
            return  # stay put
        pursuing = self._strength() >= hero_strength
        dx = 1 if hx > self.x else -1 if hx < self.x else 0
        dy = 1 if hy > self.y else -1 if hy < self.y else 0
        if not pursuing:
            dx, dy = -dx, -dy
        nx, ny = self.x + dx, self.y + dy
        if (
            world.in_bounds(nx, ny)
            and abs(nx - self.spawn[0]) + abs(ny - self.spawn[1]) <= self.guard_range
        ):
            dest = world.grid[ny][nx]
            if (
                dest.is_passable()
                and dest.enemy_units is None
                and dest.treasure is None
                and not (hx == nx and hy == ny)
            ):
                world.grid[self.y][self.x].enemy_units = None
                dest.enemy_units = self.units
                self.x, self.y = nx, ny


@dataclass
class RoamingAI(CreatureAI):
    """Wandering stacks that patrol around ``patrol_radius`` tiles."""

    patrol_radius: int = 3

    def __init__(self, x: int, y: int, units: List[Unit], patrol_radius: int = 3):
        super().__init__(x, y, units, CreatureBehavior.ROAMER)
        self.patrol_radius = patrol_radius

    def update(self, world, hero_pos: Tuple[int, int], hero_strength: int) -> None:
        if not self.units:
            return
        hx, hy = hero_pos
        dist = abs(hx - self.x) + abs(hy - self.y)
        my_strength = self._strength()
        target = None
        if dist <= self.patrol_radius:
            pursuing = my_strength >= hero_strength
            dx = 1 if hx > self.x else -1 if hx < self.x else 0
            dy = 1 if hy > self.y else -1 if hy < self.y else 0
            if not pursuing:
                dx, dy = -dx, -dy
            target = (self.x + dx, self.y + dy)
        else:
            directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
            random.shuffle(directions)
            for dx, dy in directions:
                nx, ny = self.x + dx, self.y + dy
                if abs(nx - self.spawn[0]) + abs(ny - self.spawn[1]) <= self.patrol_radius:
                    target = (nx, ny)
                    break
        if target is None:
            return
        nx, ny = target
        if world.in_bounds(nx, ny):
            dest = world.grid[ny][nx]
            if (
                dest.is_passable()
                and dest.enemy_units is None
                and dest.treasure is None
                and not (hx == nx and hy == ny)
            ):
                world.grid[self.y][self.x].enemy_units = None
                dest.enemy_units = self.units
                self.x, self.y = nx, ny
