import os
from types import SimpleNamespace
import pygame

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')

from core.entities import Unit, SWORDSMAN_STATS

pygame.init()


def test_hotkey_disables_auto_mode(monkeypatch, simple_combat):
    combat = simple_combat([Unit(SWORDSMAN_STATS, 1, 'hero')], [Unit(SWORDSMAN_STATS, 1, 'enemy')])
    combat.auto_mode = True
    # provide minimal constants used by run()
    monkeypatch.setattr(pygame, 'QUIT', 0, raising=False)
    monkeypatch.setattr(pygame, 'KEYDOWN', 1, raising=False)
    monkeypatch.setattr(pygame, 'K_ESCAPE', 2, raising=False)
    monkeypatch.setattr(pygame, 'K_h', 3, raising=False)

    events = [
        SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_h),
        SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_ESCAPE),
    ]

    def fake_get():
        nonlocal events
        ev, events = events, []
        return ev

    monkeypatch.setattr(pygame.event, 'get', fake_get)
    combat.run()
    assert not combat.auto_mode
