import sys
import types

import pytest
import sys
import types


def setup_overlay(monkeypatch, pygame_stub):
    pg = pygame_stub(
        K_u=117,
        K_ESCAPE=27,
        KEYDOWN=2,
        MOUSEBUTTONDOWN=1,
        transform=types.SimpleNamespace(smoothscale=lambda img, size: img),
    )
    monkeypatch.setattr(pg.Rect, "collidepoint", lambda self, pos: True)
    monkeypatch.setattr(pg.Surface, "get_size", lambda self: (self.get_width(), self.get_height()))
    monkeypatch.setitem(sys.modules, "pygame", pg)
    monkeypatch.setitem(sys.modules, "pygame.draw", pg.draw)
    import theme
    from ui.town_overlay import TownOverlay
    from core.buildings import Town
    towns = [Town("A"), Town("B")]
    for t in towns:
        t.owner = 0
    game = types.SimpleNamespace(world=types.SimpleNamespace(towns=lambda: towns), assets={"town": pg.Surface((10, 10))})
    overlay = TownOverlay(pg.Surface((200, 200)), game)
    return overlay, theme


@pytest.mark.serial
def test_overlay_lists_all_towns_and_uses_palette(monkeypatch, pygame_stub):
    overlay, theme = setup_overlay(monkeypatch, pygame_stub)
    overlay.draw()
    assert len(overlay.town_rects) == 2
    assert overlay.BG == theme.PALETTE["background"]
    assert overlay.PANEL == theme.PALETTE["panel"]
    assert overlay.ACCENT == theme.PALETTE["accent"]
    assert overlay.TEXT == theme.PALETTE["text"]


@pytest.mark.serial
def test_click_opens_town_screen(monkeypatch, pygame_stub):
    event_queue = [
        [],
        [types.SimpleNamespace(type=1, button=1, pos=(0, 0))],
    ]

    def get_events():
        return event_queue.pop(0) if event_queue else []

    pg = pygame_stub(
        K_u=117,
        K_ESCAPE=27,
        KEYDOWN=2,
        MOUSEBUTTONDOWN=1,
        transform=types.SimpleNamespace(smoothscale=lambda img, size: img),
        event=types.SimpleNamespace(get=get_events),
        time=types.SimpleNamespace(Clock=lambda: types.SimpleNamespace(tick=lambda fps: None)),
    )
    monkeypatch.setattr(pg.Rect, "collidepoint", lambda self, pos: True)
    monkeypatch.setattr(pg.Surface, "get_size", lambda self: (self.get_width(), self.get_height()))
    monkeypatch.setitem(sys.modules, "pygame", pg)
    monkeypatch.setitem(sys.modules, "pygame.draw", pg.draw)

    from core.game import Game
    from core.buildings import Town

    t = Town("A")
    t.owner = 0
    game = Game.__new__(Game)
    game.screen = pygame_stub.Surface((200, 200))
    game.clock = pg.time.Clock()
    game.world = types.SimpleNamespace(towns=lambda: [t])
    game.assets = {"town": pygame_stub.Surface((10, 10))}

    opened = {}

    class DummyTownScreen:
        def __init__(self, screen, game_obj, town, army=None, clock=None, town_pos=None):
            opened["town"] = town
        def run(self):
            pass

    monkeypatch.setitem(
        sys.modules, "ui.town_screen", types.SimpleNamespace(TownScreen=DummyTownScreen)
    )

    game.open_town()
    assert opened["town"] is t
