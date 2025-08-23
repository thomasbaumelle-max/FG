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


def test_positive_morale_grants_extra_turn(monkeypatch):
    hero_stats = replace(SWORDSMAN_STATS, morale=1)
    hero = Unit(hero_stats, 1, 'hero')
    enemy = Unit(SWORDSMAN_STATS, 1, 'enemy')
    combat = _create_combat([hero], [enemy])
    hero_unit = combat.hero_units[0]
    enemy_unit = combat.enemy_units[0]
    combat.turn_order = [hero_unit, enemy_unit]
    combat.current_index = 0
    monkeypatch.setattr(random, 'random', lambda: 0.0)
    combat.check_morale(hero_unit)
    assert hero_unit.extra_turns == 1
    assert combat.log[-1] == "Swordsman is inspired and gains an extra action!"
    hero_unit.acted = True
    combat.advance_turn()
    assert hero_unit.extra_turns == 0
    assert not hero_unit.acted
    assert combat.turn_order[combat.current_index] is hero_unit


def test_negative_morale_skips_turn(monkeypatch):
    hero_stats = replace(SWORDSMAN_STATS, morale=-1)
    hero = Unit(hero_stats, 1, 'hero')
    enemy = Unit(SWORDSMAN_STATS, 1, 'enemy')
    combat = _create_combat([hero], [enemy])
    hero_unit = combat.hero_units[0]
    enemy_unit = combat.enemy_units[0]
    combat.turn_order = [hero_unit, enemy_unit]
    combat.current_index = 0
    monkeypatch.setattr(random, 'random', lambda: 0.0)
    combat.check_morale(hero_unit)
    assert hero_unit.skip_turn
    assert combat.log[-1] == "Swordsman falters and loses its action!"
    combat.advance_turn()
    assert hero_unit.skip_turn is False
    assert hero_unit.acted
    assert combat.turn_order[combat.current_index] is enemy_unit
