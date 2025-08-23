import types
import sys

pygame_stub = types.SimpleNamespace()
sys.modules.setdefault("pygame", pygame_stub)

from core.game import Game
from core.entities import Hero, Unit, SWORDSMAN_STATS
from core.world import WorldMap


def test_serialization_roundtrip():
    game = Game.__new__(Game)
    game.world = WorldMap(width=2, height=2, num_obstacles=0, num_treasures=0, num_enemies=0)
    hero = Hero(1, 2, [Unit(SWORDSMAN_STATS, 10, "hero")])
    hero.gold = 42
    hero.mana = 2
    hero.ap = 3
    hero.resources["wood"] = 5
    hero.inventory = [Unit(SWORDSMAN_STATS, 5, "hero")]
    hero.equipment = {"Head": Unit(SWORDSMAN_STATS, 1, "hero")}
    hero.skill_tree["strength"] = 1
    hero.apply_bonuses_to_army()
    game.hero = hero

    data = game._serialize_state()
    new_game = Game.__new__(Game)
    new_game._load_state(data)

    assert data["hero"] == new_game._serialize_state()["hero"]
