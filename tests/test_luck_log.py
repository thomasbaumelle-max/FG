import os
import random
from dataclasses import replace

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')

from core.entities import Unit, RECRUITABLE_UNITS
import pygame

SWORDSMAN_STATS = RECRUITABLE_UNITS["swordsman"]


def test_positive_luck_logs(monkeypatch, simple_combat):
    hero_stats = replace(SWORDSMAN_STATS, luck=1)
    hero = Unit(hero_stats, 1, 'hero')
    enemy = Unit(SWORDSMAN_STATS, 1, 'enemy')
    pygame.init()
    assets = {"luck_fx": pygame.Surface((1, 1))}
    combat = simple_combat([hero], [enemy], assets=assets)
    attacker = combat.hero_units[0]
    defender = combat.enemy_units[0]
    monkeypatch.setattr(random, 'random', lambda: 0.0)
    before = len(combat.fx_queue._events)
    combat.resolve_attack(attacker, defender, 'melee')
    assert combat.log[-1] == 'Lucky strike by Swordsman!'
    assert len(combat.fx_queue._events) > before


def test_negative_luck_logs(monkeypatch, simple_combat):
    hero_stats = replace(SWORDSMAN_STATS, luck=-1)
    hero = Unit(hero_stats, 1, 'hero')
    enemy = Unit(SWORDSMAN_STATS, 1, 'enemy')
    pygame.init()
    assets = {"luck_fx": pygame.Surface((1, 1))}
    combat = simple_combat([hero], [enemy], assets=assets)
    attacker = combat.hero_units[0]
    defender = combat.enemy_units[0]
    monkeypatch.setattr(random, 'random', lambda: 0.0)
    before = len(combat.fx_queue._events)
    combat.resolve_attack(attacker, defender, 'melee')
    assert combat.log[-1] == 'Unlucky hit by Swordsman.'
    assert len(combat.fx_queue._events) > before
