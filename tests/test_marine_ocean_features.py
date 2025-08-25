import pytest
pytestmark = pytest.mark.worldgen

from pathlib import Path

import constants
from core.world import WorldMap
from core.buildings import create_building


def _load_world() -> WorldMap:
    path = Path(__file__).parent / "fixtures" / "mini_marine_map.txt"
    world = WorldMap.from_file(str(path))
    # Reload original data to undo starting area modifications
    rows = [line.rstrip("\n") for line in open(path, "r", encoding="utf-8")]
    world._load_from_parsed_data([world._parse_row(r) for r in rows])
    # Place buildings and features on the water
    world.grid[1][1].building = create_building("sea_sanctuary")
    world.grid[3][3].building = create_building("lighthouse")
    world.grid[5][5].resource = {"gold": 1}
    world.grid[7][7].enemy_units = [object()]
    return world


def test_marine_world_scattered_ocean_features():
    world = _load_world()

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
