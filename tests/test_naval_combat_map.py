from types import SimpleNamespace

from core.game import Game


def test_naval_combat_map_is_all_water(monkeypatch):
    """Heroes fighting at sea should use a water-only combat map."""

    # --- Stub out external dependencies ---
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
            self.naval_unit = "boat"

        def gain_exp(self, amount: int) -> None:  # pragma: no cover - trivial
            pass

    class DummyEnemy:
        def __init__(self):
            self.x = 0
            self.y = 0
            self.army = [DummyUnit()]

    class DummyTile:
        biome = "ocean"

    class DummyWorld:
        grid = [[DummyTile()]]
        flora_loader = None

    hero = DummyHero()
    enemy = DummyEnemy()

    game = Game.__new__(Game)
    game.screen = SimpleNamespace()
    game.assets = {}
    game.hero = hero
    game.enemy_heroes = [enemy]
    game.world = DummyWorld()
    game.biome_tilesets = {}
    game.unit_shadow_baked = {}
    game._update_caches_for_tile = lambda x, y: None
    game._notify = lambda msg: None
    game.quit_to_menu = False

    captured = {}

    class DummyCombat:
        def __init__(self, *args, **kwargs):
            captured["combat_map"] = kwargs["combat_map"]
            captured["num_obstacles"] = kwargs["num_obstacles"]
            self.hero_units = hero.army
            self.enemy_units = enemy.army
            self.exit_to_menu = False

        def run(self):
            return True, 0

    monkeypatch.setattr("core.combat.Combat", DummyCombat)

    game.combat_with_enemy_hero(enemy, initiated_by="enemy")

    grid = captured["combat_map"]
    assert all(cell == "ocean" for row in grid for cell in row)
    assert captured["num_obstacles"] == 0

