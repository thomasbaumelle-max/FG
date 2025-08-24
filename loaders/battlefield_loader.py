"""Loader for battlefield definitions.

This module provides a small helper to read battlefield metadata from a JSON
manifest. Each entry specifies an identifier, image path and optional hero
position used when rendering the combat background.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Tuple
import json
import os


@dataclass
class BattlefieldDef:
    """Definition of a combat battlefield."""

    id: str
    image: str
    hero_pos: Tuple[int, int] = (0, 0)
    meta: Dict[str, Any] = field(default_factory=dict)


def load_battlefields(path: str, assets: Dict[str, Any] | None = None) -> Dict[str, BattlefieldDef]:
    """Load battlefield definitions from ``path``.

    Parameters
    ----------
    path:
        Path to the JSON manifest containing battlefield entries.
    assets:
        Optional asset manager used to preload images referenced by entries.

    Returns
    -------
    dict
        Mapping of battlefield id to :class:`BattlefieldDef`.
    """

    defs: Dict[str, BattlefieldDef] = {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception:
        return defs

    for entry in data:
        bid = entry.get("id")
        if not bid:
            continue
        image = entry.get("image", "")
        pos = entry.get("hero_pos", [0, 0])
        hero_pos = (int(pos[0]), int(pos[1])) if isinstance(pos, (list, tuple)) and len(pos) >= 2 else (0, 0)
        meta = {k: v for k, v in entry.items() if k not in {"id", "image", "hero_pos"}}
        defs[bid] = BattlefieldDef(id=bid, image=image, hero_pos=hero_pos, meta=meta)
        if assets is not None and image:
            try:
                assets.get(image)
            except Exception:
                pass
    return defs
