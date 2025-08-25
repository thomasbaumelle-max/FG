import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')

import pygame
import importlib, sys
import types

import sys
import types
from core.buildings import Town
from core.world import WorldMap
from core.entities import Hero


def _create_game_with_town():
    game_module = importlib.import_module('core.game')
    Game = game_module.Game
    world = WorldMap(map_data=["G"])
    tile = world.grid[0][0]
    tile.building = Town()
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
    town.build_structure('barracks', hero)
    town.next_week()
    town.recruit_units('Swordsman', hero, count=1)
    assert 'barracks' in town.built_structures
    assert hero.gold == 50
    assert any(u.stats.name == 'Swordsman' for u in town.garrison)
    assert not hero.army
    sys.modules.pop('game', None)


def test_town_recruitment_limited_by_stock():
    pygame.init()
    town = Town()
    hero = Hero(0, 0, [])
    hero.resources['wood'] = 5
    hero.resources['stone'] = 5
    hero.gold = 1000
    assert town.build_structure('barracks', hero)
    town.next_week()
    # 5 initial + 5 weekly growth
    assert town.available_units('barracks').get('Swordsman') == 10
    assert town.recruit_units('Swordsman', hero, count=10)
    assert town.available_units('barracks').get('Swordsman') == 0
    assert not town.recruit_units('Swordsman', hero, count=1)


def test_recruit_into_garrison():
    pygame.init()
    town = Town()
    hero = Hero(0, 0, [])
    hero.resources['wood'] = 5
    hero.resources['stone'] = 5
    hero.gold = 1000
    assert town.build_structure('barracks', hero)
    town.next_week()
    assert town.recruit_units('Swordsman', hero, count=2, target_units=town.garrison)
    assert any(u.stats.name == 'Swordsman' and u.count == 2 for u in town.garrison)
    assert not hero.army  # units should not appear in hero army


def test_recruit_into_visiting_army():
    pygame.init()
    town = Town()
    hero = Hero(0, 0, [])
    visiting = Hero(1, 0, [])
    hero.resources['wood'] = 5
    hero.resources['stone'] = 5
    hero.gold = 1000
    assert town.build_structure('barracks', hero)
    town.next_week()
    assert town.recruit_units('Swordsman', hero, count=3, target_units=visiting.army)
    assert any(u.stats.name == 'Swordsman' and u.count == 3 for u in visiting.army)
    assert hero.gold == 1000 - 50 * 3  # payment taken from controlling hero
    assert not town.garrison


def test_townscreen_recruit_with_hero_goes_to_garrison(monkeypatch, pygame_stub):
    pg = pygame_stub(
        KEYDOWN=2,
        MOUSEBUTTONDOWN=1,
        K_u=117,
        K_ESCAPE=27,
        transform=types.SimpleNamespace(smoothscale=lambda img, size: img),
    )
    monkeypatch.setattr(pg.Rect, "collidepoint", lambda self, pos: True)
    monkeypatch.setattr(
        pg.Surface, "get_size", lambda self: (self.get_width(), self.get_height())
    )
    monkeypatch.setitem(sys.modules, "pygame", pg)
    monkeypatch.setitem(sys.modules, "pygame.draw", pg.draw)
    from ui.town_screen import TownScreen

    town = Town()
    hero = Hero(0, 0, [])
    hero.resources['wood'] = 5
    hero.resources['stone'] = 5
    hero.gold = 1000
    assert town.build_structure('barracks', hero)
    town.next_week()

    game = types.SimpleNamespace(hero=hero)
    screen = pg.display.set_mode((1, 1))
    ts = TownScreen(screen, game, town, None, None, (0, 0))
    ts.recruit_open = True
    ts.recruit_unit = 'Swordsman'
    ts.recruit_count = 1
    ts.recruit_max = 10
    # Only the buy button should report a click
    ts.btn_close.collidepoint = lambda pos: False
    ts.btn_min.collidepoint = lambda pos: False
    ts.btn_minus.collidepoint = lambda pos: False
    ts.btn_plus.collidepoint = lambda pos: False
    ts.btn_max.collidepoint = lambda pos: False
    ts.slider_rect.collidepoint = lambda pos: False
    ts.btn_buy.collidepoint = lambda pos: True
    ts._on_overlay_mousedown((0, 0), 1)

    assert any(u.stats.name == 'Swordsman' for u in town.garrison)
    assert not hero.army
    assert hero.gold == 1000 - 50


def test_townscreen_recruit_visiting_army(monkeypatch, pygame_stub):
    pg = pygame_stub(
        KEYDOWN=2,
        MOUSEBUTTONDOWN=1,
        K_u=117,
        K_ESCAPE=27,
        transform=types.SimpleNamespace(smoothscale=lambda img, size: img),
    )
    monkeypatch.setattr(pg.Rect, "collidepoint", lambda self, pos: True)
    monkeypatch.setattr(
        pg.Surface, "get_size", lambda self: (self.get_width(), self.get_height())
    )
    monkeypatch.setitem(sys.modules, "pygame", pg)
    monkeypatch.setitem(sys.modules, "pygame.draw", pg.draw)
    from ui.town_screen import TownScreen
    from core.entities import Army

    town = Town()
    hero = Hero(1, 0, [])
    hero.resources['wood'] = 5
    hero.resources['stone'] = 5
    hero.gold = 1000
    assert town.build_structure('barracks', hero)
    town.next_week()

    visiting = Army(0, 0, [], ap=4)
    game = types.SimpleNamespace(hero=hero)
    screen = pg.display.set_mode((1, 1))
    ts = TownScreen(screen, game, town, visiting, None, (0, 0))
    ts.recruit_open = True
    ts.recruit_unit = 'Swordsman'
    ts.recruit_count = 1
    ts.recruit_max = 10
    ts.btn_close.collidepoint = lambda pos: False
    ts.btn_min.collidepoint = lambda pos: False
    ts.btn_minus.collidepoint = lambda pos: False
    ts.btn_plus.collidepoint = lambda pos: False
    ts.btn_max.collidepoint = lambda pos: False
    ts.slider_rect.collidepoint = lambda pos: False
    ts.btn_buy.collidepoint = lambda pos: True
    ts._on_overlay_mousedown((0, 0), 1)

    assert any(u.stats.name == 'Swordsman' for u in visiting.units)
    assert not town.garrison
    assert hero.gold == 1000 - 50
