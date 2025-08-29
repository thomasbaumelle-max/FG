import types
import sys


def test_shipyard_purchases_spawn_boat(monkeypatch, pygame_stub):
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
    from core.world import WorldMap
    from core.entities import Hero
    from core.buildings import Shipyard
    from loaders.boat_loader import BoatDef
    from ui.shipyard_overlay import _buy_boat

    wm = WorldMap(
        width=2,
        height=1,
        biome_weights={"scarletia_echo_plain": 1.0},
        num_obstacles=0,
        num_treasures=0,
        num_enemies=0,
    )
    wm.grid[0][1].biome = "ocean"
    shipyard = Shipyard()
    shipyard.origin = (0, 0)
    wm.grid[0][0].building = shipyard

    hero = Hero(0, 0, [])
    game = types.SimpleNamespace(world=wm, hero=hero, boat_defs={"barge": BoatDef("barge", 4, 7, {}, "barge.png")})
    _buy_boat(game, shipyard, game.boat_defs["barge"])
    assert wm.grid[0][1].boat is not None

