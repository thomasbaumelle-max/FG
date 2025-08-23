from types import SimpleNamespace

from core.world import WorldMap
from core.buildings import Town
from core.game import Game


def create_game_with_towns(owners):
    width = len(owners)
    wm = WorldMap(
        width=width,
        height=1,
        biome_weights={"scarletia_echo_plain": 1.0},
        num_obstacles=0,
        num_treasures=0,
        num_enemies=0,
    )
    towns = []
    for x, owner in enumerate(owners):
        town = Town()
        town.owner = owner
        wm.grid[0][x].building = town
        towns.append(town)
    game = Game.__new__(Game)
    game.world = wm
    game._initial_town_owners = {t: o for t, o in zip(towns, owners)}
    game._enemy_town_counters = {t: 0 for t, o in zip(towns, owners) if o != 0}
    game._victory_shown = False
    game._show_victory = lambda: None
    return game, towns


def test_town_control_counter_resets():
    game, towns = create_game_with_towns([1])
    town = towns[0]
    town.owner = 0
    game._update_town_control()
    assert game._enemy_town_counters[town] == 1
    game._update_town_control()
    assert game._enemy_town_counters[town] == 2
    town.owner = 1
    game._update_town_control()
    assert game._enemy_town_counters[town] == 0


def test_victory_trigger_after_seven_turns():
    game, towns = create_game_with_towns([1, 1])
    town1, town2 = towns
    town1.owner = 0
    town2.owner = 0
    called = {}
    def fake_victory():
        called['v'] = called.get('v', 0) + 1
    game._show_victory = fake_victory
    for _ in range(6):
        game._update_town_control()
    assert called == {}
    game._update_town_control()
    assert called.get('v') == 1
    game._update_town_control()
    assert called.get('v') == 1


def test_victory_trigger_with_list_world_towns():
    town = Town()
    town.owner = 1
    world = SimpleNamespace(towns=[town])
    game = Game.__new__(Game)
    game.world = world
    game._show_victory = lambda: None
    game._init_town_ownership()
    town.owner = 0
    for _ in range(6):
        game._update_town_control()
    assert not game._victory_shown
    game._update_town_control()
    assert game._victory_shown
