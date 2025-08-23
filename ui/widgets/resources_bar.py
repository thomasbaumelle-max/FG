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
from typing import Dict, List, Tuple

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
        # Placeholder coloured squares for resource icons
        size = 24
        self.icons: Dict[str, pygame.Surface] = {
            "gold": self._make_icon(constants.YELLOW, size),
            "wood": self._make_icon(constants.GREEN, size),
            "stone": self._make_icon(constants.GREY, size),
            "crystal": self._make_icon(constants.BLUE, size),
        }
        self._deltas: Dict[str, List[_DeltaAnim]] = {name: [] for name in self.resources.as_dict()}
        # Subscribe to resource change events
        EVENT_BUS.subscribe(ON_RESOURCES_CHANGED, self.set_resources)

    # Internal helpers -------------------------------------------------
    def _make_icon(self, colour: Tuple[int, int, int], size: int) -> pygame.Surface:
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        try:
            surf = surf.convert_alpha()
        except Exception:  # pragma: no cover
            pass
        surf.fill(colour)
        if hasattr(pygame, "draw") and hasattr(pygame.draw, "rect"):
            pygame.draw.rect(
                surf, theme.FRAME_COLOURS["normal"], surf.get_rect(), theme.FRAME_WIDTH
            )
        return surf

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
