"""Utility helpers for scaling Pygame surfaces."""

from __future__ import annotations

from collections import OrderedDict
from typing import Optional, Tuple
import weakref

import pygame


# Small LRU cache for scaled surfaces.  Keys are ``(id(surface), size, smooth)``
# and values store a weak reference to the original surface along with the
# scaled copy.  The weak references automatically remove stale entries when the
# source surface is garbage-collected.  A tiny ``maxsize`` keeps memory usage
# predictable while still caching common scaling operations.
_SCALE_CACHE: OrderedDict[tuple, tuple] = OrderedDict()
_SCALE_CACHE_MAX = 16


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

    key = (id(surface), size, smooth)
    cached = _SCALE_CACHE.get(key)
    if cached is not None:
        surf_ref, scaled = cached
        if surf_ref() is surface:
            _SCALE_CACHE.move_to_end(key)
            return scaled
        # Surface was replaced or collected; drop stale entry
        _SCALE_CACHE.pop(key, None)

    if smooth:
        scaled = pygame.transform.smoothscale(surface, size)
    else:
        scaled = pygame.transform.scale(surface, size)

    def _remove(_ref, *, _key=key):
        _SCALE_CACHE.pop(_key, None)

    _SCALE_CACHE[key] = (weakref.ref(surface, _remove), scaled)
    _SCALE_CACHE.move_to_end(key)
    if len(_SCALE_CACHE) > _SCALE_CACHE_MAX:
        _SCALE_CACHE.popitem(last=False)

    return scaled


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
