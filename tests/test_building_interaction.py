import sys
import types
from core.entities import Unit, RECRUITABLE_UNITS

SWORDSMAN_STATS = RECRUITABLE_UNITS["swordsman"]


def setup_game_with_building(monkeypatch, pygame_stub):
    pg = pygame_stub(
        image=types.SimpleNamespace(load=lambda path: None),
        transform=types.SimpleNamespace(
            scale=lambda surf, size: surf, smoothscale=lambda surf, size: surf
        ),
    )
    monkeypatch.setattr(pg.image, "load", lambda path: pg.Surface((10, 10)))
    monkeypatch.setattr(pg.Rect, "collidepoint", lambda self, pos: True)
    monkeypatch.setattr(pg.Surface, "convert_alpha", lambda self: self)
    monkeypatch.setitem(sys.modules, "pygame.draw", pg.draw)
    monkeypatch.setitem(sys.modules, "pygame.image", pg.image)
    monkeypatch.setitem(sys.modules, "pygame.transform", pg.transform)
    monkeypatch.setitem(sys.modules, "pygame", pg)
    from core.world import WorldMap
    from core.entities import Hero, Unit
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


def setup_game_with_town(monkeypatch, pygame_stub):
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


def test_try_move_into_building_interacts(monkeypatch, pygame_stub):
    game, building, Game, constants = setup_game_with_building(monkeypatch, pygame_stub)
    called = {}
    building.interact = lambda hero: called.setdefault('done', True)
    monkeypatch.setattr(Game, "prompt_building_interaction", lambda self, b: "take")
    game.try_move_hero(1, 0)
    assert called.get('done') is True
    assert game.hero.ap == 1
    assert (game.hero.x, game.hero.y) == (0, 0)


def test_try_move_into_building_leave(monkeypatch, pygame_stub):
    game, building, Game, constants = setup_game_with_building(monkeypatch, pygame_stub)
    called = {}
    building.interact = lambda hero: called.setdefault('done', True)
    monkeypatch.setattr(Game, "prompt_building_interaction", lambda self, b: "leave")
    game.try_move_hero(1, 0)
    assert called == {}
    assert game.hero.ap == 1
    assert (game.hero.x, game.hero.y) == (0, 0)


def test_handle_world_click_on_building_sets_path(monkeypatch, pygame_stub):
    game, building, Game, constants = setup_game_with_building(monkeypatch, pygame_stub)
    pos = (constants.TILE_SIZE * 1 + 1, constants.TILE_SIZE * 0 + 1)
    game.handle_world_click(pos)
    assert game.path == [(1, 0)]
    assert game.path_target == (1, 0)
    assert game.move_queue == []


def test_try_move_into_town_interacts_without_opening(monkeypatch, pygame_stub):
    game, town, Game, constants = setup_game_with_town(monkeypatch, pygame_stub)
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
    assert 'open' not in called
    assert 'prompt' not in called
    assert game.hero.ap == 1
    assert (game.hero.x, game.hero.y) == (0, 0)
    assert town.owner == 0


def test_garrison_fight_and_capture(monkeypatch, pygame_stub):
    game, building, Game, constants = setup_game_with_building(monkeypatch, pygame_stub)
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


def test_garrison_defeat_retains_garrison(monkeypatch, pygame_stub):
    game, building, Game, constants = setup_game_with_building(monkeypatch, pygame_stub)
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


def test_garrison_autoresolve_clears_garrison(monkeypatch, pygame_stub):
    game, building, Game, constants = setup_game_with_building(monkeypatch, pygame_stub)
    building.garrison = [Unit(SWORDSMAN_STATS, 1, 'enemy')]

    def fake_combat(self, enemy, initiated_by='hero'):
        enemy.army = [Unit(SWORDSMAN_STATS, 0, 'enemy')]
        return True

    monkeypatch.setattr(Game, 'combat_with_enemy_hero', fake_combat)
    monkeypatch.setattr(Game, 'prompt_building_interaction', lambda self, b: 'take')
    game.try_move_hero(1, 0)
    assert building.owner == 0
    assert building.garrison == []


def test_try_move_into_owned_town_skips_interact(monkeypatch, pygame_stub):
    game, town, Game, constants = setup_game_with_town(monkeypatch, pygame_stub)
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
    assert 'open' not in called
    assert 'prompt' not in called
    assert game.hero.ap == 1
    assert (game.hero.x, game.hero.y) == (0, 0)


def test_try_move_into_owned_town_with_garrison_no_combat(monkeypatch, pygame_stub):
    game, town, Game, constants = setup_game_with_town(monkeypatch, pygame_stub)
    town.owner = 0
    town.garrison = [Unit(SWORDSMAN_STATS, 1, 'hero')]
    called = {}

    def fake_combat(self, enemy, initiated_by='hero'):
        called.setdefault('combat', True)
        return True

    monkeypatch.setattr(Game, 'combat_with_enemy_hero', fake_combat)
    monkeypatch.setattr(
        Game,
        'open_town',
        lambda self, t, army=None, town_pos=None: called.setdefault('open', True),
    )
    game.try_move_hero(1, 0)
    assert 'combat' not in called
    assert 'open' not in called

