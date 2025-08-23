import sys
import types
from core.entities import Unit, SWORDSMAN_STATS


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
        draw=types.SimpleNamespace(
            ellipse=lambda surf, color, rect: None,
            rect=lambda *args, **kwargs: None,
        ),
        time=types.SimpleNamespace(Clock=lambda: types.SimpleNamespace(tick=lambda fps: None)),
        event=types.SimpleNamespace(get=lambda: []),
        display=types.SimpleNamespace(flip=lambda: None, set_mode=lambda size: DummySurface()),
        font=types.SimpleNamespace(
            SysFont=lambda *args, **kwargs: types.SimpleNamespace(render=lambda *a, **k: DummySurface())
        ),
        init=lambda: None,
        quit=lambda: None,
    )
    return pygame_stub


def setup_game_with_building(monkeypatch):
    pygame_stub = make_pygame_stub()
    monkeypatch.setitem(sys.modules, "pygame", pygame_stub)
    monkeypatch.setitem(sys.modules, "pygame.draw", pygame_stub.draw)
    from core.world import WorldMap
    from core.entities import Hero, Unit, SWORDSMAN_STATS
    from core.buildings import create_building
    from core.game import Game
    import constants

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
    building = create_building("sawmill")
    wm.grid[0][1].building = building
    game.world = wm
    hero = Hero(0, 0, [Unit(SWORDSMAN_STATS, 1, 'hero')])
    hero.ap = 2
    game.hero = hero
    game.offset_x = 0
    game.offset_y = 0
    game.zoom = 1
    game.path = []
    game.move_queue = []
    game.path_target = None
    game.compute_path = lambda *args, **kwargs: [(1, 0)]
    game._publish_resources = lambda: None
    game.main_screen = types.SimpleNamespace(widgets={})
    game.ui_panel_rect = types.SimpleNamespace(y=1000)
    game.active_actor = hero
    return game, building, Game, constants


def setup_game_with_town(monkeypatch):
    pygame_stub = make_pygame_stub()
    monkeypatch.setitem(sys.modules, "pygame", pygame_stub)
    monkeypatch.setitem(sys.modules, "pygame.draw", pygame_stub.draw)
    from core.world import WorldMap
    from core.entities import Hero, Unit, SWORDSMAN_STATS
    from core.buildings import Town
    from core.game import Game
    import constants

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
    town = Town()
    wm.grid[0][1].building = town
    game.world = wm
    hero = Hero(0, 0, [Unit(SWORDSMAN_STATS, 1, 'hero')])
    hero.ap = 2
    game.hero = hero
    game.offset_x = 0
    game.offset_y = 0
    game.zoom = 1
    game.path = []
    game.move_queue = []
    game.path_target = None
    game.compute_path = lambda *args, **kwargs: [(1, 0)]
    game._publish_resources = lambda: None
    game.main_screen = types.SimpleNamespace(widgets={})
    game.ui_panel_rect = types.SimpleNamespace(y=1000)
    game.active_actor = hero
    return game, town, Game, constants


def test_try_move_into_building_interacts(monkeypatch):
    game, building, Game, constants = setup_game_with_building(monkeypatch)
    called = {}
    building.interact = lambda hero: called.setdefault('done', True)
    monkeypatch.setattr(Game, "prompt_building_interaction", lambda self, b: "take")
    game.try_move_hero(1, 0)
    assert called.get('done') is True
    assert game.hero.ap == 1
    assert (game.hero.x, game.hero.y) == (0, 0)


def test_try_move_into_building_leave(monkeypatch):
    game, building, Game, constants = setup_game_with_building(monkeypatch)
    called = {}
    building.interact = lambda hero: called.setdefault('done', True)
    monkeypatch.setattr(Game, "prompt_building_interaction", lambda self, b: "leave")
    game.try_move_hero(1, 0)
    assert called == {}
    assert game.hero.ap == 1
    assert (game.hero.x, game.hero.y) == (0, 0)


