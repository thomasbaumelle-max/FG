import types
import pygame

from core.entities import Hero, Unit, SWORDSMAN_STATS, Item, EquipmentSlot, HeroStats
from ui.inventory_screen import InventoryScreen


class DummySurface:
    def __init__(self, size=(10, 10)):
        self._w, self._h = size
        self.blit_calls = []

    def fill(self, *args, **kwargs):
        pass

    def get_size(self):
        return (800, 600)

    def get_width(self):
        return self._w

    def get_height(self):
        return self._h

    def blit(self, surf, pos):
        self.blit_calls.append((surf.get_width(), surf.get_height(), pos))


class Rect:
    def __init__(self, x, y, w, h):
        self.x, self.y, self.width, self.height = x, y, w, h

    @property
    def size(self):
        return (self.width, self.height)

    def collidepoint(self, pos):
        px, py = pos
        return self.x <= px < self.x + self.width and self.y <= py < self.y + self.height

    @property
    def right(self):
        return self.x + self.width

    @property
    def bottom(self):
        return self.y + self.height

    @property
    def topleft(self):
        return (self.x, self.y)


def make_screen_and_hero():
    screen = DummySurface((800, 600))
    hero = Hero(0, 0, [Unit(SWORDSMAN_STATS, 1, "hero")])
    return screen, hero


def test_drag_icon_scaled(monkeypatch):
    screen, hero = make_screen_and_hero()
    icon = DummySurface((20, 20))
    assets = {"icon": icon}
    inv = InventoryScreen(screen, assets, hero)
    item = Item(1, "Hat", EquipmentSlot.HEAD, "common", "icon", False, 1, HeroStats(0, 0, 0, 0, 0, 0, 0, 0, 0))
    inv.drag_item = item
    inv.drag_icon_size = (70, 70)
    monkeypatch.setattr(inv, "_draw_tabs", lambda: None)
    monkeypatch.setattr(inv, "_draw_center_panel", lambda: None)
    monkeypatch.setattr(inv, "_draw_equipment_panel", lambda: None)
    monkeypatch.setattr(inv, "_draw_resbar", lambda: None)
    monkeypatch.setattr(inv, "_draw_tooltip", lambda: None)
    called = []

    def scale(surf, size):
        called.append(size)
        return DummySurface(size)

    monkeypatch.setattr(pygame, "transform", types.SimpleNamespace(scale=scale), raising=False)
    monkeypatch.setattr(pygame, "mouse", types.SimpleNamespace(get_pos=lambda: (0, 0)), raising=False)
    inv.draw()
    assert called[0] == (70, 70)


def test_double_click_equip(monkeypatch):
    screen, hero = make_screen_and_hero()
    item = Item(1, "Hat", EquipmentSlot.HEAD, "common", "", False, 1, HeroStats(0, 0, 0, 0, 0, 0, 0, 0, 0))
    hero.inventory.append(item)
    inv = InventoryScreen(screen, {}, hero)
    inv.active_tab = "inventory"
    inv.item_rects = [(0, Rect(0, 0, 10, 10))]
    times = [0, 100]
    monkeypatch.setattr(pygame.time, "get_ticks", lambda: times.pop(0), raising=False)
    inv._on_lmb_down((1, 1))
    inv._on_lmb_down((1, 1))
    assert hero.equipment[EquipmentSlot.HEAD] is item
    assert item not in hero.inventory
    assert inv.drag_item is None


def test_double_click_unequip(monkeypatch):
    screen, hero = make_screen_and_hero()
    item = Item(1, "Hat", EquipmentSlot.HEAD, "common", "", False, 1, HeroStats(0, 0, 0, 0, 0, 0, 0, 0, 0))
    hero.equipment[EquipmentSlot.HEAD] = item
    inv = InventoryScreen(screen, {}, hero)
    inv.active_tab = "inventory"
    inv.slot_rects = {EquipmentSlot.HEAD: Rect(0, 0, 10, 10)}
    times = [0, 100]
    monkeypatch.setattr(pygame.time, "get_ticks", lambda: times.pop(0), raising=False)
    inv._on_lmb_down((1, 1))
    inv._on_lmb_down((1, 1))
    assert hero.equipment.get(EquipmentSlot.HEAD) is None
    assert hero.inventory[-1] is item
    assert inv.drag_item is None
