from __future__ import annotations

from typing import Set, Tuple
import heapq

from loaders.biomes import BiomeCatalog
import constants
from .entities import UnitCarrier

# Base vision range in movement cost units
BASE_VISION = 4


def compute_vision(
    world: "WorldMap", actor: "UnitCarrier", radius: int = BASE_VISION
) -> Set[Tuple[int, int]]:
    """Return coordinates of tiles visible to ``actor`` on ``world``.

    A simple breadth-first search is performed where the movement cost of each
    tile acts as the distance metric.  Tiles that would require a cumulative
    cost greater than ``radius`` are not visible.  Impassable or obstacle tiles
    block further propagation but are themselves considered visible if within
    range.
    """
    # Apply any vision bonus granted by the tile the actor currently occupies
    tile = world.grid[actor.y][actor.x]
    bonus = getattr(tile, "vision_bonus", 0)
    biome = BiomeCatalog.get(tile.biome)
    if biome is not None:
        bonus += getattr(biome, "vision_bonus", 0)
    radius += bonus
    has_boat = getattr(actor, "naval_unit", None) is not None

    visible: Set[Tuple[int, int]] = set()
    start = (actor.x, actor.y)
    queue: list[Tuple[int, Tuple[int, int]]] = [(0, start)]
    visited: Set[Tuple[int, int]] = set()
    while queue:
        cost, (x, y) = heapq.heappop(queue)
        if (x, y) in visited:
            continue
        visited.add((x, y))
        visible.add((x, y))
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if not world.in_bounds(nx, ny):
                continue
            if (nx, ny) in visited:
                continue
            tile = world.grid[ny][nx]
            biome = BiomeCatalog.get(tile.biome)
            if getattr(tile, "road", False):
                move_cost = constants.ROAD_COST
            elif biome is not None:
                move_cost = getattr(biome, "terrain_cost", 1)
            else:
                move_cost = 1
            new_cost = cost + move_cost
            if new_cost > radius:
                continue
            # Impassable terrain stops vision but can still be seen
            if not tile.is_passable(has_boat=has_boat):
                visible.add((nx, ny))
                continue
            heapq.heappush(queue, (new_cost, (nx, ny)))
    return visible


__all__ = ["compute_vision", "BASE_VISION"]
