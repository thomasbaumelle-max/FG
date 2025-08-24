import os
from types import SimpleNamespace

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from ui import menu
import constants


def _init_screen(monkeypatch):
    pygame.init()
    screen = pygame.display.set_mode((200, 200))
    monkeypatch.setattr(screen, "fill", lambda *_a, **_k: None, raising=False)
    monkeypatch.setattr(
        pygame.Surface,
        "get_rect",
        lambda self, **kwargs: pygame.Rect(0, 0, self.get_width(), self.get_height()),
        raising=False,
    )
    monkeypatch.setattr(pygame.display, "flip", lambda: None)
    class DummyClock:
        def tick(self, *_a, **_k):
            pass
    monkeypatch.setattr(pygame.time, "Clock", lambda: DummyClock(), raising=False)
    return screen


def test_cycle_menu_selection(monkeypatch):
    screen = _init_screen(monkeypatch)
    monkeypatch.setattr(pygame, "KEYDOWN", 1, raising=False)
    monkeypatch.setattr(pygame, "K_RIGHT", 2, raising=False)
    monkeypatch.setattr(pygame, "K_RETURN", 3, raising=False)
    monkeypatch.setattr(pygame, "K_LEFT", 4, raising=False)
    monkeypatch.setattr(pygame, "K_a", 5, raising=False)
    monkeypatch.setattr(pygame, "K_d", 6, raising=False)
    monkeypatch.setattr(pygame, "K_SPACE", 7, raising=False)
    monkeypatch.setattr(pygame, "K_ESCAPE", 8, raising=False)
    monkeypatch.setattr(pygame, "K_F11", 9, raising=False)
    monkeypatch.setattr(pygame, "QUIT", 10, raising=False)

    events = [
        [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_RIGHT)],
        [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_RETURN)],
    ]

    def fake_get():
        return events.pop(0) if events else []

    monkeypatch.setattr(pygame.event, "get", fake_get)
    choice, _ = menu._cycle_menu(screen, ["A", "B"], title="T")
    assert choice == 1


def test_text_input(monkeypatch):
    screen = _init_screen(monkeypatch)
    monkeypatch.setattr(pygame, "KEYDOWN", 1, raising=False)
    monkeypatch.setattr(pygame, "K_RETURN", 2, raising=False)
    monkeypatch.setattr(pygame, "K_ESCAPE", 3, raising=False)
    monkeypatch.setattr(pygame, "K_BACKSPACE", 4, raising=False)
    monkeypatch.setattr(pygame, "K_F11", 5, raising=False)
    monkeypatch.setattr(pygame, "QUIT", 6, raising=False)

    events = [
        [SimpleNamespace(type=pygame.KEYDOWN, key=0, unicode="A")],
        [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_RETURN, unicode="")],
    ]

    def fake_get():
        return events.pop(0) if events else []

    monkeypatch.setattr(pygame.event, "get", fake_get)
    text, _ = menu._text_input(screen, "Nom")
    assert text == "A"


def test_choose_scenario_annuler(monkeypatch):
    screen = _init_screen(monkeypatch)
    monkeypatch.setattr(os.path, "isdir", lambda p: True)
    monkeypatch.setattr(os, "listdir", lambda p: ["one.json", "two.json"])

    captured = {}

    def fake_simple_menu(_s, options, title=None):
        captured["options"] = list(options)
        return len(options) - 1, _s  # select "Annuler"

    monkeypatch.setattr(menu, "simple_menu", fake_simple_menu)
    scenario, _ = menu._choose_scenario(screen)
    assert scenario is None
    assert "Annuler" in captured["options"]


def test_scenario_config_confirm(monkeypatch):
    screen = _init_screen(monkeypatch)
    # Patch pygame constants used by the menu code.
    monkeypatch.setattr(pygame, "KEYDOWN", 1, raising=False)
    monkeypatch.setattr(pygame, "K_UP", 2, raising=False)
    monkeypatch.setattr(pygame, "K_DOWN", 3, raising=False)
    monkeypatch.setattr(pygame, "K_LEFT", 4, raising=False)
    monkeypatch.setattr(pygame, "K_RIGHT", 5, raising=False)
    monkeypatch.setattr(pygame, "K_RETURN", 6, raising=False)
    monkeypatch.setattr(pygame, "K_a", 7, raising=False)
    monkeypatch.setattr(pygame, "K_d", 8, raising=False)
    monkeypatch.setattr(pygame, "K_w", 9, raising=False)
    monkeypatch.setattr(pygame, "K_s", 10, raising=False)
    monkeypatch.setattr(pygame, "K_ESCAPE", 11, raising=False)
    monkeypatch.setattr(pygame, "K_F11", 12, raising=False)
    monkeypatch.setattr(pygame, "QUIT", 13, raising=False)

    events = []
    for _ in range(8):
        events.append([SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_DOWN)])
    events.append([SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_RETURN)])

    def fake_get():
        return events.pop(0) if events else []

    monkeypatch.setattr(pygame.event, "get", fake_get)
    config, _ = menu._scenario_config(screen, "foo.json")
    assert config["scenario"] == "foo.json"
    assert config["map_size"] == list(constants.MAP_SIZE_PRESETS.keys())[0]
    assert config["map_type"] == "plaine"
