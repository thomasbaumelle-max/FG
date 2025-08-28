from __future__ import annotations

"""Simple clickable icon button with optional hotkey."""

from typing import Callable, Optional

import pygame

from .. import theme
from loaders import icon_loader as IconLoader

# Event type fallbacks for environments using the pygame stub
MOUSEMOTION = getattr(pygame, "MOUSEMOTION", 3)
MOUSEBUTTONDOWN = getattr(pygame, "MOUSEBUTTONDOWN", 1)
MOUSEBUTTONUP = getattr(pygame, "MOUSEBUTTONUP", 5)
KEYDOWN = getattr(pygame, "KEYDOWN", 2)


class IconButton:
    """Display a clickable icon that invokes ``callback`` when activated."""

    def __init__(
        self,
        rect: pygame.Rect,
        icon_id: str,
        callback: Callable[[], None],
        hotkey: Optional[int] = None,
        tooltip: str = "",
        size: tuple[int, int] | None = None,
        enabled: bool = True,
    ) -> None:
        self.rect = rect
        self.icon_id = icon_id
        self.callback = callback
        self.hotkey = hotkey
        self.tooltip = tooltip
        if size is None:
            self.size = (getattr(rect, "width", 0), getattr(rect, "height", 0))
        else:
            self.size = size
        self.hovered = False
        self.pressed = False
        self.enabled = enabled
        self.font = theme.get_font(16)

    # ------------------------------------------------------------------
    def collidepoint(self, pos: tuple[int, int]) -> bool:
        x, y = pos
        return (
            self.rect.x <= x < self.rect.x + self.rect.width
            and self.rect.y <= y < self.rect.y + self.rect.height
        )

    # ------------------------------------------------------------------
    def draw(self, surface: pygame.Surface) -> None:
        """Render the button to ``surface``."""

        bg = theme.PALETTE["panel"]
        if not self.enabled:
            frame_state = "disabled"
        else:
            if self.pressed:
                bg = theme.PALETTE["accent"]
            frame_state = "highlight" if (self.hovered or self.pressed) else "normal"
        surface.fill(bg, self.rect)
        theme.draw_frame(surface, self.rect, frame_state)

        width, height = self.size
        size_min = min(width, height)
        icon = IconLoader.get(self.icon_id, size_min)
        if icon is not None:
            icon_rect = icon.get_rect()
            icon_rect.x = self.rect.x + (self.rect.width - icon_rect.width) // 2
            icon_rect.y = self.rect.y + (self.rect.height - icon_rect.height) // 2
            surface.blit(icon, icon_rect)
        elif self.font:
            letter = self.icon_id[:1].upper()
            text = self.font.render(letter, True, theme.PALETTE["text"])
            text_rect = text.get_rect()
            text_rect.x = self.rect.x + (self.rect.width - text_rect.width) // 2
            text_rect.y = self.rect.y + (self.rect.height - text_rect.height) // 2
            surface.blit(text, text_rect)

    # ------------------------------------------------------------------
    def handle(self, event: pygame.event.Event) -> bool:
        """Process a pygame event returning ``True`` if it was handled."""

        if not self.enabled:
            return False
        if event.type == MOUSEMOTION:
            self.hovered = self.collidepoint(getattr(event, "pos", (0, 0)))
        elif event.type == MOUSEBUTTONDOWN and getattr(event, "button", 0) == 1:
            if self.collidepoint(getattr(event, "pos", (0, 0))):
                self.pressed = True
                return True
        elif event.type == MOUSEBUTTONUP and getattr(event, "button", 0) == 1:
            if self.pressed:
                self.pressed = False
                if self.collidepoint(getattr(event, "pos", (0, 0))):
                    if self.callback:
                        self.callback()
                    return True
        elif event.type == KEYDOWN and self.hotkey is not None:
            if getattr(event, "key", None) == self.hotkey:
                if self.callback:
                    self.callback()
                return True
        return False

    # ------------------------------------------------------------------
    def get_tooltip(self) -> str:
        """Return the tooltip string for the button."""

        if self.hovered:
            return self.tooltip
        mouse_get_pos = getattr(getattr(pygame, "mouse", None), "get_pos", lambda: (0, 0))
        return self.tooltip if self.collidepoint(mouse_get_pos()) else ""
