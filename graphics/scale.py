"""Utility helpers for scaling Pygame surfaces."""

from __future__ import annotations

from typing import Tuple, Optional

import pygame


def scale_surface(surface: pygame.Surface, size: Tuple[int, int], smooth: bool = False) -> pygame.Surface:
    """Return a scaled copy of ``surface``.

    Parameters
    ----------
    surface:
        The :class:`pygame.Surface` to resize.
    size:
        Target ``(width, height)`` in pixels.
    smooth:
        If ``True`` use :func:`pygame.transform.smoothscale` for better
        quality when shrinking high-resolution art.  When ``False`` the
        basic :func:`pygame.transform.scale` is used, preserving crisp edges
        in pixel art.
    """
    if not hasattr(pygame, "transform"):
        return surface
    if smooth:
        return pygame.transform.smoothscale(surface, size)
    return pygame.transform.scale(surface, size)


def scale_with_anchor(
    surface: pygame.Surface,
    size: Tuple[int, int],
    anchor_px: Optional[Tuple[int, int]] = None,
    smooth: bool = False,
) -> Tuple[pygame.Surface, Optional[Tuple[int, int]]]:
    """Scale ``surface`` and ``anchor_px`` by the same factor.

    Parameters
    ----------
    surface:
        Source image to resize.
    size:
        Target ``(width, height)`` in pixels.
    anchor_px:
        Optional ``(x, y)`` anchor measured on the original surface.  When
        provided it is multiplied by the same scale factor applied to the
        surface and the adjusted coordinates are returned.
    smooth:
        Forwarded to :func:`scale_surface`.
    """

    scaled = scale_surface(surface, size, smooth)

    if anchor_px is None:
        return scaled, None

    w = surface.get_width() or 1
    scale = size[0] / w
    ax, ay = anchor_px
    return scaled, (int(ax * scale), int(ay * scale))
