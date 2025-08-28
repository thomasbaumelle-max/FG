from __future__ import annotations

import json
import os
import pygame
import theme
import settings
from loaders.i18n import load_locale
from loaders import icon_loader as IconLoader


class SpellbookOverlay:
    """Centered overlay displaying the hero's spell list."""

    BG = theme.PALETTE["background"]
    TEXT = theme.PALETTE["text"]
    # grid layout - 5 columns x 2 rows by default
    GRID_COLS = 5
    GRID_ROWS = 2
    ICON = 64  # placeholder icon size
    GAP = 10
    PER_PAGE = GRID_COLS * GRID_ROWS

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

        # mapping for non-combat spell details (cost, level and icon)
        self.spell_info: dict[str, dict[str, int | None | str | None]] = {}

        schools = self._load_spell_data()

        if not self.town and self.combat is not None:
            self.spell_names = sorted(self.combat.hero_spells.keys())
        else:
            self._load_town_spells(schools)

    def _load_spell_data(self) -> dict:
        base = os.path.dirname(os.path.dirname(__file__))
        path = os.path.join(base, "assets", "spells", "spells.json")
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except Exception:
            data = {}
        self.default_icon = data.get("default_icon")
        schools = data.get("schools", {})
        for school, levels in schools.items():
            for lvl_num, lvl in levels.items():
                for group in lvl.values():
                    for entry in group:
                        nm = entry.get("name") or entry.get("id")
                        if not nm:
                            continue
                        info = self.spell_info.setdefault(nm, {})
                        info.setdefault("cost", entry.get("cost"))
                        info.setdefault(
                            "level", int(lvl_num) if str(lvl_num).isdigit() else None
                        )
                        info["icon"] = entry.get("icon")
        return schools

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

        lvl = None
        cost = None
        if self.combat is not None:
            lvl = self.combat.hero_spells.get(name)
            spec = getattr(self.combat, "spell_defs", {}).get(name)
            if spec:
                cost = spec.cost_mana
                if spec.cooldown:
                    lines.append(f"{self.texts.get('Cooldown', 'Cooldown')}: {spec.cooldown}")
                lines.append(f"{self.texts.get('Range', 'Range')}: {spec.range}")
        info = self.spell_info.get(name, {})
        lvl = lvl if lvl is not None else info.get("level")
        cost = cost if cost is not None else info.get("cost")

        if lvl is not None:
            lines.append(f"{self.texts.get('Level', 'Level')}: {lvl}")
        if cost is not None:
            lines.append(f"{self.texts.get('Mana', 'Mana')}: {cost}")
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

    def _load_town_spells(self, schools: dict) -> None:
        """Load spells grouped by school for town view."""
        self.school_spells: dict[str, list[str]] = {}
        all_names: set[str] = set()
        for school, levels in schools.items():
            names: list[str] = []
            for lvl_num, lvl in levels.items():
                for group in lvl.values():
                    for entry in group:
                        nm = entry.get("name") or entry.get("id")
                        if not nm:
                            continue
                        names.append(nm)
                        all_names.add(nm)
            self.school_spells[school] = sorted(set(names))
        self.categories = sorted(self.school_spells.keys())
        self.current_cat = 0
        if self.categories:
            for idx, cat in enumerate(self.categories):
                spells = self.school_spells.get(cat, [])
                if spells:
                    self.current_cat = idx
                    self.spell_names = spells
                    break
            else:
                self.spell_names = []
        else:
            self.spell_names = sorted(all_names)

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
        screen_w, screen_h = self.screen.get_size()
        w = int(screen_w * 0.6)
        h = int(screen_h * 0.6)
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        overlay.fill((*self.BG, 230))
        theme.draw_frame(overlay, overlay.get_rect())
        offset_x = (screen_w - w) // 2
        offset_y = (screen_h - h) // 2

        title = self.font.render(self.texts.get("Spellbook", "Spellbook"), True, self.TEXT)
        overlay.blit(title, ((w - title.get_width()) // 2, 10))

        self._label_rects.clear()
        start = self.page * self.PER_PAGE
        end = start + self.PER_PAGE
        grid_y = 60 if self.town else 40

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
                self._tab_rects.append((rect.move(offset_x, offset_y), cat))
                x += rect.width + 5

        if not self.spell_names:
            msg = self.font.render(self.texts.get("No spells", "No spells"), True, self.TEXT)
            overlay.blit(msg, ((w - msg.get_width()) // 2, (h - msg.get_height()) // 2))
            self.screen.blit(overlay, (offset_x, offset_y))
            return

        # Grid drawing
        grid_x = 20
        font_small = theme.get_font(14) or pygame.font.SysFont(None, 14)
        for idx, name in enumerate(self.spell_names[start:end]):
            col = idx % self.GRID_COLS
            row = idx // self.GRID_COLS
            x = grid_x + col * (self.ICON + self.GAP)
            y = grid_y + row * (self.ICON + self.GAP)
            rect = pygame.Rect(x, y, self.ICON, self.ICON)

            info = self.spell_info.get(name, {})
            icon_id = info.get("icon") or self.default_icon or "spell_default"
            icon = IconLoader.get(icon_id, self.ICON)
            overlay.blit(icon, (x, y))
            theme.draw_frame(overlay, rect)

            # text info
            if self.combat is not None:
                lvl = self.combat.hero_spells.get(name)
                spec = getattr(self.combat, "spell_defs", {}).get(name)
                cost = getattr(spec, "cost_mana", None) if spec else None
            else:
                lvl = info.get("level")
                cost = info.get("cost")

            name_surf = font_small.render(name, True, self.TEXT)
            overlay.blit(name_surf, (x + 2, y + 2))
            if cost is not None:
                cost_surf = font_small.render(str(cost), True, self.TEXT)
                overlay.blit(cost_surf, (x + 2, y + self.ICON - cost_surf.get_height() - 2))
            if lvl is not None:
                lvl_surf = font_small.render(str(lvl), True, self.TEXT)
                overlay.blit(lvl_surf, (x + self.ICON - lvl_surf.get_width() - 2, y + self.ICON - lvl_surf.get_height() - 2))

            self._label_rects.append((rect.move(offset_x, offset_y), name))

        if self.num_pages > 1:
            pg = self.font.render(f"{self.page + 1}/{self.num_pages}", True, self.TEXT)
            overlay.blit(pg, (w - pg.get_width() - 10, h - pg.get_height() - 10))

        # Hover tooltip using shared logic for all modes
        if hasattr(pygame, "mouse") and hasattr(pygame.mouse, "get_pos"):
            mx, my = pygame.mouse.get_pos()
            for rect, name in self._label_rects:
                if rect.collidepoint((mx, my)):
                    self._draw_tooltip(overlay, (mx - offset_x, my - offset_y), self._spell_tooltip(name))
                    break
        self.screen.blit(overlay, (offset_x, offset_y))
