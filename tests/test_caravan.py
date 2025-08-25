import types
import sys
import types


def test_caravan_travel_and_arrival():
    from core.world import WorldMap
    from core.buildings import Town
    from core.entities import Unit, SWORDSMAN_STATS
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
    from core.entities import Hero, Unit, SWORDSMAN_STATS
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
