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

    class DummyFont:
        def render(self, *args, **kwargs):
            return DummySurface()

    event_queue = [types.SimpleNamespace(type=2, key=117)]

    def get_events():
        return [event_queue.pop()] if event_queue else []

    pygame_stub = types.SimpleNamespace(
        Surface=DummySurface,
        Rect=Rect,
        SRCALPHA=1,
        KEYDOWN=2,
        MOUSEBUTTONDOWN=1,
        K_u=117,
        K_ESCAPE=27,
        event=types.SimpleNamespace(get=get_events),
        draw=types.SimpleNamespace(rect=lambda *a, **k: None),
        transform=types.SimpleNamespace(smoothscale=lambda img, size: img),
        display=types.SimpleNamespace(
            flip=lambda: None,
            set_mode=lambda size, flags=0: DummySurface(size, flags),
        ),
        font=types.SimpleNamespace(SysFont=lambda *a, **k: DummyFont()),
        time=types.SimpleNamespace(Clock=lambda: types.SimpleNamespace(tick=lambda fps: None)),
    )
    return pygame_stub


def setup_game(monkeypatch, towns):
    pygame_stub = make_pygame_stub()
    monkeypatch.setitem(sys.modules, "pygame", pygame_stub)
    monkeypatch.setitem(sys.modules, "pygame.draw", pygame_stub.draw)
    from core.game import Game
    from core.buildings import Town
    game = Game.__new__(Game)
    game.screen = pygame_stub.Surface((200, 200))
    game.clock = pygame_stub.time.Clock()
    world = types.SimpleNamespace(towns=lambda: towns)
    game.world = world
    game.assets = {"town": pygame_stub.Surface((10, 10))}
    return game


def test_open_town_prints_when_no_town(monkeypatch, capsys):
    game = setup_game(monkeypatch, [])
    game.open_town()
    out = capsys.readouterr()
    assert "No town available" in out.out


def test_open_town_creates_overlay(monkeypatch):
    from core.buildings import Town
    t = Town("A")
    t.owner = 0
    game = setup_game(monkeypatch, [t])
    # Monkeypatch TownOverlay to observe creation
    created = {}
    class DummyOverlay:
        def __init__(self, screen, game_obj, towns):
            created['towns'] = towns
        def handle_event(self, e):
            return True
        def draw(self):
            return []
    monkeypatch.setitem(sys.modules, 'ui.town_overlay', types.SimpleNamespace(TownOverlay=DummyOverlay))
    game.open_town()
    assert created['towns'] == [t]


def test_open_town_handles_property_world(monkeypatch):
    """Ensure ``open_town`` works when ``world.towns`` is a property."""
    pygame_stub = make_pygame_stub()
    monkeypatch.setitem(sys.modules, "pygame", pygame_stub)
    monkeypatch.setitem(sys.modules, "pygame.draw", pygame_stub.draw)
    from core.game import Game
    from core.buildings import Town

    t = Town("A")
    t.owner = 0

    class World:
        def __init__(self, towns):
            self._towns = towns

        @property
        def towns(self):
            return self._towns

    game = Game.__new__(Game)
    game.screen = pygame_stub.Surface((200, 200))
    game.clock = pygame_stub.time.Clock()
    game.world = World([t])
    game.assets = {"town": pygame_stub.Surface((10, 10))}

    created = {}

    class DummyOverlay:
        def __init__(self, screen, game_obj, towns):
            created["towns"] = towns

        def handle_event(self, e):
            return True

        def draw(self):
            return []

    monkeypatch.setitem(
        sys.modules, "ui.town_overlay", types.SimpleNamespace(TownOverlay=DummyOverlay)
    )
    game.open_town()
    assert created["towns"] == [t]
