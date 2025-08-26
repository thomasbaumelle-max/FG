from __future__ import annotations

"""Simple description bar widget.

This widget displays short textual descriptions supplied by the game when the
mouse hovers over world objects.  ``update`` accepts a tuple containing the
text to display and an optional type identifier.  The type is used to colour the
text based on the mapping in ``TYPE_COLOURS``.  ``draw`` renders the bar within a
given rectangle, truncating the text with an ellipsis if it is too wide to fit.
"""

from typing import Optional, Tuple

import pygame

from .. import constants, theme
from ..state.event_bus import EVENT_BUS, ON_INFO_MESSAGE

# Colours used for different probe types
TYPE_COLOURS = {
    "enemy": constants.RED,
    "building": constants.YELLOW,
    "resource": constants.GREEN,
    "treasure": constants.YELLOW,
    "tile": constants.WHITE,
}


class DescBar:
    """Display a one-line description with colour coding."""

    def __init__(self) -> None:
        # Default font; size chosen to comfortably fit inside UI panels.
        # ``theme.get_font`` gracefully handles environments where the font
        # module is unavailable.
        self.font = theme.get_font(24)
        self.text: str = ""
        self.colour: Tuple[int, int, int] = constants.WHITE
        self._message_timer = 0
        EVENT_BUS.subscribe(ON_INFO_MESSAGE, self._on_message)

    def update(self, info: Optional[Tuple[str, str]]) -> None:
        """Update the displayed text and colour.

        ``info`` is expected to be a tuple ``(name, type)`` where ``type``
        determines the colour.  Passing ``None`` clears the bar.
        """

        if self._message_timer > 0:
            self._message_timer -= 1
            return
        if not info:
            self.text = ""
            return
        name, typ = info[0], info[1] if len(info) > 1 else "tile"
        self.text = name
        self.colour = TYPE_COLOURS.get(typ, constants.WHITE)

    def _on_message(self, text: str, typ: str = "info") -> None:
        self.text = text
        self.colour = TYPE_COLOURS.get(typ, constants.WHITE)
        self._message_timer = 120

    # Internal helper -------------------------------------------------
    def _ellipsize(self, text: str, max_width: int) -> str:
        """Return ``text`` truncated with an ellipsis to fit ``max_width``."""
        ellipsis = "..."
        if not self.font:
            return text
        if self.font.render(text, True, self.colour).get_width() <= max_width:
            return text
        truncated = text
        while truncated and self.font.render(truncated + ellipsis, True, self.colour).get_width() > max_width:
            truncated = truncated[:-1]
        return truncated + ellipsis if truncated else ellipsis

    def draw(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        """Draw the description bar onto ``surface`` within ``rect``."""
        if not self.text or not self.font:
            return
        padded_rect = rect.inflate(-6, -6)
        display_text = self._ellipsize(self.text, padded_rect.width)
        txt_surface = self.font.render(display_text, True, self.colour)
        text_pos = (
            padded_rect.x,
            padded_rect.y + (padded_rect.height - txt_surface.get_height()) // 2,
        )
        surface.blit(txt_surface, text_pos)
