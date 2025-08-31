from types import SimpleNamespace

from core.combat_rules import roll_morale, roll_luck


def test_roll_morale_table():
    rng = SimpleNamespace(random=lambda: 0.03)
    assert roll_morale(1, rng=rng) == 1
    rng.random = lambda: 0.05
    assert roll_morale(1, rng=rng) == 0
    rng.random = lambda: 0.12
    assert roll_morale(3, rng=rng) == 1
    rng.random = lambda: 0.13
    assert roll_morale(3, rng=rng) == 0
    rng.random = lambda: 0.0
    assert roll_morale(5, rng=rng) == 1
    assert roll_morale(-5, rng=rng) == -1


def test_roll_luck_table():
    rng = SimpleNamespace(random=lambda: 0.03)
    assert roll_luck(1, rng=rng) == 1.5
    rng.random = lambda: 0.05
    assert roll_luck(1, rng=rng) == 1.0
    rng.random = lambda: 0.03
    assert roll_luck(-1, rng=rng) == 0.5
    rng.random = lambda: 0.05
    assert roll_luck(-1, rng=rng) == 1.0
    rng.random = lambda: 0.08
    assert roll_luck(2, rng=rng) == 1.5
    rng.random = lambda: 0.09
    assert roll_luck(2, rng=rng) == 1.0
    rng.random = lambda: 0.0
    assert roll_luck(5, rng=rng) == 1.5
    assert roll_luck(-5, rng=rng) == 0.5
