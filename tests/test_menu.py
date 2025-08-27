import os
from types import SimpleNamespace

import constants

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


def test_options_menu_shows_translated_difficulties(monkeypatch):
    pygame.init()
    screen = pygame.display.set_mode((200, 200))

    from ui import options_menu

    monkeypatch.setattr(pygame.display, 'flip', lambda: None, raising=False)

    # Stub audio functions used by the options menu
    monkeypatch.setattr(options_menu.audio, 'get_music_volume', lambda: 0.0)
    monkeypatch.setattr(options_menu.audio, 'get_sfx_volume', lambda: 0.0)
    monkeypatch.setattr(options_menu.audio, 'get_music_tracks', lambda: [])
    monkeypatch.setattr(options_menu.audio, 'get_current_music', lambda: None)
    monkeypatch.setattr(options_menu.audio, 'get_default_music', lambda: '')
    monkeypatch.setattr(options_menu.audio, 'save_settings', lambda **_: None)
    monkeypatch.setattr(options_menu.audio, 'set_music_volume', lambda *_: None)
    monkeypatch.setattr(options_menu.audio, 'set_sfx_volume', lambda *_: None)
    monkeypatch.setattr(options_menu.audio, 'play_music', lambda *_: None)
    monkeypatch.setattr(options_menu.audio, 'stop_music', lambda: None)

    calls = []

    def fake_menu(_screen, options, title=''):
        calls.append(options)
        if len(calls) == 1:  # Open difficulty selection
            return 7, _screen
        if len(calls) == 2:  # Difficulty options displayed
            return None, _screen
        return 11, _screen  # Exit options menu

    monkeypatch.setattr(options_menu, 'simple_menu', fake_menu)

    options_menu.options_menu(screen)

    expected = [constants.DIFFICULTY_LABELS[d] for d in constants.AI_DIFFICULTIES]
    assert calls[1] == expected
