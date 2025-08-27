"""Simple overlay window to manage quests."""

from __future__ import annotations

import pygame
from typing import List, Tuple

COLOR_BG = (40, 42, 50)
COLOR_PANEL = (60, 62, 72)
COLOR_BORDER = (110, 110, 120)
COLOR_TEXT = (230, 230, 230)
COLOR_ACCENT = (200, 180, 40)


class QuestOverlay:
    """Display available, active and completed quests.

    The overlay groups quests into categories which can be toggled via
    checkboxes at the top.  Available quests can be accepted, active quests can
    be abandoned.  Completed quests are listed for reference.
    """

    def __init__(self, screen: pygame.Surface, qm: "QuestManager") -> None:
        self.screen = screen
        self.qm = qm
        self.font = pygame.font.Font(None, 24)
        self.font_big = pygame.font.Font(None, 32)
        W, H = screen.get_size()
        self.rect = pygame.Rect(0, 0, 480, 320)
        self.rect.center = (W // 2, H // 2)
        self.running = False
        self.show_available = True
        self.show_active = True
        self.show_completed = True
        self.checkbox_rects: dict[str, pygame.Rect] = {}
        self.cards: List[Tuple[str, str, pygame.Rect]] = []  # (status, id, rect)

    def run(self) -> None:
        clock = pygame.time.Clock()
        self.running = True
        while self.running:
            for evt in pygame.event.get():
                if evt.type == pygame.QUIT:
                    self.running = False
                elif evt.type == pygame.KEYDOWN and evt.key in (pygame.K_ESCAPE, pygame.K_j):
                    self.running = False
                elif evt.type == pygame.MOUSEBUTTONDOWN:
                    self._click(evt.pos)
            self.draw()
            pygame.display.flip()
            clock.tick(60)

    # ------------------------------------------------------------------ drawing
    def draw(self) -> None:
        s = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        s.fill((0, 0, 0, 160))
        self.screen.blit(s, (0, 0))
        pygame.draw.rect(self.screen, COLOR_BG, self.rect, border_radius=8)
        pygame.draw.rect(self.screen, COLOR_BORDER, self.rect, 2, border_radius=8)
        self.screen.blit(
            self.font_big.render("Quests", True, COLOR_TEXT),
            (self.rect.x + 16, self.rect.y + 10),
        )
        self._draw_filters()
        self._draw_lists()

    def _draw_filters(self) -> None:
        y = self.rect.y + 50
        x = self.rect.x + 20
        opts = [
            ("available", "Available", self.show_available),
            ("active", "Active", self.show_active),
            ("completed", "Completed", self.show_completed),
        ]
        self.checkbox_rects.clear()
        for key, label, checked in opts:
            box = pygame.Rect(x, y, 16, 16)
            pygame.draw.rect(self.screen, COLOR_PANEL, box)
            pygame.draw.rect(self.screen, COLOR_BORDER, box, 2)
            if checked:
                pygame.draw.line(self.screen, COLOR_ACCENT, box.topleft, box.bottomright, 2)
                pygame.draw.line(self.screen, COLOR_ACCENT, box.topright, box.bottomleft, 2)
            self.screen.blit(self.font.render(label, True, COLOR_TEXT), (x + 24, y - 4))
            self.checkbox_rects[key] = box
            x += 140

    def _draw_lists(self) -> None:
        self.cards.clear()
        y = self.rect.y + 90
        if self.show_available:
            y = self._draw_section("Available", self.qm.get_available(), "available", y)
        if self.show_active:
            y = self._draw_section("Active", self.qm.get_active(), "active", y)
        if self.show_completed:
            self._draw_section("Completed", self.qm.get_completed(), "completed", y)

    def _draw_section(self, title: str, quests, status: str, y: int) -> int:
        if not quests:
            return y
        self.screen.blit(self.font_big.render(title, True, COLOR_TEXT), (self.rect.x + 16, y))
        y += 32
        for q in quests:
            btn = pygame.Rect(self.rect.x + 20, y, self.rect.width - 40, 32)
            pygame.draw.rect(self.screen, COLOR_PANEL, btn, border_radius=4)
            pygame.draw.rect(self.screen, COLOR_BORDER, btn, 1, border_radius=4)
            reward = q.reward.get("gold") or q.reward.get("artifact", "")
            txt = f"{q.id} → {reward}"
            self.screen.blit(self.font.render(txt, True, COLOR_TEXT), (btn.x + 8, btn.y + 6))
            self.cards.append((status, q.id, btn))
            y += 38
        return y

    # ------------------------------------------------------------------ events
    def _click(self, pos: Tuple[int, int]) -> None:
        for key, rect in self.checkbox_rects.items():
            if rect.collidepoint(pos):
                cur = getattr(self, f"show_{key}")
                setattr(self, f"show_{key}", not cur)
                return
        for status, qid, rect in self.cards:
            if rect.collidepoint(pos):
                if status == "available":
                    self.qm.accept(qid)
                elif status == "active":
                    self.qm.abandon(qid)
                return
        if not self.rect.collidepoint(pos):
            self.running = False
