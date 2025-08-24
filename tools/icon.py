from __future__ import annotations

"""Utility functions for working with sprite sheet based icons.

The project stores certain icon sets (such as the Red Knights skills) as
spritesheets arranged in a regular grid.  ``get_icon`` extracts a single icon
from such a sheet given the coordinates within that grid.  The function is
resilient: if the sheet cannot be loaded it returns a 1×1 transparent surface
so callers can still proceed in tests without the actual image assets.
"""

from typing import Tuple
import os

try:  # pragma: no cover - used only when pygame is available
    import pygame
except Exception:  # pragma: no cover - fallback when pygame missing
    pygame = None


def get_icon(sheet_path: str, coords: Tuple[int, int], grid: int = 4):
    """Return a :class:`pygame.Surface` for the icon at ``coords``.

    Parameters
    ----------
    sheet_path:
        Path to the sprite sheet image.  The sheet is assumed to contain a
        ``grid`` by ``grid`` arrangement of equally sized icons.
    coords:
        ``(x, y)`` position of the desired icon within the grid where ``(0, 0)``
        refers to the top-left cell.
    grid:
        Number of columns/rows in the sheet.  Default is ``4`` for a 4×4 grid.
    """

    if not pygame:  # pragma: no cover - pygame unavailable
        return None

    x, y = coords
    try:
        sheet = pygame.image.load(sheet_path).convert_alpha()
        w, h = sheet.get_size()
        cell_w = w // grid
        cell_h = h // grid
        rect = pygame.Rect(x * cell_w, y * cell_h, cell_w, cell_h)
        icon = sheet.subsurface(rect).copy()
        return icon
    except Exception:  # pragma: no cover - missing file or load failure
        surf = pygame.Surface((1, 1), pygame.SRCALPHA)
        try:
            surf = surf.convert_alpha()
        except Exception:
            pass
        return surf
