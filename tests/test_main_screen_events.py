from types import SimpleNamespace
import json
from pathlib import Path

import pytest

from ui.main_screen import MainScreen
from ui.widgets.hero_list import MOUSEBUTTONDOWN, MOUSEWHEEL


class DummyHero:
    def __init__(self, name, x, y, ap=5):
        self.name = name
        self.x = x
        self.y = y
        self.ap = ap
        self.army = []


def make_game(heroes, size=(800, 600)):
    width, height = size
    screen = SimpleNamespace(get_width=lambda: width, get_height=lambda: height)

    class Game:
        def __init__(self):
            self.screen = screen
            self.offset_x = 0
            self.offset_y = 0
            self.zoom = 1.0
            self.hover_probe = lambda x, y: None
            self.zoomed = False
            self.state = SimpleNamespace(heroes=heroes)

        def _adjust_zoom(self, delta, pos):
            self.zoomed = True

    return Game()


def test_events_forwarded_to_hero_list():
    heroes = [DummyHero(f"H{i}", i, i + 1) for i in range(6)]
    game = make_game(heroes)
    ms = MainScreen(game)
    rect = ms.widgets["5"]
    card = ms.hero_list._card_rect(0, rect)
    pos = (card.x + card.width // 2, card.y + card.height // 2)

    click_evt = SimpleNamespace(type=MOUSEBUTTONDOWN, pos=pos, button=1)
    ms.handle_event(click_evt)
    assert ms.hero_list.selected_index == 0

    wheel_evt = SimpleNamespace(type=MOUSEWHEEL, y=-1, pos=pos)
    ms.handle_event(wheel_evt)
    assert ms.hero_list.scroll == 1
    assert not game.zoomed


@pytest.mark.parametrize("size", [(800, 600), (1024, 768), (1280, 720)])
def test_buttons_column_visible(size):
    game = make_game([], size=size)
    ms = MainScreen(game)
    hero_rect = ms.widgets["5"]
    buttons_rect = ms.widgets["6"]

    assert hero_rect.width > 0 and hero_rect.height > 0
    assert buttons_rect.width > 0 and buttons_rect.height > 0
    gap = buttons_rect.x - (hero_rect.x + hero_rect.width)
    # Default margin between hero list and buttons is 8 pixels
    assert gap == 8


def test_highlight_moves_when_selecting_army(monkeypatch):
    """Selecting an army from the list moves the world highlight."""

    from tests.test_army_actions import make_pygame_stub
    from state import event_bus as eb
    from ui.widgets.hero_list import HeroList
    from core.game import Game

    # Use pygame stub to avoid needing a real display
    pygame_stub = make_pygame_stub()
    pygame_stub.BLEND_RGBA_ADD = 0
    pygame_stub.transform.rotate = lambda surf, angle: surf
    # Replace pygame module references in imported modules
    monkeypatch.setattr("ui.main_screen.pygame", pygame_stub)
    monkeypatch.setattr("ui.widgets.hero_list.pygame", pygame_stub)
    monkeypatch.setattr("core.game.pygame", pygame_stub)

    # Fresh event bus for isolation
    bus = eb.EventBus()
    monkeypatch.setattr(eb, "EVENT_BUS", bus)
    monkeypatch.setattr("ui.widgets.hero_list.EVENT_BUS", bus)
    monkeypatch.setattr("core.game.EVENT_BUS", bus)
    monkeypatch.setattr("ui.main_screen.EVENT_BUS", bus)

    class DummyActor:
        def __init__(self, name, x, y):
            self.name = name
            self.x = x
            self.y = y
            self.ap = 5
            self.army = []
            self.portrait = pygame_stub.Surface((HeroList.CARD_SIZE, HeroList.CARD_SIZE))

    hero = DummyActor("Hero", 0, 0)
    army = DummyActor("Army", 1, 0)

    selected = []

    class DummyWorld:
        width = 2
        height = 1
        player_armies = [army]

        def draw(self, surface, assets, heroes, armies, sel, frame):
            selected.append(sel)
            return pygame_stub.Surface((1, 1))

    game = Game.__new__(Game)
    screen = SimpleNamespace(
        get_width=lambda: 800,
        get_height=lambda: 600,
        fill=lambda *a, **k: None,
        blit=lambda *a, **k: None,
        set_clip=lambda rect=None: None,
    )
    game.screen = screen
    game.offset_x = game.offset_y = 0
    game.zoom = 1.0
    game.path = []
    game.hero = hero
    game.active_actor = hero
    game.state = SimpleNamespace(heroes=[hero])
    game.world = DummyWorld()
    game.assets = {}
    bus.subscribe(eb.ON_SELECT_HERO, game._on_select_hero)

    ms = MainScreen(game)
    game.main_screen = ms

    # Initial draw highlights the hero
    game.draw_world(0)
    assert selected[0] is hero

    # Click on the army entry in the hero list
    rect = ms.widgets["5"]
    card = ms.hero_list._card_rect(1, rect)
    pos = (card.x + card.width // 2, card.y + card.height // 2)
    evt = SimpleNamespace(type=MOUSEBUTTONDOWN, pos=pos, button=1)
    ms.handle_event(evt)

    assert ms.hero_list.selected_index == 1
    assert game.active_actor is army

    # Draw again – the world should now highlight the army
    game.draw_world(1)
    assert selected[1] is army


def test_process_event_queue_dispatches_events():
    """Events in the queue are dispatched via the registry."""

    from core.game import Game

    class DummyWorld:
        def __init__(self):
            size = 10
            self.explored = {0: [[False for _ in range(size)] for _ in range(size)]}

        def reveal(self, player_id, x, y, radius=0):
            self.explored[player_id][y][x] = True

    class DummyHero:
        def __init__(self):
            self.army = []

    game = Game.__new__(Game)
    game.world = DummyWorld()
    game.hero = DummyHero()

    event_file = Path(__file__).resolve().parents[1] / "events" / "events.json"
    data = json.loads(event_file.read_text(encoding="utf-8"))
    explore_evt = next(e for e in data if e["type"] == "explore_tile")
    recruit_evt = next(e for e in data if e["type"] == "recruit_unit")
    game.event_queue = [explore_evt, recruit_evt]

    game.process_event_queue()

    ex_params = explore_evt["params"]
    assert game.world.explored[0][ex_params["y"]][ex_params["x"]] is True
    rec_params = recruit_evt["params"]
    assert game.hero.army == [rec_params["unit"]] * rec_params.get("count", 1)
