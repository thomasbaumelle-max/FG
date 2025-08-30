import pygame
from types import SimpleNamespace

from core.entities import UnitStats, Unit, estimate_stack_label
from ui.enemy_stack_overlay import EnemyStackOverlay
import theme
from tests.test_overlay_rendering import _ensure_stub_functions


def test_enemy_stack_overlay_shows_stats(monkeypatch):
    _ensure_stub_functions(monkeypatch)
    pygame.init()
    rendered = []

    class DummyFont:
        def render(self, text, aa, colour):
            rendered.append(text)
            return pygame.Surface((1, 1))

    monkeypatch.setattr(theme, "get_font", lambda size=16: DummyFont())

    screen = pygame.Surface((200, 200))
    assets = SimpleNamespace(get=lambda key: None)
    stats = UnitStats(
        name="Goblin",
        max_hp=6,
        attack_min=1,
        attack_max=3,
        defence_melee=2,
        defence_ranged=1,
        defence_magic=0,
        speed=5,
        attack_range=1,
        initiative=1,
        sheet="",
        hero_frames=(0, 0),
        enemy_frames=(0, 0),
    )
    unit = Unit(stats, 10, "enemy")
    overlay = EnemyStackOverlay(screen, assets, [unit])
    overlay.draw()

    expected_stats = (
        f"HP {stats.max_hp}  "
        f"ATK {stats.attack_min}-{stats.attack_max}  "
        f"DEF {stats.defence_melee}/{stats.defence_ranged}/{stats.defence_magic}  "
        f"SPD {stats.speed}"
    )

    assert stats.name in rendered
    assert estimate_stack_label(unit.count) in rendered
    assert expected_stats in rendered
