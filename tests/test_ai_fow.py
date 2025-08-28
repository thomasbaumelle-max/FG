import pytest

from core.world import WorldMap
from core.ai.faction_ai import FactionAI
from core.entities import EnemyHero, Unit, Hero
from tests.unit_stats import get_unit_stats
from core.buildings import Town, Building

SWORDSMAN_STATS = get_unit_stats("Swordsman")


def _basic_world():
    world = WorldMap(width=5, height=1)
    for x, tile in enumerate(world.grid[0]):
        tile.biome = "scarletia_echo_plain"
        tile.obstacle = False
        if x == 2:
            tile.obstacle = True
    return world


def test_ai_mine_search_respects_fog():
    world = _basic_world()
    town = Town()
    town.owner = 1
    world.grid[0][4].building = town
    world.enemy_town = (4, 0)
    hero = EnemyHero(3, 0, [Unit(SWORDSMAN_STATS, 1, "enemy")])
    ai = FactionAI(town, heroes=[hero])
    ai.update_visibility(world)
    mine = Building()
    mine.income = {"gold": 100}
    mine.owner = 0
    world.grid[0][0].building = mine
    assert ai._find_nearest_mine(world, hero) is None
    world.reveal(1, 0, 0, radius=0)
    assert ai._find_nearest_mine(world, hero) == (0, 0)


def test_ai_town_threat_respects_fog():
    world = _basic_world()
    town = Town()
    town.owner = 1
    world.grid[0][4].building = town
    world.enemy_town = (4, 0)
    ai = FactionAI(town, heroes=[])
    ai.update_visibility(world)
    hero = Hero(0, 0, [Unit(SWORDSMAN_STATS, 1, "hero")])
    assert not ai._town_threatened(world, [hero], radius=5)
    world.reveal(1, 0, 0, radius=0)
    assert ai._town_threatened(world, [hero], radius=5)
