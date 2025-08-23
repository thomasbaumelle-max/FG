from types import SimpleNamespace

import pygame

from ui.widgets.minimap import Minimap, MOUSEBUTTONDOWN
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


def test_game_updates_minimap_fog(monkeypatch):
    game, constants, Army, Unit, S_STATS = setup_game(monkeypatch)
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


def test_minimap_fog_initialized_on_game_start(monkeypatch, tmp_path):
    """Fog rectangles should be populated immediately after starting a game."""

    from types import SimpleNamespace
    import sys
    from tests.test_army_actions import make_pygame_stub

    pygame_stub = make_pygame_stub()
    # Provide drawing helpers used during Game initialisation
    pygame_stub.draw.circle = lambda *a, **k: None
    pygame_stub.draw.rect = lambda *a, **k: None
    pygame_stub.draw.polygon = lambda *a, **k: None
    pygame_stub.draw.line = lambda *a, **k: None
    pygame_stub.transform.flip = lambda surf, xbool, ybool: surf
    pygame_stub.BLEND_RGBA_MULT = 0
    pygame_stub.BLEND_RGBA_ADD = 0

    DummySurface = pygame_stub.Surface((1, 1)).__class__
    DummySurface.get_size = lambda self: (self.get_width(), self.get_height())
    DummySurface.copy = lambda self: self

    Rect = pygame_stub.Rect
    Rect.bottom = property(lambda self: self.y + self.height)
    Rect.top = property(lambda self: self.y)
    Rect.right = property(lambda self: self.x + self.width)
    Rect.left = property(lambda self: self.x)
    Rect.centerx = property(lambda self: self.x + self.width // 2)
    Rect.centery = property(lambda self: self.y + self.height // 2)
    Rect.center = property(lambda self: (self.centerx, self.centery))
    Rect.size = property(lambda self: (self.width, self.height))

    monkeypatch.setitem(sys.modules, "pygame", pygame_stub)
    monkeypatch.setitem(sys.modules, "pygame.draw", pygame_stub.draw)
    monkeypatch.setattr("ui.widgets.minimap.pygame", pygame_stub)
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

    game = Game(screen, map_file=str(map_path))
    assert game.main_screen.minimap.fog_rects
