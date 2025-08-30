from __future__ import annotations

from typing import List, Iterable
import pygame

# Shared layout constants
SLOT_COUNT = 7
SLOT_PAD = 6
ROW_H = 96
RESBAR_H = 36
TOPBAR_H = 40
GAP = 10

# Shared colours
COLOR_SLOT_BG = (36, 38, 44)
COLOR_SLOT_BD = (80, 80, 90)
COLOR_TEXT = (240, 240, 240)
COLOR_ACCENT = (210, 180, 80)
COLOR_PANEL = (28, 30, 36)

# Shared font name used across town interfaces
FONT_NAME = None


def draw_label(
    surface: pygame.Surface,
    font: pygame.font.Font,
    text: str,
    rect: pygame.Rect,
    *,
    color: tuple[int, int, int] = COLOR_TEXT,
) -> None:
    """Render ``text`` at ``rect.topleft`` using ``font`` onto ``surface``."""
    surface.blit(font.render(text, True, color), (rect.x, rect.y))


def draw_army_row(
    surface: pygame.Surface,
    font: pygame.font.Font,
    font_small: pygame.font.Font,
    army: Iterable,
    rect: pygame.Rect,
    *,
    slot_count: int = SLOT_COUNT,
    slot_pad: int = SLOT_PAD,
    color_slot_bg: tuple[int, int, int] = COLOR_SLOT_BG,
    color_slot_bd: tuple[int, int, int] = COLOR_SLOT_BD,
    color_text: tuple[int, int, int] = COLOR_TEXT,
    color_accent: tuple[int, int, int] = COLOR_ACCENT,
) -> List[pygame.Rect]:
    """Draw ``army`` unit slots within ``rect`` and return their rectangles."""
    slots: List[pygame.Rect] = []
    w = (rect.width - (slot_count + 1) * slot_pad) // slot_count
    h = rect.height - 2 * slot_pad
    y = rect.y + slot_pad
    x = rect.x + slot_pad
    for i in range(slot_count):
        r = pygame.Rect(x, y, w, h)
        slots.append(r)
        pygame.draw.rect(surface, color_slot_bg, r, border_radius=6)
        pygame.draw.rect(surface, color_slot_bd, r, 2, border_radius=6)
        if i < len(army):
            u = army[i]
            name = getattr(u.stats, "name", "Unit")
            count = getattr(u, "count", 1)
            surface.blit(font.render(name, True, color_text), (r.x + 6, r.y + 6))
            surface.blit(
                font_small.render(f"x{count}", True, color_accent),
                (r.right - 28, r.bottom - 20),
            )
        x += w + slot_pad
    return slots


def draw_slot_highlight(
    surface: pygame.Surface,
    rect: pygame.Rect,
    *,
    color: tuple[int, int, int] = COLOR_ACCENT,
    width: int = 3,
) -> None:
    """Draw a highlight around ``rect`` on ``surface``."""
    pygame.draw.rect(surface, color, rect, width, border_radius=6)


def draw_drag_ghost(
    surface: pygame.Surface,
    font: pygame.font.Font,
    font_small: pygame.font.Font,
    unit: object,
    pos: tuple[int, int],
) -> None:
    """Render a translucent ghost of ``unit`` at ``pos`` (top-left)."""
    ghost = pygame.Rect(pos[0], pos[1], 140, 64)
    pygame.draw.rect(surface, (60, 64, 80, 230), ghost, border_radius=6)
    pygame.draw.rect(surface, (120, 120, 140), ghost, 2, border_radius=6)
    name = getattr(unit.stats, "name", "Unit")
    cnt = getattr(unit, "count", 1)
    surface.blit(font.render(name, True, COLOR_TEXT), (ghost.x + 8, ghost.y + 8))
    surface.blit(
        font_small.render(f"x{cnt}", True, COLOR_ACCENT),
        (ghost.x + 8, ghost.y + 34),
    )


__all__ = [
    "SLOT_COUNT",
    "SLOT_PAD",
    "ROW_H",
    "RESBAR_H",
    "TOPBAR_H",
    "GAP",
    "COLOR_SLOT_BG",
    "COLOR_SLOT_BD",
    "COLOR_TEXT",
    "COLOR_ACCENT",
    "COLOR_PANEL",
    "FONT_NAME",
    "draw_label",
    "draw_army_row",
    "draw_slot_highlight",
    "draw_drag_ghost",
]
