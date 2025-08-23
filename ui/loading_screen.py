from __future__ import annotations

import pygame

import constants
from state.event_bus import EVENT_BUS, ON_ASSET_LOAD_PROGRESS


class LoadingScreen:
    """Very small loading screen showing asset progress."""

    def __init__(self, screen: pygame.Surface) -> None:
        self.screen = screen
        self.progress = 0.0
        EVENT_BUS.subscribe(ON_ASSET_LOAD_PROGRESS, self._on_progress)
        self._render()

    def _on_progress(self, done: int, total: int) -> None:
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
        pygame.display.flip()
