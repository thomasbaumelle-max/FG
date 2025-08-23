"""Helper for loading resource manifests into the asset manager.

This small loader mirrors the behaviour of :mod:`flora_loader` but for simple
map resources such as gold or wood.  Entries are read from a JSON manifest using
``path``/``variants`` fields and their associated images are loaded via an
:class:`~asset_manager.AssetManager`.
The loaded surfaces are stored back into the asset manager under the resource
identifier so the rest of the game can reference them by ID.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from .core import Context, read_json, expand_variants
from graphics.scale import scale_with_anchor
import constants


@dataclass
class ResourceDef:
    """Definition of a map resource parsed from the manifest."""

    id: str
    image: str
    passable: bool = True
    income: Optional[Dict[str, int]] = None


def load_resources(
    ctx: Context,
    manifest: str = "resources/resources.json",
    tile_size: int = constants.TILE_SIZE,
) -> Dict[str, ResourceDef]:
    """Load resource definitions and surfaces from ``manifest`` using ``ctx``."""

    defs: Dict[str, ResourceDef] = {}
    try:
        entries = read_json(ctx, manifest)
    except Exception:
        return defs

    for entry in entries:
        rid = entry.get("id")
        files = expand_variants(entry)
        if not rid or not files:
            continue

        img = files[0]
        rdef = ResourceDef(
            id=rid,
            image=img,
            passable=bool(entry.get("passable", True)),
            income=entry.get("income"),
        )

        try:
            surf = ctx.asset_loader.get(img) if ctx.asset_loader else None
            if surf is not None:
                surf, _ = scale_with_anchor(
                    surf, (tile_size, tile_size), smooth=False
                )
                ctx.asset_loader[rid] = surf  # type: ignore[index]
        except Exception:
            # Even if the image fails to load we still keep the definition so
            # that gameplay data remains available.
            pass

        defs[rid] = rdef

    return defs

