from __future__ import annotations

"""Widget displaying the player's resources.

The bar renders an icon followed by the numerical value for each resource
(type ``gold``, ``wood``, ``stone`` and ``crystal``).  Values are laid out from
left to right starting from the left edge of the provided rectangle.

``set_resources`` updates the displayed values.  When ``show_delta`` is
``True`` the widget will briefly animate any changes using floating text such as
``+50``.  ``update`` must be called every frame with the elapsed time in seconds
for the animation to progress.
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional

import json
import os
from pathlib import Path

import pygame

from .. import constants, theme
from ..state.game_state import PlayerResources
from ..state.event_bus import EVENT_BUS, ON_RESOURCES_CHANGED


@dataclass
class _DeltaAnim:
    """Represents a temporary floating text animation."""

    amount: int
    offset: float = 0.0  # vertical pixel offset
    time_left: float = 1.0  # seconds


class ResourcesBar:
    """Display the player's resources with optional delta animations."""

    def __init__(self, show_delta: bool = False) -> None:
        self.font = theme.get_font(24)
        self.resources = PlayerResources()
        self.show_delta = show_delta

        icons_file = os.path.join("assets", "icons", "icons.json")
        try:
            with open(icons_file, "r", encoding="utf8") as fh:
                self._icon_manifest = json.load(fh)
        except Exception:  # pragma: no cover - file missing or invalid
            self._icon_manifest = {}

        size = 24
        self.icons: Dict[str, pygame.Surface] = {}
        img_mod = getattr(pygame, "image", None)
        transform = getattr(pygame, "transform", None)
        for name in self.resources.as_dict().keys():
            icon = self._load_icon(name, size, img_mod, transform)
            if icon is None:
                icon = self._placeholder_icon(size)
            self.icons[name] = icon

        self._deltas: Dict[str, List[_DeltaAnim]] = {name: [] for name in self.resources.as_dict()}
        # Subscribe to resource change events
        EVENT_BUS.subscribe(ON_RESOURCES_CHANGED, self.set_resources)

    # Internal helpers -------------------------------------------------
    def _placeholder_icon(self, size: int) -> pygame.Surface:
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        try:
            surf = surf.convert_alpha()
        except Exception:  # pragma: no cover
            pass
        return surf

    def _load_icon(
        self,
        name: str,
        size: int,
        img_mod: Optional[object],
        transform: Optional[object],
    ) -> Optional[pygame.Surface]:
        info = self._icon_manifest.get(f"resource_{name}")
        try:
            if isinstance(info, str):
                path = Path("assets/icons") / info
                if img_mod and hasattr(img_mod, "load") and os.path.exists(path):
                    icon = img_mod.load(path)
                    if hasattr(icon, "convert_alpha"):
                        icon = icon.convert_alpha()
                    if transform and hasattr(transform, "scale"):
                        icon = transform.scale(icon, (size, size))
                    return icon
            elif isinstance(info, dict) and "file" in info:
                path = Path("assets") / info["file"]
                if img_mod and hasattr(img_mod, "load") and os.path.exists(path):
                    icon = img_mod.load(path)
                    if hasattr(icon, "convert_alpha"):
                        icon = icon.convert_alpha()
                    if transform and hasattr(transform, "scale"):
                        icon = transform.scale(icon, (size, size))
                    return icon
        except Exception:  # pragma: no cover - loading failed
            return None
        return None

    # Public API -------------------------------------------------------
    def set_resources(self, resources: PlayerResources) -> None:
        """Update displayed resources and create delta animations."""
        if self.show_delta:
            old = self.resources.as_dict()
            new = resources.as_dict()
            for name, value in new.items():
                diff = value - old.get(name, 0)
                if diff:
                    self._deltas[name].append(_DeltaAnim(diff))
        self.resources = resources

    def update(self, dt: float) -> None:
        """Advance delta animations by ``dt`` seconds."""
        if not self.show_delta:
            return
        for anims in self._deltas.values():
            for anim in anims[:]:
                anim.offset -= 30 * dt
                anim.time_left -= dt
                if anim.time_left <= 0:
                    anims.remove(anim)

    def draw(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        """Render the bar within ``rect`` on ``surface``."""
        if not self.font:
            return
        padding = 5
        x = rect.x + padding
        y_center = rect.y + rect.height // 2
        for name in ["gold", "wood", "stone", "crystal"]:
            value = getattr(self.resources, name, 0)
            icon = self.icons.get(name)
            if icon:
                pos = (x, y_center - icon.get_height() // 2)
                surface.blit(icon, pos)
                x += icon.get_width() + 4
            txt_surface = self.font.render(str(value), True, theme.PALETTE["text"])
            surface.blit(txt_surface, (x, y_center - txt_surface.get_height() // 2))
            # Draw delta animations above the value
            if self.show_delta:
                for anim in self._deltas.get(name, []):
                    colour = constants.GREEN if anim.amount > 0 else constants.RED
                    delta_surf = self.font.render(f"{anim.amount:+d}", True, colour)
                    dy = y_center - txt_surface.get_height() // 2 + anim.offset
                    surface.blit(delta_surf, (x, dy))
            x += txt_surface.get_width() + 20
