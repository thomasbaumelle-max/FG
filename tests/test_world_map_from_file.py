import pytest
pytestmark = pytest.mark.worldgen

import os
import tempfile

from core.world import WorldMap


def test_world_map_from_file_loads_tiles_correctly():
    # Create a temporary file with a mountain and characters #TE
    with tempfile.NamedTemporaryFile('w', delete=False) as tmp:
        tmp.write('M.#TE')
        tmp_path = tmp.name

    try:
        world_map = WorldMap.from_file(tmp_path)
        assert world_map.width == 4
        assert world_map.height == 1

        mountain_tile = world_map.grid[0][0]
        assert mountain_tile.biome == "mountain"
        assert not mountain_tile.obstacle
        assert not mountain_tile.is_passable()

        obstacle_tile = world_map.grid[0][1]
        assert obstacle_tile.obstacle
        assert obstacle_tile.treasure is None
        assert obstacle_tile.enemy_units is None

        treasure_tile = world_map.grid[0][2]
        assert not treasure_tile.obstacle
        assert treasure_tile.is_passable()
        assert treasure_tile.treasure is not None
        assert treasure_tile.enemy_units is None

        enemy_tile = world_map.grid[0][3]
        assert not enemy_tile.obstacle
        assert enemy_tile.is_passable()
        assert enemy_tile.treasure is None
        assert enemy_tile.enemy_units is not None
    finally:
        os.remove(tmp_path)
