from types import SimpleNamespace

import pygame
import pytest

from ui.minimap import Minimap, MOUSEBUTTONDOWN
from core.world import WorldMap
from core.buildings import Town
from tests.test_army_actions import setup_game


class DummyRenderer:
    def __init__(self, world):
        self.world = world
        self.cam_x = 0
        self.cam_y = 0
        self.zoom = 1.0
        self.surface = pygame.Surface((128, 128))
        self.centered = None

    def center_on(self, tile):
        self.centered = tile


def test_minimap_surface_and_viewport():
    world = WorldMap(width=4, height=4)
    renderer = DummyRenderer(world)
    minimap = Minimap(world, renderer)
    assert minimap.surface.get_width() == 256
    rect = pygame.Rect(0, 0, 256, 256)
    renderer.cam_x = 64
    renderer.cam_y = 64
    vp = minimap.get_viewport_rect(rect)
    assert (vp.x, vp.y, vp.width, vp.height) == (64, 64, 128, 128)


def test_minimap_city_fog_and_click():
    world = WorldMap(width=4, height=4)
    town = Town()
    town.owner = 0
    world.grid[1][1].building = town
    renderer = DummyRenderer(world)
    minimap = Minimap(world, renderer)
    assert minimap.city_points == [(96, 96)]
    fog = [[True] * 4 for _ in range(4)]
    fog[1][1] = False
    minimap.set_fog(fog)
    assert len(minimap.fog_rects) == 15
    rect = pygame.Rect(0, 0, 256, 256)
    evt = SimpleNamespace(type=MOUSEBUTTONDOWN, pos=(128, 128), button=1)
    minimap.handle_event(evt, rect)
    assert renderer.centered == (2, 2)


def test_minimap_invalidate_and_regenerate():
    world = WorldMap(width=4, height=4)
    renderer = DummyRenderer(world)
    minimap = Minimap(world, renderer)
    original_surface = minimap.surface

    # A generate without invalidation should keep the same surface instance
    minimap.generate()
    assert minimap.surface is original_surface

    # After invalidation, a new surface should be generated
    minimap.invalidate()
    minimap.generate()
    assert minimap.surface is not original_surface


def test_minimap_invalidate_region():
    world = WorldMap(width=4, height=4)
    renderer = DummyRenderer(world)
    minimap = Minimap(world, renderer)

    # Keep references to original block surfaces
    original_blocks = dict(minimap._block_cache)

    # Invalidate only the top-left tile
    minimap.invalidate_region(0, 0, 0, 0)
    minimap.generate()

    for coords, surf in original_blocks.items():
        if coords == (0, 0):
            assert minimap._block_cache[coords] is not surf
        else:
            assert minimap._block_cache[coords] is surf


def test_minimap_viewport_clamped(monkeypatch):
    world = WorldMap(width=1, height=1)
    renderer = DummyRenderer(world)
    minimap = Minimap(world, renderer)
    rect = pygame.Rect(0, 0, 256, 256)

    renderer.cam_x = 0
    renderer.cam_y = 0

    captured = {}

    def capture_rect(surface, colour, r, width=0):
        captured['rect'] = r

    monkeypatch.setattr(pygame.draw, 'rect', capture_rect)

    dest = pygame.Surface((256, 256))
    minimap.draw(dest, rect)

    view = captured['rect']
    assert view.x >= rect.x
    assert view.y >= rect.y
    assert view.x + view.width <= rect.x + rect.width
    assert view.y + view.height <= rect.y + rect.height


def test_game_updates_minimap_fog(monkeypatch, pygame_stub):
    game, constants, Army, Unit, S_STATS = setup_game(monkeypatch, pygame_stub)
    world = WorldMap(
        width=9,
        height=1,
        biome_weights={"scarletia_echo_plain": 1.0},
        num_obstacles=0,
        num_treasures=0,
        num_enemies=0,
    )
    for x in range(9):
        world.grid[0][x].obstacle = False
    game.world = world
    game.hero.x = 0
    game.hero.y = 0
    game.state.heroes = [game.hero]

    class DummyMinimap:
        def __init__(self):
            self.fog = None
            self.invalidated = False

        def set_fog(self, fog):
            self.fog = fog

        def invalidate(self):
            self.invalidated = True

    game.main_screen.minimap = DummyMinimap()

    game._update_player_visibility(game.hero)
    assert game.main_screen.minimap.fog[0][8] is True
    assert game.main_screen.minimap.invalidated is True

    game.main_screen.minimap.invalidated = False
    game.hero.x = 8
    game._update_player_visibility(game.hero)
    assert all(not cell for row in game.main_screen.minimap.fog for cell in row)
    assert game.main_screen.minimap.invalidated is True

    game.main_screen.minimap.invalidated = False
    game.hero.x = 0
    game._update_player_visibility(game.hero)
    assert game.main_screen.minimap.fog[0][8] is False
    assert game.main_screen.minimap.invalidated is True


