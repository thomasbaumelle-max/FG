from __future__ import annotations

import pygame
import theme


class SpellInfoOverlay:
    """Small panel showing spell details."""

    BG = theme.PALETTE.get("background", (40, 42, 50))
    TEXT = theme.PALETTE.get("text", (230, 230, 230))

    def __init__(self, screen: pygame.Surface, lines: list[str]) -> None:
        self.screen = screen
        self.lines = lines
        self.font = theme.get_font(16) or pygame.font.SysFont(None, 16)
        self.rect = pygame.Rect(0, 0, 0, 0)

    # ------------------------------------------------------------------ events
    def handle_event(self, event: pygame.event.Event) -> bool:
        """Return ``True`` to close the overlay."""
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return True
        return False

    # ------------------------------------------------------------------ drawing
    def draw(self) -> None:
        texts = [self.font.render(t, True, self.TEXT) for t in self.lines]
        w = max(t.get_width() for t in texts) + 20 if texts else 100
        h = sum(t.get_height() for t in texts) + 20 if texts else 40
        surface = pygame.Surface((w, h), pygame.SRCALPHA)
        surface.fill((*self.BG, 230))
        theme.draw_frame(surface, surface.get_rect())
        y = 10
        for t in texts:
            surface.blit(t, (10, y))
            y += t.get_height()
        sw, sh = self.screen.get_size()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.rect = pygame.Rect(x, y, w, h)
        self.screen.blit(surface, (x, y))
