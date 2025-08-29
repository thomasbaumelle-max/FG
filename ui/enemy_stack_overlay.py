from __future__ import annotations

import pygame
import theme
from typing import List
from core.world import ENEMY_UNIT_IMAGES


class EnemyStackOverlay:
    """Display basic information about enemy stacks on the world map."""

    BG = theme.PALETTE.get("background", (40, 42, 50))
    TEXT = theme.PALETTE.get("text", (230, 230, 230))

    COUNT_LABELS = [
        (4, "a few"),
        (9, "several"),
        (19, "pack"),
        (49, "lots"),
        (99, "horde"),
        (249, "throng"),
        (499, "swarm"),
        (999, "zounds"),
        (float("inf"), "legion"),
    ]

    def __init__(self, screen: pygame.Surface, assets, units) -> None:
        self.screen = screen
        self.assets = assets
        self.units = units
        self.font = theme.get_font(16) or pygame.font.SysFont(None, 16)
        self.rect = pygame.Rect(0, 0, 0, 0)

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return True
        return False

    @classmethod
    def _count_label(cls, count: int) -> str:
        for limit, label in cls.COUNT_LABELS:
            if count <= limit:
                return label
        return cls.COUNT_LABELS[-1][1]

    def draw(self) -> None:
        icon_size = 32
        rows: List[tuple] = []
        max_w = 0
        for unit in self.units:
            img_name = ENEMY_UNIT_IMAGES.get(unit.stats.name, unit.stats.name)
            icon = self.assets.get(img_name)
            if icon:
                try:
                    if icon.get_size() != (icon_size, icon_size):
                        icon = pygame.transform.smoothscale(icon, (icon_size, icon_size))
                except Exception:
                    icon = pygame.transform.scale(icon, (icon_size, icon_size))
            name = self.font.render(unit.stats.name, True, self.TEXT)
            count = self.font.render(self._count_label(unit.count), True, self.TEXT)
            row_h = max(
                icon.get_height() if icon else 0,
                name.get_height(),
                count.get_height(),
            )
            row_w = (
                (icon.get_width() if icon else 0)
                + 8
                + name.get_width()
                + 8
                + count.get_width()
            )
            max_w = max(max_w, row_w)
            rows.append((icon, name, count, row_h))
        width = max_w + 20
        height = sum(r[3] + 6 for r in rows) + 20
        surface = pygame.Surface((width, height), pygame.SRCALPHA)
        surface.fill((*self.BG, 230))
        theme.draw_frame(surface, surface.get_rect())
        y = 10
        for icon, name, count, row_h in rows:
            x = 10
            if icon:
                surface.blit(icon, (x, y + (row_h - icon.get_height()) // 2))
                x += icon.get_width() + 8
            surface.blit(name, (x, y + (row_h - name.get_height()) // 2))
            surface.blit(count, (width - count.get_width() - 10, y + (row_h - count.get_height()) // 2))
            y += row_h + 6
        sw, sh = self.screen.get_size()
        x = (sw - width) // 2
        y = (sh - height) // 2
        self.rect = pygame.Rect(x, y, width, height)
        self.screen.blit(surface, (x, y))
