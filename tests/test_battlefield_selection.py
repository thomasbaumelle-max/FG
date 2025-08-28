from types import SimpleNamespace
import os

from core.game import Game
from loaders.battlefield_loader import load_battlefields
import pytest


def test_battlefield_matches_tile_biome(monkeypatch):
    monkeypatch.setattr("core.game.audio.play_sound", lambda *args, **kwargs: None)

    class DummyUnit:
        def __init__(self):
            self.count = 1
            self.current_hp = 1

    class DummyHero:
        def __init__(self):
            self.x = 0
            self.y = 0
            self.army = [DummyUnit()]
            self.mana = 0
            self.max_mana = 0
            self.spells = {}
            self.faction = None
            self.naval_unit = None

        def gain_exp(self, amount: int) -> None:
            pass

    class DummyEnemy:
        def __init__(self):
            self.x = 0
            self.y = 0
            self.army = [DummyUnit()]

    class DummyTile:
        def __init__(self, biome):
            self.biome = biome
            self.enemy_units = [DummyUnit()]

    class DummyWorld:
        flora_loader = None

        def __init__(self, biome):
            self.grid = [[DummyTile(biome)]]
            self.width = 1
            self.height = 1

    hero = DummyHero()
    enemy = DummyEnemy()
    world = DummyWorld("mountain")

    game = Game.__new__(Game)
    game.screen = SimpleNamespace()
    game.assets = {}
    game.hero = hero
    game.enemy_heroes = [enemy]
    game.world = world
    game.biome_tilesets = {}
    game.unit_shadow_baked = {}
    game._update_caches_for_tile = lambda x, y: None
    game._notify = lambda msg: None
    game.quit_to_menu = False

    bf_path = os.path.join("assets", "battlefields", "battlefields.json")
    game.battlefields = load_battlefields(bf_path)

    captured = {}

    class DummyCombat:
        def __init__(self, *args, **kwargs):
            captured["battlefield_id"] = kwargs["battlefield"].id
            self.hero_units = args[2]
            self.enemy_units = args[3]
            self.exit_to_menu = False

        def run(self):
            return True, 0

    monkeypatch.setattr("core.combat.Combat", DummyCombat)

    game.combat_with_enemy_hero(enemy, initiated_by="enemy")

    assert captured["battlefield_id"] == "mountain"
