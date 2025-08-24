"""Loading helpers for faction definitions."""

from __future__ import annotations

import os
from typing import Dict

from .core import Context, read_json
from core.faction import FactionDef
from . import building_loader


def load_factions(ctx: Context, directory: str = "factions") -> Dict[str, FactionDef]:
    """Load all faction definitions found in ``directory``.

    Each JSON file in the directory represents a single :class:`FactionDef`.
    Unique buildings declared by factions are registered with the global
    building catalogue via :func:`building_loader.register_buildings`.
    """

    factions: Dict[str, FactionDef] = {}
    base = os.path.join(ctx.repo_root, "assets", directory)
    if not os.path.isdir(base):
        return factions
    for fname in os.listdir(base):
        if not fname.endswith(".json"):
            continue
        rel_path = os.path.join(directory, fname)
        try:
            data = read_json(ctx, rel_path)
        except Exception:
            continue
        fdef = FactionDef(
            id=data["id"],
            name=data.get("name", data["id"].replace("_", " ").title()),
            doctrine=dict(data.get("doctrine", {})),
            favored_spells=list(data.get("favored_spells", [])),
            unit_tags={k: list(v) for k, v in data.get("unit_tags", {}).items()},
            unique_buildings=list(data.get("unique_buildings", [])),
            army_synergies=list(data.get("army_synergies", [])),
        )
        factions[fdef.id] = fdef
        for manifest in fdef.unique_buildings:
            building_loader.register_buildings(ctx, manifest)
    return factions


__all__ = ["load_factions"]

