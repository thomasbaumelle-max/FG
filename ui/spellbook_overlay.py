from __future__ import annotations

import pygame
import theme


class SpellbookOverlay:
    """Full-screen overlay displaying the hero's spell list."""

    BG = theme.PALETTE["background"]
    TEXT = theme.PALETTE["text"]

    def __init__(self, screen: pygame.Surface, combat) -> None:
        self.screen = screen
        self.combat = combat
        self.font = theme.get_font(20) or pygame.font.SysFont(None, 20)

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Return ``True`` to close the overlay."""
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_s, pygame.K_ESCAPE):
            return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return True
        return False

    def draw(self) -> None:
        """Draw the overlay to the attached screen."""
        w, h = self.screen.get_size()
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        overlay.fill((*self.BG, 230))
        theme.draw_frame(overlay, overlay.get_rect())

        y = 40
        title = self.font.render("Spellbook", True, self.TEXT)
        overlay.blit(title, ((w - title.get_width()) // 2, 10))
        y += 20
        for name in sorted(self.combat.hero_spells.keys()):
            label = self.font.render(name, True, self.TEXT)
            overlay.blit(label, (40, y))
            y += label.get_height() + 8

        self.screen.blit(overlay, (0, 0))
