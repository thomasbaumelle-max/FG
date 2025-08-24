import types

import pygame

from core.entities import Hero, Unit, SWORDSMAN_STATS
from ui.inventory_screen import InventoryScreen


class DummySurface:
    def __init__(self, size=(800, 600)):
        self._size = size

    def fill(self, *args, **kwargs):
        pass

    def get_size(self):
        return self._size

    def blit(self, *args, **kwargs):
        pass


class Rect:
    def __init__(self, x, y, w, h):
        self.x, self.y, self.width, self.height = x, y, w, h

    @property
    def size(self):
        return (self.width, self.height)

    @property
    def centerx(self):
        return self.x + self.width // 2

    @property
    def centery(self):
        return self.y + self.height // 2

    @property
    def right(self):
        return self.x + self.width

    @property
    def bottom(self):
        return self.y + self.height

    @property
    def topleft(self):
        return (self.x, self.y)

    def collidepoint(self, pos):
        px, py = pos
        return self.x <= px < self.x + self.width and self.y <= py < self.y + self.height


def make_screen_and_hero():
    screen = DummySurface()
    hero = Hero(0, 0, [Unit(SWORDSMAN_STATS, 1, "hero")])
    return screen, hero


def test_switch_skill_tabs(monkeypatch):
    monkeypatch.setattr(pygame, "Rect", Rect)
    screen, hero = make_screen_and_hero()
    inv = InventoryScreen(screen, {}, hero)
    inv.active_tab = "skills"
    monkeypatch.setattr(
        pygame,
        "draw",
        types.SimpleNamespace(rect=lambda *a, **k: None, line=lambda *a, **k: None),
    )
    rect = inv.skill_tab_buttons["tactics"]
    assert inv.active_skill_tab == inv.SKILL_TABS[0]
    assert inv._check_skill_tab_click((rect.x + 1, rect.y + 1))
    assert inv.active_skill_tab == "tactics"


def test_skill_acquisition_per_tree(monkeypatch):
    monkeypatch.setattr(pygame, "Rect", Rect)
    screen, hero = make_screen_and_hero()
    hero.skill_points = 1
    inv = InventoryScreen(screen, {}, hero)
    inv.active_tab = "skills"
    monkeypatch.setattr(
        pygame,
        "draw",
        types.SimpleNamespace(rect=lambda *a, **k: None, line=lambda *a, **k: None),
    )
    inv._draw_skills_content()
    rect = inv.skill_rects["logistics_N"]
    inv._on_lmb_down((rect.centerx, rect.centery))
    assert "logistics_N" in hero.learned_skills["logistics"]

    rect_tactics = inv.skill_tab_buttons["tactics"]
    inv._check_skill_tab_click((rect_tactics.x + 1, rect_tactics.y + 1))
    inv._draw_skills_content()
    assert "tactics_N" in inv.skill_rects
    assert hero.learned_skills.get("tactics", set()) == set()

