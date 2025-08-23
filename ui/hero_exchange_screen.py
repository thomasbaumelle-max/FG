from __future__ import annotations
from typing import List, Tuple, Optional
import pygame

from core.entities import UnitCarrier

SLOT_COUNT = 7
SLOT_PAD = 6
ROW_H = 96
GAP = 10
COLOR_BG = (16, 18, 22)
COLOR_PANEL = (28, 30, 36)
COLOR_TEXT = (240, 240, 240)
COLOR_ACCENT = (210, 180, 80)
COLOR_SLOT_BG = (36, 38, 44)
COLOR_SLOT_BD = (80, 80, 90)

class HeroExchangeScreen:
    def __init__(
        self,
        screen: pygame.Surface,
        actor_a: UnitCarrier,
        actor_b: UnitCarrier,
        clock: Optional[pygame.time.Clock] = None,
    ) -> None:
        self.screen = screen
        self.hero_a = actor_a
        self.hero_b = actor_b
        self.clock = clock or pygame.time.Clock()
        self.running = True
        self.font = pygame.font.SysFont(None, 18)
        self.font_big = pygame.font.SysFont(None, 20, bold=True)
        self.hero_slots: List[pygame.Rect] = []
        self.other_slots: List[pygame.Rect] = []
        self.drag_active = False
        self.drag_src = ("", -1)
        self.drag_unit = None
        self.drag_offset = (0, 0)
        self.mouse_pos = (0, 0)

    def _compute_layout(self) -> Tuple[pygame.Rect, pygame.Rect]:
        W, H = self.screen.get_size()
        rect_a = pygame.Rect(20, H - ROW_H - GAP - ROW_H, W - 40, ROW_H)
        rect_b = pygame.Rect(20, H - ROW_H, W - 40, ROW_H)
        return rect_a, rect_b

    def _draw_label(self, text: str, rect: pygame.Rect) -> None:
        self.screen.blit(self.font_big.render(text, True, COLOR_TEXT), (rect.x, rect.y))

    def _draw_army_row(self, units, rect: pygame.Rect) -> List[pygame.Rect]:
        slots: List[pygame.Rect] = []
        w = (rect.width - (SLOT_COUNT + 1) * SLOT_PAD) // SLOT_COUNT
        h = rect.height - 2 * SLOT_PAD
        y = rect.y + SLOT_PAD
        x = rect.x + SLOT_PAD
        for i in range(SLOT_COUNT):
            r = pygame.Rect(x, y, w, h)
            slots.append(r)
            pygame.draw.rect(self.screen, COLOR_SLOT_BG, r, border_radius=6)
            pygame.draw.rect(self.screen, COLOR_SLOT_BD, r, 2, border_radius=6)
            if i < len(units):
                u = units[i]
                name = getattr(u.stats, "name", "Unit")
                cnt = getattr(u, "count", 1)
                self.screen.blit(self.font.render(name, True, COLOR_TEXT), (r.x + 6, r.y + 6))
                self.screen.blit(self.font.render(f"x{cnt}", True, COLOR_ACCENT), (r.right - 28, r.bottom - 20))
            x += w + SLOT_PAD
        return slots

    def draw(self) -> None:
        self.screen.fill(COLOR_BG)
        rect_a, rect_b = self._compute_layout()
        pygame.draw.rect(self.screen, COLOR_PANEL, rect_a)
        pygame.draw.rect(self.screen, COLOR_PANEL, rect_b)
        self._draw_label(getattr(self.hero_a, "name", "Hero A"), rect_a.inflate(-8, -ROW_H + 24).move(8, 4))
        self._draw_label(getattr(self.hero_b, "name", "Hero B"), rect_b.inflate(-8, -ROW_H + 24).move(8, 4))
        self.hero_slots = self._draw_army_row(self.hero_a.units, rect_a)
        self.other_slots = self._draw_army_row(self.hero_b.units, rect_b)
        if self.drag_active and self.drag_unit:
            mx, my = self.mouse_pos
            gx, gy = mx - self.drag_offset[0], my - self.drag_offset[1]
            ghost = pygame.Rect(gx, gy, 140, 64)
            pygame.draw.rect(self.screen, (60, 64, 80, 230), ghost, border_radius=6)
            pygame.draw.rect(self.screen, (120, 120, 140), ghost, 2, border_radius=6)
            name = getattr(self.drag_unit.stats, "name", "Unit")
            cnt = getattr(self.drag_unit, "count", 1)
            self.screen.blit(self.font.render(name, True, COLOR_TEXT), (ghost.x + 8, ghost.y + 8))
            self.screen.blit(self.font.render(f"x{cnt}", True, COLOR_ACCENT), (ghost.x + 8, ghost.y + 34))

    def run(self) -> None:
        while self.running:
            for evt in pygame.event.get():
                t = getattr(evt, "type", None)
                if t == pygame.QUIT:
                    self.running = False
                elif t == pygame.KEYDOWN and evt.key in (pygame.K_ESCAPE, pygame.K_b):
                    self.running = False
                elif t == pygame.MOUSEMOTION:
                    self.mouse_pos = evt.pos
                elif t == pygame.MOUSEBUTTONDOWN:
                    self._on_mousedown(evt.pos)
                elif t == pygame.MOUSEBUTTONUP:
                    self._on_mouseup(evt.pos)
            self.draw()
            pygame.display.flip()
            self.clock.tick(60)

    def _on_mousedown(self, pos: Tuple[int,int]) -> None:
        for i, r in enumerate(self.hero_slots):
            if r.collidepoint(pos) and i < len(self.hero_a.units):
                self.drag_active = True
                self.drag_src = ("a", i)
                self.drag_unit = self.hero_a.units[i]
                self.drag_offset = (pos[0] - r.x, pos[1] - r.y)
                return
        for i, r in enumerate(self.other_slots):
            if r.collidepoint(pos) and i < len(self.hero_b.units):
                self.drag_active = True
                self.drag_src = ("b", i)
                self.drag_unit = self.hero_b.units[i]
                self.drag_offset = (pos[0] - r.x, pos[1] - r.y)
                return

    def _on_mouseup(self, pos: Tuple[int,int]) -> None:
        if not self.drag_active or not self.drag_unit:
            return
        dropped = False
        for i, r in enumerate(self.hero_slots):
            if r.collidepoint(pos):
                dropped = True
                self._drop_to("a", i)
                break
        if not dropped:
            for i, r in enumerate(self.other_slots):
                if r.collidepoint(pos):
                    dropped = True
                    self._drop_to("b", i)
                    break
        self.drag_active = False
        self.drag_unit = None
        self.drag_src = ("", -1)

    def _drop_to(self, target: str, index: int) -> None:
        src_row, src_idx = self.drag_src
        if src_row not in ("a", "b") or src_idx < 0:
            return
        if target == src_row and index == src_idx:
            return
        src_list = self.hero_a.units if src_row == "a" else self.hero_b.units
        dst_list = self.hero_a.units if target == "a" else self.hero_b.units
        if index > SLOT_COUNT - 1:
            index = SLOT_COUNT - 1
        unit = src_list[src_idx]
        for u in dst_list:
            if u.stats is unit.stats:
                u.count += unit.count
                src_list.pop(src_idx)
                self.hero_a.apply_bonuses_to_army()
                self.hero_b.apply_bonuses_to_army()
                upd_a = getattr(self.hero_a, "update_portrait", None)
                if upd_a:
                    upd_a()
                upd_b = getattr(self.hero_b, "update_portrait", None)
                if upd_b:
                    upd_b()
                return
        if len(dst_list) < SLOT_COUNT:
            unit = src_list.pop(src_idx)
            if target == src_row and src_idx < index:
                index -= 1
            if index <= len(dst_list):
                dst_list.insert(index, unit)
            else:
                dst_list.append(unit)
        self.hero_a.apply_bonuses_to_army()
        self.hero_b.apply_bonuses_to_army()
        upd_a = getattr(self.hero_a, "update_portrait", None)
        if upd_a:
            upd_a()
        upd_b = getattr(self.hero_b, "update_portrait", None)
        if upd_b:
            upd_b()
