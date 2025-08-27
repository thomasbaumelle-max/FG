from __future__ import annotations

import pygame
from typing import Optional

import constants
import theme
from core.buildings import Building
from core.entities import Hero
from core import economy


def open_panel(
    screen: pygame.Surface,
    building: Building,
    clock: pygame.time.Clock,
    hero: Hero,
    econ_building: Optional[economy.Building] = None,
) -> None:
    """Display a simple information panel for ``building``.

    Shows production output, current garrison and upgrade options.
    The panel uses the shared ``theme`` colours and fonts for consistency.
    """
    font = theme.get_font(24) or pygame.font.SysFont(None, 24)
    small_font = theme.get_font(18) or pygame.font.SysFont(None, 18)

    panel_rect = pygame.Rect(0, 0, 400, 360)
    panel_rect.center = (screen.get_width() // 2, screen.get_height() // 2)
    close_rect = pygame.Rect(0, 0, 100, 30)
    close_rect.center = (panel_rect.centerx, panel_rect.bottom - 40)
    upgrade_rect = pygame.Rect(0, 0, 100, 30)
    upgrade_rect.center = (panel_rect.centerx, panel_rect.bottom - 80)

    background = screen.copy()
    hero_rects: list[pygame.Rect] = []
    garrison_rects: list[pygame.Rect] = []

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for i, rect in enumerate(hero_rects):
                    if rect.collidepoint(event.pos) and i < len(hero.army):
                        unit = hero.army.pop(i)
                        building.garrison = building.garrison or []
                        building.garrison.append(unit)
                        break
                else:
                    for i, rect in enumerate(garrison_rects):
                        if rect.collidepoint(event.pos) and building.garrison and i < len(building.garrison):
                            unit = building.garrison.pop(i)
                            hero.army.append(unit)
                            break
                if close_rect.collidepoint(event.pos):
                    return
                if building.upgrade_cost and upgrade_rect.collidepoint(event.pos):
                    player = economy.PlayerEconomy()
                    player.resources.update(hero.resources)
                    player.resources["gold"] = hero.gold
                    building.upgrade(hero, player, econ_building)
        screen.blit(background, (0, 0))
        dim = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        dim.fill((*theme.PALETTE["background"], 200))
        screen.blit(dim, (0, 0))
        pygame.draw.rect(screen, theme.PALETTE["panel"], panel_rect)
        pygame.draw.rect(screen, theme.PALETTE["accent"], panel_rect, theme.FRAME_WIDTH)

        title = font.render(
            f"{building.name} (Lvl {getattr(building, 'level', 1)})",
            True,
            theme.PALETTE["text"],
        )
        screen.blit(title, (panel_rect.x + 20, panel_rect.y + 20))

        y = panel_rect.y + 60
        prod_label = small_font.render("Production:", True, theme.PALETTE["text"])
        screen.blit(prod_label, (panel_rect.x + 20, y))
        y += 25
        if building.income:
            for res, val in building.income.items():
                line = f"{res}: {val}/day"
                text = small_font.render(line, True, theme.PALETTE["text"])
                screen.blit(text, (panel_rect.x + 40, y))
                y += 20
        elif building.growth_per_week:
            for unit, growth in building.growth_per_week.items():
                line = f"{unit}: +{growth}/week"
                text = small_font.render(line, True, theme.PALETTE["text"])
                screen.blit(text, (panel_rect.x + 40, y))
                y += 20
        else:
            text = small_font.render("None", True, theme.PALETTE["text"])
            screen.blit(text, (panel_rect.x + 40, y))
            y += 20

        hero_rects = []
        garrison_rects = []

        g_label = small_font.render("Garrison:", True, theme.PALETTE["text"])
        screen.blit(g_label, (panel_rect.x + 20, y))
        y += 25
        if building.garrison:
            for idx, unit in enumerate(building.garrison):
                line = f"{unit.count} {unit.stats.name}"
                text = small_font.render(line, True, theme.PALETTE["text"])
                rect = pygame.Rect(panel_rect.x + 40, y, panel_rect.width - 80, 20)
                garrison_rects.append(rect)
                screen.blit(text, rect.topleft)
                y += 20
        else:
            text = small_font.render("None", True, theme.PALETTE["text"])
            screen.blit(text, (panel_rect.x + 40, y))
            y += 20

        h_label = small_font.render("Hero army:", True, theme.PALETTE["text"])
        screen.blit(h_label, (panel_rect.x + 20, y))
        y += 25
        if hero.army:
            for idx, unit in enumerate(hero.army):
                line = f"{unit.count} {unit.stats.name}"
                text = small_font.render(line, True, theme.PALETTE["text"])
                rect = pygame.Rect(panel_rect.x + 40, y, panel_rect.width - 80, 20)
                hero_rects.append(rect)
                screen.blit(text, rect.topleft)
                y += 20
        else:
            text = small_font.render("None", True, theme.PALETTE["text"])
            screen.blit(text, (panel_rect.x + 40, y))
            y += 20

        u_label = small_font.render("Upgrade:", True, theme.PALETTE["text"])
        screen.blit(u_label, (panel_rect.x + 20, y))
        y += 25
        if building.upgrade_cost:
            cost_line = ", ".join(
                f"{res}: {amt}" for res, amt in building.upgrade_cost.items()
            )
            text = small_font.render(f"Cost: {cost_line}", True, theme.PALETTE["text"])
            screen.blit(text, (panel_rect.x + 40, y))
            y += 30
            pygame.draw.rect(screen, theme.PALETTE["accent"], upgrade_rect)
            pygame.draw.rect(screen, theme.PALETTE["text"], upgrade_rect, theme.FRAME_WIDTH)
            up_text = small_font.render("Upgrade", True, theme.PALETTE["text"])
            screen.blit(up_text, up_text.get_rect(center=upgrade_rect.center))
        else:
            text = small_font.render("No upgrades", True, theme.PALETTE["text"])
            screen.blit(text, (panel_rect.x + 40, y))
            y += 20

        pygame.draw.rect(screen, theme.PALETTE["accent"], close_rect)
        pygame.draw.rect(screen, theme.PALETTE["text"], close_rect, theme.FRAME_WIDTH)
        close_text = small_font.render("Close", True, theme.PALETTE["text"])
        screen.blit(close_text, close_text.get_rect(center=close_rect.center))

        pygame.display.flip()
        clock.tick(getattr(constants, "FPS", 30))