def test_minimap_fog_initialized_on_game_start(monkeypatch, tmp_path, pygame_stub):
    """Fog rectangles should be populated immediately after starting a game."""

    from types import SimpleNamespace
    import sys

    pg = pygame_stub(transform=SimpleNamespace(flip=lambda surf, xbool, ybool: surf))
    pg.draw.circle = lambda *a, **k: None
    pg.draw.rect = lambda *a, **k: None
    pg.draw.polygon = lambda *a, **k: None
    pg.draw.line = lambda *a, **k: None
    pg.BLEND_RGBA_MULT = 0
    pg.BLEND_RGBA_ADD = 0
    pg.font.Font = lambda *a, **k: SimpleNamespace(render=lambda *a2, **k2: pg.Surface((1, 1)))

    DummySurface = pg.Surface((1, 1)).__class__
    DummySurface.get_size = lambda self: (self.get_width(), self.get_height())
    DummySurface.copy = lambda self: self

    monkeypatch.setitem(sys.modules, "pygame", pg)
    monkeypatch.setitem(sys.modules, "pygame.draw", pg.draw)
    monkeypatch.setattr("ui.widgets.minimap.pygame", pg)
    monkeypatch.setattr("theme.pygame", pg, raising=False)
    monkeypatch.setitem(
        sys.modules,
        "audio",
        SimpleNamespace(init=lambda: None, play_sound=lambda *a, **k: None),
    )

    from core.game import Game

    screen = SimpleNamespace(
        get_width=lambda: 100,
        get_height=lambda: 100,
        fill=lambda *a, **k: None,
        blit=lambda *a, **k: None,
        set_clip=lambda *a, **k: None,
    )

    map_path = tmp_path / "map.txt"
    map_path.write_text("G.W.\nG.W.\n")

    monkeypatch.setenv("FG_FAST_TESTS", "1")
    game = Game(screen, map_file=str(map_path))
    assert isinstance(game.main_screen.minimap.fog_rects, list)


def test_minimap_resize_recalculates_view():
    world = WorldMap(width=4, height=4)
    renderer = DummyRenderer(world)
    minimap = Minimap(world, renderer)
    fog = [[True] * 4 for _ in range(4)]
    minimap.set_fog(fog)
    minimap.resize(128)
    assert minimap.surface.get_width() == 128
    assert all(rect.width == 33 for rect in minimap.fog_rects)


def test_minimap_updates_on_move(monkeypatch, pygame_stub):
    game, constants, Army, Unit, S_STATS = setup_game(monkeypatch, pygame_stub)
    world = WorldMap(
        width=9,
        height=1,
        biome_weights={"scarletia_echo_plain": 1.0},
        num_obstacles=0,
        num_treasures=0,
        num_enemies=0,
    )
    for x in range(9):
        world.grid[0][x].obstacle = False
    game.world = world
    game.hero.x = 0
    game.hero.y = 0
    game.state.heroes = [game.hero]

    class DummyMinimap:
        def __init__(self):
            self.fog = None
            self.invalidated = False

        def set_fog(self, fog):
            self.fog = fog

        def invalidate(self):
            self.invalidated = True

    game.main_screen.minimap = DummyMinimap()

    game._update_player_visibility(game.hero)
    assert game.main_screen.minimap.fog[0][8] is True

    for _ in range(8):
        game.main_screen.minimap.invalidated = False
        game.try_move_hero(1, 0)
        assert game.main_screen.minimap.invalidated is True

    assert game.hero.x == 8
    assert game.main_screen.minimap.fog[0][8] is False
