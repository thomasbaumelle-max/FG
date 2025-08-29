from __future__ import annotations

import os
from typing import List, Tuple

import pygame

import theme
import constants
from loaders import icon_loader as IconLoader


RESOURCE_ORDER = ["gold", "wood", "stone", "crystal"]


def open(
    screen: pygame.Surface,
    game,
    town,
    hero,
    clock: pygame.time.Clock | None = None,
) -> None:
    """Display the market as a modal overlay."""
    if not pygame.display.get_init() or pygame.display.get_surface() is None:
        return

    font = theme.get_font(16) or pygame.font.SysFont(None, 16)
    font_big = theme.get_font(20) or pygame.font.SysFont(None, 20, bold=True)

    give_res = "gold"
    get_res = "wood"
    amount = 1

    panel_rect = pygame.Rect(0, 0, 420, 260)
    panel_rect.center = screen.get_rect().center
    slider_rect = pygame.Rect(0, 0, 200, 14)
    slider_rect.midbottom = (panel_rect.centerx, panel_rect.bottom - 70)
    max_btn = pygame.Rect(panel_rect.x + 20, panel_rect.bottom - 60, 80, 28)
    trade_btn = pygame.Rect(panel_rect.right - 140, panel_rect.bottom - 60, 120, 32)

    size = 32
    gap = 10
    left_x = panel_rect.x + 30
    right_x = panel_rect.centerx + 30
    y = panel_rect.y + 60
    give_icons: List[Tuple[str, pygame.Rect]] = []
    get_icons: List[Tuple[str, pygame.Rect]] = []
    for res in RESOURCE_ORDER:
        r1 = pygame.Rect(left_x, y, size, size)
        r2 = pygame.Rect(right_x, y, size, size)
        give_icons.append((res, r1))
        get_icons.append((res, r2))
        y += size + gap

    background = screen.copy()
    offscreen = pygame.Surface(screen.get_size())
    dirty_rects: List[pygame.Rect] = [offscreen.get_rect()]
    clock = clock or pygame.time.Clock()
    running = True

    def _max_amount() -> int:
        rate = town.market_rates.get((give_res, get_res))
        if rate is None or rate <= 0:
            return 0
        pool = hero.gold if give_res == "gold" else hero.resources.get(give_res, 0)
        return pool // rate

    def _publish_resources() -> None:
        pub = getattr(game, "_publish_resources", None)
        if callable(pub):
            pub()

    def _invalidate(rect: pygame.Rect | None = None) -> None:
        if rect is None:
            rect = offscreen.get_rect()
        dirty_rects.append(rect)

    def _draw_player_resources() -> None:
        x = panel_rect.x + 20
        y = panel_rect.y + 20
        for res in RESOURCE_ORDER:
            icon = IconLoader.get(f"resource_{res}", 24)
            val = hero.gold if res == "gold" else hero.resources.get(res, 0)
            offscreen.blit(icon, (x, y))
            txt = font.render(str(val), True, theme.PALETTE["text"])
            offscreen.blit(txt, (x + 30, y + 4))
            y += 28

    def draw() -> None:
        offscreen.blit(background, (0, 0))
        dim = pygame.Surface(offscreen.get_size(), pygame.SRCALPHA)
        dim.fill((*theme.PALETTE["background"], 200))
        offscreen.blit(dim, (0, 0))
        pygame.draw.rect(offscreen, theme.PALETTE["panel"], panel_rect, border_radius=8)
        pygame.draw.rect(
            offscreen,
            theme.PALETTE["accent"],
            panel_rect,
            theme.FRAME_WIDTH,
            border_radius=8,
        )

        title = font_big.render("Market", True, theme.PALETTE["text"])
        offscreen.blit(title, (panel_rect.x + 16, panel_rect.y + 16))

        _draw_player_resources()

        for res, rect in give_icons:
            icon = IconLoader.get(f"resource_{res}", rect.width)
            offscreen.blit(icon, rect)
            if res == give_res:
                pygame.draw.rect(offscreen, theme.PALETTE["accent"], rect, 2)
        for res, rect in get_icons:
            icon = IconLoader.get(f"resource_{res}", rect.width)
            offscreen.blit(icon, rect)
            if res == get_res:
                pygame.draw.rect(offscreen, theme.PALETTE["accent"], rect, 2)

        pygame.draw.rect(offscreen, theme.PALETTE["accent"], slider_rect, 2)
        max_amt = _max_amount()
        ratio = 0 if max_amt <= 0 else min(1.0, amount / max_amt)
        knob_x = int(slider_rect.x + ratio * slider_rect.width)
        knob = pygame.Rect(knob_x - 5, slider_rect.y - 4, 10, slider_rect.height + 8)
        pygame.draw.rect(offscreen, theme.PALETTE["accent"], knob)
        amt_txt = font.render(str(amount), True, theme.PALETTE["text"])
        offscreen.blit(
            amt_txt,
            (slider_rect.centerx - amt_txt.get_width() // 2, slider_rect.bottom + 6),
        )

        pygame.draw.rect(offscreen, theme.PALETTE["accent"], max_btn, border_radius=4)
        offscreen.blit(
            font.render("Max", True, theme.PALETTE["text"]),
            (max_btn.x + 18, max_btn.y + 6),
        )
        pygame.draw.rect(offscreen, theme.PALETTE["accent"], trade_btn, border_radius=4)
        offscreen.blit(
            font.render("Exchange", True, theme.PALETTE["text"]),
            (trade_btn.x + 12, trade_btn.y + 6),
        )

        rate = town.market_rates.get((give_res, get_res))
        info = "" if rate is None else f"Rate: {rate} {give_res} -> 1 {get_res}"
        info_surf = font.render(info, True, theme.PALETTE["accent"])
        offscreen.blit(info_surf, (panel_rect.x + 20, panel_rect.bottom - 28))

    def _handle_click(pos: Tuple[int, int]) -> None:
        nonlocal give_res, get_res, amount, running
        for res, rect in give_icons:
            if rect.collidepoint(pos):
                give_res = res
                amount = 1
                _invalidate(rect)
                return
        for res, rect in get_icons:
            if rect.collidepoint(pos):
                get_res = res
                amount = 1
                _invalidate(rect)
                return
        if slider_rect.collidepoint(pos):
            rel = (pos[0] - slider_rect.x) / slider_rect.width
            amount = max(1, int(_max_amount() * rel))
            _invalidate(slider_rect)
            return
        if max_btn.collidepoint(pos):
            amount = max(1, _max_amount())
            _invalidate(max_btn)
            return
        if trade_btn.collidepoint(pos):
            if give_res != get_res and town.trade(give_res, get_res, amount, hero):
                _publish_resources()
                running = False
            _invalidate(panel_rect)
            return
        if not panel_rect.collidepoint(pos):
            running = False

    test_mode = "PYTEST_CURRENT_TEST" in os.environ
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
                _invalidate()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                _handle_click(event.pos)
        if dirty_rects:
            draw()
            for r in dirty_rects:
                screen.blit(offscreen, r, r)
            pygame.display.update(dirty_rects)
            dirty_rects.clear()
        if test_mode:
            break
        clock.tick(getattr(constants, "FPS", 30))

