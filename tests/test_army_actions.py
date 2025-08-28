import sys
import sys
import types
from core.entities import RECRUITABLE_UNITS

SWORDSMAN_STATS = RECRUITABLE_UNITS["swordsman"]


def setup_game(monkeypatch, pygame_stub):
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
    monkeypatch.setitem(sys.modules, "pygame.image", pg.image)
    monkeypatch.setitem(sys.modules, "pygame.transform", pg.transform)

    from core.world import WorldMap
    from core.entities import Hero, Army, Unit
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

    hero = Hero(2, 0, [Unit(SWORDSMAN_STATS, 1, "hero")])
    hero.ap = 10
    hero.max_ap = 10
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
    class DummyHeroList:
        def set_heroes(self, heroes):
            self.heroes = list(heroes)
    game.main_screen = types.SimpleNamespace(hero_list=DummyHeroList(), widgets={})
    game.ui_panel_rect = types.SimpleNamespace(y=1000)
    game.enemy_heroes = []
    game.hero_idx = 0
    game.active_actor = hero
    return game, constants, Army, Unit, SWORDSMAN_STATS


def test_army_collects_resource(monkeypatch, pygame_stub):
    game, constants, Army, Unit, S_STATS = setup_game(monkeypatch, pygame_stub)
    game.world.grid[0][1].resource = "wood"
    army = Army(0, 0, [Unit(S_STATS, 1, "hero")], ap=5)
    game.world.player_armies.append(army)
    game._on_select_hero(army)
    game.try_move_hero(1, 0)

    assert game.hero.resources["wood"] == 5
    assert game.world.grid[0][1].resource is None
    assert (army.x, army.y) == (1, 0)


def test_army_auto_combat_neutral(monkeypatch, pygame_stub):
    game, constants, Army, Unit, S_STATS = setup_game(monkeypatch, pygame_stub)
    enemy_tile = game.world.grid[0][1]
    enemy_tile.enemy_units = [Unit(S_STATS, 1, "enemy")]
    army = Army(0, 0, [Unit(S_STATS, 1, "hero")], ap=5)
    game.world.player_armies.append(army)

    import core.auto_resolve as auto_resolve

    def fake_resolve(hero_units, enemy_units):
        return True, 0, [Unit(S_STATS, 1, "hero")], [Unit(S_STATS, 0, "enemy")]

    monkeypatch.setattr(auto_resolve, "resolve", fake_resolve)

    game._on_select_hero(army)
    game.try_move_hero(1, 0)

    assert enemy_tile.enemy_units is None
    assert (army.x, army.y) == (1, 0)


def test_end_turn_with_army_selected(monkeypatch, pygame_stub):
    """Ensure ending the turn with an army selected does not crash."""
    game, constants, Army, Unit, S_STATS = setup_game(monkeypatch, pygame_stub)
    army = Army(0, 0, [Unit(S_STATS, 1, "hero")], ap=2, max_ap=5)
    game.world.player_armies.append(army)
    # Select the army; hero should remain the roster hero
    game._on_select_hero(army)
    assert game.active_actor is army
    # Exhaust hero and army AP then end the turn
    game.hero.ap = 0
    army.ap = 0
    game.end_turn()
    # New day: both hero and army AP restored and active actor reset to hero
    assert game.hero.ap == game.hero.max_ap
    assert army.ap == army.max_ap
    assert game.active_actor is game.hero


def test_army_full_flow(monkeypatch, pygame_stub):
    """Simulate selection, movement, resource gathering, combat and turn end."""
    game, constants, Army, Unit, S_STATS = setup_game(monkeypatch, pygame_stub)
    tile = game.world.grid[0][1]
    tile.resource = "wood"
    tile.enemy_units = [Unit(S_STATS, 1, "enemy")]
    army = Army(0, 0, [Unit(S_STATS, 1, "hero")], ap=5, max_ap=5)
    game.world.player_armies.append(army)
    game._on_select_hero(army)
    assert game.active_actor is army

    import core.auto_resolve as auto_resolve

    def fake_resolve(hero_units, enemy_units):
        return True, 0, [Unit(S_STATS, 1, "hero")], [Unit(S_STATS, 0, "enemy")]

    monkeypatch.setattr(auto_resolve, "resolve", fake_resolve)

    game.try_move_hero(1, 0)

    assert game.hero.resources["wood"] == 5
    assert tile.resource is None
    assert tile.enemy_units is None
    assert (army.x, army.y) == (1, 0)


def test_army_prompt_and_cleanup(monkeypatch, pygame_stub):
    game, constants, Army, Unit, S_STATS = setup_game(monkeypatch, pygame_stub)
    enemy_tile = game.world.grid[0][1]
    enemy_tile.enemy_units = [Unit(S_STATS, 1, "enemy")]
    army = Army(0, 0, [Unit(S_STATS, 1, "hero")], ap=5)
    game.world.player_armies.append(army)

    called = {}

    def fake_prompt(self, enemy_units, army_units=None):
        called["prompt"] = True
        return "auto"

    monkeypatch.setattr(game.__class__, "prompt_combat_choice", fake_prompt)

    import core.auto_resolve as auto_resolve

    def fake_resolve(hero_units, enemy_units):
        return False, 0, [Unit(S_STATS, 0, "hero")], [Unit(S_STATS, 1, "enemy")]

    monkeypatch.setattr(auto_resolve, "resolve", fake_resolve)

    game.screen = types.SimpleNamespace()
    game.quit_to_menu = False
    game._on_select_hero(army)
    game.try_move_hero(1, 0)

    assert called.get("prompt") is True
    assert game.world.player_armies == []

    army.ap = 0
    game.hero.ap = 0
    game.end_turn()

    assert game.hero.ap == game.hero.max_ap
    assert game.active_actor is game.hero
