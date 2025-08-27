"""Loader for faction-specific town building manifests."""
from __future__ import annotations

from typing import Dict, List

from .core import Context, read_json

# Mapping of faction identifiers to their town building manifest paths
FACTION_TOWN_BUILDING_MANIFESTS: Dict[str, str] = {
    "red_knights": "buildings/buildings_red_knights.json",
    "sylvan": "buildings/buildings_sylvan.json",
    "solaceheim": "buildings/buildings_solaceheim.json",
}

def load_town_buildings(ctx: Context, manifest: str) -> Dict[str, Dict[str, object]]:
    """Load town structure definitions from ``manifest``.

    The manifest is expected to contain a list of objects each describing a
    building. Only a handful of common fields are normalised so that the
    :class:`core.buildings.Town` class can consume the resulting mapping.
    Unknown keys are preserved as-is which allows experimental attributes to be
    carried through without explicit support in the loader.
    """

    try:
        entries: List[Dict[str, object]] = read_json(ctx, manifest)
    except Exception:
        return {}

    defs: Dict[str, Dict[str, object]] = {}
    for entry in entries:
        bid = entry.get("id")
        if not bid:
            continue
        data = dict(entry)
        # Normalise expected fields with sensible defaults
        data.setdefault("cost", {})
        data.setdefault("desc", "")
        data.setdefault("dwelling", {})
        data.setdefault("prereq", data.pop("requires", []))
        data.setdefault("image", data.get("image", ""))
        defs[bid] = data
    return defs


def load_faction_town_buildings(ctx: Context, faction_id: str) -> Dict[str, Dict[str, object]]:
    """Return town buildings defined for ``faction_id``."""

    manifest = FACTION_TOWN_BUILDING_MANIFESTS.get(faction_id)
    if not manifest:
        return {}
    return load_town_buildings(ctx, manifest)


__all__ = [
    "FACTION_TOWN_BUILDING_MANIFESTS",
    "load_town_buildings",
    "load_faction_town_buildings",
]
