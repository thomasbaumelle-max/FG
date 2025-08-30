import sys
import types
import pytest


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
    from core.entities import Hero, Army, Unit
    from tests.unit_stats import get_unit_stats
    SWORDSMAN_STATS = get_unit_stats("swordsman")
    ARCHER_STATS = get_unit_stats("archer")
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
