import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')

import pygame
import importlib, sys

from core.buildings import create_building
from core.world import WorldMap
from core.entities import Hero, Unit, SWORDSMAN_STATS


def _create_game_with_mine():
    game_module = importlib.import_module('core.game')
    Game = game_module.Game
    world = WorldMap(map_data=["G"])
    tile = world.grid[0][0]
    tile.building = create_building("mine")
    hero = Hero(0, 0, [Unit(SWORDSMAN_STATS, 1, 'hero')])
    game = Game.__new__(Game)
    game.world = world
    game.hero = hero
    game.enemy_heroes = []
    game.move_enemies_randomly = lambda: None
    game.move_enemy_heroes = lambda: None
    return game, tile.building, hero


def test_building_income_added_each_turn():
    pygame.init()
    game, mine, hero = _create_game_with_mine()
    assert hero.resources['stone'] == 0
    mine.interact(hero)
    assert mine.owner == 0
    assert hero.resources['stone'] == 5
    game.end_turn()
    assert hero.resources['stone'] == 7
    sys.modules.pop('game', None)
