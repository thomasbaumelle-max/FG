from __future__ import annotations

"""Simple minimap widget for the exploration world.

The minimap renders a scaled overview of the :class:`world.WorldMap` on a
256×256 surface.  A rectangle indicating the current camera viewport of the
:class:`render.world_renderer.WorldRenderer` is drawn over this surface.  The
widget also allows the player to recenter the camera by clicking or dragging on
it.  Allied towns are marked with coloured points and an optional fog of war
overlay can be applied.
"""

from typing import Dict, List, Optional, Tuple

import math
import os
import json
import pygame

import constants
from core.world import WorldMap, BIOME_IMAGES
from render.world_renderer import WorldRenderer
from core.buildings import Town
from .icon_button import IconButton

# Fallback event type constants for environments with a pygame stub
MOUSEBUTTONDOWN = getattr(pygame, "MOUSEBUTTONDOWN", 1)
MOUSEBUTTONUP = getattr(pygame, "MOUSEBUTTONUP", 2)
MOUSEMOTION = getattr(pygame, "MOUSEMOTION", 3)

PARCHMENT = (245, 222, 179)

FILTER_LABELS: Dict[str, str] = {
    "resources": "Resources",
    "boats": "Boats",
    "towns": "Towns",
    "buildings": "Buildings",
    "treasures": "Treasures",
}


