import theme
from core.entities import Hero, Unit, SWORDSMAN_STATS
from ui.inventory_screen import InventoryScreen


class DummySurface:
    def __init__(self, size):
        self._size = size
        self.fills = []

    def fill(self, colour, rect=None):
        self.fills.append((colour, rect))

    def get_size(self):
        return self._size

    def blit(self, *args, **kwargs):
        pass


def test_draw_fills_background_with_theme_colour(monkeypatch):
    screen = DummySurface((800, 600))
    hero = Hero(0, 0, [Unit(SWORDSMAN_STATS, 1, "hero")])
    inv = InventoryScreen(screen, {}, hero)

    monkeypatch.setattr(inv, "_draw_resource_bar", lambda: None)
    monkeypatch.setattr(inv, "_draw_tabs", lambda: None)
    monkeypatch.setattr(inv, "_draw_centre", lambda: None)
    monkeypatch.setattr(inv, "_draw_equipment", lambda: None)
    monkeypatch.setattr(inv, "_draw_tooltip", lambda: None)

    inv.draw()

    assert screen.fills[0][0] == theme.PALETTE["background"]

