import pygame
import constants

from core.entities import UnitStats, Unit
from core import combat_render
from tests.test_overlay_rendering import _ensure_stub_functions


def test_damage_overlay_drawn_when_hovering(monkeypatch, simple_combat):
    _ensure_stub_functions(monkeypatch)
    pygame.init()
    stats_att = UnitStats(
        name="att",
        max_hp=5,
        attack_min=10,
        attack_max=10,
        defence_melee=0,
        defence_ranged=0,
        defence_magic=0,
        speed=1,
        attack_range=1,
        initiative=1,
        sheet="",
        hero_frames=(0, 0),
        enemy_frames=(0, 0),
    )
    stats_def = UnitStats(
        name="def",
        max_hp=5,
        attack_min=1,
        attack_max=1,
        defence_melee=0,
        defence_ranged=0,
        defence_magic=0,
        speed=1,
        attack_range=1,
        initiative=1,
        sheet="",
        hero_frames=(0, 0),
        enemy_frames=(0, 0),
    )
    hero = Unit(stats_att, 1, "hero")
    enemy = Unit(stats_def, 3, "enemy")
    screen = pygame.Surface((800, 600))
    combat = simple_combat([hero], [enemy], screen=screen)
    combat.selected_unit = combat.hero_units[0]
    combat.selected_action = "melee"

    target = combat.enemy_units[0]
    monkeypatch.setattr(
        pygame, "mouse", __import__("types").SimpleNamespace(get_pos=lambda: (0, 0)), raising=False
    )
    combat_render.draw(combat)
    rect = combat.cell_rect(target.x, target.y)
    monkeypatch.setattr(
        pygame,
        "mouse",
        __import__("types").SimpleNamespace(get_pos=lambda: rect.center),
        raising=False,
    )

    rendered = []

    class DummyFont:
        def render(self, text, aa, colour):
            rendered.append(text)
            return pygame.Surface((1, 1))

    monkeypatch.setattr(pygame.font, "SysFont", lambda *a, **k: DummyFont())

    combat_render.draw(combat)

    assert "-2" in rendered


def test_damage_overlay_accounts_for_obstacles(monkeypatch, simple_combat):
    _ensure_stub_functions(monkeypatch)
    pygame.init()
    stats_att = UnitStats(
        name="att",
        max_hp=5,
        attack_min=10,
        attack_max=10,
        defence_melee=0,
        defence_ranged=0,
        defence_magic=0,
        speed=1,
        attack_range=6,
        initiative=1,
        sheet="",
        hero_frames=(0, 0),
        enemy_frames=(0, 0),
    )
    stats_def = UnitStats(
        name="def",
        max_hp=5,
        attack_min=1,
        attack_max=1,
        defence_melee=0,
        defence_ranged=0,
        defence_magic=0,
        speed=1,
        attack_range=1,
        initiative=1,
        sheet="",
        hero_frames=(0, 0),
        enemy_frames=(0, 0),
    )
    hero = Unit(stats_att, 1, "hero")
    enemy = Unit(stats_def, 3, "enemy")
    screen = pygame.Surface((800, 600))
    combat = simple_combat([hero], [enemy], screen=screen)
    hero_unit = combat.hero_units[0]
    enemy_unit = combat.enemy_units[0]
    combat.selected_unit = hero_unit
    combat.selected_action = "ranged"
    combat.obstacles.add((2, 0))

    monkeypatch.setattr(
        pygame, "mouse", __import__("types").SimpleNamespace(get_pos=lambda: (0, 0)), raising=False
    )
    combat_render.draw(combat)
    rect = combat.cell_rect(enemy_unit.x, enemy_unit.y)
    monkeypatch.setattr(
        pygame, "mouse", __import__("types").SimpleNamespace(get_pos=lambda: rect.center), raising=False
    )

    rendered = []

    class DummyFont:
        def render(self, text, aa, colour):
            rendered.append(text)
            return pygame.Surface((1, 1))

    monkeypatch.setattr(pygame.font, "SysFont", lambda *a, **k: DummyFont())

    combat_render.draw(combat)

    assert "-1" in rendered

