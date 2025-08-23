import types
import sys
import json

pygame_stub = types.SimpleNamespace()
sys.modules.setdefault("pygame", pygame_stub)

from core.game import Game
from core.entities import Hero
from core.world import WorldMap


def test_save_load_multiple_slots(tmp_path):
    game = Game.__new__(Game)
    game.world = WorldMap(width=1, height=1, num_obstacles=0, num_treasures=0, num_enemies=0)
    game.hero = Hero(0, 0, [])
    game.enemy_heroes = []
    game.hero.inventory = []
    game.hero.equipment = {}
    game.event_queue = ["slot1"]
    game.save_game(tmp_path / "save01.json")
    assert (tmp_path / "save_profile01.json").exists()
    game.event_queue = ["slot2"]
    game.save_game(tmp_path / "save02.json")
    assert (tmp_path / "save_profile02.json").exists()

    game2 = Game.__new__(Game)
    game2.load_game(tmp_path / "save02.json")
    assert game2.event_queue == ["slot2"]

    old_state = {
        "hero": {"x": 0, "y": 0, "gold": 0, "mana": 3, "ap": 3, "max_ap": 3, "resources": {}, "army": []},
        "world": {"width": 1, "height": 1, "tiles": [[{"biome": "scarletia_echo_plain", "obstacle": False}]]},
    }
    with (tmp_path / "savegame.json").open("w") as f:
        json.dump(old_state, f)
    with (tmp_path / "save_profile.json").open("w") as f:
        json.dump({"inventory": [], "equipment": {}, "skill_tree": {}}, f)

    game3 = Game.__new__(Game)
    game3.load_game(tmp_path / "savegame.json")
    assert game3.event_queue == []
    assert game3.enemy_heroes == []
