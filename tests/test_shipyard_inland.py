import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import constants
from core.buildings import create_building
from core.world import WorldMap


def test_shipyard_rejected_inland():
    world = WorldMap(
        width=5,
        height=5,
        num_obstacles=0,
        num_treasures=0,
        num_enemies=0,
        num_resources=0,
        num_buildings=0,
        biome_weights={"scarletia_echo_plain": 1.0},
    )
    shipyard = create_building("shipyard")
    assert not world._can_place_building(2, 2, shipyard)
    world.grid[2][1].biome = next(iter(constants.WATER_BIOMES))
    assert world._can_place_building(2, 2, shipyard)
