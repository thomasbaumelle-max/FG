import random

from core.combat_rules import roll_morale, roll_luck


def test_roll_morale_table(monkeypatch):
    monkeypatch.setattr(random, 'random', lambda: 0.03)
    assert roll_morale(1) == 1
    monkeypatch.setattr(random, 'random', lambda: 0.05)
    assert roll_morale(1) == 0
    monkeypatch.setattr(random, 'random', lambda: 0.12)
    assert roll_morale(3) == 1
    monkeypatch.setattr(random, 'random', lambda: 0.13)
    assert roll_morale(3) == 0
    monkeypatch.setattr(random, 'random', lambda: 0.0)
    assert roll_morale(5) == 1
    assert roll_morale(-5) == -1


def test_roll_luck_table(monkeypatch):
    monkeypatch.setattr(random, 'random', lambda: 0.03)
    assert roll_luck(1) == 1.5
    monkeypatch.setattr(random, 'random', lambda: 0.05)
    assert roll_luck(1) == 1.0
    monkeypatch.setattr(random, 'random', lambda: 0.03)
    assert roll_luck(-1) == 0.5
    monkeypatch.setattr(random, 'random', lambda: 0.05)
    assert roll_luck(-1) == 1.0
    monkeypatch.setattr(random, 'random', lambda: 0.08)
    assert roll_luck(2) == 1.5
    monkeypatch.setattr(random, 'random', lambda: 0.09)
    assert roll_luck(2) == 1.0
    monkeypatch.setattr(random, 'random', lambda: 0.0)
    assert roll_luck(5) == 1.5
    assert roll_luck(-5) == 0.5
