from dataclasses import dataclass

from core.combat_rules import UnitView, compute_damage, blocking_squares


@dataclass
class DummyStats:
    attack_min: int = 10
    attack_max: int = 10
    defence_melee: int = 0
    defence_ranged: int = 0
    defence_magic: int = 0
    luck: int = 0


def test_blocking_squares_simple():
    assert blocking_squares((0, 0), (2, 0)) == [(1, 0)]


def test_ranged_shot_penalty_with_obstacle():
    attacker = UnitView(side="hero", stats=DummyStats(), x=0, y=0)
    defender = UnitView(side="enemy", stats=DummyStats(), x=2, y=0)
    baseline = compute_damage(attacker, defender, attack_type="ranged", distance=2)
    blocked = compute_damage(
        attacker,
        defender,
        attack_type="ranged",
        distance=2,
        obstacles={(1, 0)},
    )
    assert blocked["value"] == int(baseline["value"] * 0.5)
