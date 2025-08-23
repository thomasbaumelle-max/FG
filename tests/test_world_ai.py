from core.world import WorldMap
from core.entities import Hero, EnemyHero, Unit, SWORDSMAN_STATS
from core.buildings import Town
from core.game import Game
import core.exploration_ai as exploration_ai


def _make_world(width, height):
    world = WorldMap(width=width, height=height)
    for row in world.grid:
        for tile in row:
            tile.biome = "scarletia_echo_plain"
            tile.obstacle = False
            tile.treasure = None
            tile.enemy_units = None
    return world


def _create_game_with_enemy():
    world = _make_world(3, 1)
    hero = Hero(0, 0, [Unit(SWORDSMAN_STATS, 1, 'hero')])
    enemy = EnemyHero(2, 0, [Unit(SWORDSMAN_STATS, 1, 'enemy')])
    game = Game.__new__(Game)
    game.world = world
    game.hero = hero
    game.enemy_heroes = [enemy]
    return game, enemy


def _create_game_with_resource():
    world = _make_world(3, 2)
    hero = Hero(2, 0, [Unit(SWORDSMAN_STATS, 1, 'hero')])
    enemy = EnemyHero(0, 0, [Unit(SWORDSMAN_STATS, 1, 'enemy')])
    world.grid[1][0].resource = "wood"
    game = Game.__new__(Game)
    game.world = world
    game.hero = hero
    game.enemy_heroes = [enemy]
    return game, enemy


def test_enemy_hero_moves_toward_hero():
    game, enemy = _create_game_with_enemy()
    Game.move_enemy_heroes(game)
    assert (enemy.x, enemy.y) == (1, 0)


def test_enemy_target_weighted_by_difficulty():
    game, enemy = _create_game_with_resource()
    step_easy = exploration_ai.compute_enemy_step(game, enemy, "Novice")
    assert step_easy == (0, 1)
    step_hard = exploration_ai.compute_enemy_step(game, enemy, "Avancé")
    assert step_hard == (1, 0)


def test_enemy_captures_town_from_adjacent():
    world = _make_world(3, 1)
    hero = Hero(2, 0, [Unit(SWORDSMAN_STATS, 1, 'hero')])
    enemy = EnemyHero(0, 0, [Unit(SWORDSMAN_STATS, 1, 'enemy')])
    town = Town()
    town.owner = 0
    world.grid[0][1].building = town
    game = Game.__new__(Game)
    game.world = world
    game.hero = hero
    game.enemy_heroes = [enemy]
    start_ap = enemy.ap
    Game.move_enemy_heroes(game)
    assert (enemy.x, enemy.y) == (0, 0)
    assert town.owner == 1
    assert enemy.ap == start_ap - 1
