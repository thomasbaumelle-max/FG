from __future__ import annotations

from typing import Dict
import os
import pygame

from core.entities import RECRUITABLE_UNITS
from .town_common import COLOR_TEXT, COLOR_ACCENT

FONT_NAME = None
COLOR_WARN = (210, 90, 70)
COLOR_DISABLED = (120, 120, 120)


def _unit_cost(unit_id: str, count: int) -> Dict[str, int]:
    try:
        import constants

        base = dict(getattr(constants, "UNIT_RECRUIT_COSTS", {}).get(unit_id, {}))
    except Exception:
        base = {}
    return {k: v * count for k, v in base.items()}


def _can_afford(hero, cost: Dict[str, int]) -> bool:
    g = cost.get("gold", 0)
    if hero.gold < g:
        return False
    for k, v in cost.items():
        if k == "gold":
            continue
        if hero.resources.get(k, 0) < v:
            return False
    return True


def open(
    screen: pygame.Surface,
    game,
    town,
    hero,
    clock,
    struct_id: str,
    unit_id: str,
) -> None:
    """Open the recruitment overlay for a specific unit."""
    font = pygame.font.SysFont(FONT_NAME, 18)
    font_small = pygame.font.SysFont(FONT_NAME, 14)
    font_big = pygame.font.SysFont(FONT_NAME, 20, bold=True)
    recruit_max = town.stock.get(unit_id, 0)
    recruit_count = min(1, recruit_max)
    portrait_path = os.path.join(
        "assets",
        "units",
        "portrait",
        f"{unit_id.lower()}_portrait.png",
    )
    try:
        recruit_portrait = pygame.image.load(portrait_path).convert_alpha()
    except Exception:
        recruit_portrait = None
    recruit_stats = RECRUITABLE_UNITS.get(unit_id)
    recruit_rect = pygame.Rect(0, 0, 360, 190)
    recruit_rect.center = screen.get_rect().center
    btn_min = pygame.Rect(0, 0, 28, 28)
    btn_minus = pygame.Rect(0, 0, 28, 28)
    btn_plus = pygame.Rect(0, 0, 28, 28)
    btn_max = pygame.Rect(0, 0, 28, 28)
    slider_rect = pygame.Rect(0, 0, 72, 8)
    btn_buy = pygame.Rect(0, 0, 120, 32)
    btn_close = pygame.Rect(0, 0, 24, 24)
    y = recruit_rect.y + recruit_rect.height - 44
    x = recruit_rect.x + 16
    btn_min.topleft = (x, y)
    btn_minus.topleft = (x + 32, y)
    slider_rect.topleft = (x + 64, y + 10)
    btn_plus.topleft = (slider_rect.right + 8, y)
    btn_max.topleft = (btn_plus.right + 4, y)
    btn_buy.topleft = (recruit_rect.right - btn_buy.width - 16, y)
    btn_close.topleft = (recruit_rect.right - 28, recruit_rect.y + 8)
    clock = clock or pygame.time.Clock()
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_b):
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if btn_close.collidepoint(event.pos):
                    running = False
                elif btn_min.collidepoint(event.pos):
                    recruit_count = 0
                elif btn_minus.collidepoint(event.pos):
                    recruit_count = max(0, recruit_count - 1)
                elif btn_plus.collidepoint(event.pos):
                    recruit_count = min(recruit_max, recruit_count + 1)
                elif btn_max.collidepoint(event.pos):
                    recruit_count = recruit_max
                elif (
                    slider_rect.collidepoint(event.pos)
                    and slider_rect.width > 0
                    and recruit_max > 0
                ):
                    ratio = (event.pos[0] - slider_rect.x) / slider_rect.width
                    recruit_count = max(0, min(recruit_max, int(recruit_max * ratio + 0.5)))
                elif btn_buy.collidepoint(event.pos):
                    cost = _unit_cost(unit_id, recruit_count)
                    if recruit_count > 0 and _can_afford(hero, cost):
                        if town.recruit_units(unit_id, hero, recruit_count, town.garrison):
                            if hasattr(hero, "apply_bonuses_to_army"):
                                hero.apply_bonuses_to_army()
                            if hasattr(game, "_publish_resources"):
                                game._publish_resources()
                            running = False
        # draw overlay
        s = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        s.fill((0, 0, 0, 160))
        screen.blit(s, (0, 0))
        r = recruit_rect
        pygame.draw.rect(screen, (40, 42, 50), r, border_radius=8)
        pygame.draw.rect(screen, (110, 110, 120), r, 2, border_radius=8)
        title = f"Recruit {unit_id} – {struct_id.replace('_', ' ').title()}"
        screen.blit(font_big.render(title, True, COLOR_TEXT), (r.x + 16, r.y + 12))
        portrait_rect = pygame.Rect(r.x + 16, r.y + 40, 72, 72)
        if recruit_portrait:
            portrait = recruit_portrait
            if portrait.get_size() != (72, 72):
                portrait = pygame.transform.scale(portrait, (72, 72))
            screen.blit(portrait, portrait_rect)
        else:
            pygame.draw.rect(screen, (70, 72, 84), portrait_rect)
        st = recruit_stats
        if st:
            lines = [
                f"HP {st.max_hp}",
                f"DMG {st.attack_min}-{st.attack_max}",
                f"DEF M/R/Mg {st.defence_melee}/{st.defence_ranged}/{st.defence_magic}",
                f"SPD {st.speed}  INIT {st.initiative}",
            ]
            yy = portrait_rect.y
            for line in lines:
                screen.blit(
                    font_small.render(line, True, COLOR_TEXT),
                    (portrait_rect.right + 10, yy),
                )
                yy += 18
        cost = _unit_cost(unit_id, recruit_count)
        cost_str = " / ".join(f"{k}:{v}" for k, v in cost.items()) if cost else "Free"
        can_afford = _can_afford(hero, cost)
        col = COLOR_TEXT if can_afford else COLOR_WARN
        screen.blit(
            font.render(f"Cost x{recruit_count}: {cost_str}", True, col),
            (r.x + 16, r.y + 120),
        )
        pygame.draw.rect(screen, (60, 62, 72), btn_min, border_radius=4)
        pygame.draw.rect(screen, (60, 62, 72), btn_minus, border_radius=4)
        pygame.draw.rect(screen, (60, 62, 72), slider_rect, border_radius=4)
        if recruit_max > 0:
            filled = int(slider_rect.width * recruit_count / recruit_max)
            pygame.draw.rect(
                screen,
                (80, 160, 80),
                pygame.Rect(
                    slider_rect.x,
                    slider_rect.y,
                    filled,
                    slider_rect.height,
                ),
                border_radius=4,
            )
        pygame.draw.rect(screen, (60, 62, 72), btn_plus, border_radius=4)
        pygame.draw.rect(screen, (60, 62, 72), btn_max, border_radius=4)
        btn_col = (70, 140, 70) if recruit_count > 0 and can_afford else COLOR_DISABLED
        pygame.draw.rect(screen, btn_col, btn_buy, border_radius=4)
        screen.blit(font_small.render("min", True, COLOR_TEXT), (btn_min.x + 3, btn_min.y + 5))
        screen.blit(font_big.render("-", True, COLOR_TEXT), (btn_minus.x + 8, btn_minus.y + 2))
        screen.blit(font_big.render("+", True, COLOR_TEXT), (btn_plus.x + 6, btn_plus.y + 2))
        screen.blit(font_small.render("max", True, COLOR_TEXT), (btn_max.x + 2, btn_max.y + 5))
        screen.blit(font_big.render("Recruit", True, COLOR_TEXT), (btn_buy.x + 12, btn_buy.y + 2))
        pygame.draw.rect(screen, (90, 50, 50), btn_close, border_radius=4)
        screen.blit(font.render("x", True, COLOR_TEXT), (btn_close.x + 7, btn_close.y + 3))
        pygame.display.update()
        clock.tick(60)
