import os
import random
from dataclasses import replace

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')

import pygame

from core.entities import Unit, SWORDSMAN_STATS
from core.combat import Combat
import constants

pygame.init()


def _create_combat(hero_units, enemy_units):
    screen = pygame.Surface(
        (
            constants.COMBAT_GRID_WIDTH * constants.COMBAT_TILE_SIZE,
            constants.COMBAT_GRID_HEIGHT * constants.COMBAT_TILE_SIZE,
        )
    )
    assets = {}
    return Combat(screen, assets, hero_units, enemy_units)


def test_positive_luck_logs(monkeypatch):
    hero_stats = replace(SWORDSMAN_STATS, luck=1)
    hero = Unit(hero_stats, 1, 'hero')
    enemy = Unit(SWORDSMAN_STATS, 1, 'enemy')
    combat = _create_combat([hero], [enemy])
    attacker = combat.hero_units[0]
    defender = combat.enemy_units[0]
    monkeypatch.setattr(random, 'random', lambda: 0.0)
    combat.resolve_attack(attacker, defender, 'melee')
    assert combat.log[-1] == 'Lucky strike by Swordsman!'


def test_negative_luck_logs(monkeypatch):
    hero_stats = replace(SWORDSMAN_STATS, luck=-1)
    hero = Unit(hero_stats, 1, 'hero')
    enemy = Unit(SWORDSMAN_STATS, 1, 'enemy')
    combat = _create_combat([hero], [enemy])
    attacker = combat.hero_units[0]
    defender = combat.enemy_units[0]
    monkeypatch.setattr(random, 'random', lambda: 0.0)
    combat.resolve_attack(attacker, defender, 'melee')
    assert combat.log[-1] == 'Unlucky hit by Swordsman.'
