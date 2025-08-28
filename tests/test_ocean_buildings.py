from core.buildings import create_building
from core.entities import Hero, Unit
from tests.unit_stats import get_unit_stats

SWORDSMAN_STATS = get_unit_stats("swordsman")
from core.vision import compute_vision
from core.world import WorldMap
import constants


def test_sea_sanctuary_revives_first_dead_unit():
    hero = Hero(0, 0, [Unit(SWORDSMAN_STATS, 0, "hero")])
    building = create_building("sea_sanctuary")
    building.interact(hero)
    assert hero.alive()


def test_lighthouse_grants_vision_bonus():
    wm = WorldMap(
        width=10,
        height=1,
        biome_weights={"scarletia_echo_plain": 1.0},
        num_obstacles=0,
        num_treasures=0,
        num_enemies=0,
    )
    hero = Hero(0, 0, [Unit(SWORDSMAN_STATS, 1, "hero")])
    before = compute_vision(wm, hero)
    building = create_building("lighthouse")
    building.interact(hero)
    after = compute_vision(wm, hero)
    assert (6, 0) in after and (6, 0) not in before


def test_ocean_buildings_spawn_on_water():
    rows = ["W.W.", "W.W."]
    world = WorldMap(map_data=rows)
    world._place_buildings(0)
    found = {"sea_sanctuary": False, "lighthouse": False}
    for row in world.grid:
        for tile in row:
            if tile.building:
                bid = tile.building.id
                if bid in found:
                    assert tile.biome in constants.WATER_BIOMES
                    found[bid] = True
    assert all(found.values())

