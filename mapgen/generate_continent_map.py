"""Utility to generate continent maps with resources and cities."""

from __future__ import annotations

import argparse
import random
from typing import List, Tuple

from .continents import generate_continent_map as _base_generate

RESOURCE_CHAR = "r"  # feature symbol for resource deposits
CITY_CHAR = "T"       # feature symbol for towns/cities


def _place_features(rows: List[str], num_resources: int, num_cities: int) -> List[str]:
    """Place simple resource deposits and cities on ``rows``.

    ``rows`` is the list returned by :func:`mapgen.continents.generate_continent_map`
    where even indices hold biome letters and odd indices contain feature
    symbols.  Resources and cities are marked by replacing the feature
    character with :data:`RESOURCE_CHAR` and :data:`CITY_CHAR` respectively.
    """

    if not rows:
        return rows
    height = len(rows)
    width = len(rows[0]) // 2
    grid = [list(r) for r in rows]
    land_cells: List[Tuple[int, int]] = [
        (x, y)
        for y in range(height)
        for x in range(width)
        if grid[y][2 * x] not in {"W", "R"}
    ]
    random.shuffle(land_cells)
    for _ in range(min(num_resources, len(land_cells))):
        x, y = land_cells.pop()
        grid[y][2 * x + 1] = RESOURCE_CHAR
    for _ in range(min(num_cities, len(land_cells))):
        x, y = land_cells.pop()
        grid[y][2 * x + 1] = CITY_CHAR
    return ["".join(r) for r in grid]


def generate_continent_map(width: int, height: int, seed: int | None = None,
                           num_resources: int = 5, num_cities: int = 2,
                           return_metadata: bool = False):
    """Generate a continent map and place resources and cities."""
    generated = _base_generate(width, height, seed=seed, return_metadata=return_metadata)
    if return_metadata and hasattr(generated, "rows"):
        generated.rows = _place_features(generated.rows, num_resources, num_cities)
        return generated
    rows = generated if isinstance(generated, list) else generated.rows
    return _place_features(rows, num_resources, num_cities)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("width", type=int)
    parser.add_argument("height", type=int)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--resources", type=int, default=5,
                        help="number of resource deposits to place")
    parser.add_argument("--cities", type=int, default=2,
                        help="number of cities to place")
    args = parser.parse_args()

    rows = generate_continent_map(
        args.width,
        args.height,
        seed=args.seed,
        num_resources=args.resources,
        num_cities=args.cities,
    )
    for row in rows:
        print(row)


if __name__ == "__main__":
    main()
