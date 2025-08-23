from __future__ import annotations

import pygame

import theme


def build_overlay(screen: pygame.Surface, size: tuple[int, int] | None = None):
    """Return a callable that renders a dimmed background with a centred panel.

    The returned function draws the overlay each time it is called and
    returns the panel ``Rect`` for further rendering.
    """
    background = screen.copy()
    if size is None:
        size = (screen.get_width() - 100, screen.get_height() - 100)
    panel_rect = pygame.Rect(0, 0, *size)
    panel_rect.center = (screen.get_width() // 2, screen.get_height() // 2)

    def draw() -> pygame.Rect:
        screen.blit(background, (0, 0))
        dim = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        dim.fill((*theme.PALETTE["background"], 200))
        screen.blit(dim, (0, 0))
        pygame.draw.rect(screen, theme.PALETTE["panel"], panel_rect)
        pygame.draw.rect(screen, theme.PALETTE["accent"], panel_rect, theme.FRAME_WIDTH)
        return panel_rect

    return draw
