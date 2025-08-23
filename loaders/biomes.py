"""Biome manifest adapter using :mod:`manifests.core`."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

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
    terrain_cost: int = 1
    passable: bool = True
    overlays: List[str] = field(default_factory=list)
    vision_bonus: int = 0


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
    def load(cls, ctx: Context, manifest: str = "biomes/biomes.json") -> None:
        data = read_json(ctx, manifest)
        biomes: Dict[str, Biome] = {}
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
                terrain_cost=int(entry.get("terrain_cost", entry.get("movement_cost", 1))),
                passable=bool(entry.get("passable", True)),
                overlays=list(entry.get("overlays", [])),
                vision_bonus=int(entry.get("vision_bonus", 0)),
            )
            biomes[biome.id] = biome
        cls._biomes = biomes
        # Refresh derived mappings in constants
        constants.BIOME_BASE_IMAGES = constants.build_biome_base_images()

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
