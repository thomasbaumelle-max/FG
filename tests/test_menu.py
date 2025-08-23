import os
from types import SimpleNamespace

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')

import pygame

from ui import menu


def test_menu_selection(monkeypatch):
    pygame.init()
    screen = pygame.display.set_mode((200, 200))
    monkeypatch.setattr(screen, 'fill', lambda *_args, **_kwargs: None, raising=False)
    monkeypatch.setattr(pygame.Surface, 'get_rect', lambda self, **kwargs: pygame.Rect(0, 0, self.get_width(), self.get_height()), raising=False)
    monkeypatch.setattr(pygame, 'KEYDOWN', 1, raising=False)
    monkeypatch.setattr(pygame, 'K_DOWN', 2, raising=False)
    monkeypatch.setattr(pygame, 'K_RETURN', 3, raising=False)
    monkeypatch.setattr(pygame, 'K_UP', 4, raising=False)
    monkeypatch.setattr(pygame, 'K_w', 5, raising=False)
    monkeypatch.setattr(pygame, 'K_s', 6, raising=False)
    monkeypatch.setattr(pygame, 'K_SPACE', 7, raising=False)
    monkeypatch.setattr(pygame, 'K_F11', 8, raising=False)
    monkeypatch.setattr(pygame, 'QUIT', 9, raising=False)
    class DummyClock:
        def tick(self, *_args, **_kwargs):
            pass

    monkeypatch.setattr(pygame.time, 'Clock', lambda: DummyClock(), raising=False)
    events = [
        [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_DOWN)],
        [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_RETURN)],
    ]

    def fake_get():
        return events.pop(0) if events else []

    monkeypatch.setattr(pygame.event, 'get', fake_get)
    monkeypatch.setattr(pygame.display, 'flip', lambda: None)
    choice, _ = menu._menu(screen, ['A', 'B'])
    assert choice == 1


def test_menu_escape(monkeypatch):
    pygame.init()
    screen = pygame.display.set_mode((200, 200))
    monkeypatch.setattr(screen, 'fill', lambda *_args, **_kwargs: None, raising=False)
    monkeypatch.setattr(pygame.Surface, 'get_rect', lambda self, **kwargs: pygame.Rect(0, 0, self.get_width(), self.get_height()), raising=False)
    monkeypatch.setattr(pygame, 'KEYDOWN', 1, raising=False)
    monkeypatch.setattr(pygame, 'K_ESCAPE', 2, raising=False)
    monkeypatch.setattr(pygame, 'QUIT', 3, raising=False)
    monkeypatch.setattr(pygame, 'K_UP', 4, raising=False)
    monkeypatch.setattr(pygame, 'K_w', 5, raising=False)
    monkeypatch.setattr(pygame, 'K_DOWN', 6, raising=False)
    monkeypatch.setattr(pygame, 'K_s', 7, raising=False)
    monkeypatch.setattr(pygame, 'K_RETURN', 8, raising=False)
    monkeypatch.setattr(pygame, 'K_SPACE', 9, raising=False)
    monkeypatch.setattr(pygame, 'K_F11', 10, raising=False)

    class DummyClock:
        def tick(self, *_args, **_kwargs):
            pass

    monkeypatch.setattr(pygame.time, 'Clock', lambda: DummyClock(), raising=False)
    events = [[SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_ESCAPE)]]

    def fake_get():
        return events.pop(0) if events else []

    monkeypatch.setattr(pygame.event, 'get', fake_get)
    monkeypatch.setattr(pygame.display, 'flip', lambda: None)
    choice, _ = menu._menu(screen, ['A', 'B'])
    assert choice is None
