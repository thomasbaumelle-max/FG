import types
import sys
import json

pygame_stub = types.SimpleNamespace()
sys.modules.setdefault("pygame", pygame_stub)

from core.game import Game, SAVE_FORMAT_VERSION
from core.entities import Unit, SWORDSMAN_STATS, Hero
from core.world import WorldMap


def test_load_legacy_save(tmp_path):
    game = Game.__new__(Game)
    game.world = WorldMap(width=3, height=3, num_obstacles=0, num_treasures=0, num_enemies=0)
    game.hero = Hero(0, 0, [Unit(SWORDSMAN_STATS, 5, "hero")])
    game.hero.inventory = []
    game.hero.equipment = {}
    game.hero.apply_bonuses_to_army()

    expected = game._serialize_state()

    save_path = tmp_path / "save.json"
    game.save_game(save_path)

    with save_path.open() as f:
        legacy = json.load(f)
    legacy.pop("version", None)
    with save_path.open("w") as f:
        json.dump(legacy, f)

    game2 = Game.__new__(Game)
    game2.load_game(save_path)
    loaded = game2._serialize_state()

    assert loaded["version"] == SAVE_FORMAT_VERSION
    assert expected == loaded
