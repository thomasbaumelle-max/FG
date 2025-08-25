import sys
import types

import pytest

pygame_stub = types.SimpleNamespace()
sys.modules.setdefault("pygame", pygame_stub)

from core.world import WorldMap
from core.entities import Hero, Unit, SWORDSMAN_STATS
from core.buildings import create_building
from core.game import Game


@pytest.mark.serial
def test_place_resources_and_collect(rng, monkeypatch):
    monkeypatch.setattr("random.shuffle", rng.shuffle)
    wm = WorldMap(
        width=3,
        height=1,
        biome_weights={"scarletia_echo_plain": 1.0},
        num_obstacles=0,
        num_treasures=0,
        num_enemies=0,
    )
    wm.grid[0][0].biome = "scarletia_crimson_forest"
    wm.grid[0][1].biome = "mountain"
    wm.grid[0][2].biome = "scarletia_volcanic"
    for x in range(3):
        wm.grid[0][x].obstacle = False
    wm._place_resources(
        per_biome_counts={
            "scarletia_crimson_forest": 1,
            "mountain": 1,
            "scarletia_volcanic": 1,
        }
    )
    assert wm.grid[0][0].building.image == "buildings/sawmill/sawmill_0.png"
    assert wm.grid[0][1].building.image == "buildings/mine/mine_0.png"
    assert wm.grid[0][2].building.image == "buildings/crystal_mine/crystal_mine_0.png"
    hero = Hero(0, 0, [Unit(SWORDSMAN_STATS, 1, 'hero')])
    wm.grid[0][0].building.interact(hero)
    wm.grid[0][1].building.interact(hero)
    wm.grid[0][2].building.interact(hero)
    assert wm.grid[0][0].building.owner == 0
    assert wm.grid[0][1].building.owner == 0
    assert wm.grid[0][2].building.owner == 0
    assert hero.resources["wood"] == 5
    assert hero.resources["stone"] == 5
    assert hero.resources["crystal"] == 5
def test_building_income_each_turn():
    game = Game.__new__(Game)
    game.world = WorldMap(
        width=1,
        height=3,
        biome_weights={"scarletia_echo_plain": 1.0},
        num_obstacles=0,
        num_treasures=0,
        num_enemies=0,
    )
    hero = Hero(0, 0, [])
    game.hero = hero
    sawmill = create_building("sawmill")
    mine = create_building("mine")
    crystal = create_building("crystal_mine")
    game.world.grid[0][0].building = sawmill
    game.world.grid[1][0].building = mine
    game.world.grid[2][0].building = crystal
    for y in range(3):
        game.world.grid[y][0].obstacle = False
    sawmill.interact(hero)
    mine.interact(hero)
    crystal.interact(hero)
    hero.resources["wood"] = 0
    hero.resources["stone"] = 0
    hero.resources["crystal"] = 0
    game.end_turn()
    assert hero.resources["wood"] == sawmill.income["wood"]
    assert hero.resources["stone"] == mine.income["stone"]
    assert hero.resources["crystal"] == crystal.income["crystal"]
