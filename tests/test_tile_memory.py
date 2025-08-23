import sys

from core.world import WorldMap


class DictTile:
    """Reference tile using a ``__dict__`` for attributes."""

    def __init__(self) -> None:
        self.biome = "scarletia_echo_plain"
        self.obstacle = False
        self.treasure = None
        self.enemy_units = None
        self.resource = None
        self.building = None
        self.owner = None


def test_tile_memory_reduction() -> None:
    """Ensure dataclass tiles consume less memory than dict-based tiles."""

    old_tile = DictTile()
    old_size = sys.getsizeof(old_tile) + sys.getsizeof(old_tile.__dict__)

    world = WorldMap(width=1, height=1, num_obstacles=0, num_treasures=0, num_enemies=0)
    new_size = sys.getsizeof(world.grid[0][0])

    assert new_size < old_size
