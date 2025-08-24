import os
import tempfile

from core.world import WorldMap
from core.entities import REEF_SERPENT_STATS


def test_ocean_tiles_spawn_marine_enemies():
    # create a map with a single ocean tile containing an enemy
    with tempfile.NamedTemporaryFile("w", delete=False) as tmp:
        tmp.write("WE")
        path = tmp.name
    try:
        world = WorldMap.from_file(path)
        tile = world.grid[0][0]
        assert tile.biome == "ocean"
        assert tile.enemy_units is not None
        assert all(u.stats.name == REEF_SERPENT_STATS.name for u in tile.enemy_units)
    finally:
        os.remove(path)
