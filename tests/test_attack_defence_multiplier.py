import pytest

from core.combat_rules import compute_damage
from core.entities import UnitStats, Unit


def make_unit(*, attack=0, defence=0):
    stats = UnitStats(
        name="Test",
        max_hp=10,
        attack_min=20,
        attack_max=20,
        defence_melee=defence,
        defence_ranged=defence,
        defence_magic=defence,
        speed=0,
        attack_range=1,
        initiative=1,
        sheet="",
        hero_frames=(0, 0),
        enemy_frames=(0, 0),
        morale=0,
        luck=0,
        abilities=[],
    )
    unit = Unit(stats, 1, "hero")
    unit.x, unit.y = 0, 0
    unit.facing = (0, 1)
    unit.attack_bonus = 0
    unit.attack = attack
    return unit


def test_attack_exceeds_defence():
    attacker = make_unit(attack=5)
    defender = make_unit(defence=0)
    attacker.y = 1  # place attacker in front (no flank bonus)
    result = compute_damage(attacker, defender)
    assert result["value"] == 25


def test_attack_below_defence():
    attacker = make_unit(attack=0)
    defender = make_unit(defence=5)
    attacker.y = 1
    result = compute_damage(attacker, defender)
    assert result["value"] == 18
