import types
import sys

import pytest


@pytest.mark.serial
def test_drag_from_garrison_creates_army(monkeypatch, pygame_stub):
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
    monkeypatch.setattr(pg.Surface, "convert_alpha", lambda self: self)
    monkeypatch.setitem(sys.modules, "pygame", pg)
    monkeypatch.setitem(sys.modules, "pygame.draw", pg.draw)
    monkeypatch.setitem(sys.modules, "pygame.transform", pg.transform)
    from core.world import WorldMap
    from core.entities import Hero, Unit, SWORDSMAN_STATS
    from core.buildings import Town
    from ui.town_screen import TownScreen

    game = types.SimpleNamespace()
    wm = WorldMap(
        width=3,
        height=1,
        biome_weights={"scarletia_echo_plain": 1.0},
        num_obstacles=0,
        num_treasures=0,
        num_enemies=0,
    )
    game.world = wm
    town = Town()
    wm.grid[0][0].building = town
    hero = Hero(2, 0, [])
    game.hero = hero
    game.state = types.SimpleNamespace(heroes=[hero])
    class DummyHeroList:
        def __init__(self):
            self.heroes = []
        def set_heroes(self, heroes):
            self.heroes = heroes
    game.main_screen = types.SimpleNamespace(hero_list=DummyHeroList())
    screen = pg.display.set_mode((1, 1))
    ts = TownScreen(screen, game, town, None, None, (0, 0))
    ts.town.garrison.append(Unit(SWORDSMAN_STATS, 1, "hero"))
    ts.drag_src = ("garrison", 0)
    ts.drag_unit = ts.town.garrison[0]
    ts._drop_to("hero", 0)
    assert len(game.world.player_armies) == 1
    assert game.main_screen.hero_list.heroes[-1] is game.world.player_armies[0]

def test_hero_army_exchange_merge_delete(monkeypatch, pygame_stub):
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
    monkeypatch.setattr(pg.Surface, "convert_alpha", lambda self: self)
    monkeypatch.setitem(sys.modules, "pygame", pg)
    monkeypatch.setitem(sys.modules, "pygame.draw", pg.draw)
    monkeypatch.setitem(sys.modules, "pygame.transform", pg.transform)
    from core.world import WorldMap
    from core.entities import Hero, Army, Unit, SWORDSMAN_STATS, ARCHER_STATS
    from core.game import Game
    from ui.hero_exchange_screen import HeroExchangeScreen

    game = Game.__new__(Game)
    wm = WorldMap(
        width=3,
        height=1,
        biome_weights={"scarletia_echo_plain": 1.0},
        num_obstacles=0,
        num_treasures=0,
        num_enemies=0,
    )
    game.world = wm
    hero = Hero(0, 0, [Unit(SWORDSMAN_STATS, 1, "hero"), Unit(ARCHER_STATS, 1, "hero")])
    game.hero = hero
    army = Army(1, 0, [Unit(SWORDSMAN_STATS, 2, "hero")], ap=4)
    wm.player_armies.append(army)
    game.state = types.SimpleNamespace(heroes=[hero])
    class DummyHeroList:
        def __init__(self):
            self.heroes = []
        def set_heroes(self, heroes):
            self.heroes = list(heroes)
    game.main_screen = types.SimpleNamespace(hero_list=DummyHeroList())

    screen = pg.display.set_mode((200, 200))
    ex = HeroExchangeScreen(screen, hero, army)

    # Exchange archer from hero to army
    ex.drag_src = ("a", 1)
    ex.drag_unit = hero.army[1]
    ex._drop_to("b", 1)
    assert len(hero.army) == 1
    assert len(army.units) == 2 and army.units[1].stats is ARCHER_STATS

    # Merge swordsman into army
    ex.drag_src = ("a", 0)
    ex.drag_unit = hero.army[0]
    ex._drop_to("b", 0)
    assert len(hero.army) == 0
    assert army.units[0].count == 3

    # Move all units back to hero, leaving army empty
    ex.drag_src = ("b", 1)
    ex.drag_unit = army.units[1]
    ex._drop_to("a", 0)
    ex.drag_src = ("b", 0)
    ex.drag_unit = army.units[0]
    ex._drop_to("a", 1)
    assert not army.units

    game._cleanup_armies()
    assert wm.player_armies == []


@pytest.mark.serial
def test_army_reintegrated_removes_ghost(monkeypatch, pygame_stub):
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
    monkeypatch.setattr(pg.Surface, "convert_alpha", lambda self: self)
    monkeypatch.setitem(sys.modules, "pygame", pg)
    monkeypatch.setitem(sys.modules, "pygame.draw", pg.draw)
    monkeypatch.setitem(sys.modules, "pygame.transform", pg.transform)
    from core.world import WorldMap
    from core.entities import Hero, Unit, SWORDSMAN_STATS
    from core.buildings import Town
    from ui.town_screen import TownScreen

    game = types.SimpleNamespace()
    wm = WorldMap(
        width=3,
        height=1,
        biome_weights={"scarletia_echo_plain": 1.0},
        num_obstacles=0,
        num_treasures=0,
        num_enemies=0,
    )
    game.world = wm
    town = Town()
    wm.grid[0][0].building = town
    hero = Hero(2, 0, [])
    game.hero = hero
    game.state = types.SimpleNamespace(heroes=[hero])

    class DummyHeroList:
        def __init__(self):
            self.heroes = []

        def set_heroes(self, heroes):
            self.heroes = list(heroes)

    game.main_screen = types.SimpleNamespace(hero_list=DummyHeroList())

    def refresh():
        heroes = list(game.state.heroes)
        game.main_screen.hero_list.set_heroes(heroes + game.world.player_armies)

    game.refresh_army_list = refresh

    screen = pg.display.set_mode((1, 1))
    ts = TownScreen(screen, game, town, None, None, (0, 0))
    ts.town.garrison.append(Unit(SWORDSMAN_STATS, 1, "hero"))

    # Move unit from garrison to create an army
    ts.drag_src = ("garrison", 0)
    ts.drag_unit = ts.town.garrison[0]
    ts._drop_to("hero", 0)
    assert len(game.world.player_armies) == 1

    # Move unit back to garrison, disbanding the army
    ts.drag_src = ("hero", 0)
    ts.drag_unit = ts.army_units[0]
    ts._drop_to("garrison", 0)

    assert game.world.player_armies == []
    assert game.main_screen.hero_list.heroes == [hero]
