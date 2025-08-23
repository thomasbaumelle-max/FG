from types import SimpleNamespace

import pygame

from ui.widgets.hero_army_panel import HeroArmyPanel, MOUSEBUTTONDOWN, MOUSEBUTTONUP


from types import SimpleNamespace

import pygame

from ui.widgets.hero_army_panel import HeroArmyPanel, MOUSEBUTTONDOWN, MOUSEBUTTONUP


class DummyUnit:
    def __init__(self, name):
        self.name = name
        self.count = 1
        self.current_hp = 5
        self.stats = SimpleNamespace(max_hp=10)


class DummyHero:
    def __init__(self, units):
        self.army = units


def center(rect: pygame.Rect) -> tuple[int, int]:
    return (rect.x + rect.width // 2, rect.y + rect.height // 2)


def test_drag_and_swap_stacks():
    u1, u2 = DummyUnit("A"), DummyUnit("B")
    hero = DummyHero([u1, u2])
    panel = HeroArmyPanel(hero)
    rect = pygame.Rect(0, 0, 300, 200)
    cell0 = panel._cell_rect(0, rect)
    cell1 = panel._cell_rect(1, rect)

    evt_down = SimpleNamespace(type=MOUSEBUTTONDOWN, button=1, pos=center(cell0))
    panel.handle_event(evt_down, rect)
    evt_up = SimpleNamespace(type=MOUSEBUTTONUP, button=1, pos=center(cell1))
    panel.handle_event(evt_up, rect)

    assert hero.army[0] is u2 and hero.army[1] is u1


def test_callbacks_for_right_click_and_double_click():
    unit = DummyUnit("A")
    hero = DummyHero([unit])
    seen_unit = []
    opened = []

    def on_detail(u):
        seen_unit.append(u)

    def on_open(h):
        opened.append(h)

    panel = HeroArmyPanel(hero, on_unit_detail=on_detail, on_open_hero=on_open)
    rect = pygame.Rect(0, 0, 300, 200)

    cell0 = panel._cell_rect(0, rect)
    evt_right = SimpleNamespace(type=MOUSEBUTTONDOWN, button=3, pos=center(cell0))
    panel.handle_event(evt_right, rect)
    assert seen_unit == [unit]

    portrait = panel._portrait_rect(rect)
    evt_double = SimpleNamespace(
        type=MOUSEBUTTONDOWN, button=1, pos=center(portrait), clicks=2
    )
    panel.handle_event(evt_double, rect)
    assert opened == [hero]
