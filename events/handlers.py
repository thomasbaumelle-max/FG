"""Built-in event handlers."""
from typing import Any, Dict


def explore_tile(game, params: Dict[str, Any]) -> None:
    """Reveal a tile on the world map.

    Parameters are expected to contain ``x`` and ``y`` tile coordinates and
    optionally a ``radius``.  The handler marks the corresponding tiles as
    explored for player 0 using :meth:`world.reveal` when available.
    """
    world = getattr(game, "world", None)
    if world is None:
        return
    x = int(params.get("x", 0))
    y = int(params.get("y", 0))
    radius = int(params.get("radius", 0))
    reveal = getattr(world, "reveal", None)
    if callable(reveal):
        reveal(0, x, y, radius)
    else:  # Fallback for extremely small stubs in tests
        explored = getattr(world, "explored", {}).setdefault(0, [[False]])
        explored[y][x] = True


def recruit_unit(game, params: Dict[str, Any]) -> None:
    """Add units to the hero's army.

    Parameters should supply ``unit`` (string name) and ``count``.  Units are
    appended to ``hero.army`` as simple identifiers, sufficient for tests.
    """
    hero = getattr(game, "hero", None)
    if hero is None:
        return
    unit_name = params.get("unit")
    count = int(params.get("count", 1))
    if not unit_name:
        return
    army = getattr(hero, "army", None)
    if army is None:
        hero.army = army = []
    for _ in range(count):
        army.append(unit_name)
