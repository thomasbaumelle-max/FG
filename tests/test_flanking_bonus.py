from dataclasses import dataclass

from core.combat_rules import UnitView, compute_damage


@dataclass
class DummyStats:
    attack_min: int = 10
    attack_max: int = 10
    defence_melee: int = 0
    defence_ranged: int = 0
    defence_magic: int = 0
    luck: int = 0


def make_defender():
    stats = DummyStats()
    return UnitView(side="enemy", stats=stats, x=0, y=0, facing=(0, 1))


def make_attacker(x, y):
    stats = DummyStats()
    return UnitView(side="hero", stats=stats, x=x, y=y)


def test_back_attack():
    attacker = make_attacker(0, -1)
    defender = make_defender()
    result = compute_damage(attacker, defender)
    assert result["value"] == 12


def test_flank_attack():
    attacker = make_attacker(-1, 0)
    defender = make_defender()
    result = compute_damage(attacker, defender)
    assert result["value"] == 11


def test_front_attack():
    attacker = make_attacker(0, 1)
    defender = make_defender()
    result = compute_damage(attacker, defender)
    assert result["value"] == 10

