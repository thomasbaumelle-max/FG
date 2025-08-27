import sys
import types


def test_townscreen_click_without_resources(monkeypatch, pygame_stub):
    pg = pygame_stub(transform=types.SimpleNamespace(smoothscale=lambda img, size: img))
    pg.image = types.SimpleNamespace(load=lambda path: pg.Surface((1, 1)))
    monkeypatch.setattr(pg.Rect, "collidepoint", lambda self, pos: True)
    monkeypatch.setitem(sys.modules, "pygame", pg)
    monkeypatch.setitem(sys.modules, "pygame.draw", pg.draw)

    from ui.town_screen import TownScreen
    from core.buildings import Town
    from core.entities import Hero

    pygame = pg
    pygame.init()
    town = Town(faction_id="red_knights")
    hero = Hero(0, 0, [])
    hero.gold = 0
    hero.resources["wood"] = 0
    hero.resources["stone"] = 0

    game = types.SimpleNamespace(hero=hero)
    screen = pg.display.set_mode((1, 1))
    ts = TownScreen(screen, game, town, None, None, (0, 0))
    ts.building_cards = [("barracks", pg.Rect(0, 0, 10, 10))]

    ts._on_mousedown((0, 0), 1)

    assert "barracks" not in town.built_structures

