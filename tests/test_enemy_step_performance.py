import time
import pytest

from core.world import WorldMap
from core.entities import Hero, EnemyHero, Unit, SWORDSMAN_STATS
from core.game import Game
import core.exploration_ai as exploration_ai


def _make_world(width, height):
    world = WorldMap(width=width, height=height)
    for row in world.grid:
        for tile in row:
            tile.biome = "scarletia_echo_plain"
            tile.obstacle = False
            tile.treasure = None
            tile.resource = None
            tile.enemy_units = None
    return world


@pytest.mark.slow
def test_enemy_step_distance_filter_performance(monkeypatch):
    world = _make_world(50, 50)
    hero = Hero(0, 0, [Unit(SWORDSMAN_STATS, 1, "hero")])
    enemy = EnemyHero(1, 1, [Unit(SWORDSMAN_STATS, 1, "enemy")])

    # Populate far resources to create many potential targets.
    for x in range(25, 50):
        for y in range(25, 50):
            world.grid[y][x].resource = "wood"

    game = Game.__new__(Game)
    game.world = world
    game.hero = hero
    game.enemy_heroes = [enemy]
    game._rebuild_world_caches()

    call_counter = {"count": 0}

    def stub_compute_path(start, goal, avoid_enemies=None, frontier_limit=None):
        call_counter["count"] += 1
        time.sleep(0.001)
        return [goal]

    monkeypatch.setattr(game, "compute_path", stub_compute_path)

    monkeypatch.setattr(exploration_ai, "MAX_TARGET_RADIUS", 10**9)
    start = time.perf_counter()
    exploration_ai.compute_enemy_step(game, enemy)
    old_duration = time.perf_counter() - start
    old_calls = call_counter["count"]

    call_counter["count"] = 0
    monkeypatch.setattr(exploration_ai, "MAX_TARGET_RADIUS", 20)
    start = time.perf_counter()
    exploration_ai.compute_enemy_step(game, enemy)
    new_duration = time.perf_counter() - start
    new_calls = call_counter["count"]

    assert new_calls < old_calls
    assert new_duration < old_duration
