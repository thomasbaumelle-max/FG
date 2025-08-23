from core.world import WorldMap
from core.entities import Hero, Unit, SWORDSMAN_STATS
from core.game import Game
import constants
import types


def _make_world(width, height):
    world = WorldMap(width=width, height=height)
    for row in world.grid:
        for tile in row:
            tile.biome = "scarletia_echo_plain"
            tile.obstacle = False
            tile.treasure = None
            tile.enemy_units = None
    return world


def _make_game(world, hero_pos):
    game = Game.__new__(Game)
    game.world = world
    game.hero = Hero(hero_pos[0], hero_pos[1], [Unit(SWORDSMAN_STATS, 1, 'hero')])
    game.enemy_heroes = []
    game.path = []
    game.path_target = None
    game.move_queue = []
    game.offset_x = 0
    game.offset_y = 0
    game.zoom = 1
    game.ui_panel_rect = types.SimpleNamespace(y=constants.TILE_SIZE * 10)
    game.active_actor = game.hero
    return game


def test_pathfinding_avoids_enemy_when_possible():
    world = _make_world(3, 3)
    world.grid[1][1].enemy_units = [Unit(SWORDSMAN_STATS, 1, 'enemy')]
    game = _make_game(world, (0, 1))
    path = game.compute_path((0, 1), (2, 1))
    assert path is not None
    assert (1, 1) not in path


def test_pathfinding_falls_back_through_enemy_if_blocked():
    world = _make_world(3, 1)
    world.grid[0][1].enemy_units = [Unit(SWORDSMAN_STATS, 1, 'enemy')]
    game = _make_game(world, (0, 0))
    pos = (2 * constants.TILE_SIZE, 0)
    game.handle_world_click(pos)
    assert game.path == [(1, 0), (2, 0)]


def test_path_recomputed_after_enemy_moves():
    world = _make_world(3, 3)
    game = _make_game(world, (0, 1))
    initial = game.compute_path((0, 1), (2, 1))
    game.path = initial
    game.path_target = (2, 1)
    world.grid[1][1].enemy_units = [Unit(SWORDSMAN_STATS, 1, 'enemy')]
    pos = (2 * constants.TILE_SIZE, 1 * constants.TILE_SIZE)
    game.handle_world_click(pos)
    assert game.move_queue
    assert (1, 1) not in game.move_queue

