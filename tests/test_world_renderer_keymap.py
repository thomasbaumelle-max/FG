from types import SimpleNamespace

import pygame

import settings
from render.world_renderer import WorldRenderer


class DummyWorld:
    width = 100
    height = 100

    def in_bounds(self, x, y):  # pragma: no cover - trivial
        return True


def test_handle_event_uses_settings_keymap(monkeypatch):
    monkeypatch.setattr(pygame, "KEYDOWN", 1, raising=False)
    monkeypatch.setattr(pygame, "K_f", 70, raising=False)
    settings.KEYMAP["pan_left"] = ["K_f"]
    renderer = WorldRenderer({})
    renderer.surface = pygame.Surface((100, 100))
    renderer.world = DummyWorld()
    renderer.cam_x = 50
    evt = SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_f)
    renderer.handle_event(evt)
    assert renderer.cam_x == 50 - renderer.pan_speed

