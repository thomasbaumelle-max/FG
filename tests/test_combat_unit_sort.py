import pygame
import pytest
from core.entities import UnitStats, Unit
from core import combat_render
from tests.test_overlay_rendering import _ensure_stub_functions


pytestmark = pytest.mark.combat


def _make_unit(name: str, side: str = "hero") -> Unit:
    stats = UnitStats(
        name=name,
        max_hp=1,
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
    return Unit(stats, 1, side)


def test_units_drawn_in_coordinate_order(monkeypatch, simple_combat):
    _ensure_stub_functions(monkeypatch)
    screen = pygame.Surface((800, 600))

    u1 = _make_unit("u1")
    u2 = _make_unit("u2")
    u3 = _make_unit("u3")
    u3.stats.battlefield_scale = 1.75

    assets = {"u1": pygame.Surface((10, 10)), "u2": pygame.Surface((10, 10)), "u3": pygame.Surface((10, 10))}

    combat = simple_combat([u1, u2, u3], [], screen=screen, assets=assets)

    # Place units in an unsorted order
    combat.units[0].x, combat.units[0].y = 1, 0  # u1
    combat.units[1].x, combat.units[1].y = 0, 0  # u2
    combat.units[2].x, combat.units[2].y = 0, 1  # u3

    calls = []
    orig_blit = pygame.Surface.blit

    def tracking_blit(self, src, dest, area=None, special_flags=0):
        for name, surf in assets.items():
            if src is surf:
                calls.append(name)
        return orig_blit(self, src, dest, area, special_flags)

    monkeypatch.setattr(pygame.Surface, "blit", tracking_blit)

    combat_render.draw(combat)

    # Units should be drawn in order sorted by (y, x): u2, u1, then u3
    assert calls == ["u2", "u1", "u3"]
    assert [(u.y, u.x) for u in combat.units] == [(0, 0), (0, 1), (1, 0)]
