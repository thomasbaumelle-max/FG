import os
import random
from dataclasses import replace

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')

from core.entities import Unit, SWORDSMAN_STATS


def test_positive_luck_logs(monkeypatch, simple_combat):
    hero_stats = replace(SWORDSMAN_STATS, luck=1)
    hero = Unit(hero_stats, 1, 'hero')
    enemy = Unit(SWORDSMAN_STATS, 1, 'enemy')
    combat = simple_combat([hero], [enemy])
    attacker = combat.hero_units[0]
    defender = combat.enemy_units[0]
    monkeypatch.setattr(random, 'random', lambda: 0.0)
    combat.resolve_attack(attacker, defender, 'melee')
    assert combat.log[-1] == 'Lucky strike by Swordsman!'


def test_negative_luck_logs(monkeypatch, simple_combat):
    hero_stats = replace(SWORDSMAN_STATS, luck=-1)
    hero = Unit(hero_stats, 1, 'hero')
    enemy = Unit(SWORDSMAN_STATS, 1, 'enemy')
    combat = simple_combat([hero], [enemy])
    attacker = combat.hero_units[0]
    defender = combat.enemy_units[0]
    monkeypatch.setattr(random, 'random', lambda: 0.0)
    combat.resolve_attack(attacker, defender, 'melee')
    assert combat.log[-1] == 'Unlucky hit by Swordsman.'