class Minimap:
    """Render and interact with a small overview map."""

    _instances: List["Minimap"] = []

    def __init__(
        self,
        world: WorldMap,
        renderer: WorldRenderer,
        size: int = 256,
        player_colour: Tuple[int, int, int] = constants.BLUE,
    ) -> None:
        self.world = world
        self.renderer = renderer
        self.size = size
        self.player_colour = player_colour
        base = pygame.Surface((size, size), pygame.SRCALPHA)
        try:
            self.surface = base.convert_alpha()
        except Exception:  # pragma: no cover - pygame stub without convert_alpha
            self.surface = base
        # Coordinates of towns for faction colouring
        self.city_points: List[Tuple[int, int]] = []
        self.city_colours: List[Tuple[int, int, int]] = []
        # Icons for points of interest: (surface, x, y, category)
        self.poi_icons: List[Tuple[pygame.Surface, int, int, str]] = []
        self.fog_rects: List[pygame.Rect] = []
        self.fog: Optional[List[List[bool]]] = None
        self._dragging = False

        # Filter menu state
        self.filters: Dict[str, bool] = {
            "towns": True,
            "resources": True,
            "boats": True,
            "buildings": True,
            "treasures": True,
        }
        self.show_menu = False
        self.menu_rect: Optional[pygame.Rect] = None
        self.menu_checkboxes: Dict[str, pygame.Rect] = {}
        try:
            self._menu_font = pygame.font.Font(None, 14)
        except Exception:  # pragma: no cover - pygame stub without font
            self._menu_font = None

        # Button to toggle the filter menu
        btn_size = 16
        btn_rect = pygame.Rect(0, 0, btn_size, btn_size)
        self._menu_button = IconButton(
            btn_rect,
            "nav_settings",
            self._toggle_menu,
            tooltip="Filters",
            size=(btn_size, btn_size),
        )

        # icon manifest and cache
        self._icon_manifest: Dict[str, str] = {}
        self._icon_cache: Dict[str, pygame.Surface] = {}
        self._load_icon_manifest()

        try:
            font = pygame.font.Font(None, 14)
            colour = constants.DARK_GREY
            self._compass = {
                "N": font.render("N", True, colour),
                "E": font.render("E", True, colour),
                "S": font.render("S", True, colour),
                "O": font.render("O", True, colour),
            }
        except Exception:  # pragma: no cover - pygame stub without font
            self._compass = {}

        # Divide the minimap into cacheable blocks
        self.block_size = 64
        self._cols = (self.size + self.block_size - 1) // self.block_size
        self._rows = (self.size + self.block_size - 1) // self.block_size
        self._block_cache: Dict[Tuple[int, int], pygame.Surface] = {}
        self._dirty_blocks = {
            (bx, by) for bx in range(self._cols) for by in range(self._rows)
        }
        self.generate()
        Minimap._instances.append(self)

    # ------------------------------------------------------------------
    def _load_icon_manifest(self) -> None:
        """Load the mapping of icon identifiers to file paths."""
        path = os.path.join(
            os.path.dirname(__file__), "..", "..", "assets", "icons", "icons.json"
        )
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, dict):
                self._icon_manifest = {str(k): str(v) for k, v in data.items()}
        except Exception:  # pragma: no cover - missing asset file
            self._icon_manifest = {}

    def _get_icon(self, name: str) -> Optional[pygame.Surface]:
        """Return a cached icon surface for ``name`` if available."""
        if name not in self._icon_cache:
            path = self._icon_manifest.get(name)
            if not path:
                return None
            try:
                surf = pygame.image.load(path).convert_alpha()
            except Exception:  # pragma: no cover - stub or missing file
                surf = pygame.Surface((8, 8), pygame.SRCALPHA)
            self._icon_cache[name] = surf
        return self._icon_cache.get(name)

    # ------------------------------------------------------------------
    def resize(self, size: int) -> None:
        """Resize the minimap and regenerate its view."""
        if size == self.size:
            return
        self.size = size
        base = pygame.Surface((size, size), pygame.SRCALPHA)
        try:
            self.surface = base.convert_alpha()
        except Exception:  # pragma: no cover - pygame stub without convert_alpha
            self.surface = base
        self._cols = (self.size + self.block_size - 1) // self.block_size
        self._rows = (self.size + self.block_size - 1) // self.block_size
        self._block_cache = {}
        self._dirty_blocks = {
            (bx, by) for bx in range(self._cols) for by in range(self._rows)
        }
        self.generate()
        if self.fog is not None:
            self.set_fog(self.fog)

    # ------------------------------------------------------------------
    def generate(self) -> None:
        """Regenerate cached block surfaces and compose the minimap."""
        if not self._dirty_blocks:
            return

        tile_w = self.size / self.world.width
        tile_h = self.size / self.world.height

        # Recompute city and POI locations each time as they are few in number
        self.city_points.clear()
        self.city_colours.clear()
        self.poi_icons.clear()
        for y in range(self.world.height):
            for x in range(self.world.width):
                tile = self.world.grid[y][x]
                cx = int((x + 0.5) * tile_w)
                cy = int((y + 0.5) * tile_h)
                if isinstance(tile.building, Town):
                    owner = getattr(tile.building, "owner", None)
                    if owner == 0:
                        colour = self.player_colour
                    elif owner == 1:
                        colour = constants.RED
                    else:
                        colour = constants.GREY
                    self.city_points.append((cx, cy))
                    self.city_colours.append(colour)
                    icon = self._get_icon("poi_dwelling")
                    if icon:
                        self.poi_icons.append((icon, cx, cy, "towns"))
                else:
                    if tile.building:
                        key = f"poi_{tile.building.id}"
                        icon = self._get_icon(key)
                        if icon:
                            self.poi_icons.append((icon, cx, cy, "buildings"))
                    if tile.treasure:
                        icon = self._get_icon("poi_treasure_chest")
                        if icon:
                            self.poi_icons.append((icon, cx, cy, "treasures"))
                    if tile.resource:
                        icon = self._get_icon(f"resource_{tile.resource}")
                        if icon:
                            self.poi_icons.append((icon, cx, cy, "resources"))
                    if tile.boat:
                        icon = self._get_icon("poi_boat")
                        if icon:
                            self.poi_icons.append((icon, cx, cy, "boats"))

        surf = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
        surf.fill(constants.BLACK)

        for by in range(self._rows):
            for bx in range(self._cols):
                bw = min(self.block_size, self.size - bx * self.block_size)
                bh = min(self.block_size, self.size - by * self.block_size)
                if (bx, by) in self._dirty_blocks:
                    block = pygame.Surface((bw, bh), pygame.SRCALPHA)
                    block.fill(constants.BLACK)
                    px0 = bx * self.block_size
                    py0 = by * self.block_size
                    px1 = px0 + bw
                    py1 = py0 + bh
                    tx0 = int(px0 / tile_w)
                    ty0 = int(py0 / tile_h)
                    tx1 = int(min(self.world.width, math.ceil(px1 / tile_w)))
                    ty1 = int(min(self.world.height, math.ceil(py1 / tile_h)))
                    for ty in range(ty0, ty1):
                        for tx in range(tx0, tx1):
                            tile = self.world.grid[ty][tx]
                            colour = BIOME_IMAGES.get(
                                tile.biome, BIOME_IMAGES["scarletia_echo_plain"]
                            )[1]
                            rect = pygame.Rect(
                                int(tx * tile_w - px0),
                                int(ty * tile_h - py0),
                                int(tile_w + 1),
                                int(tile_h + 1),
                            )
                            block.fill(colour, rect)
                    try:
                        self._block_cache[(bx, by)] = block.convert_alpha()
                    except Exception:  # pragma: no cover
                        self._block_cache[(bx, by)] = block
                surf.blit(self._block_cache[(bx, by)], (bx * self.block_size, by * self.block_size))

        try:
            self.surface = surf.convert_alpha()
        except Exception:  # pragma: no cover
            self.surface = surf
        if getattr(self.surface, "get_width", lambda: self.size)() != self.size:
            self.surface.get_width = lambda: self.size  # type: ignore[attr-defined]
            self.surface.get_height = lambda: self.size  # type: ignore[attr-defined]
        self._dirty_blocks.clear()

    # ------------------------------------------------------------------
    def invalidate(self) -> None:
        """Invalidate the entire minimap cache."""
        self._dirty_blocks.update(
            (bx, by) for bx in range(self._cols) for by in range(self._rows)
        )

    @classmethod
    def invalidate_all(cls) -> None:
        """Invalidate all existing minimap instances."""
        for inst in cls._instances:
            inst.invalidate()

    # ------------------------------------------------------------------
    def invalidate_region(self, x0: int, y0: int, x1: int, y1: int) -> None:
        """Invalidate a region of world tiles.

        ``(x0, y0)`` and ``(x1, y1)`` specify the bounds in world tile
        coordinates (inclusive). Only blocks intersecting this region will be
        regenerated on the next call to :meth:`generate`.
        """
        tile_w = self.size / self.world.width
        tile_h = self.size / self.world.height
        px0 = int(x0 * tile_w)
        py0 = int(y0 * tile_h)
        px1 = int((x1 + 1) * tile_w)
        py1 = int((y1 + 1) * tile_h)
        bx0 = max(0, px0 // self.block_size)
        by0 = max(0, py0 // self.block_size)
        bx1 = min(self._cols - 1, (max(px1 - 1, 0)) // self.block_size)
        by1 = min(self._rows - 1, (max(py1 - 1, 0)) // self.block_size)
        for bx in range(bx0, bx1 + 1):
            for by in range(by0, by1 + 1):
                self._dirty_blocks.add((bx, by))

    # ------------------------------------------------------------------
    def set_fog(self, fog: Optional[List[List[bool]]]) -> None:
        """Provide fog-of-war information.

        ``fog`` should be a 2D list matching the world's dimensions where
        ``True`` indicates the tile is hidden.  Passing ``None`` clears any
        overlay.
        """
        self.fog = fog
        self.fog_rects.clear()
        if not fog:
            return
        tile_w = self.size / self.world.width
        tile_h = self.size / self.world.height
        for y in range(self.world.height):
            for x in range(self.world.width):
                if fog[y][x]:
                    rect = pygame.Rect(int(x * tile_w), int(y * tile_h), int(tile_w + 1), int(tile_h + 1))
                    self.fog_rects.append(rect)

    # ------------------------------------------------------------------
    def _toggle_menu(self) -> None:
        """Toggle the visibility of the filter dropdown menu."""
        self.show_menu = not self.show_menu

    # ------------------------------------------------------------------
    def _center_at(self, pos: Tuple[int, int], rect: pygame.Rect) -> None:
        """Center the renderer's camera on the map position ``pos``."""
        rel_x = (pos[0] - rect.x) / rect.width
        rel_y = (pos[1] - rect.y) / rect.height
        tx = int(rel_x * self.world.width)
        ty = int(rel_y * self.world.height)
        self.renderer.center_on((tx, ty))

    def handle_event(self, evt: object, rect: pygame.Rect) -> None:
        """Handle mouse interaction for recentering the camera and filters."""
        etype = getattr(evt, "type", None)
        button = getattr(evt, "button", 0)
        # Update filter button position and delegate events to it
        size = self._menu_button.rect.width
        self._menu_button.rect.x = rect.x + rect.width - size - 4
        self._menu_button.rect.y = rect.y + 4
        if self._menu_button.handle(evt):
            return

        if etype == MOUSEBUTTONDOWN:
            if self.show_menu:
                if self.menu_rect and self.menu_rect.collidepoint(evt.pos):
                    if button == 1:
                        for key, box in self.menu_checkboxes.items():
                            if box.collidepoint(evt.pos):
                                self.filters[key] = not self.filters[key]
                                return
                else:
                    self.show_menu = False
                    return
            if button == 1 and not self.show_menu:
                x, y = evt.pos
                if rect.x <= x < rect.x + rect.width and rect.y <= y < rect.y + rect.height:
                    self._dragging = True
                    self._center_at(evt.pos, rect)
        elif etype == MOUSEMOTION and self._dragging and not self.show_menu:
            x, y = evt.pos
            if rect.x <= x < rect.x + rect.width and rect.y <= y < rect.y + rect.height:
                self._center_at(evt.pos, rect)
        elif etype == MOUSEBUTTONUP and button == 1:
            self._dragging = False

    # ------------------------------------------------------------------
    def get_viewport_rect(self, rect: pygame.Rect) -> pygame.Rect:
        """Return the viewport rectangle in minimap coordinates."""
        scale_x = rect.width / (self.world.width * constants.TILE_SIZE)
        scale_y = rect.height / (self.world.height * constants.TILE_SIZE)
        w = self.renderer.surface.get_width() / self.renderer.zoom * scale_x
        h = self.renderer.surface.get_height() / self.renderer.zoom * scale_y
        x = rect.x + self.renderer.cam_x * scale_x
        y = rect.y + self.renderer.cam_y * scale_y
        return pygame.Rect(int(x), int(y), int(w), int(h))

    # ------------------------------------------------------------------
    def draw(self, dest: pygame.Surface, rect: pygame.Rect) -> None:
        """Draw the minimap onto ``dest`` within ``rect``."""
        dest.fill(PARCHMENT, rect)
        try:
            scaled = pygame.transform.smoothscale(self.surface, rect.size)
        except Exception:  # pragma: no cover - pygame stub without transform
            try:
                scaled = pygame.transform.scale(self.surface, rect.size)
            except Exception:  # pragma: no cover
                scaled = self.surface
        try:
            sub = dest.subsurface(rect)
            blit_back = False
        except Exception:
            sub = pygame.Surface(rect.size, pygame.SRCALPHA)
            blit_back = True
        sub.blit(scaled, (0, 0))

        scale_x = rect.width / self.size
        scale_y = rect.height / self.size
        icon_size = max(4, rect.width // 16)
        for icon, cx, cy, category in self.poi_icons:
            if not self.filters.get(category, True):
                continue
            try:
                scaled_icon = pygame.transform.smoothscale(icon, (icon_size, icon_size))
            except Exception:  # pragma: no cover - pygame stub without transform
                try:
                    scaled_icon = pygame.transform.scale(icon, (icon_size, icon_size))
                except Exception:  # pragma: no cover
                    scaled_icon = icon
            sx = int(cx * scale_x) - icon_size // 2
            sy = int(cy * scale_y) - icon_size // 2
            sub.blit(scaled_icon, (sx, sy))

        if self.filters.get("towns", True):
            for (cx, cy), colour in zip(self.city_points, self.city_colours):
                sx = int(cx * scale_x)
                sy = int(cy * scale_y)
                pygame.draw.circle(sub, colour, (sx, sy), 3)

        for fog_rect in self.fog_rects:
            r = pygame.Rect(
                int(fog_rect.x * scale_x),
                int(fog_rect.y * scale_y),
                int(fog_rect.width * scale_x),
                int(fog_rect.height * scale_y),
            )
            sub.fill(constants.BLACK, r)

        if blit_back:
            dest.blit(sub, rect)

        view = self.get_viewport_rect(rect)
        if view.x < rect.x:
            dx = rect.x - view.x
            view.x = rect.x
            view.width -= dx
        if view.y < rect.y:
            dy = rect.y - view.y
            view.y = rect.y
            view.height -= dy
        if view.x + view.width > rect.x + rect.width:
            view.width = rect.x + rect.width - view.x
        if view.y + view.height > rect.y + rect.height:
            view.height = rect.y + rect.height - view.y

        pygame.draw.rect(dest, constants.WHITE, view, 1)

        pygame.draw.rect(dest, constants.DARK_GREY, rect, 2)
        if hasattr(pygame.draw, "line"):
            for i in range(1, 4):
                x = rect.x + i * rect.width // 4
                pygame.draw.line(dest, constants.DARK_GREY, (x, rect.y), (x, rect.y + 4))
                pygame.draw.line(
                    dest,
                    constants.DARK_GREY,
                    (x, rect.y + rect.height - 4),
                    (x, rect.y + rect.height),
                )
                y = rect.y + i * rect.height // 4
                pygame.draw.line(dest, constants.DARK_GREY, (rect.x, y), (rect.x + 4, y))
                pygame.draw.line(
                    dest,
                    constants.DARK_GREY,
                    (rect.x + rect.width - 4, y),
                    (rect.x + rect.width, y),
                )

        if self._compass:
            n = self._compass.get("N")
            e = self._compass.get("E")
            s = self._compass.get("S")
            o = self._compass.get("O")
            if n:
                dest.blit(n, (rect.centerx - n.get_width() // 2, rect.y + 2))
            if s:
                dest.blit(
                    s,
                    (rect.centerx - s.get_width() // 2, rect.bottom - s.get_height() - 2),
                )
            if e:
                dest.blit(
                    e,
                    (rect.right - e.get_width() - 2, rect.centery - e.get_height() // 2),
                )
            if o:
                dest.blit(o, (rect.x + 2, rect.centery - o.get_height() // 2))

        self._menu_button.rect.x = (
            rect.x + rect.width - self._menu_button.rect.width - 4
        )
        self._menu_button.rect.y = rect.y + 4
        self._menu_button.draw(dest)

        self._draw_menu(dest, rect)

    # ------------------------------------------------------------------
    def _draw_menu(self, dest: pygame.Surface, rect: pygame.Rect) -> None:
        if not self.show_menu:
            return
        w = min(120, rect.width - 8)
        h = min(20 * len(FILTER_LABELS) + 8, rect.height - 8)
        x = rect.x + rect.width - w - 4
        y = rect.y + self._menu_button.rect.height + 4
        if x < rect.x + 4:
            x = rect.x + 4
        if y + h > rect.y + rect.height - 4:
            y = rect.y + rect.height - h - 4
        menu = pygame.Rect(x, y, w, h)
        self.menu_rect = menu
        pygame.draw.rect(dest, constants.DARK_GREY, menu)
        inner = menu.inflate(-4, -4)
        dest.fill(PARCHMENT, inner)
        self.menu_checkboxes.clear()
        if not self._menu_font:
            return
        x = inner.x + 4
        y = inner.y + 2
        for key, label in FILTER_LABELS.items():
            box = pygame.Rect(x, y, 12, 12)
            pygame.draw.rect(dest, constants.DARK_GREY, box, 1)
            if self.filters.get(key, True):
                pygame.draw.line(dest, constants.DARK_GREY, box.topleft, box.bottomright, 2)
                pygame.draw.line(dest, constants.DARK_GREY, box.topright, box.bottomleft, 2)
            if self._menu_font:
                dest.blit(
                    self._menu_font.render(label, True, constants.DARK_GREY),
                    (box.right + 4, y - 2),
                )
            self.menu_checkboxes[key] = box
            y += 20

