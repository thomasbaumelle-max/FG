import types
import sys
from core.entities import RECRUITABLE_UNITS

SWORDSMAN_STATS = RECRUITABLE_UNITS["swordsman"]


def test_caravan_travel_and_arrival():
    from core.world import WorldMap
    from core.buildings import Town
    from core.entities import Unit
    from state.game_state import GameState

    world = WorldMap(width=5, height=1, biome_weights={"scarletia_echo_plain": 1.0}, num_obstacles=0, num_treasures=0, num_enemies=0)
    t1, t2 = Town("A"), Town("B")
    world.grid[0][0].building = t1
    world.grid[0][3].building = t2

    gs = GameState(world=world)

    unit = Unit(SWORDSMAN_STATS, 5, "hero")
    t1.garrison.append(unit)
    assert t1.send_caravan(t2, [unit], world)
    assert not t1.garrison

    gs.next_day(); gs.next_day(); gs.next_day()
    assert t2.garrison and t2.garrison[0] is unit


def test_townscreen_launches_caravan(monkeypatch, pygame_stub):
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
    from core.entities import Hero, Unit
    from core.buildings import Town
    from ui.town_screen import TownScreen

    game = types.SimpleNamespace()
    world = WorldMap(width=2, height=1, biome_weights={"scarletia_echo_plain": 1.0}, num_obstacles=0, num_treasures=0, num_enemies=0)
    t1, t2 = Town("A"), Town("B")
    world.grid[0][0].building = t1
    world.grid[0][1].building = t2
    game.world = world
    game.hero = Hero(0, 0, [])

    screen = pg.display.set_mode((1, 1))
    ts = TownScreen(screen, game, t1, None, None, (0, 0))
    unit = Unit(SWORDSMAN_STATS, 1, "hero")
    t1.garrison.append(unit)
    assert ts.launch_caravan(t2)
    assert unit not in t1.garrison
    t1.advance_day()
    assert t2.garrison and t2.garrison[0] is unit


def test_townscreen_selects_and_sends_queue(monkeypatch, pygame_stub):
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
    from core.entities import Hero, Unit
    from core.buildings import Town
    from ui.town_screen import TownScreen

    game = types.SimpleNamespace()
    world = WorldMap(width=2, height=1, biome_weights={"scarletia_echo_plain": 1.0}, num_obstacles=0, num_treasures=0, num_enemies=0)
    t1, t2 = Town("A"), Town("B")
    world.grid[0][0].building = t1
    world.grid[0][1].building = t2
    game.world = world
    game.hero = Hero(0, 0, [])

    screen = pg.display.set_mode((1, 1))
    ts = TownScreen(screen, game, t1, None, None, (0, 0))
    u1 = Unit(SWORDSMAN_STATS, 1, "hero")
    u2 = Unit(SWORDSMAN_STATS, 2, "hero")
    t1.garrison.extend([u1, u2])

    ts.select_unit(0)
    ts.select_unit(1)
    assert ts.send_queued_caravan(t2)
    assert u1 not in t1.garrison and u2 not in t1.garrison
    world.advance_day()
    assert u1 in t2.garrison and u2 in t2.garrison


def test_world_map_advances_caravans():
    from core.world import WorldMap
    from core.buildings import Town
    from core.entities import Unit

    world = WorldMap(width=3, height=1, biome_weights={"scarletia_echo_plain": 1.0}, num_obstacles=0, num_treasures=0, num_enemies=0)
    t1, t2 = Town("A"), Town("B")
    world.grid[0][0].building = t1
    world.grid[0][2].building = t2
    unit = Unit(SWORDSMAN_STATS, 1, "hero")
    t1.garrison.append(unit)
    assert t1.send_caravan(t2, [unit], world)
    world.advance_day()
    world.advance_day()
    assert unit in t2.garrison


def test_auto_caravan_to_nearest_ally():
    from core.world import WorldMap
    from core.buildings import Town
    from core.entities import Unit, Hero

    world = WorldMap(width=5, height=1, biome_weights={"scarletia_echo_plain": 1.0}, num_obstacles=0, num_treasures=0, num_enemies=0)
    t1, t2 = Town("A"), Town("B")
    world.grid[0][0].building = t1
    world.grid[0][3].building = t2
    t1.owner = t2.owner = 1

    unit = Unit(SWORDSMAN_STATS, 2, "hero")
    t1.garrison.append(unit)
    hero = Hero(4, 0, [])

    world.advance_day(hero)
    assert not t1.garrison and t1.caravan_orders

    for _ in range(3):
        world.advance_day(hero)
    assert unit in t2.garrison


def test_townscreen_cancel_and_intercept(monkeypatch, pygame_stub):
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
    from core.entities import Hero, Unit
    from core.buildings import Town
    from ui.town_screen import TownScreen

    game = types.SimpleNamespace()
    world = WorldMap(width=2, height=1, biome_weights={"scarletia_echo_plain": 1.0}, num_obstacles=0, num_treasures=0, num_enemies=0)
    t1, t2 = Town("A"), Town("B")
    world.grid[0][0].building = t1
    world.grid[0][1].building = t2
    game.world = world
    game.hero = Hero(0, 0, [])

    screen = pg.display.set_mode((1, 1))
    ts = TownScreen(screen, game, t1, None, None, (0, 0))
    u1 = Unit(SWORDSMAN_STATS, 1, "hero")
    u2 = Unit(SWORDSMAN_STATS, 2, "hero")
    t1.garrison.extend([u1, u2])

    assert ts.launch_caravan(t2, [u1])
    assert ts.launch_caravan(t2, [u2])
    assert ts.cancel_caravan(0)
    assert u1 in t1.garrison
    assert ts.intercept_caravan(0)
    assert u2 in game.hero.army
