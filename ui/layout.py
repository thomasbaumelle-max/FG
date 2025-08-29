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

    # ------------------------------------------------------------------
    # Additional helpers
    # ------------------------------------------------------------------
    def split_h(self, ratio: float, margin: int = 0) -> tuple[pygame.Rect, pygame.Rect]:
        """Split the area into two horizontal rectangles.

        Parameters
        ----------
        ratio:
            Fraction of the width to allocate to the left rect.  The right
            rect takes the remaining space.
        margin:
            Gap in pixels inserted between the two rects.
        """

        left_w = int(self.rect.width * ratio)
        right_w = self.rect.width - left_w - margin
        left = pygame.Rect(self.rect.x, self.rect.y, left_w, self.rect.height)
        right = pygame.Rect(
            self.rect.x + left_w + margin, self.rect.y, right_w, self.rect.height
        )
        return left, right

    def anchor(
        self,
        width: int | float,
        height: int | float,
        anchor: str = "topleft",
        margin: int = 0,
    ) -> pygame.Rect:
        """Return a rectangle anchored within the current one.

        ``width`` and ``height`` may be absolute pixel values or floats in the
        range 0..1 to specify a proportion of the parent size.  The ``anchor``
        uses :class:`pygame.Rect` attribute names (``topleft``, ``topright``,
        ``midbottom`` ...).  Margins move the rectangle away from the anchored
        edges.
        """

        if isinstance(width, float):
            width = int(self.rect.width * width)
        if isinstance(height, float):
            height = int(self.rect.height * height)

        parent = self.rect
        x = parent.x
        y = parent.y

        if "left" in anchor:
            x = parent.left
        elif "right" in anchor:
            x = parent.right - width
        elif "center" in anchor or "mid" in anchor:
            x = parent.centerx - width // 2

        if "top" in anchor:
            y = parent.top
        elif "bottom" in anchor:
            y = parent.bottom - height
        elif "center" in anchor or "mid" in anchor:
            y = parent.centery - height // 2

        r = pygame.Rect(x, y, width, height)

        if "left" in anchor:
            r.x += margin
        if "right" in anchor:
            r.x -= margin
        if "top" in anchor:
            r.y += margin
        if "bottom" in anchor:
            r.y -= margin
        return r
