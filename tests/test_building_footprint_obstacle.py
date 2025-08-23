import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from core.buildings import Building
from core.world import WorldMap


def test_multi_tile_building_blocks_movement():
    """Tiles covered by a non-passable building become obstacles."""

    building = Building()
    building.footprint = [(0, 0), (1, 0), (0, 1), (1, 1)]  # 2x2 footprint
    building.passable = False

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
    world._stamp_building(0, 0, building)

    # All tiles covered by the building's 2x2 footprint should be impassable
    blocked = [(0, 0), (1, 0), (0, 1), (1, 1)]
    for x, y in blocked:
        tile = world.grid[y][x]
        assert tile.building is building
        assert not tile.is_passable()

    # A tile outside the footprint remains passable
    assert world.grid[4][4].is_passable()

