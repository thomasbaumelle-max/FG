import os
import random
from dataclasses import replace

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')

from core.entities import Unit, RECRUITABLE_UNITS
import pygame

SWORDSMAN_STATS = RECRUITABLE_UNITS["swordsman"]


def test_positive_morale_grants_extra_turn(monkeypatch, simple_combat):
    hero_stats = replace(SWORDSMAN_STATS, morale=1)
    hero = Unit(hero_stats, 1, 'hero')
    enemy = Unit(SWORDSMAN_STATS, 1, 'enemy')
    pygame.init()
    assets = {"morale_fx": pygame.Surface((1, 1))}
    combat = simple_combat([hero], [enemy], assets=assets)
    hero_unit = combat.hero_units[0]
    enemy_unit = combat.enemy_units[0]
    combat.turn_order = [hero_unit, enemy_unit]
    combat.current_index = 0
    calls = {"count": 0}

    def fake_random() -> float:
        calls["count"] += 1
        return 0.0

    monkeypatch.setattr(random, "random", fake_random)
    before = len(combat.fx_queue._events)
    combat.check_morale(hero_unit)
    assert hero_unit.extra_turns == 1
    assert hero_unit.morale_pending
    assert calls["count"] == 1
    assert combat.log[-1] == "Swordsman is inspired and gains an extra action!"
    assert len(combat.fx_queue._events) == before
    hero_unit.acted = True
    combat.advance_turn()
    assert len(combat.fx_queue._events) == before + 1
    assert hero_unit.extra_turns == 0
    assert hero_unit.morale_pending
    assert not hero_unit.acted
    assert combat.turn_order[combat.current_index] is hero_unit
    combat.check_morale(hero_unit)
    assert calls["count"] == 1
    hero_unit.acted = True
    combat.advance_turn()
    assert hero_unit.morale_pending is False
    assert combat.turn_order[combat.current_index] is enemy_unit
    assert len(combat.fx_queue._events) == before + 1


def test_morale_not_rechecked_after_extra_turn(monkeypatch, simple_combat):
    hero_stats = replace(SWORDSMAN_STATS, morale=1)
    hero = Unit(hero_stats, 1, "hero")
    enemy = Unit(SWORDSMAN_STATS, 1, "enemy")
    pygame.init()
    assets = {"morale_fx": pygame.Surface((1, 1))}
    combat = simple_combat([hero], [enemy], assets=assets)
    hero_unit = combat.hero_units[0]
    enemy_unit = combat.enemy_units[0]
    combat.turn_order = [hero_unit, enemy_unit]
    combat.current_index = 0
    calls = {"count": 0}

    def fake_random() -> float:
        calls["count"] += 1
        return 0.0

    monkeypatch.setattr(random, "random", fake_random)
    combat.check_morale(hero_unit)
    assert hero_unit.extra_turns == 1
    hero_unit.acted = True
    combat.advance_turn()
    assert hero_unit.extra_turns == 0
    hero_unit.acted = True
    combat.advance_turn()
    assert calls["count"] == 1
    assert hero_unit.extra_turns == 0
    assert combat.turn_order[combat.current_index] is enemy_unit


def test_negative_morale_skips_turn(monkeypatch, simple_combat):
    hero_stats = replace(SWORDSMAN_STATS, morale=-1)
    hero = Unit(hero_stats, 1, 'hero')
    enemy = Unit(SWORDSMAN_STATS, 1, 'enemy')
    pygame.init()
    assets = {"morale_fx": pygame.Surface((1, 1))}
    combat = simple_combat([hero], [enemy], assets=assets)
    hero_unit = combat.hero_units[0]
    enemy_unit = combat.enemy_units[0]
    combat.turn_order = [hero_unit, enemy_unit]
    combat.current_index = 0
    monkeypatch.setattr(random, 'random', lambda: 0.0)
    before = len(combat.fx_queue._events)
    combat.check_morale(hero_unit)
    assert hero_unit.skip_turn
    assert not hero_unit.morale_pending
    assert combat.log[-1] == "Swordsman falters and loses its action!"
    assert len(combat.fx_queue._events) == before + 1
    combat.advance_turn()
    assert hero_unit.skip_turn is False
    assert hero_unit.acted
    assert hero_unit.morale_pending is False
    assert combat.turn_order[combat.current_index] is enemy_unit
