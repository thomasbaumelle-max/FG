from __future__ import annotations

"""Widget displaying a hero portrait and a grid of unit stacks.

The panel allows rearranging unit stacks via drag & drop.  Right-clicking a
stack triggers an optional callback to show unit details.  Double-clicking the
hero portrait invokes another callback to open a hero overview screen.
"""

from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple

import pygame

import constants, theme, audio
from core.entities import Unit, UnitCarrier
from state.event_bus import EVENT_BUS, ON_SELECT_HERO
from .quantity_dialog import QuantityDialog

MOUSEBUTTONDOWN = getattr(pygame, "MOUSEBUTTONDOWN", 1)
MOUSEBUTTONUP = getattr(pygame, "MOUSEBUTTONUP", 2)


@dataclass
class _DragState:
    index: int
    unit: Unit


class HeroArmyPanel:
    """Display a portrait and a grid for the hero's army."""
    PADDING = 4
    # (columns, half-cell offset)
    GRID_LAYOUT = [(4, 0), (3, 1)]
    GRID_ROWS = len(GRID_LAYOUT)
    GRID_COLS = max(cols + (offset + 1) // 2 for cols, offset in GRID_LAYOUT)
    GRID_CELLS = sum(cols for cols, _ in GRID_LAYOUT)
    MAX_PORTRAIT = 96
    MAX_CELL = 72

    FORMATION_BUTTON_HEIGHT = 20
    SPLIT_BUTTON_HEIGHT = 20
    FORMATIONS = [
        ("relâchée", "relachee"),
        ("serrée", "serree"),
        ("carrée", "carree"),
    ]

    def __init__(
        self,
        hero: Optional[UnitCarrier] = None,
        *,
        on_unit_detail: Optional[Callable[[Unit], None]] = None,
        on_open_hero: Optional[Callable[[UnitCarrier], None]] = None,
    ) -> None:
        self.hero = hero
        self.on_unit_detail = on_unit_detail
        self.on_open_hero = on_open_hero
        self.grid: List[Optional[Unit]] = [None] * self.GRID_CELLS
        self.portrait = self._make_portrait()
        if hero is not None:
            self.set_hero(hero)
        self.font = theme.get_font(16)
        self.drag: Optional[_DragState] = None
        # Currently selected stack index for operations like splitting
        self.selected: Optional[int] = None
        # Update displayed hero when selection changes
        EVENT_BUS.subscribe(ON_SELECT_HERO, self.set_hero)
        self.selected_formation = "serree"

    # ------------------------------------------------------------------
    def set_hero(self, hero: UnitCarrier) -> None:
        """Assign the hero or army whose troops will be displayed."""
        self.hero = hero
        army = list(getattr(hero, "army", getattr(hero, "units", [])))
        self.grid = list(army[: self.GRID_CELLS])
        while len(self.grid) < self.GRID_CELLS:
            self.grid.append(None)
        self.selected_formation = getattr(hero, "formation", "serree")
        portrait = getattr(hero, "portrait", None)
        if isinstance(portrait, str):
            try:
                portrait = pygame.image.load(portrait).convert_alpha()
            except Exception:  # pragma: no cover - loading may fail
                portrait = None
        if portrait is not None and hasattr(portrait, "blit"):
            self.portrait = portrait
        else:
            self.portrait = self._make_portrait()

    # ------------------------------------------------------------------
    def _make_portrait(self) -> pygame.Surface:
        surf = pygame.Surface((1, 1))
        surf.fill(theme.PALETTE["panel"])
        if hasattr(pygame, "draw") and hasattr(pygame.draw, "rect"):
            pygame.draw.rect(
                surf, theme.FRAME_COLOURS["normal"], surf.get_rect(), theme.FRAME_WIDTH
            )
        return surf

    # ------------------------------------------------------------------
    def _layout(self, rect: pygame.Rect) -> Tuple[int, int, int, int]:
        """Compute sizes and positions for dynamic layout.

        Returns ``(cell_size, portrait_size, grid_x, grid_y)`` where
        ``grid_x``/``grid_y`` is the top-left corner of the unit grid.
        """

        content_h = max(1, rect.height - self.FORMATION_BUTTON_HEIGHT - self.PADDING)
        portrait_max_h = min(
            self.MAX_PORTRAIT, content_h - self.SPLIT_BUTTON_HEIGHT - self.PADDING
        )
        grid_min_w = self.GRID_COLS * 1 + (self.GRID_COLS - 1) * self.PADDING
        portrait_max_w = min(
            self.MAX_PORTRAIT, rect.width - grid_min_w - 2 * self.PADDING
        )
        portrait_size = max(1, min(portrait_max_h, portrait_max_w))

        avail_w = max(1, rect.width - portrait_size - 2 * self.PADDING)
        cell_w = max(
            1,
            min(
                (avail_w - (self.GRID_COLS - 1) * self.PADDING) // self.GRID_COLS,
                self.MAX_CELL,
            ),
        )
        cell_h = max(
            1,
            min(
                (content_h - (self.GRID_ROWS - 1) * self.PADDING) // self.GRID_ROWS,
                self.MAX_CELL,
            ),
        )
        cell_size = max(1, min(cell_w, cell_h))

        grid_w = self.GRID_COLS * cell_size + (self.GRID_COLS - 1) * self.PADDING
        if grid_w > avail_w:
            portrait_size = max(1, rect.width - grid_w - 2 * self.PADDING)
            avail_w = max(1, rect.width - portrait_size - 2 * self.PADDING)
            cell_w = max(
                1,
                min(
                    (avail_w - (self.GRID_COLS - 1) * self.PADDING) // self.GRID_COLS,
                    self.MAX_CELL,
                ),
            )
            cell_size = max(1, min(cell_w, cell_h))
            grid_w = self.GRID_COLS * cell_size + (self.GRID_COLS - 1) * self.PADDING
        grid_h = self.GRID_ROWS * cell_size + (self.GRID_ROWS - 1) * self.PADDING

        gx = rect.x + portrait_size + self.PADDING + max(0, (avail_w - grid_w) // 2)
        rect_right = rect.x + rect.width
        gx = max(rect.x, min(gx, rect_right - grid_w))
        gy = rect.y + max(0, (content_h - grid_h) // 2)
        gy = max(rect.y, min(gy, rect.y + content_h - grid_h))
        return cell_size, portrait_size, gx, gy

    def _portrait_rect(self, rect: pygame.Rect) -> pygame.Rect:
        _, portrait, _, gy = self._layout(rect)
        return pygame.Rect(rect.x, gy, portrait, portrait)

    def _grid_origin(self, rect: pygame.Rect) -> Tuple[int, int]:
        """Top-left corner of the army grid within ``rect``."""
        _, _, gx, gy = self._layout(rect)
        return gx, gy
    
    def _point_in_rect(self, pos: Tuple[int, int], r: pygame.Rect) -> bool:
        x, y = pos
        return r.x <= x < r.x + r.width and r.y <= y < r.y + r.height


    def _formation_rects(self, rect: pygame.Rect) -> List[pygame.Rect]:
        """Return rectangles for the formation selection buttons."""
        _, portrait, _, _ = self._layout(rect)
        width = rect.width - portrait - 2 * self.PADDING
        btn_w = (width - 2 * self.PADDING) // 3
        x = rect.x + portrait + self.PADDING
        y = rect.y + rect.height - self.FORMATION_BUTTON_HEIGHT - self.PADDING
        rects = []
        for i in range(3):
            rects.append(
                pygame.Rect(
                    x + i * (btn_w + self.PADDING),
                    y,
                    btn_w,
                    self.FORMATION_BUTTON_HEIGHT,
                )
            )
        return rects

    def _split_button_rect(self, rect: pygame.Rect) -> pygame.Rect:
        """Rectangle of the split stack button below the portrait."""
        p = self._portrait_rect(rect)
        return pygame.Rect(p.x, p.bottom + self.PADDING, p.width, self.SPLIT_BUTTON_HEIGHT)


    def _cell_rect(self, index: int, rect: pygame.Rect) -> pygame.Rect:
        cell, _, gx, gy = self._layout(rect)
        idx = index
        for row, (cols, offset) in enumerate(self.GRID_LAYOUT):
            if idx < cols:
                x = gx + offset * (cell + self.PADDING) // 2
                x += idx * (cell + self.PADDING)
                y = gy + row * (cell + self.PADDING)
                return pygame.Rect(x, y, cell, cell)
            idx -= cols
        raise IndexError("cell index out of range")

    def _cell_at(self, pos: Tuple[int, int], rect: pygame.Rect) -> Optional[int]:
        for idx in range(len(self.grid)):
            if self._point_in_rect(pos, self._cell_rect(idx, rect)):
                return idx
        return None

    def _commit_grid(self) -> None:
        if self.hero is None:
            return
        army = [u for u in self.grid if u is not None]
        if hasattr(self.hero, "army"):
            self.hero.army = army  # type: ignore[attr-defined]
        else:
            self.hero.units = army  # type: ignore[attr-defined]

    # ------------------------------------------------------------------
    def handle_event(self, evt: object, rect: pygame.Rect) -> None:
        etype = getattr(evt, "type", None)
        if etype == MOUSEBUTTONDOWN:
            button = getattr(evt, "button", 0)
            pos = getattr(evt, "pos", (0, 0))
            if button == 1:
                if self._point_in_rect(pos, self._split_button_rect(rect)):
                    self._split_selected()
                    return
                # Formation buttons
                for (label, key), brect in zip(self.FORMATIONS, self._formation_rects(rect)):
                    if self._point_in_rect(pos, brect):
                        self.selected_formation = key
                        if self.hero is not None:
                            setattr(self.hero, "formation", key)
                        return
                if self._point_in_rect(pos, self._portrait_rect(rect)):
                    if getattr(evt, "clicks", 1) >= 2 and self.hero and self.on_open_hero:
                        self.on_open_hero(self.hero)
                else:
                    idx = self._cell_at(pos, rect)
                    if idx is not None:
                        self.selected = idx
                        unit = self.grid[idx]
                        if unit is not None:
                            self.drag = _DragState(idx, unit)
                            audio.play_sound("drag_start")
            elif button == 3:
                idx = self._cell_at(pos, rect)
                if idx is not None:
                    unit = self.grid[idx]
                    if unit is not None and self.on_unit_detail:
                        self.on_unit_detail(unit)
        elif etype == MOUSEBUTTONUP:
            if getattr(evt, "button", 0) == 1 and self.drag is not None:
                pos = getattr(evt, "pos", (0, 0))
                target = self._cell_at(pos, rect)
                if target is not None:
                    self.grid[self.drag.index], self.grid[target] = (
                        self.grid[target],
                        self.grid[self.drag.index],
                    )
                    self._commit_grid()
                self.drag = None
                audio.play_sound("drag_drop")

    # ------------------------------------------------------------------
    def _split_selected(self) -> None:
        """Split the currently selected stack into an empty slot."""
        if self.selected is None:
            return
        unit = self.grid[self.selected]
        if unit is None or getattr(unit, "count", 0) <= 1:
            return
        try:
            dest = self.grid.index(None)
        except ValueError:
            return
        screen = pygame.display.get_surface()
        if screen is None:
            return
        dlg = QuantityDialog(screen, unit.count)
        qty = dlg.run()
        if qty is None or qty <= 0 or qty >= unit.count:
            return
        unit.count -= qty
        new_unit = Unit(unit.stats, qty, unit.side)
        if hasattr(unit, "icon"):
            setattr(new_unit, "icon", getattr(unit, "icon"))
        self.grid[dest] = new_unit
        self._commit_grid()

    # ------------------------------------------------------------------
    def draw(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        # portrait + nom (nom à l'intérieur)
        p_rect = self._portrait_rect(rect)
        portrait = self.portrait
        try:
            if portrait.get_size() != p_rect.size:
                portrait = pygame.transform.smoothscale(portrait, p_rect.size)
        except Exception:
            pass
        surface.blit(portrait, p_rect)
        if self.font and self.hero:
            name = getattr(self.hero, "name", "Hero")
            name_s = self.font.render(name, True, theme.PALETTE["text"])
            name_pos = (
                p_rect.x + (p_rect.width - name_s.get_width()) // 2,
                p_rect.y + p_rect.height + 4,
            )
            # clamp pour rester dans le panel
            if name_pos[1] + name_s.get_height() > rect.y + rect.height - 4:
                name_pos = (
                    name_pos[0],
                    rect.y + rect.height - 4 - name_s.get_height(),
                )
            surface.blit(name_s, name_pos)
    
        # grille centrée
        for idx, unit in enumerate(self.grid):
            cell = self._cell_rect(idx, rect)
            surface.fill((36, 38, 44), cell)
            pygame.draw.rect(surface, (74, 76, 86), cell, 1)
            if self.selected == idx:
                pygame.draw.rect(surface, (200, 200, 80), cell, 2)
            if unit is None: continue
            # icon
            icon = getattr(unit, "icon", None)
            if isinstance(icon, str):
                try:
                    icon = pygame.image.load(icon).convert_alpha()
                except Exception:
                    icon = None
            if icon:
                try:
                    if icon.get_size() != cell.size:
                        icon = pygame.transform.smoothscale(icon, cell.size)
                except Exception:
                    icon = None
            if icon:
                surface.blit(icon, cell.topleft)
            # count + barre HP
            if self.font:
                count = self.font.render(
                    theme.format_number(getattr(unit, "count", 0)),
                    True,
                    theme.PALETTE["text"],
                )
                surface.blit(count, (cell.x + 2, cell.y + 2))
            max_hp = getattr(getattr(unit, "stats", None), "max_hp", 0)
            cur_hp = getattr(unit, "current_hp", 0)
            if max_hp > 0:
                bar = pygame.Rect(
                    cell.x + 2,
                    cell.y + cell.height - 7,
                    cell.width - 4,
                    5,
                )
                pygame.draw.rect(surface, (90,30,30), bar)
                inner = pygame.Rect(bar.x, bar.y, int(bar.width*cur_hp/max_hp), bar.height)
                pygame.draw.rect(surface, (80,180,80), inner)

        # formation buttons
        if self.font:
            for (label, key), brect in zip(self.FORMATIONS, self._formation_rects(rect)):
                surface.fill((36, 38, 44), brect)
                pygame.draw.rect(surface, (74, 76, 86), brect, 1)
                if self.selected_formation == key:
                    pygame.draw.rect(surface, (200, 200, 80), brect, 2)
                text = self.font.render(label, True, theme.PALETTE["text"])
                surface.blit(
                    text,
                    (
                        brect.x + (brect.width - text.get_width()) // 2,
                        brect.y + (brect.height - text.get_height()) // 2,
                    ),
                )

        # split button
        srect = self._split_button_rect(rect)
        surface.fill((36, 38, 44), srect)
        pygame.draw.rect(surface, (74, 76, 86), srect, 1)
        if self.font:
            txt = self.font.render("Split", True, theme.PALETTE["text"])
            surface.blit(
                txt,
                (
                    srect.x + (srect.width - txt.get_width()) // 2,
                    srect.y + (srect.height - txt.get_height()) // 2,
                ),
            )
