from __future__ import annotations

import pygame
import theme
import settings
from loaders.i18n import load_locale


class SpellbookOverlay:
    """Full-screen overlay displaying the hero's spell list."""

    BG = theme.PALETTE["background"]
    TEXT = theme.PALETTE["text"]
    PER_PAGE = 10

    def __init__(self, screen: pygame.Surface, combat) -> None:
        self.screen = screen
        self.combat = combat
        self.font = theme.get_font(20) or pygame.font.SysFont(None, 20)
        self.texts = load_locale(settings.LANGUAGE)
        # Pagination state
        self.page: int = 0
        self.spell_names = sorted(self.combat.hero_spells.keys())
        # label rects for tooltip lookup populated during draw
        self._label_rects: list[tuple[pygame.Rect, str]] = []

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
        y = 40
        start = self.page * self.PER_PAGE
        end = start + self.PER_PAGE
        for name in self.spell_names[start:end]:
            label = self.font.render(name, True, self.TEXT)
            pos = (40, y)
            overlay.blit(label, pos)
            rect = pygame.Rect(pos, label.get_size())
            self._label_rects.append((rect, name))
            y += label.get_height() + 8

        if self.num_pages > 1:
            pg = self.font.render(f"{self.page + 1}/{self.num_pages}", True, self.TEXT)
            overlay.blit(pg, (w - pg.get_width() - 10, h - pg.get_height() - 10))

        mx, my = pygame.mouse.get_pos()
        for rect, name in self._label_rects:
            if rect.collidepoint((mx, my)):
                self._draw_tooltip(overlay, (mx, my), self._spell_tooltip(name))
                break

        self.screen.blit(overlay, (0, 0))
