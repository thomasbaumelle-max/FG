import os
import random

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')

from dataclasses import replace
from core.entities import (
    Unit,
    RECRUITABLE_UNITS,
    CAVALRY_STATS,
    DRAGON_STATS,
    PRIEST_STATS,
    apply_defence,
)
from core import combat_ai
import constants
from core import combat

SWORDSMAN_STATS = RECRUITABLE_UNITS["swordsman"]


def test_unit_stats_have_abilities():
    assert 'charge' in CAVALRY_STATS.abilities
    assert 'flying' in DRAGON_STATS.abilities
    assert 'multi_shot' in DRAGON_STATS.abilities
    assert 'passive_heal' in PRIEST_STATS.abilities


def test_unit_spells_loaded_from_manifest():
    assert combat.UNIT_SPELLS.get(SWORDSMAN_STATS.name, {}).get('Shield Block') == 1


def test_multi_shot_double_damage(simple_combat):
    hero = Unit(SWORDSMAN_STATS, 1, 'hero')
    dragon_stats = replace(DRAGON_STATS, abilities=[a for a in DRAGON_STATS.abilities if a != 'dragon_breath'])
    dragon = Unit(dragon_stats, 1, 'enemy')
    combat = simple_combat([hero], [dragon])
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


def test_flying_reachable_all_board(simple_combat):
    dragon = Unit(DRAGON_STATS, 1, 'hero')
    combat = simple_combat([dragon], [])
    reach = combat.reachable_squares(dragon)
    assert len(reach) == constants.COMBAT_GRID_WIDTH * constants.COMBAT_GRID_HEIGHT - 1


def test_passive_heal_heals_ally(simple_combat):
    priest = Unit(PRIEST_STATS, 1, 'hero')
    ally = Unit(SWORDSMAN_STATS, 1, 'hero')
    ally.current_hp = 10
    combat = simple_combat([priest, ally], [])
    priest_unit = combat.hero_units[0]
    ally_unit = combat.hero_units[1]
    combat.apply_passive_abilities(priest_unit)
    assert ally_unit.current_hp == 15
