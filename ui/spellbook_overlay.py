from __future__ import annotations

import json
import os
import pygame
import theme
import settings
from loaders.i18n import load_locale


class SpellbookOverlay:
    """Full-screen overlay displaying the hero's spell list."""

    BG = theme.PALETTE["background"]
    TEXT = theme.PALETTE["text"]
    PER_PAGE = 10

    def __init__(self, screen: pygame.Surface, combat=None, *, town: bool = False) -> None:
        self.screen = screen
        self.combat = combat
        self.town = town
        self.font = theme.get_font(20) or pygame.font.SysFont(None, 20)
        self.texts = load_locale(settings.LANGUAGE)
        # Pagination state
        self.page: int = 0
        # label rects for tooltip lookup populated during draw
        self._label_rects: list[tuple[pygame.Rect, str]] = []
        self._tab_rects: list[tuple[pygame.Rect, str]] = []

        if not self.town and self.combat is not None:
            self.spell_names = sorted(self.combat.hero_spells.keys())
        else:
            self._load_town_spells()

    # ------------------------------------------------------------------ helpers
    @property
    def num_pages(self) -> int:
        """Return total number of pages."""
        if not self.spell_names:
            return 1
        return (len(self.spell_names) - 1) // self.PER_PAGE + 1

    def _spell_tooltip(self, name: str) -> list[str]:
        """Return tooltip lines for a spell name."""
        lines = [name.replace("_", " ").title()]
        lvl = self.combat.hero_spells.get(name)
        if lvl:
            lines.append(f"{self.texts.get('Level', 'Level')}: {lvl}")
        spec = getattr(self.combat, "spell_defs", {}).get(name)
        if spec:
            lines.append(f"{self.texts.get('Mana', 'Mana')}: {spec.cost_mana}")
            if spec.cooldown:
                lines.append(f"{self.texts.get('Cooldown', 'Cooldown')}: {spec.cooldown}")
            lines.append(f"{self.texts.get('Range', 'Range')}: {spec.range}")
        return lines

    def _draw_tooltip(self, surface: pygame.Surface, pos: tuple[int, int], lines: list[str]) -> None:
        font = theme.get_font(16) or pygame.font.SysFont(None, 16)
        texts = [font.render(t, True, self.TEXT) for t in lines]
        w = max(t.get_width() for t in texts) + 10
        h = sum(t.get_height() for t in texts) + 10
        tip = pygame.Surface((w, h), pygame.SRCALPHA)
        tip.fill((*self.BG, 220))
        theme.draw_frame(tip, tip.get_rect())
        y = 5
        for t in texts:
            tip.blit(t, (5, y))
            y += t.get_height()
        x, y = pos
        sw, sh = surface.get_size()
        if x + w > sw:
            x -= w
        if y + h > sh:
            y -= h
        surface.blit(tip, (x, y))

    def _load_town_spells(self) -> None:
        """Load spells grouped by school for town view."""
        path = os.path.join("assets", "spells", "spells.json")
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except Exception:
            data = {}
        schools = data.get("schools", {})
        self.school_spells: dict[str, list[str]] = {}
        for school, levels in schools.items():
            names: list[str] = []
            for lvl in levels.values():
                for group in lvl.values():
                    for entry in group:
                        nm = entry.get("name") or entry.get("id")
                        if nm:
                            names.append(nm)
            self.school_spells[school] = sorted(set(names))
        self.categories = sorted(self.school_spells.keys())
        self.current_cat = 0
        if self.categories:
            self.spell_names = self.school_spells[self.categories[0]]
        else:
            self.spell_names = []

    # ------------------------------------------------------------------ events
    def handle_event(self, event: pygame.event.Event) -> bool:
        """Return ``True`` to close the overlay."""
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_s, pygame.K_ESCAPE):
                return True
            if event.key in (pygame.K_RIGHT, pygame.K_PAGEDOWN):
                if self.page + 1 < self.num_pages:
                    self.page += 1
            elif event.key in (pygame.K_LEFT, pygame.K_PAGEUP):
                if self.page > 0:
                    self.page -= 1
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                if self.town:
                    for idx, (rect, cat) in enumerate(self._tab_rects):
                        if rect.collidepoint(event.pos):
                            self.current_cat = idx
                            self.spell_names = self.school_spells.get(cat, [])
                            self.page = 0
                            return False
                return True
            if event.button in (5,):
                if self.page + 1 < self.num_pages:
                    self.page += 1
            elif event.button in (4,):
                if self.page > 0:
                    self.page -= 1
        return False

    # ------------------------------------------------------------------ drawing
    def draw(self) -> None:
        """Draw the overlay to the attached screen."""
        w, h = self.screen.get_size()
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        overlay.fill((*self.BG, 230))
        theme.draw_frame(overlay, overlay.get_rect())

        title = self.font.render(self.texts.get("Spellbook", "Spellbook"), True, self.TEXT)
        overlay.blit(title, ((w - title.get_width()) // 2, 10))

        self._label_rects.clear()
        start = self.page * self.PER_PAGE
        end = start + self.PER_PAGE
        y = 60 if self.town else 40

        if self.town:
            # Draw category tabs
            self._tab_rects.clear()
            x = 20
            tab_y = 30
            for idx, cat in enumerate(self.categories):
                label = self.font.render(cat.title(), True, self.TEXT)
                rect = pygame.Rect(x, tab_y, label.get_width() + 20, label.get_height() + 10)
                pygame.draw.rect(overlay, (*self.BG, 0), rect)
                state = "highlight" if idx == self.current_cat else "normal"
                theme.draw_frame(overlay, rect, state)
                overlay.blit(label, (rect.x + 10, rect.y + 5))
                self._tab_rects.append((rect, cat))
                x += rect.width + 5

        for name in self.spell_names[start:end]:
            label = self.font.render(name, True, self.TEXT)
            pos = (40, y)
            overlay.blit(label, pos)
            lw, lh = label.get_size()
            rect = pygame.Rect(pos[0], pos[1], lw, lh)
            self._label_rects.append((rect, name))
            y += label.get_height() + 8

        if self.num_pages > 1:
            pg = self.font.render(f"{self.page + 1}/{self.num_pages}", True, self.TEXT)
            overlay.blit(pg, (w - pg.get_width() - 10, h - pg.get_height() - 10))

        if not self.town and self.combat is not None:
            mx, my = pygame.mouse.get_pos()
            for rect, name in self._label_rects:
                if rect.collidepoint((mx, my)):
                    self._draw_tooltip(overlay, (mx, my), self._spell_tooltip(name))
                    break

        self.screen.blit(overlay, (0, 0))
