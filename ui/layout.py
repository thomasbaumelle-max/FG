from __future__ import annotations

"""Simple docking layout helpers for UI components.

The :class:`Layout` class manages a mutable rectangle and allows reserving
areas from its edges using "docking" operations.  Each operation returns the
allocated :class:`pygame.Rect` and shrinks the remaining area accordingly.
Optional margins create gaps between consecutive elements.  This approach keeps
layout calculations declarative and makes it easy to adapt to different screen
sizes.
"""

from dataclasses import dataclass
import pygame


@dataclass
class Layout:
    """Utility to progressively split a rectangle using docking semantics."""

    rect: pygame.Rect

    def dock_left(self, width: int, margin: int = 0) -> pygame.Rect:
        r = pygame.Rect(self.rect.x, self.rect.y, width, self.rect.height)
        self.rect.x += width + margin
        self.rect.width -= width + margin
        return r

    def dock_right(self, width: int, margin: int = 0) -> pygame.Rect:
        r = pygame.Rect(
            self.rect.x + self.rect.width - width, self.rect.y, width, self.rect.height
        )
        self.rect.width -= width + margin
        return r

    def dock_top(self, height: int, margin: int = 0) -> pygame.Rect:
        r = pygame.Rect(self.rect.x, self.rect.y, self.rect.width, height)
        self.rect.y += height + margin
        self.rect.height -= height + margin
        return r

    def dock_bottom(self, height: int, margin: int = 0) -> pygame.Rect:
        r = pygame.Rect(
            self.rect.x,
            self.rect.y + self.rect.height - height,
            self.rect.width,
            height,
        )
        self.rect.height -= height + margin
        return r

    def remaining(self) -> pygame.Rect:
        """Return a copy of the current remaining rectangle."""
        return pygame.Rect(self.rect.x, self.rect.y, self.rect.width, self.rect.height)
