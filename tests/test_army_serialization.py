import sys
import types

pygame_stub = types.SimpleNamespace()
sys.modules.setdefault("pygame", pygame_stub)

from core.game import Game
from core.entities import Hero, Army, Unit, SWORDSMAN_STATS
from core.world import WorldMap


def test_armies_persist_across_save_load(tmp_path):
    game = Game.__new__(Game)
    game.world = WorldMap(width=3, height=3, num_obstacles=0, num_treasures=0, num_enemies=0)
    hero = Hero(0, 0, [Unit(SWORDSMAN_STATS, 1, "hero")])
    game.hero = hero
    army = Army(2, 2, [Unit(SWORDSMAN_STATS, 5, "hero")], ap=3, max_ap=3)
    game.world.player_armies.append(army)
    hero.equipment = {}

    original = game._serialize_state()
    save_path = tmp_path / "save.json"
    game.save_game(save_path)

    game2 = Game.__new__(Game)
    game2.load_game(save_path)
    loaded = game2._serialize_state()

    assert original["player_armies"] == loaded["player_armies"]
