import audio
from tests.test_army_actions import setup_game
from core.game import Game as GameClass
from core.entities import Boat
from loaders.boat_loader import BoatDef
import audio


def setup_water_game(monkeypatch):
    game, constants, Army, Unit, S_STATS = setup_game(monkeypatch)
    game.compute_path = GameClass.compute_path.__get__(game, GameClass)
    game._compute_path_cached = GameClass._compute_path_cached.__get__(game, GameClass)
    game.world.grid[0][0].biome = "scarletia_echo_plain"
    game.world.grid[0][1].biome = "ocean"
    game.world.grid[0][2].biome = "scarletia_echo_plain"
    game.hero.x = 0
    game.hero.y = 0
    game.hero.ap = 10
    game.boat_defs = {"barge": BoatDef("barge", 4, 7, {}, "barge.png")}
    boat = Boat("barge", 1, 0, 4, 7, owner=0)
    game.world.grid[0][1].boat = boat
    return game


def test_path_requires_boat(monkeypatch):
    game = setup_water_game(monkeypatch)
    assert game.compute_path((0, 0), (2, 0)) is None
    boat = game.world.grid[0][1].boat
    game.embark(game.hero, boat)
    game._compute_path_cached.cache_clear()
    assert game.compute_path((1, 0), (2, 0)) == [(2, 0)]


def test_embark_disembark_cost(monkeypatch):
    game = setup_water_game(monkeypatch)
    monkeypatch.setattr(audio, "play_sound", lambda *a, **k: None)
    boat = game.world.grid[0][1].boat
    start_ap = game.hero.ap
    game.embark(game.hero, boat)
    assert (game.hero.x, game.hero.y) == (1, 0)
    assert game.hero.ap == start_ap - 1
    game.try_move_hero(1, 0)
    assert (game.hero.x, game.hero.y) == (2, 0)
    assert game.hero.ap == start_ap - 3
    assert game.hero.naval_unit is None
    assert game.world.grid[0][1].boat is not None
