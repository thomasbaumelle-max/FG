from types import SimpleNamespace

import pygame
import theme

from core.entities import Unit, SWORDSMAN_STATS
from ui import combat_summary


class DummyScreen:
    def __init__(self, size):
        self._w, self._h = size
        self.fills = []
        self.blit_calls = []

    def get_width(self):
        return self._w

    def get_height(self):
        return self._h

    def fill(self, colour, rect=None):
        self.fills.append((colour, rect))

    def blit(self, _surf, dest):
        self.blit_calls.append(dest)

    def copy(self):
        return self

    def get_size(self):
        return (self._w, self._h)


def _run_show_stats(monkeypatch, simple_combat):
    screen = DummyScreen((800, 600))
    hero = Unit(SWORDSMAN_STATS, 1, "hero")
    enemy = Unit(SWORDSMAN_STATS, 1, "enemy")
    combat = simple_combat([hero], [enemy], screen=screen)

    image_calls: list[Unit] = []

    def fake_get_unit_image(*a, **k):
        image_calls.append(a[0])
        return None

    monkeypatch.setattr(combat, "get_unit_image", fake_get_unit_image)

    rendered: list[str] = []

    class DummyTextSurface:
        def get_rect(self, **kwargs):
            center = kwargs.get("center", (0, 0))
            return pygame.Rect(center[0] - 5, center[1] - 5, 10, 10)

    def SysFont(_name, _size):
        class DummyFont:
            def render(self, text, _aa, _colour):
                rendered.append(text)
                return DummyTextSurface()

            def size(self, text):
                return (len(text) * 10, 10)

        return DummyFont()

    monkeypatch.setattr(pygame.font, "SysFont", SysFont)
    monkeypatch.setattr(pygame, "MOUSEBUTTONDOWN", 1, raising=False)
    monkeypatch.setattr(pygame, "QUIT", 2, raising=False)

    events = [
        [],
        [
            SimpleNamespace(type=pygame.MOUSEBUTTONDOWN, button=1, pos=(400, 560))
        ],
    ]

    def fake_get():
        return events.pop(0) if events else []

    monkeypatch.setattr(pygame.event, "get", fake_get)
    monkeypatch.setattr(pygame.display, "flip", lambda: None)
    monkeypatch.setattr(pygame.draw, "rect", lambda *a, **k: None)

    class Rect:
        def __init__(self, x, y, w, h):
            self.x, self.y, self.width, self.height = x, y, w, h

        def collidepoint(self, pos):
            x, y = pos
            return self.x <= x <= self.x + self.width and self.y <= y <= self.y + self.height

        @property
        def centerx(self):
            return self.x + self.width // 2

        @property
        def centery(self):
            return self.y + self.height // 2

        @property
        def center(self):
            return (self.centerx, self.centery)

        @center.setter
        def center(self, pos):
            cx, cy = pos
            self.x = cx - self.width // 2
            self.y = cy - self.height // 2

        @property
        def bottom(self):
            return self.y + self.height

        @property
        def right(self):
            return self.x + self.width

    monkeypatch.setattr(pygame, "Rect", Rect)

    def fake_overlay(_screen):
        def draw():
            return Rect(50, 50, 700, 500)

        return draw

    monkeypatch.setattr(combat_summary, "build_overlay", fake_overlay)

    combat.show_stats()
    return screen, rendered, image_calls


def test_show_stats_no_background_fill(monkeypatch, simple_combat):
    screen, _, _ = _run_show_stats(monkeypatch, simple_combat)
    assert screen.fills == []


def test_show_stats_renders_heading(monkeypatch, simple_combat):
    _, rendered, _ = _run_show_stats(monkeypatch, simple_combat)
    assert any(text in ("Victoire", "Défaite") for text in rendered)


def test_show_stats_columns(monkeypatch, simple_combat):
    screen, _, _ = _run_show_stats(monkeypatch, simple_combat)
    width = screen.get_width()
    xs = [dest[0] for dest in screen.blit_calls if isinstance(dest, tuple)]
    assert any(x < width // 2 for x in xs)
    assert any(x > width // 2 for x in xs)


def test_reward_section_before_table(monkeypatch, simple_combat):
    _, rendered, _ = _run_show_stats(monkeypatch, simple_combat)
    assert rendered.index("Expérience gagnée : 0") < rendered.index("Unité")


def test_header_uses_unit_images(monkeypatch, simple_combat):
    _, _, calls = _run_show_stats(monkeypatch, simple_combat)
    # One hero and one enemy unit -> header and table rows for each side
    assert len(calls) == 4

