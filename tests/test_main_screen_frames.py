import pygame
from types import SimpleNamespace
import theme
from ui.main_screen import MainScreen


class DummySurface(pygame.Surface):
    def __init__(self, size):
        super().__init__(size)


def _dummy_game(width: int, height: int):
    surface = DummySurface((width, height))
    return SimpleNamespace(
        screen=surface,
        offset_x=0,
        offset_y=0,
        zoom=1.0,
        hover_probe=lambda x, y: None,
        _adjust_zoom=lambda delta, pos: None,
    )


def test_main_screen_draws_frames(monkeypatch):
    game = _dummy_game(320, 240)
    ms = MainScreen(game)
    # ensure minimap exists so all panels are drawn
    ms.minimap = SimpleNamespace(draw=lambda s, r: None)

    calls = []
    original = theme.draw_frame

    def spy(surface, rect, state="normal"):
        calls.append((rect, state))
        original(surface, rect, state)

    monkeypatch.setattr(theme, "draw_frame", spy)
    ms.draw(game.screen)
    assert len(calls) >= 7
