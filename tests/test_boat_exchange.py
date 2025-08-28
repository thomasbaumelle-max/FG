import types
import sys


def test_boat_garrison_exchange(monkeypatch, pygame_stub):
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
    from core.entities import Hero, Unit, Boat
    from tests.unit_stats import get_unit_stats
    SWORDSMAN_STATS = get_unit_stats("swordsman")
    from ui.boat_screen import BoatScreen

    hero = Hero(0, 0, [Unit(SWORDSMAN_STATS, 1, "hero")])
    boat = Boat("barge", 1, 0, 4, 7, owner=0, garrison=[Unit(SWORDSMAN_STATS, 2, "hero")])
    game = types.SimpleNamespace(hero=hero)
    screen = pg.display.set_mode((200, 200))
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

