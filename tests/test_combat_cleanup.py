import pygame
import pytest

from core.entities import Unit, SWORDSMAN_STATS
import audio
import core.combat_render as combat_render
pytestmark = pytest.mark.combat


def test_combat_clears_dead_stacks(monkeypatch, simple_combat):
    hero = Unit(SWORDSMAN_STATS, 3, 'hero')
    enemy = Unit(SWORDSMAN_STATS, 1, 'enemy')
    combat = simple_combat([hero], [enemy])
    combat.auto_mode = True
    combat._auto_resolve_done = True

    monkeypatch.setattr(pygame.event, 'get', lambda: [])
    monkeypatch.setattr(pygame.display, 'flip', lambda: None)
    monkeypatch.setattr(pygame.time, 'wait', lambda ms: None)

    class DummyClock:
        def tick(self, fps):
            pass

    monkeypatch.setattr(pygame.time, 'Clock', lambda: DummyClock())
    monkeypatch.setattr(combat_render, 'draw', lambda *a, **k: None)
    monkeypatch.setattr(audio, 'play_sound', lambda *a, **k: None)

    hero_wins, _ = combat.run()
    assert hero_wins
    assert combat.enemy_units == []
    assert all(u.count > 0 for u in combat.hero_units)
    assert all(u.count > 0 for u in combat.units)
