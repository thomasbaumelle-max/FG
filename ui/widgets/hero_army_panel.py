from __future__ import annotations

"""Widget displaying a hero portrait and a grid of unit stacks.

The panel allows rearranging unit stacks via drag & drop.  Right-clicking a
stack triggers an optional callback to show unit details.  Double-clicking the
hero portrait invokes another callback to open a hero overview screen.
"""

from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple

import pygame

import constants, theme
from core.entities import Unit, UnitCarrier
from state.event_bus import EVENT_BUS, ON_SELECT_HERO

MOUSEBUTTONDOWN = getattr(pygame, "MOUSEBUTTONDOWN", 1)
MOUSEBUTTONUP = getattr(pygame, "MOUSEBUTTONUP", 2)


@dataclass
class _DragState:
    index: int
    unit: Unit


class HeroArmyPanel:
    """Display a portrait and a grid for the hero's army."""

    PORTRAIT_SIZE = 72
    CELL_SIZE = 48
    PADDING = 4
    # (columns, half-cell offset)
    GRID_LAYOUT = [(4, 0), (3, 1)]
    GRID_ROWS = len(GRID_LAYOUT)
    GRID_COLS = max(cols + (offset + 1) // 2 for cols, offset in GRID_LAYOUT)
    GRID_CELLS = sum(cols for cols, _ in GRID_LAYOUT)

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
        try:  # pragma: no cover - font module may be missing
            self.font = pygame.font.SysFont(None, 16)
        except Exception:  # pragma: no cover - font module missing
            self.font = None
        self.drag: Optional[_DragState] = None
        # Update displayed hero when selection changes
        EVENT_BUS.subscribe(ON_SELECT_HERO, self.set_hero)

    # ------------------------------------------------------------------
    def set_hero(self, hero: UnitCarrier) -> None:
        """Assign the hero or army whose troops will be displayed."""
        self.hero = hero
        army = list(getattr(hero, "army", getattr(hero, "units", [])))
        self.grid = list(army[: self.GRID_CELLS])
        while len(self.grid) < self.GRID_CELLS:
            self.grid.append(None)
        portrait = getattr(hero, "portrait", None)
        if isinstance(portrait, str):
            try:
                portrait = pygame.image.load(portrait).convert_alpha()
            except Exception:  # pragma: no cover - loading may fail
                portrait = None
        if portrait is not None and hasattr(portrait, "blit"):
            size_fn = getattr(portrait, "get_size", None)
            if size_fn:
                width, height = size_fn()
            else:
                width, height = portrait.get_width(), portrait.get_height()
            if (width, height) != (self.PORTRAIT_SIZE, self.PORTRAIT_SIZE):
                try:
                    portrait = pygame.transform.scale(
                        portrait, (self.PORTRAIT_SIZE, self.PORTRAIT_SIZE)
                    )
                except Exception:  # pragma: no cover
                    portrait = None
            if portrait is not None:
                self.portrait = portrait
        if portrait is None:
            self.portrait = self._make_portrait()

    # ------------------------------------------------------------------
    def _make_portrait(self) -> pygame.Surface:
        surf = pygame.Surface((self.PORTRAIT_SIZE, self.PORTRAIT_SIZE))
        surf.fill(theme.PALETTE["panel"])
        if hasattr(pygame, "draw") and hasattr(pygame.draw, "rect"):
            pygame.draw.rect(surf, theme.FRAME_COLOURS["normal"], surf.get_rect(), theme.FRAME_WIDTH)
        return surf

    def _portrait_rect(self, rect: pygame.Rect) -> pygame.Rect:
        return pygame.Rect(rect.x, rect.y, self.PORTRAIT_SIZE, self.PORTRAIT_SIZE)

    def _grid_origin(self, rect: pygame.Rect) -> Tuple[int, int]:
        """Top-left corner of the army grid within ``rect``."""
        max_cols = max(
            cols + (offset + 1) // 2 for cols, offset in self.GRID_LAYOUT
        )
        rows = len(self.GRID_LAYOUT)
        grid_w = max_cols * self.CELL_SIZE + (max_cols - 1) * self.PADDING
        grid_h = rows * self.CELL_SIZE + (rows - 1) * self.PADDING
        left = rect.x + self.PORTRAIT_SIZE + self.PADDING
        avail_w = rect.x + rect.width - left
        x = left + (avail_w - grid_w) // 2
        y = rect.y + (rect.height - grid_h) // 2
        return x, y
    
    def _point_in_rect(self, pos: Tuple[int, int], r: pygame.Rect) -> bool:
        x, y = pos
        return r.x <= x < r.x + r.width and r.y <= y < r.y + r.height


    def _cell_rect(self, index: int, rect: pygame.Rect) -> pygame.Rect:
        gx, gy = self._grid_origin(rect)
        idx = index
        for row, (cols, offset) in enumerate(self.GRID_LAYOUT):
            if idx < cols:
                x = gx + offset * (self.CELL_SIZE + self.PADDING) // 2
                x += idx * (self.CELL_SIZE + self.PADDING)
                y = gy + row * (self.CELL_SIZE + self.PADDING)
                return pygame.Rect(x, y, self.CELL_SIZE, self.CELL_SIZE)
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
                if self._point_in_rect(pos, self._portrait_rect(rect)):
                    if getattr(evt, "clicks", 1) >= 2 and self.hero and self.on_open_hero:
                        self.on_open_hero(self.hero)
                else:
                    idx = self._cell_at(pos, rect)
                    if idx is not None:
                        unit = self.grid[idx]
                        if unit is not None:
                            self.drag = _DragState(idx, unit)
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

    # ------------------------------------------------------------------
    def draw(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        # portrait + nom (nom à l'intérieur)
        p_rect = self._portrait_rect(rect)
        surface.blit(self.portrait, p_rect)
        if self.font and self.hero:
            name = getattr(self.hero, "name", "Hero")
            name_s = self.font.render(name, True, (230,230,235))
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
            surface.fill((36,38,44), cell)
            pygame.draw.rect(surface, (74,76,86), cell, 1)
            if unit is None: continue
            # icon
            icon = getattr(unit, "icon", None)
            if icon:
                try:
                    if icon.get_size() != cell.size:
                        icon = pygame.transform.smoothscale(icon, cell.size)
                except Exception: icon = None
            if icon: surface.blit(icon, cell.topleft)
            # count + barre HP
            if self.font:
                count = self.font.render(str(getattr(unit, "count", 0)), True, (230,230,235))
                surface.blit(count, (cell.x+2, cell.y+2))
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
