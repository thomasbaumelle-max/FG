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
import pygame

import constants
from core.world import WorldMap, BIOME_IMAGES
from render.world_renderer import WorldRenderer
from core.buildings import Town

# Fallback event type constants for environments with a pygame stub
MOUSEBUTTONDOWN = getattr(pygame, "MOUSEBUTTONDOWN", 1)
MOUSEBUTTONUP = getattr(pygame, "MOUSEBUTTONUP", 2)
MOUSEMOTION = getattr(pygame, "MOUSEMOTION", 3)


class Minimap:
    """Render and interact with a small overview map."""

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
        self.city_points: List[Tuple[int, int]] = []
        self.fog_rects: List[pygame.Rect] = []
        self.fog: Optional[List[List[bool]]] = None
        self._dragging = False

        # Divide the minimap into cacheable blocks
        self.block_size = 64
        self._cols = (self.size + self.block_size - 1) // self.block_size
        self._rows = (self.size + self.block_size - 1) // self.block_size
        self._block_cache: Dict[Tuple[int, int], pygame.Surface] = {}
        self._dirty_blocks = {
            (bx, by) for bx in range(self._cols) for by in range(self._rows)
        }
        self.generate()

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

        # Recompute city locations every time as they are few in number
        self.city_points.clear()
        for y in range(self.world.height):
            for x in range(self.world.width):
                tile = self.world.grid[y][x]
                if isinstance(tile.building, Town) and tile.building.owner == 0:
                    cx = int((x + 0.5) * tile_w)
                    cy = int((y + 0.5) * tile_h)
                    self.city_points.append((cx, cy))

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
    def _center_at(self, pos: Tuple[int, int], rect: pygame.Rect) -> None:
        """Center the renderer's camera on the map position ``pos``."""
        rel_x = (pos[0] - rect.x) / rect.width
        rel_y = (pos[1] - rect.y) / rect.height
        tx = int(rel_x * self.world.width)
        ty = int(rel_y * self.world.height)
        self.renderer.center_on((tx, ty))

    def handle_event(self, evt: object, rect: pygame.Rect) -> None:
        """Handle mouse interaction for recentering the camera."""
        if getattr(evt, "type", None) == MOUSEBUTTONDOWN and getattr(evt, "button", 0) == 1:
            x, y = evt.pos
            if rect.x <= x < rect.x + rect.width and rect.y <= y < rect.y + rect.height:
                self._dragging = True
                self._center_at(evt.pos, rect)
        elif getattr(evt, "type", None) == MOUSEMOTION and self._dragging:
            x, y = evt.pos
            if rect.x <= x < rect.x + rect.width and rect.y <= y < rect.y + rect.height:
                self._center_at(evt.pos, rect)
        elif getattr(evt, "type", None) == MOUSEBUTTONUP and getattr(evt, "button", 0) == 1:
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
        try:
            scaled = pygame.transform.smoothscale(self.surface, rect.size)
        except Exception:  # pragma: no cover - pygame stub without transform
            try:
                scaled = pygame.transform.scale(self.surface, rect.size)
            except Exception:  # pragma: no cover
                scaled = self.surface
        dest.blit(scaled, rect)

        scale_x = rect.width / self.size
        scale_y = rect.height / self.size
        for cx, cy in self.city_points:
            sx = rect.x + int(cx * scale_x)
            sy = rect.y + int(cy * scale_y)
            pygame.draw.circle(dest, self.player_colour, (sx, sy), 3)
        for fog_rect in self.fog_rects:
            r = pygame.Rect(
                rect.x + int(fog_rect.x * scale_x),
                rect.y + int(fog_rect.y * scale_y),
                int(fog_rect.width * scale_x),
                int(fog_rect.height * scale_y),
            )
            dest.fill(constants.BLACK, r)

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
