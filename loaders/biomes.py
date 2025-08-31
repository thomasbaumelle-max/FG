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

        def _asset_exists(rel: str) -> bool:
            """Return ``True`` if an image for ``rel`` exists in search paths."""

            for base in ctx.search_paths:
                base_abs = (
                    base if os.path.isabs(base) else os.path.join(ctx.repo_root, base)
                )
                rel_path = rel
                if os.path.isdir(os.path.join(base_abs, rel_path)):
                    rel_path = os.path.join(rel_path, os.path.basename(rel_path))

                png_file = os.path.join(base_abs, f"{rel_path}.png")
                zero_file = os.path.join(base_abs, f"{rel_path}_0.png")
                if os.path.isfile(png_file) or os.path.isfile(zero_file):
                    return True

                pattern = os.path.join(base_abs, f"{rel_path}_*.png")
                if glob.glob(pattern):
                    return True
            return False

        biomes: Dict[str, Biome] = {}
        for path in files:
            data = read_json(ctx, path)
            base_dir = os.path.dirname(path)
            for entry in data:
                require_keys(entry, ["id"])
                colour = entry.get("colour", [0, 0, 0])
                entry_path = entry.get("path", "")
                if entry_path and not os.path.isabs(entry_path):
                    # By default treat paths as relative to the asset search root.
                    # When a manifest wishes to reference files relative to its own
                    # directory it can use an explicit ``./`` or ``../`` prefix.  If
                    # the resulting file does not exist there, fall back to resolving
                    # relative to the manifest location so realm-specific assets such
                    # as ``realms/<realm>/biomes/<tile>.png`` are picked up without
                    # needing explicit ``./`` prefixes.
                    if entry_path.startswith("./") or entry_path.startswith("../"):
                        entry_path = os.path.join(base_dir, entry_path)
                    elif not _asset_exists(entry_path):
                        candidate = os.path.join(base_dir, entry_path)
                        if _asset_exists(candidate):
                            entry_path = candidate
                entry_path = os.path.normpath(entry_path).replace(os.sep, "/")
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
        if base.endswith(".png"):
            key = base
        elif biome.variants > 1:
            key = f"{base}_{i}.png"
        else:
            # Support single-variant biomes whose manifest omits the ``_0`` suffix
            # by loading ``<path>.png`` instead of ``<path>_0.png``.
            key = f"{base}.png"
        surf = ctx.asset_loader.get(key) if ctx.asset_loader else None
        if surf and hasattr(surf, "get_size"):
            if surf.get_size() != (tile_size, tile_size):
                surf = scale_surface(surf, (tile_size, tile_size), smooth=False)
        tileset.surfaces.append(surf)
    return tileset
