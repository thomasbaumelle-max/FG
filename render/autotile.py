"""Autotiling utilities for biome transitions and shorelines.

This module provides an ``AutoTileRenderer`` that draws tiles with
NESW autotiling, stable pseudo-random variants, and optional shoreline
overlays.  The renderer supports blending biomes together using masks
and can be integrated with an asset manager for image loading.

Example integration::

    assets = AssetManager(root="assets", tile_size=64)
    r = AutoTileRenderer(assets, tile_size=64)
    r.register_biome("grass", ["tiles/grass_0", "tiles/grass_1", "tiles/grass_2"])
    r.set_coast_overlays(
        edges={
            "n": "overlays/mask_n", "e": "overlays/mask_e",
            "s": "overlays/mask_s", "w": "overlays/mask_w",
        },
        corners={
            "ne": "overlays/mask_ne", "nw": "overlays/mask_nw",
            "se": "overlays/mask_se", "sw": "overlays/mask_sw",
        },
    )
    r.draw_map(screen, (ox, oy), biome_grid, water_map)

``biome_grid`` is a 2D array of biome names and ``water_map`` is a 2D array
of booleans where ``True`` marks water cells.
"""

from __future__ import annotations
import pygame
from typing import Dict, List, Optional, Tuple

# NESW directions and bitmask
DIRS = {
    "n": (0, -1, 1),  # (dx, dy, bit)
    "e": (1,  0, 2),
    "s": (0,  1, 4),
    "w": (-1, 0, 8),
}
CORNERS = {
    "ne": (1, -1),
    "nw": (-1, -1),
    "se": (1, 1),
    "sw": (-1, 1),
}


def apply_overlay(
    surface: pygame.Surface,
    base_img: Optional[pygame.Surface],
    overlay_img: Optional[pygame.Surface],
    mask: Optional[pygame.Surface],
) -> pygame.Surface:
    """Compose ``overlay_img`` onto ``surface`` using ``mask``.

    ``base_img`` is first blitted if provided.  When ``mask`` is given, it is
    multiplied with the overlay before blitting, allowing the caller to shape
    the overlay with an alpha mask.  The destination surface is returned to
    allow chaining calls.
    """

    if base_img:
        surface.blit(base_img, (0, 0))

    if overlay_img:
        if mask:
            overlay = overlay_img.copy()
            blend_flag = getattr(pygame, "BLEND_RGBA_MULT", 0)
            overlay.blit(mask, (0, 0), special_flags=blend_flag)
        else:
            overlay = overlay_img
        surface.blit(overlay, (0, 0))

    return surface

def _stable_variant_index(x: int, y: int, n: int, base_weight: int = 2) -> int:
    """Return a stable index based on ``x`` and ``y`` while favoring the base tile.

    ``n`` is the total number of images available for the biome. Index ``0`` is
    the primary image and the remaining indices are variants used to break up
    repetition. ``base_weight`` is the relative weight of the base tile compared to
    the variants (each variant has a weight of ``1``). A lower value increases the
    frequency of variants. The function is deterministic and does not rely on the
    :mod:`random` module, ensuring stable renders across sessions.
    """
    if n <= 1:
        return 0

    # 2D hash with prime numbers to avoid obvious patterns
    h = (x * 73856093) ^ (y * 19349663)
    total = base_weight + (n - 1)
    r = (h & 0x7FFFFFFF) % total
    if r < base_weight:
        return 0
    # Uniform distribution of the remaining variants
    return 1 + (r - base_weight) % (n - 1)

