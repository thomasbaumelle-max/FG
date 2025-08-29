from __future__ import annotations

from typing import Dict
import os
import pygame

from core.entities import RECRUITABLE_UNITS
import theme
from loaders import icon_loader as IconLoader

FONT_NAME = None
COLOR_WARN = theme.PALETTE["warning"]
COLOR_DISABLED = theme.PALETTE["disabled"]

STAT_ICONS = {
    "hp": "stat_hp",
    "attack": "stat_attack_melee",
    "defence_melee": "stat_defence_melee",
    "defence_ranged": "stat_defence_ranged",
    "defence_magic": "stat_defence_magic",
    "speed": "stat_speed",
    "initiative": "stat_initiative",
}

RESOURCE_ICONS = {
    "gold": "resource_gold",
    "wood": "resource_wood",
    "stone": "resource_stone",
    "crystal": "resource_crystal",
}


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
    info = town.get_dwelling_info(struct_id).get(unit_id, (0, 0))
    recruit_max = info[0]
    growth = info[1]
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

    # Main panel placement -------------------------------------------------
    MARGIN = 16
    recruit_rect = pygame.Rect(0, 0, 440, 280)
    screen_rect = screen.get_rect()
    min_w = recruit_rect.width + 2 * MARGIN
    min_h = recruit_rect.height + 2 * MARGIN
    if screen_rect.width < min_w or screen_rect.height < min_h:
        screen_rect = pygame.Rect(0, 0, max(screen_rect.width, min_w), max(screen_rect.height, min_h))
    recruit_rect.center = screen_rect.center

    # Widgets --------------------------------------------------------------
    btn_min = pygame.Rect(0, 0, 28, 28)
    btn_minus = pygame.Rect(0, 0, 28, 28)
    btn_plus = pygame.Rect(0, 0, 28, 28)
    btn_max = pygame.Rect(0, 0, 28, 28)
    slider_rect = pygame.Rect(0, 0, 72, 8)
    btn_buy = pygame.Rect(0, 0, 120, 32)
    btn_close = pygame.Rect(0, 0, 24, 24)

    control_y = recruit_rect.bottom - MARGIN - btn_min.height
    x = recruit_rect.x + MARGIN
    btn_min.topleft = (x, control_y)
    btn_minus.topleft = (btn_min.right + 4, control_y)
    slider_rect.topleft = (btn_minus.right + 4, control_y + (btn_min.height - slider_rect.height) // 2)
    btn_plus.topleft = (slider_rect.right + 8, control_y)
    btn_max.topleft = (btn_plus.right + 4, control_y)
    btn_buy.topleft = (
        recruit_rect.right - btn_buy.width - MARGIN,
        recruit_rect.bottom - MARGIN - btn_buy.height,
    )
    btn_close.topleft = (recruit_rect.right - btn_close.width - MARGIN, recruit_rect.y + MARGIN)
    clock = clock or pygame.time.Clock()
    background = screen.copy()
    running = True
    while running:
        info = town.get_dwelling_info(struct_id).get(unit_id, (0, 0))
        recruit_max = info[0]
        growth = info[1]
        recruit_count = min(recruit_count, recruit_max)
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
        # draw overlay
        screen.blit(background, (0, 0))
        s = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        s.fill((*theme.PALETTE["background"], 160))
        screen.blit(s, (0, 0))
        r = recruit_rect
        pygame.draw.rect(screen, theme.PALETTE["panel"], r, border_radius=8)
        pygame.draw.rect(screen, theme.PALETTE["accent"], r, theme.FRAME_WIDTH, border_radius=8)
        title = f"Recruit {unit_id} – {struct_id.replace('_', ' ').title()}"
        screen.blit(
            font_big.render(title, True, theme.PALETTE["text"]),
            (r.x + MARGIN, r.y + MARGIN),
        )
        portrait_size = 96
        portrait_rect = pygame.Rect(r.x + MARGIN, r.y + 40, portrait_size, portrait_size)
        pygame.draw.rect(screen, theme.PALETTE["accent"], portrait_rect, theme.FRAME_WIDTH)
        inner_portrait = portrait_rect.inflate(-4, -4)
        if recruit_portrait:
            portrait = recruit_portrait
            if portrait.get_size() != inner_portrait.size:
                portrait = pygame.transform.scale(portrait, inner_portrait.size)
            screen.blit(portrait, inner_portrait)
        else:
            pygame.draw.rect(screen, theme.PALETTE["panel"], inner_portrait)
        st = recruit_stats
        if st:
            stats = [
                ("hp", str(st.max_hp)),
                ("attack", f"{st.attack_min}-{st.attack_max}"),
                ("defence_melee", str(st.defence_melee)),
                ("defence_ranged", str(st.defence_ranged)),
                ("defence_magic", str(st.defence_magic)),
                ("speed", str(st.speed)),
                ("initiative", str(st.initiative)),
            ]
            yy = portrait_rect.y
            for key, value in stats:
                icon = IconLoader.get(STAT_ICONS[key], 24)
                screen.blit(icon, (portrait_rect.right + 10, yy))
                txt = font_small.render(value, True, theme.PALETTE["text"])
                screen.blit(
                    txt,
                    (
                        portrait_rect.right + 10 + icon.get_width() + 4,
                        yy + (icon.get_height() - txt.get_height()) // 2,
                    ),
                )
                yy += max(icon.get_height(), txt.get_height()) + 4
        stock_txt = f"Stock: {recruit_max} / +{growth} par semaine"
        screen.blit(
            font_small.render(stock_txt, True, theme.PALETTE["accent"]),
            (portrait_rect.x, portrait_rect.bottom + 4),
        )
        cost = _unit_cost(unit_id, recruit_count)
        can_afford = _can_afford(hero, cost)
        cost_label = font.render(f"Cost x{recruit_count}:", True, theme.PALETTE["text"])
        cost_y = max(portrait_rect.bottom + 24, control_y - 40)
        screen.blit(cost_label, (r.x + MARGIN, cost_y))
        xx = r.x + MARGIN + cost_label.get_width() + 8
        for res, amt in cost.items():
            icon = IconLoader.get(RESOURCE_ICONS.get(res, res), 24)
            screen.blit(icon, (xx, cost_y))
            txt = font.render(str(amt), True, theme.PALETTE["text"] if can_afford else COLOR_WARN)
            screen.blit(txt, (xx + icon.get_width() + 4, cost_y + (icon.get_height() - txt.get_height()) // 2))
            xx += icon.get_width() + txt.get_width() + 12
        pygame.draw.rect(screen, theme.PALETTE["panel"], btn_min, border_radius=4)
        pygame.draw.rect(screen, theme.PALETTE["panel"], btn_minus, border_radius=4)
        pygame.draw.rect(screen, theme.PALETTE["panel"], slider_rect, border_radius=4)
        if recruit_max > 0:
            filled = int(slider_rect.width * recruit_count / recruit_max)
            pygame.draw.rect(
                screen,
                theme.PALETTE["accent"],
                pygame.Rect(
                    slider_rect.x,
                    slider_rect.y,
                    filled,
                    slider_rect.height,
                ),
                border_radius=4,
            )
        pygame.draw.rect(screen, theme.PALETTE["panel"], btn_plus, border_radius=4)
        pygame.draw.rect(screen, theme.PALETTE["panel"], btn_max, border_radius=4)
        btn_col = theme.PALETTE["accent"] if recruit_count > 0 and can_afford else COLOR_DISABLED
        pygame.draw.rect(screen, btn_col, btn_buy, border_radius=4)
        screen.blit(font_small.render("min", True, theme.PALETTE["text"]), (btn_min.x + 3, btn_min.y + 5))
        screen.blit(font_big.render("-", True, theme.PALETTE["text"]), (btn_minus.x + 8, btn_minus.y + 2))
        screen.blit(font_big.render("+", True, theme.PALETTE["text"]), (btn_plus.x + 6, btn_plus.y + 2))
        screen.blit(font_small.render("max", True, theme.PALETTE["text"]), (btn_max.x + 2, btn_max.y + 5))
        screen.blit(font_big.render("Recruit", True, theme.PALETTE["text"]), (btn_buy.x + 12, btn_buy.y + 2))
        pygame.draw.rect(screen, theme.PALETTE["warning"], btn_close, border_radius=4)
        screen.blit(font.render("x", True, theme.PALETTE["text"]), (btn_close.x + 7, btn_close.y + 3))
        pygame.display.update()
        clock.tick(60)
