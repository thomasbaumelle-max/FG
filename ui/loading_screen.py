from __future__ import annotations

import pygame

import constants
import theme
from state.event_bus import EVENT_BUS, ON_ASSET_LOAD_PROGRESS


class LoadingScreen:
    """Very small loading screen showing asset progress."""

    def __init__(self, screen: pygame.Surface) -> None:
        self.screen = screen
        self.progress = 0.0
        self.done = 0
        self.total = 0

        # Font for progress text. ``theme.get_font`` already performs the
        # necessary ``pygame.font`` initialisation and returns ``None`` when the
        # font subsystem is unavailable (e.g. during headless tests).
        self.font = theme.get_font(20)

        EVENT_BUS.subscribe(ON_ASSET_LOAD_PROGRESS, self._on_progress)
        self._render()

    def _on_progress(self, done: int, total: int) -> None:
        self.done = done
        self.total = total
        self.progress = done / total if total else 1.0
        self._render()

    def _render(self) -> None:
        self.screen.fill(constants.BLACK)
        width = int(self.screen.get_width() * 0.6)
        height = 30
        x = (self.screen.get_width() - width) // 2
        y = (self.screen.get_height() - height) // 2
        pygame.draw.rect(self.screen, constants.WHITE, (x, y, width, height), 2)
        inner = int(width * self.progress)
        if inner > 0:
            pygame.draw.rect(
                self.screen, constants.GREEN, (x + 2, y + 2, inner - 4, height - 4)
            )

        if getattr(self, "font", None):  # pragma: no branch
            percent = int(self.progress * 100)
            text = f"{self.done}/{self.total} – {percent}%"
            surf = self.font.render(text, True, constants.WHITE)
            rect = surf.get_rect()
            rect.midtop = (self.screen.get_width() // 2, y + height + 10)
            self.screen.blit(surf, rect)

        pygame.display.flip()
