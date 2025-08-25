from __future__ import annotations

"""Load icon surfaces from JSON mapping with caching and reload support."""

import json
from pathlib import Path
from typing import Dict

import pygame

# Load icon mapping once at import time
_ROOT = Path(__file__).resolve().parent.parent
_ASSETS_DIR = _ROOT / "assets"
_ICONS_DIR = _ASSETS_DIR / "icons"

with open(_ICONS_DIR / "icons.json", "r", encoding="utf-8") as f:
    _ICON_MAP: Dict[str, str | dict] = json.load(f)

# Cache for loaded pygame surfaces
_CACHE: Dict[str, pygame.Surface] = {}


def _placeholder_surface() -> pygame.Surface:
    surf = pygame.Surface((1, 1))
    surf.fill((100, 100, 100))
    return surf


def get(icon_id: str, size: int) -> pygame.Surface:
    """Return the surface for ``icon_id`` scaled to ``size``.

    If the icon file is missing or fails to load, a grey placeholder surface
    of the requested size is returned instead.
    """

    if icon_id not in _CACHE:
        entry = _ICON_MAP.get(icon_id)
        filename = None
        if isinstance(entry, str):
            filename = entry
        elif isinstance(entry, dict):
            filename = entry.get("file")
        if isinstance(filename, str):
            path = _ICONS_DIR / filename
            if not path.is_file():
                # Support paths relative to the assets directory
                path = _ASSETS_DIR / filename
            try:
                surf = pygame.image.load(path).convert_alpha()
            except Exception:
                surf = _placeholder_surface()
        else:
            surf = _placeholder_surface()
        _CACHE[icon_id] = surf

    surf = _CACHE[icon_id]
    if surf.get_size() != (size, size):
        return pygame.transform.smoothscale(surf, (size, size))
    return surf


def reload() -> None:
    """Clear the internal surface cache."""

    _CACHE.clear()