class AutoTileRenderer:
    """Render tiles with biome transitions and shoreline overlays."""

    def __init__(self, assets: Optional[object], tile_size: int = 64):
        """Create a renderer.

        Parameters
        ----------
        assets:
            Object with ``get(key) -> pygame.Surface`` (for example, an
            ``AssetManager``). When ``None`` a placeholder surface is used.
        tile_size:
            Square size of tiles in pixels.
        """
        self.assets = assets
        self.tile = tile_size
        self.biomes: Dict[str, List[str]] = {}       # biome -> list of asset keys
        self.edge_keys: Dict[str, str] = {}          # "n","e","s","w" -> asset key
        self.corner_keys: Dict[str, str] = {}        # "ne","nw","se","sw" -> asset key
        self._cache: Dict[Tuple[str, Tuple[int,int]], pygame.Surface] = {}

    # ---------- Resource registration ----------
    def register_biome(self, biome: str, base_keys: List[str]) -> None:
        """Associate a biome with a base image and its variants."""
        self.biomes[biome] = list(base_keys)

    def set_coast_overlays(self, edges: Dict[str, str], corners: Dict[str, str]) -> None:
        """Associate shoreline edge and corner overlay assets."""
        self.edge_keys.update(edges or {})
        self.corner_keys.update(corners or {})

    # ---------- Image loading/caching ----------
    def _get_image(self, key: str, size: Optional[Tuple[int,int]] = None) -> pygame.Surface:
        if not key:
            return self._placeholder(size)
        size = size or (self.tile, self.tile)
        ck = (key, size)
        if ck in self._cache:
            return self._cache[ck]
        surf: Optional[pygame.Surface] = None
        if self.assets and hasattr(self.assets, "get"):
            surf = self.assets.get(key)
        if isinstance(surf, pygame.Surface):
            if surf.get_size() != size:
                surf = pygame.transform.smoothscale(surf, size)
        else:
            try:
                img = pygame.image.load(key)
                img = img.convert_alpha()
                surf = pygame.transform.smoothscale(img, size)
            except Exception:
                surf = self._placeholder(size)
        self._cache[ck] = surf
        return surf

    def _placeholder(self, size: Optional[Tuple[int,int]]) -> pygame.Surface:
        w, h = size or (self.tile, self.tile)
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        s.fill((255, 0, 255, 140))
        pygame.draw.rect(s, (0, 0, 0, 180), s.get_rect(), 2)
        return s

    # ---------- Mask calculations ----------
    @staticmethod
    def _in_bounds(grid_w: int, grid_h: int, x: int, y: int) -> bool:
        return 0 <= x < grid_w and 0 <= y < grid_h

    def _mask_nesw(self, water: List[List[bool]], x: int, y: int) -> int:
        """Return the NESW bitmask (1,2,4,8) based on surrounding water."""
        h = len(water)
        w = len(water[0]) if h else 0
        mask = 0
        for d, (dx, dy, bit) in DIRS.items():
            nx, ny = x + dx, y + dy
            if self._in_bounds(w, h, nx, ny) and water[ny][nx]:
                mask |= bit
        return mask

    def _corner_needed(self, water: List[List[bool]], x: int, y: int, corner: str, n_mask: int) -> bool:
        """Return ``True`` if a concave corner overlay is needed.

        A corner overlay is used when two adjacent sides are water but the
        diagonal tile is not, smoothing the shoreline.
        """
        dx, dy = CORNERS[corner]
        h = len(water)
        w = len(water[0]) if h else 0
        # Sides involved for this corner
        a_dir = "n" if dy < 0 else "s"
        b_dir = "e" if dx > 0 else "w"
        a_bit = DIRS[a_dir][2]
        b_bit = DIRS[b_dir][2]
        if (n_mask & a_bit) and (n_mask & b_bit):
            nx, ny = x + dx, y + dy
            if not (self._in_bounds(w, h, nx, ny) and water[ny][nx]):
                return True
        return False

    # ---------- Rendering ----------
    def draw_cell(
        self,
        surface: pygame.Surface,
        origin: Tuple[int, int],
        x: int,
        y: int,
        biome_grid: List[List[str]],
        water: List[List[bool]],
        biome_priority: Optional[Dict[str, int]] = None,
        masks: Optional[Dict[str, Dict[str, pygame.Surface]]] = None,
        alpha_edges: int = 255,
        alpha_corners: int = 255,
    ) -> None:
        """Draw a cell at ``(x, y)`` with biome transitions and shorelines."""

        ox, oy = origin
        px = ox + x * self.tile
        py = oy + y * self.tile

        biome = biome_grid[y][x]

        # Temporary surface to compose the tile
        tile_surf = pygame.Surface((self.tile, self.tile), pygame.SRCALPHA)

        # 1) base variant
        keys = self.biomes.get(biome, [])
        key = keys[_stable_variant_index(x, y, len(keys))] if keys else ""
        base = self._get_image(key, size=(self.tile, self.tile))
        apply_overlay(tile_surf, base, None, None)

        # If the tile itself is water, skip shoreline overlays
        if not water[y][x]:
            # 2) edges
            mask = self._mask_nesw(water, x, y)
            for d in ("n", "e", "s", "w"):
                if mask & DIRS[d][2]:
                    k = self.edge_keys.get(d, "")
                    if not k:
                        continue
                    edge = self._get_image(k, size=(self.tile, self.tile))
                    if alpha_edges != 255:
                        edge = edge.copy()
                        edge.set_alpha(alpha_edges)
                    tile_surf.blit(edge, (0, 0))

            # 3) corners (simple concave corners)
            for c in ("ne", "nw", "se", "sw"):
                if self._corner_needed(water, x, y, c, mask):
                    k = self.corner_keys.get(c, "")
                    if not k:
                        continue
                    corner = self._get_image(k, size=(self.tile, self.tile))
                    if alpha_corners != 255:
                        corner = corner.copy()
                        corner.set_alpha(alpha_corners)
                    tile_surf.blit(corner, (0, 0))

        # 4) transitions between biomes using masks
        if biome_priority and masks:
            cur_prio = biome_priority.get(biome, 0)
            h = len(biome_grid)
            w = len(biome_grid[0]) if h else 0

            edge_masks = masks.get("edge", {})
            for d, (dx, dy, _) in DIRS.items():
                mask_img = edge_masks.get(d)
                if not mask_img:
                    continue
                nx, ny = x + dx, y + dy
                if not self._in_bounds(w, h, nx, ny):
                    continue
                nb_biome = biome_grid[ny][nx]
                if nb_biome == biome:
                    continue
                if biome_priority.get(nb_biome, 0) <= cur_prio:
                    continue
                keys = self.biomes.get(nb_biome, [])
                k = keys[_stable_variant_index(nx, ny, len(keys))] if keys else ""
                overlay = self._get_image(k, size=(self.tile, self.tile))
                apply_overlay(tile_surf, None, overlay, mask_img)

            corner_masks = masks.get("corner", {})
            for c, (dx, dy) in CORNERS.items():
                mask_img = corner_masks.get(c)
                if not mask_img:
                    continue
                nx, ny = x + dx, y + dy
                if not self._in_bounds(w, h, nx, ny):
                    continue
                nb_biome = biome_grid[ny][nx]
                if nb_biome == biome:
                    continue
                if biome_priority.get(nb_biome, 0) <= cur_prio:
                    continue
                keys = self.biomes.get(nb_biome, [])
                k = keys[_stable_variant_index(nx, ny, len(keys))] if keys else ""
                overlay = self._get_image(k, size=(self.tile, self.tile))
                apply_overlay(tile_surf, None, overlay, mask_img)

        # Blit final composition
        surface.blit(tile_surf, (px, py))

    def draw_map(
        self,
        surface: pygame.Surface,
        origin: Tuple[int,int],
        biome_grid: List[List[str]],
        water_map: List[List[bool]],
        biome_priority: Optional[Dict[str, int]] = None,
        masks: Optional[Dict[str, Dict[str, pygame.Surface]]] = None,
    ) -> None:
        """Draw the entire map in top-down view (no culling)."""
        h = len(biome_grid)
        if not h:
            return
        w = len(biome_grid[0])
        for y in range(h):
            for x in range(w):
                self.draw_cell(
                    surface,
                    origin,
                    x,
                    y,
                    biome_grid,
                    water_map,
                    biome_priority,
                    masks,
                )
