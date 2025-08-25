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
        enabled: bool = True,
    ) -> None:
        self.rect = rect
        self.icon_id = icon_id
        self.callback = callback
        self.hotkey = hotkey
        self.tooltip = tooltip
        self.hovered = False
        self.pressed = False
        self.enabled = enabled
        self.font = theme.get_font(16)

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

        icon = IconLoader.get(self.icon_id, self.rect.w)
        if icon is not None:
            icon_rect = icon.get_rect()
            icon_rect.center = self.rect.center
            surface.blit(icon, icon_rect)
        elif self.font:
            letter = self.icon_id[:1].upper()
            text = self.font.render(letter, True, theme.PALETTE["text"])
            text_rect = text.get_rect()
            text_rect.center = self.rect.center
            surface.blit(text, text_rect)

    # ------------------------------------------------------------------
    def handle(self, event: pygame.event.Event) -> bool:
        """Process a pygame event returning ``True`` if it was handled."""

        if not self.enabled:
            return False
        if event.type == MOUSEMOTION:
            self.hovered = self.rect.collidepoint(getattr(event, "pos", (0, 0)))
        elif event.type == MOUSEBUTTONDOWN and getattr(event, "button", 0) == 1:
            if self.rect.collidepoint(getattr(event, "pos", (0, 0))):
                self.pressed = True
                return True
        elif event.type == MOUSEBUTTONUP and getattr(event, "button", 0) == 1:
            if self.pressed:
                self.pressed = False
                if self.rect.collidepoint(getattr(event, "pos", (0, 0))):
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

        return self.tooltip
