import random

from core.combat_rules import roll_morale, roll_luck


def test_roll_morale_table(monkeypatch):
    monkeypatch.setattr(random, 'random', lambda: 0.03)
    assert roll_morale(1) == 'extra'
    monkeypatch.setattr(random, 'random', lambda: 0.05)
    assert roll_morale(1) == 'normal'
    monkeypatch.setattr(random, 'random', lambda: 0.12)
    assert roll_morale(3) == 'extra'
    monkeypatch.setattr(random, 'random', lambda: 0.13)
    assert roll_morale(3) == 'normal'
    monkeypatch.setattr(random, 'random', lambda: 0.0)
    assert roll_morale(5) == 'extra'
    assert roll_morale(-5) == 'penalty'


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
