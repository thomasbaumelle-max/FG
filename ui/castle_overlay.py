from __future__ import annotations

from typing import List, Tuple

import pygame

from core.entities import RECRUITABLE_UNITS
from .town_common import COLOR_TEXT, COLOR_ACCENT
from . import recruit_overlay

FONT_NAME = None
COLOR_DISABLED = (120, 120, 120)


def open(screen: pygame.Surface, game, town, hero, clock) -> None:
    """Open a simple castle recruitment overview."""
    font_big = pygame.font.SysFont(FONT_NAME, 20, bold=True)
    font_small = pygame.font.SysFont(FONT_NAME, 14)
    castle_rect = pygame.Rect(0, 0, 860, 520)
    castle_rect.center = screen.get_rect().center
    castle_unit_cards: List[Tuple[str, pygame.Rect]] = []
    clock = clock or pygame.time.Clock()
    background = screen.copy()
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_b):
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for uid, rc in castle_unit_cards:
                    if rc.collidepoint(event.pos):
                        screen.blit(background, (0, 0))
                        recruit_overlay.open(screen, game, town, hero, clock, "castle", uid)
                        break
        # draw overlay
        screen.blit(background, (0, 0))
        s = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        s.fill((0, 0, 0, 170))
        screen.blit(s, (0, 0))
        r = castle_rect
        pygame.draw.rect(screen, (36, 38, 46), r, border_radius=8)
        pygame.draw.rect(screen, (120, 120, 130), r, 2, border_radius=8)
        screen.blit(
            font_big.render("Castle – Recruitment Overview", True, COLOR_TEXT),
            (r.x + 16, r.y + 10),
        )
        units = town.list_all_recruitables()
        cols = 2
        cw, ch = (r.width - 3 * 16) // cols, 130
        x = r.x + 16
        y = r.y + 48
        castle_unit_cards = []
        for i, uid in enumerate(units):
            card = pygame.Rect(x, y, cw, ch)
            pygame.draw.rect(screen, (48, 50, 58), card, border_radius=8)
            pygame.draw.rect(screen, (100, 100, 110), card, 2, border_radius=8)
            screen.blit(
                font_big.render(uid, True, COLOR_TEXT), (card.x + 10, card.y + 6)
            )
            bh = pygame.Rect(card.x + 10, card.y + 34, 72, 72)
            uh = pygame.Rect(card.right - 82, card.y + 34, 72, 72)
            pygame.draw.rect(screen, (70, 72, 84), bh)
            pygame.draw.rect(screen, (70, 72, 84), uh)
            st = RECRUITABLE_UNITS.get(uid)
            if st:
                lines = [
                    f"HP {st.max_hp}",
                    f"DMG {st.attack_min}-{st.attack_max}",
                    f"DEF M/R/Mg {st.defence_melee}/{st.defence_ranged}/{st.defence_magic}",
                    f"SPD {st.speed}  INIT {st.initiative}",
                ]
                yy = card.y + 34
                for line in lines:
                    screen.blit(
                        font_small.render(line, True, COLOR_TEXT),
                        (bh.right + 10, yy),
                    )
                    yy += 18
            hint = font_small.render("Click to recruit", True, COLOR_ACCENT)
            screen.blit(hint, (card.right - hint.get_width() - 8, card.bottom - 22))
            castle_unit_cards.append((uid, card))
            if (i % cols) == cols - 1:
                x = r.x + 16
                y += ch + 12
            else:
                x += cw + 16
        info = font_small.render("Esc to close", True, COLOR_DISABLED)
        screen.blit(info, (r.right - info.get_width() - 10, r.bottom - 20))
        pygame.display.update()
        clock.tick(60)
