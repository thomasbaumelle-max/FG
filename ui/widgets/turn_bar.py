from __future__ import annotations

"""Widget displaying the current turn as a calendar label."""

from typing import Callable, Optional

import pygame

from .. import theme
from ..state.game_state import GameCalendar
from ..state.event_bus import EVENT_BUS, ON_TURN_END

# Fallback event constant for environments with a pygame stub
MOUSEBUTTONDOWN = getattr(pygame, "MOUSEBUTTONDOWN", 1)


class TurnBar:
    """Display the game's calendar and animate on turn end."""

    def __init__(
        self,
        calendar: Optional[GameCalendar] = None,
        on_click: Optional[Callable[[GameCalendar], None]] = None,
    ) -> None:
        self.calendar = calendar or GameCalendar()
        self.on_click = on_click
        try:
            self.font = pygame.font.Font(None, 24)
        except Exception:  # pragma: no cover - font module missing
            self.font = None
        self._flash_time = 0.0
        EVENT_BUS.subscribe(ON_TURN_END, self._on_turn_end)

    # ------------------------------------------------------------------
    def set_turn(self, turn_index: int) -> None:
        """Update the calendar to ``turn_index``."""

        self.calendar.turn_index = turn_index

    # ------------------------------------------------------------------
    def on_turn_end(self) -> None:
        """Trigger a short flash animation when a turn ends."""

        self._flash_time = 0.5

    # ------------------------------------------------------------------
    def update(self, dt: float) -> None:
        """Advance the flash animation by ``dt`` seconds."""

        if self._flash_time > 0:
            self._flash_time = max(0.0, self._flash_time - dt)

    # ------------------------------------------------------------------
    def handle_event(self, event: pygame.event.Event, rect: pygame.Rect) -> bool:
        """Handle mouse clicks inside ``rect``.

        When the bar is clicked the optional ``on_click`` callback is invoked
        with the current :class:`GameCalendar` and ``True`` is returned.
        """

        if event.type == MOUSEBUTTONDOWN and getattr(event, "button", 0) == 1:
            x, y = event.pos
            if rect.x <= x < rect.x + rect.width and rect.y <= y < rect.y + rect.height:
                if self.on_click:
                    self.on_click(self.calendar)
                return True
        return False

    # ------------------------------------------------------------------
    def _on_turn_end(self, turn_index: int) -> None:
        """Update calendar and start animation from event bus."""

        self.set_turn(turn_index)
        self.on_turn_end()

    # ------------------------------------------------------------------
    def draw(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        """Render the bar and current date label within ``rect``."""
        colour = theme.PALETTE["accent"] if self._flash_time > 0 else theme.PALETTE["panel"]
        surface.fill(colour, rect)
        if not self.font:
            return
        label = self.calendar.label()
        text_surf = self.font.render(label, True, theme.PALETTE["text"])
        surface.blit(text_surf, (
            rect.x + 5,
            rect.y + rect.height // 2 - text_surf.get_height() // 2,
        ))
