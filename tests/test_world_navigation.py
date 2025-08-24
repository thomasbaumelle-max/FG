import audio
from tests.test_army_actions import setup_game
from core.game import Game as GameClass


def setup_water_game(monkeypatch):
    game, constants, Army, Unit, S_STATS = setup_game(monkeypatch)
    # restore real pathfinding implementation
    game.compute_path = GameClass.compute_path.__get__(game, GameClass)
    game._compute_path_cached = GameClass._compute_path_cached.__get__(game, GameClass)
    game._compute_path_cached.cache_clear()
    # configure simple map with a water tile between land tiles
    game.world.grid[0][0].biome = "scarletia_echo_plain"
    game.world.grid[0][1].biome = "ocean"
    game.world.grid[0][2].biome = "scarletia_echo_plain"
    game.hero.x = 0
    game.hero.y = 0
    game.hero.ap = 10
    return game


def test_path_requires_boat(monkeypatch):
    game = setup_water_game(monkeypatch)
    # cannot cross water without a boat
    assert game.compute_path((0, 0), (2, 0)) is None
    # after obtaining a boat, water becomes traversable
    game.hero.naval_unit = "barge"
    assert game.compute_path((0, 0), (2, 0)) == [(1, 0), (2, 0)]


def test_embark_disembark_cost(monkeypatch):
    game = setup_water_game(monkeypatch)
    monkeypatch.setattr(audio, "play_sound", lambda *a, **k: None)
    game.hero.naval_unit = "barge"
    start_ap = game.hero.ap
    # embark onto water
    game.try_move_hero(1, 0)
    assert (game.hero.x, game.hero.y) == (1, 0)
    assert game.hero.ap == start_ap - 2  # move + embark cost
    # disembark onto land
    game.try_move_hero(1, 0)
    assert (game.hero.x, game.hero.y) == (2, 0)
    assert game.hero.ap == start_ap - 4
    # boat remains available after docking
    assert game.hero.naval_unit == "barge"
