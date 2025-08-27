import types
import pytest
import pygame
import theme
from loaders import icon_loader as IconLoader
from core.entities import Hero, Unit, SWORDSMAN_STATS
from ui.inventory_screen import InventoryScreen


class DummySurface:
    def __init__(self, size):
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
        return self.x <= px < self.right and self.y <= py < self.bottom


@pytest.mark.parametrize("size", [(800, 600), (640, 480), (400, 300)])
def test_army_grid_above_resbar(monkeypatch, size):
    monkeypatch.setattr(pygame, "Rect", Rect)
    monkeypatch.setattr(pygame, "draw", types.SimpleNamespace(rect=lambda *a, **k: None))
    monkeypatch.setattr(theme, "draw_frame", lambda *a, **k: None)
    monkeypatch.setattr(IconLoader, "get", lambda *a, **k: None)

    screen = DummySurface(size)
    hero = Hero(0, 0, [Unit(SWORDSMAN_STATS, 1, "hero")])
    inv = InventoryScreen(screen, {}, hero)
    inv.active_tab = "stats"

    inv._draw_stats_content()

    gy = inv.army_rects[0][1].y
    cell = inv.army_rects[0][1].height
    assert gy + cell < inv.resbar_rect.y

