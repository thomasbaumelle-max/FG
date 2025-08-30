import types
import sys
from core.entities import RECRUITABLE_UNITS

SWORDSMAN_STATS = RECRUITABLE_UNITS["swordsman"]


def test_caravan_travel_and_arrival():
    from core.world import WorldMap
    from core.buildings import Town
    from core.entities import Unit
    from state.game_state import GameState

    world = WorldMap(width=5, height=1, biome_weights={"scarletia_echo_plain": 1.0}, num_obstacles=0, num_treasures=0, num_enemies=0)
    t1, t2 = Town("A"), Town("B")
    world.grid[0][0].building = t1
    world.grid[0][3].building = t2

    gs = GameState(world=world)

    unit = Unit(SWORDSMAN_STATS, 5, "hero")
    t1.garrison.append(unit)
    assert t1.send_caravan(t2, [unit], world)
    assert not t1.garrison

    gs.next_day(); gs.next_day(); gs.next_day()
    assert t2.garrison and t2.garrison[0] is unit



def test_world_map_advances_caravans():
    from core.world import WorldMap
    from core.buildings import Town
    from core.entities import Unit

    world = WorldMap(width=3, height=1, biome_weights={"scarletia_echo_plain": 1.0}, num_obstacles=0, num_treasures=0, num_enemies=0)
    t1, t2 = Town("A"), Town("B")
    world.grid[0][0].building = t1
    world.grid[0][2].building = t2
    unit = Unit(SWORDSMAN_STATS, 1, "hero")
    t1.garrison.append(unit)
    assert t1.send_caravan(t2, [unit], world)
    world.advance_day()
    world.advance_day()
    assert unit in t2.garrison


def test_auto_caravan_to_nearest_ally():
    from core.world import WorldMap
    from core.buildings import Town
    from core.entities import Unit, Hero

    world = WorldMap(width=5, height=1, biome_weights={"scarletia_echo_plain": 1.0}, num_obstacles=0, num_treasures=0, num_enemies=0)
    t1, t2 = Town("A"), Town("B")
    world.grid[0][0].building = t1
    world.grid[0][3].building = t2
    t1.owner = t2.owner = 1

    unit = Unit(SWORDSMAN_STATS, 2, "hero")
    t1.garrison.append(unit)
    hero = Hero(4, 0, [])

    world.advance_day(hero)
    assert not t1.garrison and t1.caravan_orders

    for _ in range(3):
        world.advance_day(hero)
    assert unit in t2.garrison


