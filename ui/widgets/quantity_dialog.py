from __future__ import annotations

"""Small overlay dialog to choose a quantity value.

The dialog is intentionally minimalistic and meant for quick numeric
selection, for example when splitting a unit stack.  It presents ``+`` and
``-`` buttons to adjust the value as well as *OK* and *Cancel* buttons.
``run`` returns the selected value or ``None`` if cancelled.
"""

from typing import Optional

import pygame

import constants, theme

MOUSEBUTTONDOWN = getattr(pygame, "MOUSEBUTTONDOWN", 1)
KEYDOWN = getattr(pygame, "KEYDOWN", 2)


class QuantityDialog:
    """Modal helper used to request a numeric value from the player."""

    WIDTH = 200
    HEIGHT = 120
    BTN_W = 32
    BTN_H = 24

    def __init__(self, screen: pygame.Surface, maximum: int) -> None:
        self.screen = screen
        self.maximum = maximum
        self.value = max(1, minimum(maximum // 2, maximum - 1)) if maximum > 1 else 1
        self.font = theme.get_font(20)
        w, h = screen.get_size()
        self.rect = pygame.Rect(0, 0, self.WIDTH, self.HEIGHT)
        self.rect.center = (w // 2, h // 2)
        y = self.rect.y + 40
        x = self.rect.x + 20
        self.minus_rect = pygame.Rect(x, y, self.BTN_W, self.BTN_H)
        self.plus_rect = pygame.Rect(
            self.rect.right - 20 - self.BTN_W, y, self.BTN_W, self.BTN_H
        )
        self.ok_rect = pygame.Rect(
            self.rect.x + 20,
            self.rect.bottom - 40,
            self.BTN_W * 2,
            self.BTN_H,
        )
        self.cancel_rect = pygame.Rect(
            self.rect.right - 20 - self.BTN_W * 2,
            self.rect.bottom - 40,
            self.BTN_W * 2,
            self.BTN_H,
        )

    # ------------------------------------------------------------------ drawing
    def _draw(self) -> None:
        overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (0, 0))
        pygame.draw.rect(self.screen, theme.PALETTE["panel"], self.rect)
        theme.draw_frame(self.screen, self.rect, "normal")
        if self.font:
            txt = self.font.render(str(self.value), True, theme.PALETTE["text"])
            txt_rect = txt.get_rect()
            txt_rect.center = (self.rect.centerx, self.minus_rect.centery)
            self.screen.blit(txt, txt_rect)
            minus = self.font.render("-", True, theme.PALETTE["text"])
            plus = self.font.render("+", True, theme.PALETTE["text"])
            self.screen.blit(minus, minus.get_rect(center=self.minus_rect.center))
            self.screen.blit(plus, plus.get_rect(center=self.plus_rect.center))
            ok = self.font.render("OK", True, theme.PALETTE["text"])
            cancel = self.font.render("Cancel", True, theme.PALETTE["text"])
            self.screen.blit(ok, ok.get_rect(center=self.ok_rect.center))
            self.screen.blit(cancel, cancel.get_rect(center=self.cancel_rect.center))
        pygame.draw.rect(self.screen, theme.FRAME_COLOURS["normal"], self.minus_rect, 1)
        pygame.draw.rect(self.screen, theme.FRAME_COLOURS["normal"], self.plus_rect, 1)
        pygame.draw.rect(self.screen, theme.FRAME_COLOURS["normal"], self.ok_rect, 1)
        pygame.draw.rect(self.screen, theme.FRAME_COLOURS["normal"], self.cancel_rect, 1)

    # ------------------------------------------------------------------
    def run(self) -> Optional[int]:
        clock = pygame.time.Clock()
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return None
                if event.type == KEYDOWN and getattr(event, "key", None) == pygame.K_ESCAPE:
                    return None
                if event.type == MOUSEBUTTONDOWN and getattr(event, "button", 0) == 1:
                    pos = getattr(event, "pos", (0, 0))
                    if self.minus_rect.collidepoint(pos):
                        self.value = max(1, self.value - 1)
                    elif self.plus_rect.collidepoint(pos):
                        self.value = min(self.maximum - 1, self.value + 1)
                    elif self.ok_rect.collidepoint(pos):
                        return self.value
                    elif self.cancel_rect.collidepoint(pos):
                        return None
            self._draw()
            pygame.display.flip()
            clock.tick(constants.FPS)


def minimum(a: int, b: int) -> int:
    return a if a < b else b
