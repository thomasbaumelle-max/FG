import sys
import types


def make_pygame_stub():
    class Rect:
        def __init__(self, x, y, w, h):
            self.x, self.y, self.width, self.height = x, y, w, h

        def collidepoint(self, pos):
            return True

    class DummySurface:
        def __init__(self, size=(10, 10), flags=0):
            self._size = size

        def get_size(self):
            return self._size

        def fill(self, *args, **kwargs):
            pass

        def blit(self, *args, **kwargs):
            pass

        def copy(self):
            return DummySurface(self._size)

    pygame_stub = types.SimpleNamespace(
        Surface=DummySurface,
        Rect=Rect,
        SRCALPHA=1,
        K_u=117,
        K_ESCAPE=27,
        KEYDOWN=2,
        MOUSEBUTTONDOWN=1,
        transform=types.SimpleNamespace(smoothscale=lambda img, size: img),
        draw=types.SimpleNamespace(rect=lambda *a, **k: None),
        event=types.SimpleNamespace(get=lambda: []),
        display=types.SimpleNamespace(flip=lambda: None),
    )
    return pygame_stub


def setup_overlay(monkeypatch):
    pygame_stub = make_pygame_stub()
    monkeypatch.setitem(sys.modules, "pygame", pygame_stub)
    monkeypatch.setitem(sys.modules, "pygame.draw", pygame_stub.draw)
    import theme
    from ui.town_overlay import TownOverlay
    from core.buildings import Town
    towns = [Town("A"), Town("B")]
    for t in towns:
        t.owner = 0
    game = types.SimpleNamespace(world=types.SimpleNamespace(towns=lambda: towns), assets={"town": pygame_stub.Surface((10, 10))})
    overlay = TownOverlay(pygame_stub.Surface((200, 200)), game)
    return overlay, theme


def test_overlay_lists_all_towns_and_uses_palette(monkeypatch):
    overlay, theme = setup_overlay(monkeypatch)
    overlay.draw()
    assert len(overlay.town_rects) == 2
    assert overlay.BG == theme.PALETTE["background"]
    assert overlay.PANEL == theme.PALETTE["panel"]
    assert overlay.ACCENT == theme.PALETTE["accent"]
    assert overlay.TEXT == theme.PALETTE["text"]


def test_click_opens_town_screen(monkeypatch):
    event_queue = [
        [],
        [types.SimpleNamespace(type=1, button=1, pos=(0, 0))],
    ]

    def get_events():
        return event_queue.pop(0) if event_queue else []

    pygame_stub = make_pygame_stub()
    pygame_stub.event = types.SimpleNamespace(get=get_events)
    pygame_stub.time = types.SimpleNamespace(Clock=lambda: types.SimpleNamespace(tick=lambda fps: None))
    monkeypatch.setitem(sys.modules, "pygame", pygame_stub)
    monkeypatch.setitem(sys.modules, "pygame.draw", pygame_stub.draw)

    from core.game import Game
    from core.buildings import Town

    t = Town("A")
    t.owner = 0
    game = Game.__new__(Game)
    game.screen = pygame_stub.Surface((200, 200))
    game.clock = pygame_stub.time.Clock()
    game.world = types.SimpleNamespace(towns=lambda: [t])
    game.assets = {"town": pygame_stub.Surface((10, 10))}

    opened = {}

    class DummyTownScreen:
        def __init__(self, screen, game_obj, town):
            opened["town"] = town
        def run(self):
            pass

    monkeypatch.setitem(
        sys.modules, "ui.town_screen", types.SimpleNamespace(TownScreen=DummyTownScreen)
    )

    game.open_town()
    assert opened["town"] is t
