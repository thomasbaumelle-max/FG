import types
import sys
import json

pygame_stub = types.SimpleNamespace()
sys.modules.setdefault("pygame", pygame_stub)

from core.game import Game
from core.entities import Hero, Unit, SWORDSMAN_STATS
from core.world import WorldMap


def test_load_game_with_unknown_unit(tmp_path):
    game = Game.__new__(Game)
    game.world = WorldMap(width=3, height=3, num_obstacles=0, num_treasures=0, num_enemies=0)
    hero = Hero(0, 0, [Unit(SWORDSMAN_STATS, 1, "hero")])
    game.hero = hero
    hero.equipment = {}

    save_path = tmp_path / "save.json"
    game.save_game(save_path)

    with save_path.open() as f:
        data = json.load(f)
    data["hero"]["army"][0]["name"] = "mystery_unit"
    with save_path.open("w") as f:
        json.dump(data, f)

    game2 = Game.__new__(Game)
    game2.load_game(save_path)
    assert game2.hero.units == []
