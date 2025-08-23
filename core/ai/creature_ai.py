from __future__ import annotations

"""Behaviour for neutral creature stacks roaming the world map."""

from dataclasses import dataclass, field
import random
from typing import List, Tuple

from core.entities import Unit


@dataclass
class CreatureAI:
    """Lightweight AI controller for a neutral group of creatures.

    Each instance tracks a stack of units spawned at a given position.  The
    group patrols around its spawn point within ``patrol_radius`` tiles and
    reacts to the player's hero: if the hero is weaker it will pursue, otherwise
    it attempts to flee.
    """

    x: int
    y: int
    units: List[Unit]
    patrol_radius: int = 3
    spawn: Tuple[int, int] = field(init=False)

    def __post_init__(self) -> None:
        self.spawn = (self.x, self.y)

    def _strength(self) -> int:
        return sum(u.count for u in self.units)

    def update(self, world, hero_pos: Tuple[int, int], hero_strength: int) -> None:
        """Update the creature group's position for one world turn."""
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
