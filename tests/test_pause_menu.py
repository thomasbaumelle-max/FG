import os
from types import SimpleNamespace

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from ui import menu
from core.game import Game


def test_escape_opens_pause_menu(monkeypatch):
    pygame.init()
    screen = pygame.display.set_mode((200, 200))

    game = Game.__new__(Game)
    game.screen = screen
    game.quit_to_menu = False
    game.main_screen = SimpleNamespace(
        handle_event=lambda event: False,
        draw=lambda surf: [],
        turn_bar=SimpleNamespace(update=lambda dt: None),
    )
    game.update_movement = lambda: None
    game.draw_world = lambda frame: pygame.Rect(0, 0, 0, 0)
    game.clock = SimpleNamespace(tick=lambda fps: 0)
    game.anim_frame = 0
    game.save_slots = ["a", "b", "c"]
    game.profile_slots = ["ap", "bp", "cp"]
    game.current_slot = 0
    game.default_save_path = "a"
    game.default_profile_path = "ap"

    monkeypatch.setattr(pygame, "QUIT", 1, raising=False)
    monkeypatch.setattr(pygame, "KEYDOWN", 2, raising=False)
    monkeypatch.setattr(pygame, "K_ESCAPE", 3, raising=False)
    monkeypatch.setattr(pygame, "K_UP", 4, raising=False)
    monkeypatch.setattr(pygame, "K_w", 5, raising=False)
    monkeypatch.setattr(pygame, "K_DOWN", 6, raising=False)
    monkeypatch.setattr(pygame, "K_s", 7, raising=False)
    monkeypatch.setattr(pygame, "K_LEFT", 8, raising=False)
    monkeypatch.setattr(pygame, "K_a", 9, raising=False)
    monkeypatch.setattr(pygame, "K_RIGHT", 10, raising=False)
    monkeypatch.setattr(pygame, "K_d", 11, raising=False)
    monkeypatch.setattr(pygame, "K_PLUS", 12, raising=False)
    monkeypatch.setattr(pygame, "K_EQUALS", 13, raising=False)
    monkeypatch.setattr(pygame, "K_KP_PLUS", 14, raising=False)
    monkeypatch.setattr(pygame, "K_MINUS", 15, raising=False)
    monkeypatch.setattr(pygame, "K_KP_MINUS", 16, raising=False)
    monkeypatch.setattr(pygame, "K_t", 17, raising=False)
    monkeypatch.setattr(pygame, "K_h", 18, raising=False)
    monkeypatch.setattr(pygame, "K_F5", 19, raising=False)
    monkeypatch.setattr(pygame, "K_F9", 20, raising=False)
    monkeypatch.setattr(pygame, "K_i", 21, raising=False)
    monkeypatch.setattr(pygame, "K_1", 22, raising=False)
    monkeypatch.setattr(pygame, "K_2", 23, raising=False)
    monkeypatch.setattr(pygame, "K_3", 24, raising=False)
    monkeypatch.setattr(pygame.display, "toggle_fullscreen", lambda: None)
    monkeypatch.setattr(pygame.display, "get_surface", lambda: screen)
    monkeypatch.setattr(pygame, "quit", lambda: None, raising=False)

    called = {"pause": False}

    events = [
        [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_ESCAPE)],
        [SimpleNamespace(type=pygame.QUIT)],
    ]

    def fake_get():
        return events.pop(0) if events else []

    monkeypatch.setattr(pygame.event, "get", fake_get)
    monkeypatch.setattr(pygame.display, "update", lambda *_: None, raising=False)
    monkeypatch.setattr(screen, "fill", lambda *_args, **_kwargs: None, raising=False)

    def fake_pause(scr, g):
        called["pause"] = True
        return False, scr

    monkeypatch.setattr(menu, "pause_menu", fake_pause)

    game.run()

    assert called["pause"]
    assert game.quit_to_menu is False

