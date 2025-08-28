import random
from pathlib import Path

import pygame
import pytest

from core.world import WorldMap
from core.game import Game
from core.ai.faction_ai import FactionAI
from core.entities import Hero, EnemyHero, Unit
from tests.unit_stats import get_unit_stats

SWORDSMAN_STATS = get_unit_stats("swordsman")
from core.buildings import Town
from state.game_state import GameState
from core import economy


@pytest.fixture(scope="module")
def _plaine_world_base() -> WorldMap:
    random.seed(0)
    path = Path(__file__).parent / "fixtures" / "mini_continent_map.txt"
    return WorldMap.from_file(str(path))


@pytest.fixture
def plaine_world(_plaine_world_base) -> WorldMap:
    return _plaine_world_base.clone()


@pytest.mark.slow
@pytest.mark.worldgen
def test_enemy_starting_area_has_town(plaine_world):
    world = plaine_world
    assert world.enemy_starting_area is not None
    x0, y0, size = world.enemy_starting_area
    def base(name: str) -> str:
        return "Town" if name.startswith("Town") else name

    buildings = {
        base(world.grid[y][x].building.name)
        for y in range(y0, y0 + size)
        for x in range(x0, x0 + size)
        if world.grid[y][x].building
    }
    assert {"Town", "Mine", "Crystal Mine", "Sawmill"} <= buildings
    assert world.enemy_town is not None
    ex, ey = world.enemy_town
    town_tile = world.grid[ey][ex]
    assert isinstance(town_tile.building, Town)
    assert town_tile.building.owner == 1
    assert world.enemy_start is not None
    sx, sy = world.enemy_start
    assert abs(sx - ex) + abs(sy - ey) == 1
    assert world.grid[sy][sx].building is None


def _make_simple_world():
    world = WorldMap(width=5, height=1)
    for tile in world.grid[0]:
        tile.biome = "scarletia_echo_plain"
        tile.obstacle = False
    player_town = Town()
    player_town.owner = 0
    world.grid[0][0].building = player_town
    world.hero_town = (0, 0)
    world.hero_start = (1, 0)
    world.starting_area = (0, 0, 1)
    enemy_town = Town()
    enemy_town.owner = 1
    world.grid[0][4].building = enemy_town
    world.enemy_town = (4, 0)
    world.enemy_start = (3, 0)
    world.enemy_starting_area = (4, 0, 1)
    return world


def _make_defended_world():
    world = WorldMap(width=5, height=2)
    for y in range(world.height):
        for tile in world.grid[y]:
            tile.biome = "scarletia_echo_plain"
            tile.obstacle = False
    player_town = Town()
    player_town.owner = 0
    world.grid[0][0].building = player_town
    world.hero_town = (0, 0)
    world.hero_start = (1, 0)
    world.starting_area = (0, 0, 1)
    enemy_town = Town()
    enemy_town.owner = 1
    world.grid[0][4].building = enemy_town
    world.enemy_town = (4, 0)
    world.enemy_start = (3, 0)
    world.enemy_starting_area = (4, 0, 1)
    return world


def test_ai_hero_spawns_and_moves():
    world = _make_simple_world()
    game = Game.__new__(Game)
    game.world = world
    game.screen = pygame.Surface((1, 1))
    game.hero = Hero(0, 0, [Unit(SWORDSMAN_STATS, 1, "hero")])
    game.state = GameState(world=world, heroes=[game.hero])
    game._econ_building_map = {}
    game.state.economy.players[0] = economy.PlayerEconomy()
    ai_econ = economy.PlayerEconomy()
    game.state.economy.players[1] = ai_econ
    game.ai_player = FactionAI(world.grid[0][4].building, heroes=[], economy=ai_econ)
    game.enemy_heroes = game.ai_player.heroes
    game._spawn_enemy_heroes()
    assert game.enemy_heroes
    enemy = game.enemy_heroes[0]
    assert (enemy.x, enemy.y) == (3, 0)
    game.end_turn()
    assert (enemy.x, enemy.y) == (2, 0)


def test_ai_cannot_spawn_from_captured_town():
    world = _make_simple_world()
    game = Game.__new__(Game)
    game.world = world
    game.screen = pygame.Surface((1, 1))
    game.hero = Hero(0, 0, [Unit(SWORDSMAN_STATS, 1, "hero")])
    game.state = GameState(world=world, heroes=[game.hero])
    econ_state = game.state.economy
    game._econ_building_map = {}
    econ_state.players[0] = economy.PlayerEconomy()
    ai_econ = economy.PlayerEconomy()
    econ_state.players[1] = ai_econ
    player_b = economy.Building(id="player_town", owner=0)
    enemy_b = economy.Building(id="enemy_town", owner=1, garrison={SWORDSMAN_STATS.name: 2})
    econ_state.buildings = [player_b, enemy_b]
    game._econ_building_map[world.grid[0][0].building] = player_b
    game._econ_building_map[world.grid[0][4].building] = enemy_b
    game.ai_player = FactionAI(world.grid[0][4].building, heroes=[], economy=ai_econ)
    game.enemy_heroes = game.ai_player.heroes

    # Initial spawn creates a hero, second call recruits from the garrison
    game._spawn_enemy_heroes()
    assert game.enemy_heroes
    game._spawn_enemy_heroes()
    enemy_hero = game.enemy_heroes[0]
    assert any(u.stats.name == SWORDSMAN_STATS.name and u.count == 2 for u in enemy_hero.army)

    # Player captures the enemy town
    tile = world.grid[0][4]
    tile.building.garrison = []
    captured = tile.capture(game.hero, 0, econ_state, enemy_b)
    assert captured
    assert enemy_b.owner == 0
    assert enemy_b.garrison == {}

    # Even if the economy building is refilled, the AI should ignore it
    enemy_b.garrison[SWORDSMAN_STATS.name] = 2
    pre = [u.count for u in enemy_hero.army]
    game._spawn_enemy_heroes()
    post = [u.count for u in enemy_hero.army]
    assert pre == post
    assert enemy_b.garrison[SWORDSMAN_STATS.name] == 2


def test_enemy_cannot_recapture_adjacent_defended_town():
    world = _make_defended_world()
    game = Game.__new__(Game)
    game.world = world
    game.screen = pygame.Surface((1, 1))
    hero = Hero(4, 1, [Unit(SWORDSMAN_STATS, 1, "hero")])
    game.hero = hero
    game.state = GameState(world=world, heroes=[hero])
    econ_state = game.state.economy
    game._econ_building_map = {}
    econ_state.players[0] = economy.PlayerEconomy()
    ai_econ = economy.PlayerEconomy()
    econ_state.players[1] = ai_econ
    player_b = economy.Building(id="player_town", owner=0)
    enemy_b = economy.Building(id="enemy_town", owner=1)
    econ_state.buildings = [player_b, enemy_b]
    game._econ_building_map[world.grid[0][0].building] = player_b
    game._econ_building_map[world.grid[0][4].building] = enemy_b
    game.ai_player = FactionAI(world.grid[0][4].building, heroes=[], economy=ai_econ)
    game.enemy_heroes = game.ai_player.heroes

    tile = world.grid[0][4]
    tile.building.garrison = []
    assert game._capture_tile(4, 0, tile, hero, 0, econ_state, enemy_b)
    assert world.enemy_town is None
    assert game.ai_player.town is None

    enemy = EnemyHero(3, 0, [Unit(SWORDSMAN_STATS, 1, "enemy")])
    game.enemy_heroes.append(enemy)
    game.move_enemy_heroes()
    assert tile.building.owner == 0

