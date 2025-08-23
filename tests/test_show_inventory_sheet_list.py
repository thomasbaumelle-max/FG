import pygame
from types import SimpleNamespace

from core.entities import Hero, Unit, SWORDSMAN_STATS
from core.game import Game
from ui.inventory_screen import InventoryScreen


def test_show_inventory_handles_list_sheet(monkeypatch):
    pygame.Surface.get_size = lambda self: (self.get_width(), self.get_height())
    pygame.transform = SimpleNamespace(scale=lambda img, size: img)
    class Rect:
        def __init__(self, x, y, w, h):
            self.x = x
            self.y = y
            self.width = w
            self.height = h

        @property
        def right(self):
            return self.x + self.width

        @property
        def bottom(self):
            return self.y + self.height

        @property
        def topleft(self):
            return (self.x, self.y)

        def move(self, pos):
            return Rect(self.x + pos[0], self.y + pos[1], self.width, self.height)

    pygame.Rect = Rect
    hero = Hero(0, 0, [Unit(SWORDSMAN_STATS, 1, "hero")])
    assets = {"units": [pygame.Surface((10, 10))]}
    screen = pygame.Surface((800, 600))
    screen.get_size = lambda: (800, 600)
    clock = pygame.time.Clock()

    class DummyGame:
        show_inventory = Game.show_inventory

        def __init__(self):
            self.screen = screen
            self.assets = assets
            self.hero = hero
            self.clock = clock

        def open_pause_menu(self):
            return False, self.screen

    game = DummyGame()
    ran = {}

    def fake_run(self):
        self.centre_rect.size = (400, 300)
        self._draw_centre()
        ran["called"] = True
        return False, screen

    monkeypatch.setattr(InventoryScreen, "run", fake_run)

    assert game.show_inventory() is False
    assert ran.get("called")

