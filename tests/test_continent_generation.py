import random

import pytest
from mapgen.continents import generate_continent_map


@pytest.mark.slow
def test_generate_continent_map_contains_land_and_ocean():
    random.seed(0)
    width, height = 20, 15
    rows = generate_continent_map(width, height, seed=0)
    assert len(rows) == height
    assert all(len(r) == width * 2 for r in rows)
    chars = set(''.join(rows))
    assert 'W' in chars  # ocean present
    land_chars = chars.intersection(set('GFDMHSJI'))
    assert land_chars  # at least one land tile


@pytest.mark.slow
def test_biome_adjacency_respects_rules():
    random.seed(0)
    width, height = 20, 15
    rows = generate_continent_map(width, height, seed=0, biome_chars="GFDI")
    grid = [[row[i] for i in range(0, len(row), 2)] for row in rows]
    height = len(grid)
    width = len(grid[0]) if grid else 0
    from mapgen.continents import DEFAULT_BIOME_COMPATIBILITY
    for y in range(height):
        for x in range(width):
            c1 = grid[y][x]
            if c1 in ("W",):
                continue
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < width and 0 <= ny < height:
                    c2 = grid[ny][nx]
                    if c2 in ("W",):
                        continue
                    assert c2 in DEFAULT_BIOME_COMPATIBILITY.get(c1, {c2})
