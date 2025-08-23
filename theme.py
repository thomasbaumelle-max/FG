"""UI theme definitions for a Heroes-like style.

Centralises colours, frame styles and font helper so widgets can remain
visually consistent.  This module avoids hard-coding palette information
throughout the code base and provides a small abstraction for fonts so tests
can run even when pygame's font subsystem is unavailable.
"""

from __future__ import annotations

try:  # pragma: no cover - optional when pygame missing
    import pygame
except Exception:  # pragma: no cover
    pygame = None

# ---------------------------------------------------------------------------
# Colour palette
# ---------------------------------------------------------------------------
# Slightly saturated blue/brown scheme reminiscent of classic Heroes games
PALETTE = {
    "background": (20, 20, 40),  # dark blue background
    "panel": (60, 50, 40),       # brown panels
    "accent": (210, 180, 90),    # golden highlights
    "text": (230, 230, 230),     # near white text
}

# Frame colours for different UI states
FRAME_COLOURS = {
    "normal": (150, 120, 90),
    "highlight": (255, 215, 0),
    "disabled": (110, 110, 110),
}

# Default frame thickness used by widgets
FRAME_WIDTH = 2


def get_font(size: int = 16):
    """Return the default UI font or ``None`` when unavailable."""
    if pygame is None:
        return None
    try:  # pragma: no cover - depends on system fonts
        return pygame.font.Font(None, size)
    except Exception:  # pragma: no cover - font module missing
        return None


# ---------------------------------------------------------------------------
# Frame rendering
# ---------------------------------------------------------------------------
_FRAME_CACHE: dict[tuple[int, int, int], tuple["pygame.Surface", "pygame.Surface", "pygame.Surface"]] = {}


def _slice_surfaces(colour: tuple[int, int, int]):
    """Return cached 9-slice surfaces for ``colour``."""
    if pygame is None:
        raise RuntimeError("pygame required for drawing frames")
    if colour in _FRAME_CACHE:
        return _FRAME_CACHE[colour]
    w = FRAME_WIDTH
    corner = pygame.Surface((w, w), pygame.SRCALPHA)
    corner.fill(colour)
    horiz = pygame.Surface((1, w), pygame.SRCALPHA)
    horiz.fill(colour)
    vert = pygame.Surface((w, 1), pygame.SRCALPHA)
    vert.fill(colour)
    _FRAME_CACHE[colour] = (corner, horiz, vert)
    return corner, horiz, vert


def draw_frame(surface: "pygame.Surface", rect: "pygame.Rect", state: str = "normal") -> None:
    """Draw a simple 9-slice style frame around ``rect`` on ``surface``."""
    if pygame is None:
        return
    colour = FRAME_COLOURS.get(state, FRAME_COLOURS["normal"])
    corner, horiz, vert = _slice_surfaces(colour)
    w = FRAME_WIDTH
    transform = getattr(pygame, "transform", None)
    if not transform or not hasattr(transform, "scale"):
        draw = getattr(getattr(pygame, "draw", None), "rect", None)
        if draw:
            draw(surface, colour, rect, w)
        return
    # Edges
    if rect.width > 2 * w:
        top = transform.scale(horiz, (rect.width - 2 * w, w))
        bottom = transform.scale(horiz, (rect.width - 2 * w, w))
        surface.blit(top, (rect.left + w, rect.top))
        surface.blit(bottom, (rect.left + w, rect.bottom - w))
    if rect.height > 2 * w:
        left = transform.scale(vert, (w, rect.height - 2 * w))
        right = transform.scale(vert, (w, rect.height - 2 * w))
        surface.blit(left, (rect.left, rect.top + w))
        surface.blit(right, (rect.right - w, rect.top + w))
    # Corners
    surface.blit(corner, rect.topleft)
    surface.blit(transform.flip(corner, True, False), (rect.right - w, rect.top))
    surface.blit(transform.flip(corner, False, True), (rect.left, rect.bottom - w))
    surface.blit(transform.flip(corner, True, True), (rect.right - w, rect.bottom - w))
