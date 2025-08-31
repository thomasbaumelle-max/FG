"""Biome manifest adapter using :mod:`manifests.core`."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import glob
import os
import logging
import pygame

from .core import Context, read_json, require_keys
from graphics.scale import scale_surface
import constants

logger = logging.getLogger(__name__)


@dataclass
class Biome:
    id: str
    type: str
    description: str
    path: str
    variants: int
    colour: Tuple[int, int, int]
    flora: List[str]
    terrain_cost: float = 1.0
    passable: bool = True
    overlays: List[str] = field(default_factory=list)
    vision_bonus: int = 0
    weight: float = 1.0
    priority: int = 0


@dataclass
class BiomeTileset:
    id: str
    path: str
    variants: int
    surfaces: List[pygame.Surface] = field(default_factory=list)

    def surface_for(self, variant: int) -> pygame.Surface:
        if not self.surfaces:
            size = constants.COMBAT_TILE_SIZE
            return pygame.Surface((size, size), pygame.SRCALPHA)
        return self.surfaces[variant % len(self.surfaces)]

    def variant_for(self, x: int, y: int) -> int:
        if self.variants <= 0:
            return 0
        return (x * 928371 + y * 689287) % self.variants


class BiomeCatalog:
    _biomes: Dict[str, Biome] = {}

    @classmethod
    def load(cls, ctx: Context, realm: str = "scarletia") -> None:
        """Load biome definitions for a realm.

        Always loads ``assets/biomes/biomes.json`` first.  If ``realm`` is
        provided, any ``biomes*.json`` files under ``assets/realms/<realm>/`` are
        merged on top, allowing realms to extend or override the common
        definitions.
        """
        files: List[str] = []
        for base in ctx.search_paths:
            base_abs = (
                base if os.path.isabs(base) else os.path.join(ctx.repo_root, base)
            )
            candidate = os.path.join(base_abs, "biomes", "biomes.json")
            if os.path.isfile(candidate):
                files.append(os.path.relpath(candidate, base_abs).replace(os.sep, "/"))
        if not files:
            files.append("biomes/biomes.json")

        if realm:
            for base in ctx.search_paths:
                base_abs = (
                    base if os.path.isabs(base) else os.path.join(ctx.repo_root, base)
                )
                candidate = os.path.join(base_abs, "realms", realm)
                if os.path.isdir(candidate):
                    pattern = os.path.join(candidate, "biomes*.json")
                    for fn in sorted(glob.glob(pattern)):
                        rel = os.path.relpath(fn, base_abs).replace(os.sep, "/")
                        files.append(rel)

        biomes: Dict[str, Biome] = {}
        for path in files:
            data = read_json(ctx, path)
            base_dir = os.path.dirname(path)
            for entry in data:
                require_keys(entry, ["id"])
                colour = entry.get("colour", [0, 0, 0])
                entry_path = entry.get("path", "")
                if entry_path:
                    entry_path = os.path.normpath(
                        entry_path
                        if os.path.isabs(entry_path)
                        else os.path.join(base_dir, entry_path)
                    ).replace(os.sep, "/")
                if entry_path:
                    img_rel = (
                        entry_path if entry_path.endswith(".png") else f"{entry_path}.png"
                    )
                    found = False
                    for base in ctx.search_paths:
                        base_abs = (
                            base if os.path.isabs(base) else os.path.join(ctx.repo_root, base)
                        )
                        if os.path.isfile(os.path.join(base_abs, img_rel)):
                            found = True
                            break
                        if os.path.isfile(os.path.join(base_abs, f"{entry_path}_0.png")):
                            found = True
                            break
                    if not found:
                        msg = (
                            f"Biome {entry['id']} missing image '{img_rel}' "
                            f"(search_paths={list(ctx.search_paths)})"
                        )
                        logger.error(msg)
                        if ctx.asset_loader:
                            raise FileNotFoundError(msg)
                biome = Biome(
                    id=entry["id"],
                    type=entry.get("type", ""),
                    description=entry.get("description", ""),
                    path=entry_path,
                    variants=int(entry.get("variants", 1)),
                    colour=tuple(colour),
                    flora=list(entry.get("flora", [])),
                    terrain_cost=float(
                        constants.TERRAIN_COSTS.get(entry.get("type", ""), 1.0)
                    ),
                    passable=bool(entry.get("passable", True)),
                    overlays=list(entry.get("overlays", [])),
                    vision_bonus=int(entry.get("vision_bonus", 0)),
                    weight=float(entry.get("weight", 1.0)),
                    priority=int(entry.get("priority", 0)),
                )
                biomes[biome.id] = biome
                if ctx.asset_loader and biome.path:
                    key = (
                        biome.path
                        if biome.path.endswith(".png")
                        else f"{biome.path}.png"
                    )
                    _sentinel = object()
                    if (
                        ctx.asset_loader.get(key, default=_sentinel, biome_id=biome.id)
                        is _sentinel
                    ):
                        raise RuntimeError(
                            f"Biome {biome.id} missing image '{key}'"
                            f" (search_paths={list(ctx.search_paths)})"
                        )
        cls._biomes = biomes
        # Refresh derived mappings in constants
        constants.BIOME_BASE_IMAGES = constants.build_biome_base_images()
        constants.DEFAULT_BIOME_WEIGHTS = constants.build_default_biome_weights()
        constants.BIOME_PRIORITY = constants.build_biome_priority()
        from core import world as core_world
        core_world.init_biome_images()
        core_world.load_biome_char_map(ctx, realm)
        try:
            from ui.widgets.minimap import Minimap
            Minimap.invalidate_all()
        except Exception:
            pass

    @classmethod
    def get(cls, biome_id: str) -> Optional[Biome]:
        return cls._biomes.get(biome_id)


def load_tileset(
    ctx: Context,
    biome: Biome,
    tile_size: Optional[int] = None,
    variants: Optional[int] = None,
) -> BiomeTileset:
    if tile_size is None:
        tile_size = constants.COMBAT_TILE_SIZE

    base = biome.path[:-4] if biome.path.endswith(".png") else biome.path

    matches: List[str] = []
    # If no variant count is supplied, try to auto-detect available files
    if variants is None:
        seen: set[str] = set()
        for root in ctx.search_paths:
            root_abs = root if os.path.isabs(root) else os.path.join(ctx.repo_root, root)
            pattern = os.path.join(root_abs, f"{base}_*.png")
            for fn in sorted(glob.glob(pattern)):
                rel = os.path.relpath(fn, root_abs).replace(os.sep, "/")
                if rel not in seen:
                    matches.append(rel)
                    seen.add(rel)
        if not matches:
            for root in ctx.search_paths:
                root_abs = root if os.path.isabs(root) else os.path.join(ctx.repo_root, root)
                candidate = os.path.join(root_abs, f"{base}.png")
                if os.path.isfile(candidate):
                    matches.append(
                        os.path.relpath(candidate, root_abs).replace(os.sep, "/")
                    )
                    break
        variants = len(matches) if matches else 1
    else:
        variants = max(variants, 1)

    if biome.variants > variants:
        logger.warning(
            "Biome %s specifies %d variants but only %d files found",
            biome.id,
            biome.variants,
            variants,
        )

    tileset = BiomeTileset(id=biome.id, path=biome.path, variants=variants)

    if tileset.variants > 1:
        attempted: List[str] = []
        sentinel = object()
        for i in range(tileset.variants):
            key = f"{base}_{i}.png"
            attempted.append(key)
            surf = (
                ctx.asset_loader.get(key, default=sentinel) if ctx.asset_loader else None
            )
            if surf is sentinel:
                continue
            if surf and hasattr(surf, "get_size"):
                if surf.get_size() != (tile_size, tile_size):
                    surf = scale_surface(surf, (tile_size, tile_size), smooth=False)
            tileset.surfaces.append(surf)
        if not tileset.surfaces:
            raise RuntimeError(
                f"Biome {biome.id} missing tileset images {attempted}"
            )
    else:
        sentinel = object()
        attempted = [
            matches[0]
            if matches
            else (biome.path if biome.path.endswith(".png") else f"{base}.png")
        ]
        key = attempted[0]
        surf = (
            ctx.asset_loader.get(key, default=sentinel) if ctx.asset_loader else None
        )
        if surf is sentinel:
            raise RuntimeError(
                f"Biome {biome.id} missing tileset images {attempted}"
            )
        if surf and hasattr(surf, "get_size"):
            if surf.get_size() != (tile_size, tile_size):
                surf = scale_surface(surf, (tile_size, tile_size), smooth=False)
        tileset.surfaces.append(surf)
    return tileset
