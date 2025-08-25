import random

import pytest
from mapgen.continents import generate_continent_map
from core.world import WorldMap


def _shipyard_positions(world: WorldMap):
    return [
        (x, y)
        for y in range(world.height)
        for x in range(world.width)
        if world.grid[y][x].building and world.grid[y][x].building.name == "Shipyard"
    ]


@pytest.mark.slow
def test_starting_area_has_shipyard_when_near_water():
    random.seed(0)
    rows = generate_continent_map(30, 30, seed=0)
    world = WorldMap(map_data=rows)
    htx, hty = world.hero_town
    shipyards = _shipyard_positions(world)
    assert any(abs(x - htx) + abs(y - hty) <= 5 for x, y in shipyards)


@pytest.mark.slow
def test_each_continent_has_shipyard():
    random.seed(0)
    rows = generate_continent_map(30, 30, seed=0)
    world = WorldMap(map_data=rows)
    shipyards = set(_shipyard_positions(world))
    for continent in world._find_continents():
        assert any((x, y) in shipyards for x, y in continent)
