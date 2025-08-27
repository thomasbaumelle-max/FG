import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')

import pygame

from loaders import building_loader
from core import economy
from core.buildings import Town
from core.entities import Hero


def test_dwelling_manifest_growth():
    pygame.init()
    defs = building_loader.load_default_buildings()
    assert 'swordsman_camp' in defs
    asset = defs['swordsman_camp']
    assert asset.growth_per_week.get('Swordsman') == 5


def test_weekly_transfer_to_garrison():
    b = economy.Building(
        id='camp',
        growth_per_week={'Swordsman': 5},
        stock={'Swordsman': 3},
    )
    state = economy.GameEconomyState(
        calendar=economy.GameCalendar(),
        players={},
        buildings=[b],
    )
    economy.advance_week(state)
    assert b.stock.get('Swordsman', 0) == 0
    assert b.garrison.get('Swordsman') == 8


def test_town_available_units():
    pygame.init()
    town = Town(faction_id="red_knights")
    hero = Hero(0, 0, [])
    hero.resources['wood'] = 5
    hero.resources['stone'] = 5
    hero.gold = 100
    assert town.build_structure('barracks', hero)
    town.next_week()
    assert town.available_units('barracks').get('Swordsman') == 10
