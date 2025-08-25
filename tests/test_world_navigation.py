import audio
from tests.test_army_actions import setup_game
from core.game import Game as GameClass
from core.entities import Boat
from loaders.boat_loader import BoatDef
import pytest
import random
import copy
from pathlib import Path

from core.world import WorldMap
import constants


@pytest.fixture(scope="module")
def _plaine_world_base() -> WorldMap:
    random.seed(0)
    path = Path(__file__).parent / "fixtures" / "mini_continent_map.txt"
    return WorldMap.from_file(str(path))


@pytest.fixture
def plaine_world(_plaine_world_base) -> WorldMap:
    return copy.deepcopy(_plaine_world_base)


@pytest.fixture(scope="module")
def _marine_world_base() -> WorldMap:
    random.seed(0)
    path = Path(__file__).parent / "fixtures" / "mini_marine_map.txt"
    return WorldMap.from_file(str(path))


@pytest.fixture
def marine_world(_marine_world_base) -> WorldMap:
    return copy.deepcopy(_marine_world_base)


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


def setup_open_sea_game(monkeypatch):
    """Create a game where the hero and a boat are at sea away from land."""
    game, constants, Army, Unit, S_STATS = setup_game(monkeypatch)
    game.compute_path = GameClass.compute_path.__get__(game, GameClass)
    game._compute_path_cached = GameClass._compute_path_cached.__get__(game, GameClass)
    for x in range(3):
        game.world.grid[0][x].biome = "ocean"
    game.hero.x = 0
    game.hero.y = 0
    game.hero.ap = 10
    game.boat_defs = {"barge": BoatDef("barge", 4, 7, {}, "barge.png")}
    game.hero.naval_unit = "barge"
    boat = Boat("barge", 1, 0, 4, 7, owner=0)
    game.world.grid[0][1].boat = boat
    return game, boat


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


def test_move_without_boat_notifies(monkeypatch):
    game = setup_water_game(monkeypatch)
    game.world.grid[0][1].boat = None
    monkeypatch.setattr(audio, "play_sound", lambda *a, **k: None)
    notices = []
    game._notify = lambda msg: notices.append(msg)
    game.try_move_hero(1, 0)
    assert notices == ["A boat is required to embark."]
    assert (game.hero.x, game.hero.y) == (0, 0)


def test_move_onto_boat_auto_embark(monkeypatch):
    game = setup_water_game(monkeypatch)
    monkeypatch.setattr(audio, "play_sound", lambda *a, **k: None)
    start_ap = game.hero.ap
    game.try_move_hero(1, 0)
    assert (game.hero.x, game.hero.y) == (1, 0)
    assert game.hero.ap == start_ap - 1
    assert game.hero.naval_unit == "barge"
    assert game.world.grid[0][1].boat is None

def test_embark_requires_adjacent_land(monkeypatch):
    game, boat = setup_open_sea_game(monkeypatch)
    monkeypatch.setattr(audio, "play_sound", lambda *a, **k: None)
    assert not game.embark(game.hero, boat)
    assert game.hero.naval_unit == "barge"
    assert game.world.grid[0][1].boat is boat


def test_disembark_requires_adjacent_land(monkeypatch):
    game, _ = setup_open_sea_game(monkeypatch)
    game.disembark(game.hero, 0, 0)
    assert game.hero.naval_unit == "barge"
    assert game.world.grid[0][0].boat is None


@pytest.mark.slow
@pytest.mark.worldgen
def test_plaine_map_is_land_heavy(plaine_world):
    world = plaine_world
    total = world.width * world.height
    land = sum(
        1
        for row in world.grid
        for tile in row
        if tile.biome not in constants.WATER_BIOMES
    )
    water = total - land
    assert land >= water


@pytest.mark.slow
@pytest.mark.worldgen
def test_marine_map_features_and_starting_islands(marine_world):
    world = marine_world
    total = world.width * world.height
    water = sum(
        1
        for row in world.grid
        for tile in row
        if tile.biome in constants.WATER_BIOMES
    )
    assert water > 0

    assert world.starting_area and world.enemy_starting_area
    assert any(
        tile.building and tile.building.name == "Shipyard"
        for row in world.grid
        for tile in row
    )
