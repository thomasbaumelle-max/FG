from __future__ import annotations

from typing import List, Tuple

import pygame

from core.entities import Hero, HeroStats, Unit, RECRUITABLE_UNITS
from .town_common import COLOR_TEXT, COLOR_ACCENT

FONT_NAME = None


def open(screen: pygame.Surface, game, town, hero, clock) -> None:
    """Open the tavern overlay allowing hero recruitment."""
    font = pygame.font.SysFont(FONT_NAME, 18)
    font_small = pygame.font.SysFont(FONT_NAME, 14)
    font_big = pygame.font.SysFont(FONT_NAME, 20, bold=True)
    tavern_rect = pygame.Rect(0, 0, 420, 260)
    tavern_rect.center = screen.get_rect().center
    tavern_cards: List[Tuple[int, pygame.Rect]] = []
    tavern_msg = ""
    tavern_heroes = [
        {
            "name": "Bran",
            "cost": 1500,
            "stats": HeroStats(1, 1, 0, 0, 0, 0, 0, 0, 0),
            "army": [Unit(RECRUITABLE_UNITS["swordsman"], 10, "hero")],
        },
        {
            "name": "Luna",
            "cost": 2500,
            "stats": HeroStats(0, 0, 1, 1, 0, 0, 0, 0, 0),
            "army": [Unit(RECRUITABLE_UNITS["archer"], 10, "hero")],
        },
    ]
    clock = clock or pygame.time.Clock()
    background = screen.copy()
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_b):
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                handled = False
                for idx, btn in tavern_cards:
                    if btn.collidepoint(event.pos):
                        info = tavern_heroes[idx]
                        cost = info["cost"]
                        if hero.gold >= cost:
                            hero.gold -= cost
                            new_hero = Hero(
                                town.origin[0],
                                town.origin[1],
                                info["army"],
                                info["stats"],
                            )
                            new_hero.name = info["name"]
                            game.add_hero(new_hero)
                            if hasattr(game, "_publish_resources"):
                                game._publish_resources()
                            running = False
                        else:
                            tavern_msg = "Not enough gold"
                        handled = True
                        break
                if not handled and not tavern_rect.collidepoint(event.pos):
                    running = False
        # draw
        screen.blit(background, (0, 0))
        s = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        s.fill((0, 0, 0, 160))
        screen.blit(s, (0, 0))
        r = tavern_rect
        pygame.draw.rect(screen, (40, 42, 50), r, border_radius=8)
        pygame.draw.rect(screen, (110, 110, 120), r, 2, border_radius=8)
        screen.blit(font_big.render("Tavern – Hire Heroes", True, COLOR_TEXT), (r.x + 16, r.y + 12))
        card_w, card_h, gap = 180, 180, 20
        x = r.x + 20
        y = r.y + 60
        tavern_cards = []
        for idx, info in enumerate(tavern_heroes):
            card = pygame.Rect(x + idx * (card_w + gap), y, card_w, card_h)
            pygame.draw.rect(screen, (60, 62, 72), card, border_radius=6)
            pygame.draw.rect(screen, (110, 110, 120), card, 2, border_radius=6)
            portrait = pygame.Rect(card.x + 8, card.y + 8, 64, 64)
            pygame.draw.rect(screen, (80, 80, 90), portrait)
            pygame.draw.rect(screen, (110, 110, 120), portrait, 2)
            name = info["name"]
            cost = info["cost"]
            screen.blit(font.render(name, True, COLOR_TEXT), (card.x + 8, card.y + 80))
            screen.blit(
                font_small.render(f"Cost: {cost}", True, COLOR_ACCENT),
                (card.x + 8, card.y + 110),
            )
            btn = pygame.Rect(card.x + 40, card.bottom - 40, 100, 28)
            pygame.draw.rect(screen, (70, 140, 70), btn, border_radius=4)
            screen.blit(font_small.render("Hire", True, COLOR_TEXT), (btn.x + 28, btn.y + 6))
            tavern_cards.append((idx, btn))
        if tavern_msg:
            msg_surf = font_small.render(tavern_msg, True, (210, 90, 70))
            msg_rect = msg_surf.get_rect()
            msg_rect.midtop = (r.centerx, r.bottom - 30)
            screen.blit(msg_surf, msg_rect)
        pygame.display.update()
        clock.tick(60)
