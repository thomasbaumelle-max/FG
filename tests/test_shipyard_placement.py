from pathlib import Path

from core.world import WorldMap
from core.buildings import Town, create_building


def _load_world() -> WorldMap:
    path = Path(__file__).parent / "fixtures" / "mini_continent_map.txt"
    world = WorldMap.from_file(str(path))
    # Place the hero's town on the first continent
    world.grid[2][4].building = Town()
    world.hero_town = (4, 2)
    # Shipyard near the hero's town
    world.grid[3][4].building = create_building("shipyard")
    # Shipyard on the second continent
    world.grid[7][7].building = create_building("shipyard")
    return world


def _shipyard_positions(world: WorldMap):
    return [
        (x, y)
        for y in range(world.height)
        for x in range(world.width)
        if world.grid[y][x].building and world.grid[y][x].building.name == "Shipyard"
    ]


def test_starting_area_has_shipyard_when_near_water():
    world = _load_world()
    htx, hty = world.hero_town
    shipyards = _shipyard_positions(world)
    assert any(abs(x - htx) + abs(y - hty) <= 5 for x, y in shipyards)


def test_each_continent_has_shipyard():
    world = _load_world()
    shipyards = set(_shipyard_positions(world))
    for continent in world._find_continents():
        assert any((x, y) in shipyards for x, y in continent)
