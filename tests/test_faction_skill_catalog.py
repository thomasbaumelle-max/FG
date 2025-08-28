import pygame

import core.entities as entities
from core.entities import Hero, Unit
from tests.unit_stats import get_unit_stats

SWORDSMAN_STATS = get_unit_stats("swordsman")
from core.faction import FactionDef
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


def test_skill_catalog_changes_with_faction():
    entities.build_skill_catalog("red_knights")
    red = set(entities.SKILL_CATALOG.keys())
    entities.build_skill_catalog("sylvan")
    syl = set(entities.SKILL_CATALOG.keys())
    assert "logistics_N" in red and "logistics_N" not in syl


def test_inventory_skill_tabs_vary_by_faction(monkeypatch):
    monkeypatch.setattr(pygame, "Rect", Rect)
    screen = DummySurface()
    hero_red = Hero(0, 0, [Unit(SWORDSMAN_STATS, 1, "hero")],
                    faction=FactionDef(id="red_knights", name="Red"))
    inv_red = InventoryScreen(screen, {}, hero_red)
    hero_syl = Hero(0, 0, [Unit(SWORDSMAN_STATS, 1, "hero")],
                    faction=FactionDef(id="sylvan", name="Sylvan"))
    inv_syl = InventoryScreen(screen, {}, hero_syl)
    assert inv_red.SKILL_TABS != inv_syl.SKILL_TABS

