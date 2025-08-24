from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from .core import Context, read_json, require_keys


@dataclass
class BoatDef:
    """Definition for a boat type loaded from ``boats.json``."""

    id: str
    movement: int
    capacity: int
    cost: Dict[str, int]
    path: str


def load_boats(ctx: Context, manifest: str = "boats.json") -> Dict[str, BoatDef]:
    """Load boat definitions from ``manifest`` using ``ctx``.

    Surfaces are loaded via the provided :class:`AssetManager` (if any) and
    registered under their boat ``id`` so other systems can reference them by
    identifier.
    """

    defs: Dict[str, BoatDef] = {}
    try:
        entries = read_json(ctx, manifest)
    except Exception:
        return defs

    for entry in entries:
        require_keys(entry, ["id", "movement", "capacity", "cost", "path"])
        bdef = BoatDef(
            id=entry["id"],
            movement=int(entry["movement"]),
            capacity=int(entry["capacity"]),
            cost={k: int(v) for k, v in entry.get("cost", {}).items()},
            path=entry["path"],
        )
        defs[bdef.id] = bdef

        # Preload and register surface under the boat id for convenience.
        try:
            if ctx.asset_loader is not None:
                surf = ctx.asset_loader.get(bdef.path)
                ctx.asset_loader[bdef.id] = surf  # type: ignore[index]
        except Exception:
            pass

    return defs
