import types
import sys

from tests.test_open_town import make_pygame_stub


def test_shipyard_purchases_spawn_boat(monkeypatch):
    pygame_stub = make_pygame_stub()
    monkeypatch.setitem(sys.modules, "pygame", pygame_stub)
    monkeypatch.setitem(sys.modules, "pygame.draw", pygame_stub.draw)
    from core.world import WorldMap
    from core.entities import Hero
    from core.buildings import Shipyard
    from loaders.boat_loader import BoatDef
    from ui.shipyard_screen import ShipyardScreen

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
    ss = types.SimpleNamespace(game=game, shipyard=shipyard)
    ShipyardScreen._buy_boat(ss, game.boat_defs["barge"])
    assert wm.grid[0][1].boat is not None

