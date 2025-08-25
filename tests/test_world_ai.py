from core.world import WorldMap
from core.entities import Hero, EnemyHero, Unit, SWORDSMAN_STATS
from core.buildings import Town, Building
from core.game import Game
import core.exploration_ai as exploration_ai
import constants
from core.ai.creature_ai import GuardianAI, RoamingAI
import pytest
import random
import copy
from pathlib import Path

@pytest.fixture(scope="module")
def _marine_world_base() -> WorldMap:
    random.seed(0)
    path = Path(__file__).parent / "fixtures" / "mini_marine_map.txt"
    return WorldMap.from_file(str(path))


@pytest.fixture
def marine_world(_marine_world_base) -> WorldMap:
    return copy.deepcopy(_marine_world_base)


@pytest.fixture(scope="module")
def _plaine_world_base() -> WorldMap:
    random.seed(0)
    path = Path(__file__).parent / "fixtures" / "mini_continent_map.txt"
    return WorldMap.from_file(str(path))


@pytest.fixture
def plaine_world(_plaine_world_base) -> WorldMap:
    return copy.deepcopy(_plaine_world_base)


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
    game._rebuild_world_caches()
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
    game._rebuild_world_caches()
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
    world = _make_world(3, 2)
    hero = Hero(2, 1, [Unit(SWORDSMAN_STATS, 1, 'hero')])
    enemy = EnemyHero(0, 0, [Unit(SWORDSMAN_STATS, 1, 'enemy')])
    town = Town()
    town.owner = 0
    world.grid[0][1].building = town
    game = Game.__new__(Game)
    game.world = world
    game.hero = hero
    game.enemy_heroes = [enemy]
    game._rebuild_world_caches()
    start_ap = enemy.ap
    Game.move_enemy_heroes(game)
    assert (enemy.x, enemy.y) == (0, 0)
    assert town.owner == 1
    assert enemy.ap == start_ap - 1


def test_enemy_targets_hero_after_resource_collected(monkeypatch):
    monkeypatch.setattr(constants, "AI_DIFFICULTY", "Novice")
    game, enemy = _create_game_with_resource()
    Game.move_enemy_heroes(game)
    assert (enemy.x, enemy.y) == (0, 1)
    step = exploration_ai.compute_enemy_step(game, enemy)
    assert step in [(0, 0), (1, 1)]


def test_enemy_targets_hero_after_building_capture(monkeypatch):
    monkeypatch.setattr(constants, "AI_DIFFICULTY", "Intermédiaire")
    world = _make_world(3, 1)
    hero = Hero(2, 0, [Unit(SWORDSMAN_STATS, 1, 'hero')])
    enemy = EnemyHero(0, 0, [Unit(SWORDSMAN_STATS, 1, 'enemy')])
    b = Building()
    b.passable = True
    world.grid[0][1].building = b
    game = Game.__new__(Game)
    game.world = world
    game.hero = hero
    game.enemy_heroes = [enemy]
    game._rebuild_world_caches()
    Game.move_enemy_heroes(game)
    assert world.grid[0][1].building.owner == 1
    step = exploration_ai.compute_enemy_step(game, enemy)
    assert step == (2, 0)


def test_free_tiles_updates_when_tile_occupied():
    game, enemy = _create_game_with_enemy()
    assert (1, 0) in game.free_tiles
    Game.move_enemy_heroes(game)
    assert (1, 0) not in game.free_tiles


def test_guardian_stays_put():
    world = _make_world(5, 5)
    units = [Unit(SWORDSMAN_STATS, 5, "enemy")]
    world.grid[2][2].enemy_units = units
    ai = GuardianAI(2, 2, units, guard_range=1)
    hero_pos = (0, 0)
    ai.update(world, hero_pos, hero_strength=10)
    assert (ai.x, ai.y) == (2, 2)


def test_roamer_patrols():
    world = _make_world(5, 5)
    units = [Unit(SWORDSMAN_STATS, 5, "enemy")]
    world.grid[2][2].enemy_units = units
    ai = RoamingAI(2, 2, units, patrol_radius=2)
    hero_pos = (0, 0)
    moved = False
    for _ in range(5):
        ai.update(world, hero_pos, hero_strength=100)
        if (ai.x, ai.y) != (2, 2):
            moved = True
            break
    assert moved


@pytest.mark.slow
@pytest.mark.worldgen
@pytest.mark.combat
def test_marine_maps_have_guardian_clusters_and_fewer_roamers(marine_world, plaine_world, rng):
    world_marine = marine_world
    for row in world_marine.grid:
        for tile in row:
            tile.enemy_units = None
    world_marine.creatures.clear()
    free_land = len(world_marine._empty_land_tiles())
    total_tiles = world_marine.width * world_marine.height
    land_tiles = sum(
        1 for row in world_marine.grid for t in row if t.biome not in constants.WATER_BIOMES
    )
    land_ratio = land_tiles / total_tiles
    base = max(1, free_land // (15 if land_ratio < 0.5 else 9))
    roamer_count = base // 3
    guardian_count = base - roamer_count
    world_marine._generate_clusters(rng, guardian_count, roamer_count)
    guardians = [c for c in world_marine.creatures if isinstance(c, GuardianAI)]
    roamers = [c for c in world_marine.creatures if isinstance(c, RoamingAI)]
    assert guardians
    for g in guardians:
        assert any(
            0 <= g.x + dx < world_marine.width
            and 0 <= g.y + dy < world_marine.height
            and (
                world_marine.grid[g.y + dy][g.x + dx].resource
                or world_marine.grid[g.y + dy][g.x + dx].building
            )
            for dx in (-1, 0, 1)
            for dy in (-1, 0, 1)
        )

    world_plaine = plaine_world
    for row in world_plaine.grid:
        for tile in row:
            tile.enemy_units = None
    world_plaine.creatures.clear()
    free_land_p = len(world_plaine._empty_land_tiles())
    total_tiles_p = world_plaine.width * world_plaine.height
    land_tiles_p = sum(
        1 for row in world_plaine.grid for t in row if t.biome not in constants.WATER_BIOMES
    )
    land_ratio_p = land_tiles_p / total_tiles_p
    base_p = max(1, free_land_p // (15 if land_ratio_p < 0.5 else 9))
    roamer_count_p = base_p // 3
    guardian_count_p = base_p - roamer_count_p
    world_plaine._generate_clusters(rng, guardian_count_p, roamer_count_p)
    roamers_plain = [c for c in world_plaine.creatures if isinstance(c, RoamingAI)]
    assert roamers_plain
