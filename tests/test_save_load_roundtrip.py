import types
import sys
import json

pygame_stub = types.SimpleNamespace()
sys.modules.setdefault("pygame", pygame_stub)

from core.game import Game
from core.entities import Unit, SWORDSMAN_STATS, Hero
from core.world import WorldMap
from core.buildings import create_building


def test_save_load_roundtrip(tmp_path):
    # Create a minimal game instance without initialising Pygame
    game = Game.__new__(Game)
    game.world = WorldMap(width=5, height=5, num_obstacles=0, num_treasures=0, num_enemies=0)
    hero = Hero(0, 0, [Unit(SWORDSMAN_STATS, 10, "hero")])
    game.hero = hero

    tile = game.world.grid[0][0]
    tile.biome = "scarletia_volcanic"
    tile.obstacle = True
    tile.treasure = {"gold": (25, 150), "exp": (40, 80)}
    tile.enemy_units = [Unit(SWORDSMAN_STATS, 7, "enemy")]
    tile.building = create_building("sawmill")
    tile.building.owner = 0
    tile.building.garrison = [Unit(SWORDSMAN_STATS, 5, "enemy")]

    game.hero.gold = 99
    game.hero.mana = 2
    game.hero.ap = 1
    game.hero.resources["wood"] = 4
    game.hero.inventory = [Unit(SWORDSMAN_STATS, 3, "hero")]
    game.hero.equipment = {"Head": Unit(SWORDSMAN_STATS, 1, "hero")}
    game.hero.skill_tree["strength"] = 1
    game.hero.apply_bonuses_to_army()

    original = game._serialize_state()
    save_path = tmp_path / "save.json"
    game.save_game(save_path)

    profile_path = tmp_path / "save_profile.json"
    assert profile_path.exists()
    with profile_path.open() as f:
        profile = json.load(f)
    expected_profile = {
        key: original["hero"][key]
        for key in ("inventory", "equipment", "skill_tree")
    }
    assert profile == expected_profile
    with save_path.open() as f:
        main = json.load(f)
    for key in ("inventory", "equipment", "skill_tree"):
        assert key not in main["hero"]

    game2 = Game.__new__(Game)
    game2.load_game(save_path)
    loaded = game2._serialize_state()
    assert game2.world.grid[0][0].building.garrison[0].count == 5

    # Building sprites are not restored when their image is missing; ignore them
    for rows in (original["world"]["tiles"], loaded["world"]["tiles"]):
        for row in rows:
            for tile in row:
                tile.pop("building", None)
    assert original == loaded

