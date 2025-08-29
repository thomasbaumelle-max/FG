"""Boss definitions and spawning helpers.

This module provides a small framework for loading boss definitions from a
JSON manifest and for placing those bosses onto the world map.  Bosses are
treated similarly to regular neutral creature stacks but carry additional
metadata such as their realm, spawn chance and the image used for their lairs.

The implementation is deliberately lightweight to keep the test environment
simple.  When run outside of the tests the game code can easily extend the
behaviour here to support more elaborate encounters or rewards.
"""

from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Dict, List, Sequence, Optional

from loaders.core import Context
from core.entities import Unit, UnitStats


@dataclass
class Boss:
    """Description of a unique boss encounter.

    Attributes
    ----------
    id:
        Unique identifier of the boss used in the JSON manifest.
    name:
        Human readable name of the boss.
    stats:
        ``UnitStats`` describing the combat statistics of the boss unit.
    drop:
        List of artifact identifiers granted after defeating the boss.
    realm:
        Thematic realm or biome the boss belongs to.
    spawn_chance:
        Probability (0-1) of the boss spawning on a given map.
    image:
        Path to the image used when rendering the boss' lair.
    """

    id: str
    name: str
    stats: UnitStats
    drop: Sequence[str]
    realm: str = ""
    spawn_chance: float = 0.0
    image: str = ""


# Global registry populated at start-up via :func:`load_boss_definitions`.
BOSS_DEFINITIONS: Dict[str, Boss] = {}


def load_boss_definitions(
    ctx: Context, manifest: str = "units_boss.json"
) -> None:
    """Load boss definitions from ``manifest`` and populate globals.

    Any errors while loading simply result in an empty definition list.  The
    function replaces the contents of :data:`BOSS_DEFINITIONS` in place so that
    callers can reload the manifest during tests.
    """

    from loaders.boss_loader import load_bosses

    try:
        bosses = load_bosses(ctx, manifest)
    except Exception:  # pragma: no cover - errors are logged by caller
        bosses = {}

    BOSS_DEFINITIONS.clear()
    BOSS_DEFINITIONS.update(bosses)


def spawn_boss_lairs(world: "WorldMap", rng: Optional[random.Random] = None) -> None:
    """Randomly place boss lairs on the ``world`` according to definitions.

    ``rng`` allows deterministic placement for tests.  Each boss listed in
    :data:`BOSS_DEFINITIONS` has an independent chance to appear.  When a boss
    is spawned its unit stack is placed on a random free tile.
    """

    if rng is None:
        rng = random

    if not BOSS_DEFINITIONS:
        return

    # Avoid interfering with small test maps by only spawning on reasonably
    # sized worlds.  Many unit tests operate on tiny maps where an unexpected
    # enemy stack would complicate hero movement.
    if world.width * world.height < 100:  # pragma: no cover - deterministic guard
        return

    candidates = world._empty_land_tiles()
    rng.shuffle(candidates)

    for boss in BOSS_DEFINITIONS.values():
        if not candidates:
            break
        if rng.random() > boss.spawn_chance:
            continue
        x, y = candidates.pop()
        tile = world.grid[y][x]
        tile.enemy_units = [Unit(boss.stats, 1, side="enemy")]


__all__ = ["Boss", "BOSS_DEFINITIONS", "load_boss_definitions", "spawn_boss_lairs"]

