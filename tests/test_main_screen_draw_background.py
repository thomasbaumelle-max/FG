from types import SimpleNamespace

import pygame

import theme
from core.game import Game
from ui.main_screen import MainScreen


class DummySurface(pygame.Surface):
    """Surface tracking all fill operations for assertions."""

    def __init__(self, size):
        super().__init__(size)
        self.fills = []

    def fill(self, colour, rect=None):
        self.fills.append((colour, rect))
        return super().fill(colour, rect)


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


def test_draw_preserves_world_surface():
    """MainScreen.draw should not clear the existing world view."""

    game = _dummy_game(320, 240)
    ms = MainScreen(game)
    screen = game.screen
    world_rect = ms.widgets["1"]
    world_colour = (10, 20, 30)

    screen.fill(theme.PALETTE["background"])
    screen.fill(world_colour, world_rect)
    ms.draw(screen)

    overlap_colour = world_colour
    for colour, rect in screen.fills[2:]:
        if rect is None:
            overlap_colour = colour
            continue
        wx, wy, ww, wh = world_rect.x, world_rect.y, world_rect.width, world_rect.height
        rx, ry, rw, rh = rect.x, rect.y, rect.width, rect.height
        if not (rx + rw <= wx or wx + ww <= rx or ry + rh <= wy or wy + wh <= ry):
            overlap_colour = colour
    assert overlap_colour == world_colour


def test_run_fills_background_before_world(monkeypatch):
    """Game.run should clear the screen before drawing the world."""

    operations = []

    class RunSurface(pygame.Surface):
        def __init__(self, size):
            super().__init__(size)

        def fill(self, colour, rect=None):
            operations.append(("fill", colour))
            return super().fill(colour, rect)

    screen = RunSurface((10, 10))
    game = Game.__new__(Game)
    game.screen = screen
    game.clock = SimpleNamespace(tick=lambda fps: 0)
    game.anim_frame = 0
    game.quit_to_menu = False
    game.main_screen = SimpleNamespace(
        handle_event=lambda e: False,
        draw=lambda s: [],
        turn_bar=SimpleNamespace(update=lambda dt: None),
    )
    game.update_movement = lambda: None

    def fake_draw_world(frame):
        operations.append(("world", frame))
        return pygame.Rect(0, 0, 0, 0)

    game.draw_world = fake_draw_world

    monkeypatch.setattr(pygame, "QUIT", 0, raising=False)
    monkeypatch.setattr(pygame.event, "get", lambda: [SimpleNamespace(type=0)])
    monkeypatch.setattr(pygame.display, "update", lambda rects: None, raising=False)
    monkeypatch.setattr(pygame, "quit", lambda: None, raising=False)

    game.run()

    assert operations[0] == ("fill", theme.PALETTE["background"])
    assert operations[1][0] == "world"

