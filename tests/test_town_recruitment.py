import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')

import pygame
import importlib, sys

from core.buildings import Town
from core.world import WorldMap
from core.entities import Hero
from core import economy


def _create_game_with_town():
    game_module = importlib.import_module('core.game')
    Game = game_module.Game
    world = WorldMap(map_data=["G"])
    tile = world.grid[0][0]
    tile.building = Town(faction_id="red_knights")
    hero = Hero(0, 0, [])
    game = Game.__new__(Game)
    game.world = world
    game.hero = hero
    game.enemy_heroes = []
    game.move_enemies_randomly = lambda: None
    game.move_enemy_heroes = lambda: None
    return game, tile.building, hero


def test_town_build_and_recruit():
    pygame.init()
    game, town, hero = _create_game_with_town()
    hero.resources['wood'] = 5
    hero.resources['stone'] = 5
    hero.gold = 100
    player = economy.PlayerEconomy()
    player.resources['wood'] = 5
    player.resources['stone'] = 5
    player.resources['gold'] = 100
    town.build_structure('barracks', hero, player)
    town.next_week()
    town.recruit_units('Swordsman', hero, count=1)
    assert 'barracks' in town.built_structures
    assert hero.gold == 50
    assert any(u.stats.name == 'Swordsman' for u in town.garrison)
    assert not hero.army
    sys.modules.pop('game', None)


def test_town_recruitment_limited_by_stock():
    pygame.init()
    town = Town(faction_id="red_knights")
    hero = Hero(0, 0, [])
    hero.resources['wood'] = 5
    hero.resources['stone'] = 5
    hero.gold = 1000
    player = economy.PlayerEconomy()
    player.resources['wood'] = 5
    player.resources['stone'] = 5
    player.resources['gold'] = 1000
    assert town.build_structure('barracks', hero, player)
    town.next_week()
    # 5 initial + 5 weekly growth
    assert town.available_units('barracks').get('Swordsman') == 10
    assert town.recruit_units('Swordsman', hero, count=10)
    assert town.available_units('barracks').get('Swordsman') == 0
    assert not town.recruit_units('Swordsman', hero, count=1)


def test_recruit_into_garrison():
    pygame.init()
    town = Town(faction_id="red_knights")
    hero = Hero(0, 0, [])
    hero.resources['wood'] = 5
    hero.resources['stone'] = 5
    hero.gold = 1000
    player = economy.PlayerEconomy()
    player.resources['wood'] = 5
    player.resources['stone'] = 5
    player.resources['gold'] = 1000
    assert town.build_structure('barracks', hero, player)
    town.next_week()
    assert town.recruit_units('Swordsman', hero, count=2, target_units=town.garrison)
    assert any(u.stats.name == 'Swordsman' and u.count == 2 for u in town.garrison)
    assert not hero.army  # units should not appear in hero army


def test_recruit_into_visiting_army():
    pygame.init()
    town = Town(faction_id="red_knights")
    hero = Hero(0, 0, [])
    visiting = Hero(1, 0, [])
    hero.resources['wood'] = 5
    hero.resources['stone'] = 5
    hero.gold = 1000
    player = economy.PlayerEconomy()
    player.resources['wood'] = 5
    player.resources['stone'] = 5
    player.resources['gold'] = 1000
    assert town.build_structure('barracks', hero, player)
    town.next_week()
    assert town.recruit_units('Swordsman', hero, count=3, target_units=visiting.army)
    assert any(u.stats.name == 'Swordsman' and u.count == 3 for u in visiting.army)
    assert hero.gold == 1000 - 50 * 3  # payment taken from controlling hero
    assert not town.garrison
