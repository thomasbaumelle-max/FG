import random

import pytest
from mapgen.continents import generate_continent_map
from core.world import WorldMap
import constants


@pytest.mark.slow
def test_marine_world_scattered_ocean_features():
    random.seed(0)
    rows = generate_continent_map(30, 30, seed=0, map_type="marine")
    world = WorldMap(map_data=rows)

    buildings = {"sea_sanctuary": 0, "lighthouse": 0}
    water_resources = 0
    water_creatures = 0
    for row in world.grid:
        for tile in row:
            if tile.biome in constants.WATER_BIOMES:
                if tile.building and tile.building.id in buildings:
                    buildings[tile.building.id] += 1
                if tile.resource is not None:
                    water_resources += 1
                if tile.enemy_units is not None:
                    water_creatures += 1

    assert buildings["sea_sanctuary"] >= 1
    assert buildings["lighthouse"] >= 1
    assert water_resources >= 1
    assert water_creatures >= 1
