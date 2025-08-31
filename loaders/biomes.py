"""Biome manifest adapter using :mod:`manifests.core`."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import glob
import os
import pygame

from .core import Context, read_json, require_keys
from graphics.scale import scale_surface
import constants


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
    def load(cls, ctx: Context, manifest: str = "realms/scarletia") -> None:
        """Load biome definitions.

        ``manifest`` may point to a single JSON file or to a directory. When a
        directory is supplied, all files matching ``biomes*.json`` within that
        directory are merged.
        """
        # Resolve manifest to a list of files
        files: List[str] = []
        for base in ctx.search_paths:
            base_abs = base if os.path.isabs(base) else os.path.join(ctx.repo_root, base)
            candidate = os.path.join(base_abs, manifest)
            if os.path.isdir(candidate):
                pattern = os.path.join(candidate, "biomes*.json")
                for fn in sorted(glob.glob(pattern)):
                    files.append(os.path.relpath(fn, base_abs))
                break
        else:
            files.append(manifest)

        biomes: Dict[str, Biome] = {}
        for path in files:
            data = read_json(ctx, path)
            for entry in data:
                require_keys(entry, ["id"])
                colour = entry.get("colour", [0, 0, 0])
                biome = Biome(
                    id=entry["id"],
                    type=entry.get("type", ""),
                    description=entry.get("description", ""),
                    path=entry.get("path", ""),
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
        cls._biomes = biomes
        # Refresh derived mappings in constants
        constants.BIOME_BASE_IMAGES = constants.build_biome_base_images()
        constants.DEFAULT_BIOME_WEIGHTS = constants.build_default_biome_weights()
        constants.BIOME_PRIORITY = constants.build_biome_priority()
        from core import world as core_world
        core_world.init_biome_images()
        core_world.load_biome_char_map(ctx, manifest)
        try:
            from ui.widgets.minimap import Minimap
            Minimap.invalidate_all()
        except Exception:
            pass

    @classmethod
    def get(cls, biome_id: str) -> Optional[Biome]:
        return cls._biomes.get(biome_id)


def load_tileset(ctx: Context, biome: Biome, tile_size: Optional[int] = None) -> BiomeTileset:
    if tile_size is None:
        tile_size = constants.COMBAT_TILE_SIZE
    tileset = BiomeTileset(id=biome.id, path=biome.path, variants=biome.variants)
    base = biome.path
    for i in range(max(1, biome.variants)):
        key = f"{base}_{i}.png" if not base.endswith(".png") else base
        surf = ctx.asset_loader.get(key) if ctx.asset_loader else None
        if surf and hasattr(surf, "get_size"):
            if surf.get_size() != (tile_size, tile_size):
                surf = scale_surface(surf, (tile_size, tile_size), smooth=False)
        tileset.surfaces.append(surf)
    return tileset
