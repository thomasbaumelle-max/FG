import types
import sys

pygame_stub = types.SimpleNamespace()
sys.modules.setdefault("pygame", pygame_stub)

from core.buildings import Building
from core.entities import Hero, Unit, SWORDSMAN_STATS
from core import economy
from core.game import Game
from core.world import WorldMap
from state.game_state import GameState


def test_building_upgrade_updates_income_and_resources():
    hero = Hero(0, 0, [])
    hero.gold = 150
    hero.resources = {}
    b = Building()
    b.production_per_level = {"gold": 5}
    b.income = {"gold": 5}
    b.upgrade_cost = {"gold": 100}
    econ_b = economy.Building(
        id="mine",
        provides=dict(b.income),
        level=1,
        upgrade_cost=dict(b.upgrade_cost),
        production_per_level=dict(b.production_per_level),
    )
    assert b.upgrade(hero, econ_b)
    assert b.level == 2
    assert b.income["gold"] == 10
    assert hero.gold == 50
    assert econ_b.level == 2
    assert econ_b.provides["gold"] == 10


def test_building_upgrade_persisted(tmp_path):
    game = Game.__new__(Game)
    game.world = WorldMap(width=1, height=1, num_obstacles=0, num_treasures=0, num_enemies=0)
    game.hero = Hero(0, 0, [Unit(SWORDSMAN_STATS, 1, "hero")])
    game.hero.inventory = []
    game.hero.equipment = {}
    game.hero.apply_bonuses_to_army()
    game.hero.gold = 200

    b = Building()
    b.name = "mine"
    b.image = "mine"
    b.production_per_level = {"stone": 2}
    b.income = {"stone": 2}
    b.upgrade_cost = {"gold": 100}
    game.world.grid[0][0].building = b

    econ_b = economy.Building(
        id=b.name,
        owner=None,
        provides=dict(b.income),
        level=1,
        upgrade_cost=dict(b.upgrade_cost),
        production_per_level=dict(b.production_per_level),
    )
    game._econ_building_map = {b: econ_b}
    game.state = GameState(world=game.world, heroes=[game.hero])
    game.state.economy.buildings.append(econ_b)
    game.state.economy.players[0] = economy.PlayerEconomy()

    assert b.upgrade(game.hero, econ_b)

    save_path = tmp_path / "save.json"
    game.save_game(save_path)
    game2 = Game.__new__(Game)
    game2.load_game(save_path)
    loaded_b = game2.world.grid[0][0].building
    assert loaded_b.level == 2
    assert loaded_b.income["stone"] == 4
