import random

from core.world import WorldMap
import constants


def test_random_size_and_weights():
    # Ensure deterministic test behaviour
    random.seed(0)
    wm = WorldMap(
        size_range=(5, 6),
        biome_weights={"scarletia_echo_plain": 1.0},
        num_treasures=0,
        num_enemies=0,
    )
    assert 5 <= wm.width <= 6
    assert 5 <= wm.height <= 6
    for row in wm.grid:
        for tile in row:
            assert tile.biome == "scarletia_echo_plain"


def test_resource_and_building_placement():
    random.seed(0)
    wm_res = WorldMap(
        width=10,
        height=10,
        num_obstacles=0,
        num_treasures=0,
        num_enemies=0,
        num_resources=1,
        num_buildings=0,
        biome_weights={"scarletia_crimson_forest": 1.0},
    )
    resources = [tile.resource for row in wm_res.grid for tile in row if tile.resource]
    assert len(resources) > 0
    assert all(res in constants.RESOURCES for res in resources)

    wm_bld = WorldMap(
        width=5,
        height=5,
        num_obstacles=0,
        num_treasures=0,
        num_enemies=0,
        num_resources=0,
        num_buildings=1,
        biome_weights={"mountain": 1.0},
    )
    buildings = [
        tile.building.image for row in wm_bld.grid for tile in row if tile.building
    ]
    assert buildings == ["buildings/mine/mine_0.png"]
