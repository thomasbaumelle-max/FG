import sys
import types
import pytest
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
    from core.entities import Hero, Unit
    from core.game import Game
    from loaders.biomes import BiomeCatalog, Biome
    from loaders.core import Context
    import constants, os
    repo_root = os.path.dirname(os.path.dirname(__file__))
    ctx = Context(repo_root=repo_root, search_paths=["assets"], asset_loader=None)
    BiomeCatalog.load(ctx)
    # Add custom swamp biome using constants table
    swamp_biome = Biome(
        id="swamp",
        type="swamp",
        description="",
        path="",
        variants=1,
        colour=(0, 0, 0),
        flora=[],
        terrain_cost=constants.TERRAIN_COSTS["swamp"],
    )
    BiomeCatalog._biomes["swamp"] = swamp_biome
    game = Game.__new__(Game)
    wm = WorldMap(width=3, height=1, biome_weights={"scarletia_echo_plain": 1.0}, num_obstacles=0, num_treasures=0, num_enemies=0)
    for x in range(3):
        wm.grid[0][x].obstacle = False
    wm.grid[0][1].biome = "scarletia_volcanic"
    wm.grid[0][2].biome = "swamp"
    game.world = wm
    hero = Hero(0, 0, [Unit(SWORDSMAN_STATS, 1, "hero")])
    hero.ap = 10
    hero.max_ap = 10
    game.hero = hero
    game.offset_x = 0
    game.offset_y = 0
    game.zoom = 1
    game.path = []
    game.move_queue = []
    game.path_target = None
    game.compute_path = lambda *a, **k: [(1, 0), (2, 0)]
    game._publish_resources = lambda: None
    game.main_screen = types.SimpleNamespace(widgets={})
    game.ui_panel_rect = types.SimpleNamespace(y=1000)
    game.enemy_heroes = []
    game.active_actor = hero
    return game, constants


def test_multi_terrain_ap_cost(monkeypatch, pygame_stub):
    game, constants = setup_game(monkeypatch, pygame_stub)
    game.try_move_hero(1, 0)
    game.try_move_hero(1, 0)
    expected = 10 - (
        constants.TERRAIN_COSTS["volcanic"] + constants.TERRAIN_COSTS["swamp"]
    )
    assert game.hero.ap == pytest.approx(expected)
    assert (game.hero.x, game.hero.y) == (2, 0)
