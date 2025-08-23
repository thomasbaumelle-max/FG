import os
import random

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')

import pygame

from core.entities import (
    Unit,
    SWORDSMAN_STATS,
    CAVALRY_STATS,
    DRAGON_STATS,
    PRIEST_STATS,
    apply_defence,
)
from core.combat import Combat
from core import combat_ai
import constants

pygame.init()


def _create_combat(hero_units, enemy_units):
    screen = pygame.Surface((constants.COMBAT_GRID_WIDTH * constants.COMBAT_TILE_SIZE, constants.COMBAT_GRID_HEIGHT * constants.COMBAT_TILE_SIZE))
    assets = {}
    return Combat(screen, assets, hero_units, enemy_units)


def test_unit_stats_have_abilities():
    assert 'charge' in CAVALRY_STATS.abilities
    assert 'flying' in DRAGON_STATS.abilities
    assert 'multi_shot' in DRAGON_STATS.abilities
    assert 'passive_heal' in PRIEST_STATS.abilities


def test_multi_shot_double_damage():
    hero = Unit(SWORDSMAN_STATS, 1, 'hero')
    dragon = Unit(DRAGON_STATS, 1, 'enemy')
    combat = _create_combat([hero], [dragon])
    hero = combat.hero_units[0]
    dragon = combat.enemy_units[0]
    combat.move_unit(hero, 2, 2)
    combat.move_unit(dragon, 3, 2)
    random.seed(0)
    combat_ai.enemy_ai_turn(combat, dragon)
    base_dmg = dragon.stats.attack_max * dragon.count
    expected = apply_defence(base_dmg, hero, 'melee')
    if 'multi_shot' in DRAGON_STATS.abilities:
        expected *= 2
    assert hero.current_hp == hero.stats.max_hp - expected


def test_flying_reachable_all_board():
    dragon = Unit(DRAGON_STATS, 1, 'hero')
    combat = _create_combat([dragon], [])
    reach = combat.reachable_squares(dragon)
    assert len(reach) == constants.COMBAT_GRID_WIDTH * constants.COMBAT_GRID_HEIGHT - 1


def test_passive_heal_heals_ally():
    priest = Unit(PRIEST_STATS, 1, 'hero')
    ally = Unit(SWORDSMAN_STATS, 1, 'hero')
    ally.current_hp = 10
    combat = _create_combat([priest, ally], [])
    priest_unit = combat.hero_units[0]
    ally_unit = combat.hero_units[1]
    combat.apply_passive_abilities(priest_unit)
    assert ally_unit.current_hp == 15
