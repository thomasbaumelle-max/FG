"""Adapters for building manifests."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import pygame

from .asset_manager import AssetManager
from .core import Context, read_json, expand_variants


Vec2 = Tuple[int, int]


@dataclass
class BuildingAsset:
    """Description of a world map building.

    The schema intentionally mirrors :class:`FloraAsset` so that manifests are
    consistent across asset types.  ``provides`` describes the resource granted
    each day by the building (if any).
    """

    id: str
    provides: Optional[Dict[str, object]] = None  # {"resource": str, "per_day": int}
    growth_per_week: Dict[str, int] = field(default_factory=dict)  # dwellings
    footprint: List[Vec2] = None  # list of (x, y) coordinates relative to origin
    anchor_px: Vec2 = (32, 64)
    passable: bool = False
    occludes: bool = True
    path: Optional[str] = None  # préfixe relatif
    variants: int = 1
    files: List[str] = field(default_factory=list)  # chemins relatifs PNG
    scale: float = 1.0
    upgrade_cost: Dict[str, int] = field(default_factory=dict)
    production_per_level: Dict[str, int] = field(default_factory=dict)
    requires: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:  # pragma: no cover - trivial
        if self.footprint is None:
            self.footprint = [(0, 0)]

    # ------------------------------------------------------------------
    def file_list(self) -> List[str]:
        """Return potential image file paths for this building."""

        if self.files:
            return list(self.files)
        entry = {"path": self.path, "variants": self.variants}
        return expand_variants(entry)
def get_surface(
    asset: BuildingAsset, asset_mgr: AssetManager, tile_size: int
) -> Tuple[pygame.Surface, float]:
    """Return a scaled surface for ``asset`` and the scale factor used."""

    files = asset.file_list()
    if not files:
        return asset_mgr.get(""), 1.0

    path = files[0]
    surf = asset_mgr.get(path)

    try:
        target_w = (max(x for x, _ in asset.footprint) + 1) * tile_size
    except ValueError:
        target_w = tile_size

    src_w = surf.get_width() or 1
    scale = target_w / src_w

    if (
        scale != 1.0
        and hasattr(pygame, "transform")
        and hasattr(pygame.transform, "smoothscale")
    ):
        new_size = (
            int(round(surf.get_width() * scale)),
            int(round(surf.get_height() * scale)),
        )
        surf = pygame.transform.smoothscale(surf, new_size)

    return surf, scale


def load_buildings(
    ctx: Context, manifest: str = "buildings/buildings.json"
) -> Dict[str, BuildingAsset]:
    """Return building definitions from ``manifest`` as :class:`BuildingAsset`.

    ``footprint`` may be provided either as ``[w, h]`` describing a rectangular
    area or as an explicit list of coordinate pairs.
    """

    try:
        entries = read_json(ctx, manifest)
    except Exception:
        return {}

    defs: Dict[str, BuildingAsset] = {}
    for entry in entries:
        fp = entry.get("footprint", [1, 1])
        if isinstance(fp, (list, tuple)) and len(fp) == 2 and all(
            isinstance(v, (int, float)) for v in fp
        ):
            w, h = int(fp[0]), int(fp[1])
            footprint = [(x, y) for y in range(h) for x in range(w)]
        else:
            footprint = [tuple(p) for p in fp]
        files = expand_variants(entry)
        # Skip entries that do not reference any image files.  ``expand_variants``
        # returns an empty list when neither ``path`` nor ``files`` is provided,
        # which means this definition cannot be rendered on the world map and
        # would otherwise cause downstream code to crash when trying to access
        # the first file in the list.
        if not files:
            continue

        a = BuildingAsset(
            id=entry["id"],
            provides=entry.get("provides"),
            growth_per_week=dict(entry.get("growth_per_week", {})),
            footprint=footprint,
            anchor_px=tuple(entry.get("anchor_px", (32, 64))),
            passable=bool(entry.get("passable", False)),
            occludes=bool(entry.get("occludes", True)),
            path=entry.get("path"),
            variants=int(entry.get("variants", 1)),
            files=files,
            upgrade_cost=dict(entry.get("upgrade_cost", {})),
            production_per_level=dict(entry.get("production_per_level", {})),
            requires=list(entry.get("requires", [])),
        )
        defs[a.id] = a
    return defs


def load_default_buildings() -> Dict[str, BuildingAsset]:
    """Load building definitions using the repository's asset paths."""

    repo_root = os.path.dirname(os.path.dirname(__file__))
    search: List[str] = []
    extra = os.environ.get("FG_ASSETS_DIR")
    if extra:
        search.extend(p for p in extra.split(os.pathsep) if p)
    search.append(os.path.join(repo_root, "assets"))
    ctx = Context(repo_root=repo_root, search_paths=search, asset_loader=None)
    return load_buildings(ctx)


BUILDINGS: Dict[str, BuildingAsset] = load_default_buildings()


def register_buildings(ctx: Context, manifest: str) -> None:
    """Load additional building definitions and register them globally."""

    BUILDINGS.update(load_buildings(ctx, manifest))


