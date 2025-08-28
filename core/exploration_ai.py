"""Basic overworld exploration AI utilities.

This module provides helper functions for enemy heroes to navigate the
overworld using the same pathfinding logic as the player.  Targets are chosen
among the player's hero and valuable tiles such as resources or treasure.  The
behaviour can be influenced by the global AI difficulty setting.
"""

from __future__ import annotations

from typing import Optional, Tuple, List

import random
import json
from pathlib import Path


# Difficulty presets used by :func:`compute_enemy_step` are defined in a JSON
# file under ``assets/`` so that tweaking the AI does not require touching the
# source code.  The file maps difficulty labels to parameter dictionaries with
# keys ``hero_weight``, ``resource_weight``, ``building_weight`` and
# ``avoid_enemies``.


def _load_difficulty_params(path: Path = Path(__file__).resolve().parents[1] / "assets" / "ai_difficulty.json"):
    """Load and validate AI difficulty parameters from ``path``.

    The configuration must be a mapping of difficulty labels to parameter
    dictionaries.  Each parameter set must define integer weights for
    ``hero_weight``, ``resource_weight`` and ``building_weight`` as well as a
    boolean ``avoid_enemies`` flag.
    """

    with path.open(encoding="utf-8") as fh:
        data = json.load(fh)

    if not isinstance(data, dict):
        raise ValueError("Difficulty config must be a mapping")

    required = {"hero_weight", "resource_weight", "building_weight", "avoid_enemies"}
    for name, params in data.items():
        if not isinstance(params, dict):
            raise ValueError(f"Parameters for '{name}' must be a mapping")
        missing = required - params.keys()
        if missing:
            missing_list = ", ".join(sorted(missing))
            raise ValueError(f"Missing keys for difficulty '{name}': {missing_list}")
        if not all(isinstance(params[k], (int, float)) for k in ("hero_weight", "resource_weight", "building_weight")):
            raise ValueError(f"Weights for difficulty '{name}' must be numbers")
        if not isinstance(params["avoid_enemies"], bool):
            raise ValueError(f"'avoid_enemies' for '{name}' must be a boolean")

    return data


# Load parameters at module import so that ``compute_enemy_step`` can simply
# look up the selected difficulty.
DIFFICULTY_PARAMS = _load_difficulty_params()

# Maximum straight-line distance for potential targets.
# Objectives beyond this radius are ignored to avoid expensive pathfinding.
MAX_TARGET_RADIUS: int = 20


def compute_enemy_step(game, enemy, difficulty: str = "Intermédiaire") -> Optional[Tuple[int, int]]:
    """Return the next step for ``enemy`` based on the current game state.

    ``difficulty`` controls the aggressiveness of the AI.  Higher difficulty
    values make enemy heroes prioritise the player's hero more strongly while
    easier settings allow for more wandering behaviour.  Targets are scored
    using a simple weighting scheme so that dangerous or valuable objectives can
    override distance considerations.
    """

    params = DIFFICULTY_PARAMS.get(difficulty, DIFFICULTY_PARAMS["Intermédiaire"])
    start = (enemy.x, enemy.y)

    # Gather potential targets (resources, treasures, neutral buildings)
    targets: List[Tuple[Tuple[int, int], float]] = []
    for x, y in getattr(game, "treasure_tiles", []):
        tile = game.world.grid[y][x]
        if tile.treasure is not None:
            value = sum(v[1] for v in tile.treasure.values()) if isinstance(tile.treasure, dict) else 0
            weight = params["resource_weight"] + value / 100
            targets.append(((x, y), weight))
    for x, y in getattr(game, "resource_tiles", []):
        tile = game.world.grid[y][x]
        if tile.resource is not None:
            targets.append(((x, y), params["resource_weight"]))
    for x, y in getattr(game, "neutral_buildings", []):
        tile = game.world.grid[y][x]
        if tile.building and getattr(tile.building, "owner", None) != 1:
            targets.append(((x, y), params["building_weight"]))

    hero_target = ((game.hero.x, game.hero.y), params["hero_weight"])

    best_path: Optional[List[Tuple[int, int]]] = None
    best_score: float = float("inf")

    # Consider all objectives including the player's hero
    for target, weight in [hero_target, *targets]:
        if MAX_TARGET_RADIUS is not None:
            raw_dist = abs(target[0] - start[0]) + abs(target[1] - start[1])
            if raw_dist > MAX_TARGET_RADIUS:
                continue
        path = game.compute_path(start, target, avoid_enemies=params["avoid_enemies"])
        if path:
            score = len(path) / weight
            if score < best_score:
                best_score = score
                best_path = path

    if best_path:
        return best_path[0]

    # Fallback: wander towards a random free tile using the precomputed cache
    # on the game instance.  This avoids scanning the whole grid each turn.
    candidates: List[Tuple[int, int]] = list(getattr(game, "free_tiles", []))
    random.shuffle(candidates)
    for target in candidates:
        path = game.compute_path(start, target, avoid_enemies=params["avoid_enemies"])
        if path:
            return path[0]
    return None