def test_handle_world_click_on_building_sets_path(monkeypatch):
    game, building, Game, constants = setup_game_with_building(monkeypatch)
    pos = (constants.TILE_SIZE * 1 + 1, constants.TILE_SIZE * 0 + 1)
    game.handle_world_click(pos)
    assert game.path == [(1, 0)]
    assert game.path_target == (1, 0)
    assert game.move_queue == []


def test_try_move_into_town_interacts_and_opens(monkeypatch):
    game, town, Game, constants = setup_game_with_town(monkeypatch)
    called = {}
    orig_interact = town.interact
    town.interact = lambda hero: (called.setdefault('interact', True), orig_interact(hero))
    monkeypatch.setattr(
        Game,
        "open_town",
        lambda self, t, army=None, town_pos=None: called.setdefault('open', True),
    )
    monkeypatch.setattr(Game, "prompt_building_interaction", lambda self, b: called.setdefault('prompt', True))
    game.try_move_hero(1, 0)
    assert called.get('interact') is True
    assert called.get('open') is True
    assert 'prompt' not in called
    assert game.hero.ap == 1
    assert (game.hero.x, game.hero.y) == (0, 0)
    assert town.owner == 0


def test_garrison_fight_and_capture(monkeypatch):
    game, building, Game, constants = setup_game_with_building(monkeypatch)
    building.garrison = [Unit(SWORDSMAN_STATS, 1, 'enemy')]

    def fake_combat(self, enemy, initiated_by='hero'):
        enemy.army = []
        return True

    monkeypatch.setattr(Game, 'combat_with_enemy_hero', fake_combat)
    monkeypatch.setattr(Game, 'prompt_building_interaction', lambda self, b: 'take')
    game.try_move_hero(1, 0)
    assert building.owner == 0
    assert building.garrison == []
    assert game.hero.ap == 1


def test_garrison_defeat_retains_garrison(monkeypatch):
    game, building, Game, constants = setup_game_with_building(monkeypatch)
    building.garrison = [Unit(SWORDSMAN_STATS, 1, 'enemy')]

    def fake_combat(self, enemy, initiated_by='hero'):
        self.hero.army = []
        return True

    monkeypatch.setattr(Game, 'combat_with_enemy_hero', fake_combat)
    monkeypatch.setattr(Game, 'prompt_building_interaction', lambda self, b: 'take')
    game.try_move_hero(1, 0)
    assert building.owner is None
    assert building.garrison
    assert game.hero.army == []
    assert game.hero.ap == 2


def test_garrison_autoresolve_clears_garrison(monkeypatch):
    game, building, Game, constants = setup_game_with_building(monkeypatch)
    building.garrison = [Unit(SWORDSMAN_STATS, 1, 'enemy')]

    def fake_combat(self, enemy, initiated_by='hero'):
        enemy.army = [Unit(SWORDSMAN_STATS, 0, 'enemy')]
        return True

    monkeypatch.setattr(Game, 'combat_with_enemy_hero', fake_combat)
    monkeypatch.setattr(Game, 'prompt_building_interaction', lambda self, b: 'take')
    game.try_move_hero(1, 0)
    assert building.owner == 0
    assert building.garrison == []


def test_try_move_into_owned_town_skips_interact(monkeypatch):
    game, town, Game, constants = setup_game_with_town(monkeypatch)
    town.owner = 0
    called = {}
    orig_interact = town.interact
    town.interact = lambda hero: (called.setdefault('interact', True), orig_interact(hero))
    monkeypatch.setattr(
        Game,
        "open_town",
        lambda self, t, army=None, town_pos=None: called.setdefault('open', True),
    )
    monkeypatch.setattr(Game, "prompt_building_interaction", lambda self, b: called.setdefault('prompt', True))
    game.try_move_hero(1, 0)
    assert 'interact' not in called
    assert called.get('open') is True
    assert 'prompt' not in called
    assert game.hero.ap == 1
    assert (game.hero.x, game.hero.y) == (0, 0)

