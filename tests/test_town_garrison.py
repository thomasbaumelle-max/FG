import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')

import pygame

from core.buildings import Town
from core.entities import Hero, Unit, SWORDSMAN_STATS


def test_garrison_transfer():
    pygame.init()
    town = Town()
    hero = Hero(0, 0, [Unit(SWORDSMAN_STATS, 5, 'hero')])
    assert len(hero.army) == 1
    assert len(town.garrison) == 0
    assert town.transfer_to_garrison(hero, 0)
    assert len(hero.army) == 0
    assert len(town.garrison) == 1
    assert town.transfer_from_garrison(hero, 0)
    assert len(hero.army) == 1
    assert len(town.garrison) == 0


def test_garrison_stacking():
    pygame.init()
    town = Town()
    hero = Hero(0, 0, [Unit(SWORDSMAN_STATS, 5, 'hero'), Unit(SWORDSMAN_STATS, 3, 'hero')])
    assert town.transfer_to_garrison(hero, 0)
    assert town.transfer_to_garrison(hero, 0)
    assert len(town.garrison) == 1
    assert town.garrison[0].count == 8
    hero.army.append(Unit(SWORDSMAN_STATS, 2, 'hero'))
    assert town.transfer_from_garrison(hero, 0)
    assert len(town.garrison) == 0
    assert len(hero.army) == 1
    assert hero.army[0].count == 10
