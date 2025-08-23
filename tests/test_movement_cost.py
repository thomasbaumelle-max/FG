import sys
import types

def make_pygame_stub():
    class Rect:
        def __init__(self, x, y, w, h):
            self.x, self.y, self.width, self.height = x, y, w, h
        def collidepoint(self, pos):
            return True
    class DummySurface:
        def convert_alpha(self):
            return self
        def get_width(self):
            return 10
        def get_height(self):
            return 10
        def get_rect(self):
            return Rect(0, 0, 10, 10)
        def blit(self, *args, **kwargs):
            pass
        def fill(self, *args, **kwargs):
            pass
    def load(path):
        return DummySurface()
    pygame_stub = types.SimpleNamespace(
        image=types.SimpleNamespace(load=load),
        transform=types.SimpleNamespace(scale=lambda surf, size: surf, smoothscale=lambda surf, size: surf),
        Surface=lambda size, flags=0: DummySurface(),
        SRCALPHA=1,
        Rect=Rect,
        draw=types.SimpleNamespace(ellipse=lambda surf, color, rect: None, rect=lambda *a, **k: None),
        time=types.SimpleNamespace(Clock=lambda: types.SimpleNamespace(tick=lambda fps: None)),
        event=types.SimpleNamespace(get=lambda: []),
        display=types.SimpleNamespace(flip=lambda: None, set_mode=lambda size: DummySurface()),
        font=types.SimpleNamespace(SysFont=lambda *a, **k: types.SimpleNamespace(render=lambda *a, **k: DummySurface())),
        init=lambda: None,
        quit=lambda: None,
    )
    return pygame_stub

def setup_game(monkeypatch):
    pygame_stub = make_pygame_stub()
    monkeypatch.setitem(sys.modules, "pygame", pygame_stub)
    monkeypatch.setitem(sys.modules, "pygame.draw", pygame_stub.draw)
    from core.world import WorldMap
    from core.entities import Hero, Unit, SWORDSMAN_STATS
    from core.game import Game
    from loaders.biomes import BiomeCatalog
    from loaders.core import Context
    import constants, os
    repo_root = os.path.dirname(os.path.dirname(__file__))
    ctx = Context(repo_root=repo_root, search_paths=["assets"], asset_loader=None)
    BiomeCatalog.load(ctx)
    game = Game.__new__(Game)
    wm = WorldMap(width=2, height=1, biome_weights={"scarletia_volcanic": 1.0}, num_obstacles=0, num_treasures=0, num_enemies=0)
    for x in range(2):
        wm.grid[0][x].obstacle = False
    game.world = wm
    hero = Hero(0, 0, [Unit(SWORDSMAN_STATS, 1, 'hero')])
    hero.ap = 5
    hero.max_ap = 5
    game.hero = hero
    game.offset_x = 0
    game.offset_y = 0
    game.zoom = 1
    game.path = []
    game.move_queue = []
    game.path_target = None
    game.compute_path = lambda *a, **k: [(1, 0)]
    game._publish_resources = lambda: None
    game.main_screen = types.SimpleNamespace(widgets={})
    game.ui_panel_rect = types.SimpleNamespace(y=1000)
    game.enemy_heroes = []
    game.active_actor = hero
    return game, constants

def test_terrain_cost_deducted(monkeypatch):
    game, constants = setup_game(monkeypatch)
    game.try_move_hero(1, 0)
    assert game.hero.ap == 3
    assert (game.hero.x, game.hero.y) == (1, 0)

def test_road_cost_bonus(monkeypatch):
    game, constants = setup_game(monkeypatch)
    game.world.grid[0][1].road = True
    game.try_move_hero(1, 0)
    assert game.hero.ap == 5 - constants.ROAD_COST
    assert (game.hero.x, game.hero.y) == (1, 0)
