import types
import sys

from tests.test_open_town import make_pygame_stub


def test_boat_garrison_exchange(monkeypatch):
    pygame_stub = make_pygame_stub()
    monkeypatch.setitem(sys.modules, "pygame", pygame_stub)
    monkeypatch.setitem(sys.modules, "pygame.draw", pygame_stub.draw)
    from core.entities import Hero, Unit, SWORDSMAN_STATS, Boat
    from ui.boat_screen import BoatScreen

    hero = Hero(0, 0, [Unit(SWORDSMAN_STATS, 1, "hero")])
    boat = Boat("barge", 1, 0, 4, 7, owner=0, garrison=[Unit(SWORDSMAN_STATS, 2, "hero")])
    game = types.SimpleNamespace(hero=hero)
    screen = pygame_stub.display.set_mode((200, 200))
    bs = BoatScreen(screen, game, boat)
    bs.drag_src = ("hero", 0)
    bs.drag_unit = hero.army[0]
    bs._drop_to("boat", 0)
    assert len(hero.army) == 0
    assert boat.garrison[0].count == 3
    bs.drag_src = ("boat", 0)
    bs.drag_unit = boat.garrison[0]
    bs._drop_to("hero", 0)
    assert len(boat.garrison) == 0
    assert hero.army[0].count == 3

