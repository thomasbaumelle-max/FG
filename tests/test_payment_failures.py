import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from core.buildings import Town, Building
from core.entities import Hero
from core import economy


def test_build_structure_payment_failure():
    pygame.init()
    town = Town(faction_id="red_knights")
    hero = Hero(0, 0, [])
    hero.gold = 0
    hero.resources["wood"] = 0
    hero.resources["stone"] = 0
    player = economy.PlayerEconomy()
    # Resources mirror hero
    player.resources["gold"] = 0
    player.resources["wood"] = 0
    player.resources["stone"] = 0
    assert not town.build_structure("barracks", hero, player)
    assert "barracks" not in town.built_structures
    assert not town.built_today
    assert hero.gold == 0
    assert player.resources["wood"] == 0


def test_building_upgrade_payment_failure():
    hero = Hero(0, 0, [])
    hero.gold = 50
    player = economy.PlayerEconomy()
    player.resources["gold"] = 50
    b = Building()
    b.upgrade_cost = {"gold": 100}
    econ_b = economy.Building(id="mine", upgrade_cost=dict(b.upgrade_cost))
    assert not b.upgrade(hero, player, econ_b)
    assert b.level == 1
    assert hero.gold == 50
    assert econ_b.level == 1
