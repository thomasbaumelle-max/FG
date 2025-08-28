import sys
import types


def setup_game(monkeypatch, pygame_stub, towns):
    event_queue = [types.SimpleNamespace(type=2, key=117)]

    def get_events():
        return [event_queue.pop()] if event_queue else []

    pg = pygame_stub(
        KEYDOWN=2,
        MOUSEBUTTONDOWN=1,
        K_u=117,
        K_ESCAPE=27,
        transform=types.SimpleNamespace(smoothscale=lambda img, size: img),
    )
    monkeypatch.setattr(pg.event, "get", get_events)
    monkeypatch.setattr(pg.Rect, "collidepoint", lambda self, pos: True)
    monkeypatch.setattr(
        pg.Surface, "get_size", lambda self: (self.get_width(), self.get_height())
    )
    monkeypatch.setitem(sys.modules, "pygame.draw", pg.draw)
    monkeypatch.setitem(sys.modules, "pygame.transform", pg.transform)

    from core.game import Game
    from core.buildings import Town

    game = Game.__new__(Game)
    game.screen = pg.Surface((200, 200))
    game.clock = pg.time.Clock()
    world = types.SimpleNamespace(towns=lambda: towns)
    game.world = world
    game.assets = {"town": pg.Surface((10, 10))}
    return game



def test_open_town_prints_when_no_town(monkeypatch, pygame_stub, capsys):
    game = setup_game(monkeypatch, pygame_stub, [])
    game.open_town()
    out = capsys.readouterr()
    assert "No town available" in out.out


def test_open_town_creates_overlay(monkeypatch, pygame_stub):
    from core.buildings import Town
    t = Town("A")
    t.owner = 0
    game = setup_game(monkeypatch, pygame_stub, [t])
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


def test_open_town_handles_property_world(monkeypatch, pygame_stub):
    """Ensure ``open_town`` works when ``world.towns`` is a property."""
    pg = pygame_stub(
        KEYDOWN=2,
        MOUSEBUTTONDOWN=1,
        K_u=117,
        K_ESCAPE=27,
        transform=types.SimpleNamespace(smoothscale=lambda img, size: img),
    )
    monkeypatch.setattr(pg.Rect, "collidepoint", lambda self, pos: True)
    monkeypatch.setattr(
        pg.Surface, "get_size", lambda self: (self.get_width(), self.get_height())
    )
    monkeypatch.setitem(sys.modules, "pygame.draw", pg.draw)
    monkeypatch.setitem(sys.modules, "pygame.transform", pg.transform)
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
    game.screen = pg.Surface((200, 200))
    game.clock = pg.time.Clock()
    game.world = World([t])
    game.assets = {"town": pg.Surface((10, 10))}

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


def test_open_town_passes_scene_states(monkeypatch, pygame_stub):
    import types
    import sys
    from loaders.town_scene_loader import TownScene, TownBuilding

    monkeypatch.setenv("FG_FAST_TESTS", "0")
    pg = pygame_stub(KEYDOWN=2, MOUSEBUTTONDOWN=1)
    monkeypatch.setattr(pg.event, "get", lambda: [])

    from core.game import Game
    from core.buildings import Town

    game = Game.__new__(Game)
    game.screen = pg.Surface((100, 100))
    game.clock = pg.time.Clock()
    game.assets = {}
    game.ctx = types.SimpleNamespace(repo_root=".")

    town = Town("A")
    town.owner = 0
    town.built_structures.add("smith")

    scene = TownScene(
        size=(10, 10),
        layers=[],
        buildings=[
            TownBuilding("tavern", "", (0, 0), {}),
            TownBuilding("smith", "", (0, 0), {}),
            TownBuilding("mage_guild", "", (0, 0), {}),
        ],
    )

    import loaders.town_scene_loader as tsl

    def fake_load(path, assets):
        return scene

    monkeypatch.setattr(tsl, "load_town_scene", fake_load)

    captured = {}

    class DummySceneScreen:
        def __init__(
            self,
            screen,
            scn,
            assets,
            clock,
            building_states=None,
            game=None,
            town=None,
        ):
            captured["states"] = dict(building_states)

        def run(self, debug=False):
            return False

    monkeypatch.setitem(
        sys.modules,
        "ui.town_scene_screen",
        types.SimpleNamespace(TownSceneScreen=DummySceneScreen),
    )

    class DummyTownScreen:
        def __init__(self, *args, **kwargs):
            pass

        def run(self):
            pass

    monkeypatch.setitem(
        sys.modules,
        "ui.town_screen",
        types.SimpleNamespace(TownScreen=DummyTownScreen),
    )

    game.open_town(town)

    assert captured["states"] == {
        "tavern": "built",
        "smith": "built",
        "mage_guild": "unbuilt",
    }
