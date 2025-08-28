import types
import sys
from core.entities import RECRUITABLE_UNITS

SWORDSMAN_STATS = RECRUITABLE_UNITS["swordsman"]


def setup_basic_game(monkeypatch, pygame_stub):
    pg = pygame_stub(
        image=types.SimpleNamespace(load=lambda path: None),
        transform=types.SimpleNamespace(
            scale=lambda surf, size: surf, smoothscale=lambda surf, size: surf
        ),
    )
    monkeypatch.setattr(pg.image, "load", lambda path: pg.Surface((10, 10)))
    monkeypatch.setattr(pg.Rect, "collidepoint", lambda self, pos: True)
    monkeypatch.setattr(pg.Surface, "convert_alpha", lambda self: self)
    monkeypatch.setitem(sys.modules, "pygame", pg)
    monkeypatch.setitem(sys.modules, "pygame.draw", pg.draw)

    from core.world import WorldMap
    from core.entities import Hero, Unit
    from core.game import Game
    from loaders.biomes import BiomeCatalog
    from loaders.core import Context
    import constants, os

    repo_root = os.path.dirname(os.path.dirname(__file__))
    ctx = Context(repo_root=repo_root, search_paths=["assets"], asset_loader=None)
    BiomeCatalog.load(ctx)

    game = Game.__new__(Game)
    wm = WorldMap(
        width=3,
        height=1,
        biome_weights={"scarletia_echo_plain": 1.0},
        num_obstacles=0,
        num_treasures=0,
        num_enemies=0,
    )
    for x in range(3):
        wm.grid[0][x].obstacle = False
    game.world = wm

    hero = Hero(0, 0, [Unit(SWORDSMAN_STATS, 1, "hero")])
    hero.ap = 10
    game.hero = hero
    game.state = types.SimpleNamespace(heroes=[hero])
    game.offset_x = 0
    game.offset_y = 0
    game.zoom = 1
    game.path = []
    game.move_queue = []
    game.path_target = None
    game.compute_path = lambda *a, **k: [(1, 0)]
    game._publish_resources = lambda: None
    game.screen = pygame_stub.Surface((10, 10))
    class DummyHeroList:
        def set_heroes(self, heroes):
            self.heroes = list(heroes)
    game.main_screen = types.SimpleNamespace(hero_list=DummyHeroList(), widgets={})
    game.ui_panel_rect = types.SimpleNamespace(y=1000)
    game.enemy_heroes = []
    game.hero_idx = 0
    game.active_actor = hero
    game.quit_to_menu = False
    return game, constants, Hero, Unit, SWORDSMAN_STATS


def test_enemy_before_treasure(monkeypatch, pygame_stub):
    game, constants, Hero, Unit, S_STATS = setup_basic_game(monkeypatch, pygame_stub)

    tile = game.world.grid[0][1]
    tile.treasure = {"gold": (5, 5)}
    tile.enemy_units = [Unit(S_STATS, 1, "enemy")]

    order: list[str] = []

    monkeypatch.setattr(game, "prompt_combat_choice", lambda units: order.append("combat") or "auto")
    import core.auto_resolve as auto_resolve

    def fake_resolve(hero_units, enemy_units):
        return True, 0, hero_units, enemy_units

    monkeypatch.setattr(auto_resolve, "resolve", fake_resolve)
    monkeypatch.setattr(auto_resolve, "show_summary", lambda *a, **k: None)
    monkeypatch.setattr(game, "prompt_treasure_choice", lambda t: order.append("treasure") or "gold")

    start_gold = game.hero.gold
    game.try_move_hero(1, 0)

    assert order == ["combat", "treasure"]
    assert game.hero.gold == start_gold + 5


def test_building_before_treasure(monkeypatch, pygame_stub):
    from tests.test_building_interaction import setup_game_with_building

    game, building, Game, constants = setup_game_with_building(monkeypatch, pygame_stub)
    tile = game.world.grid[0][1]
    tile.treasure = {"gold": (5, 5)}
    game.quit_to_menu = False

    order: list[str] = []

    monkeypatch.setattr(Game, "prompt_building_interaction", lambda self, b: order.append("building") or "leave")
    monkeypatch.setattr(Game, "prompt_treasure_choice", lambda self, t: order.append("treasure") or "gold")

    game.try_move_hero(1, 0)

    assert order == ["building"]
    assert tile.treasure is not None
