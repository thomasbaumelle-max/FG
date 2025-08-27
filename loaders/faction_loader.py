"""Loading helpers for faction definitions."""

from __future__ import annotations

from typing import Dict, List

from .core import Context, read_json
from core.faction import FactionDef
from core.buildings import register_faction_buildings


def load_factions(ctx: Context, manifest: str = "factions/factions.json") -> Dict[str, FactionDef]:
    """Load faction definitions from ``manifest``.

    ``manifest`` should be a JSON array describing factions. ``unique_buildings``
    entries are interpreted as building manifest paths and registered via
    :func:`core.buildings.register_faction_buildings`.
    """

    factions: Dict[str, FactionDef] = {}
    try:
        entries: List[Dict[str, object]] = read_json(ctx, manifest)
    except Exception:
        return factions

    for data in entries:
        fdef = FactionDef(
            id=data["id"],
            name=data.get("name", data["id"].replace("_", " ").title()),
            color=data.get("color", ""),
            description=data.get("description", ""),
            type=data.get("type", ""),
            doctrine=dict(data.get("doctrine", {})),
            favored_spells=list(
                data.get("favored_spells", data.get("favored_magic", []))
            ),
            unit_tags={k: list(v) for k, v in data.get("unit_tags", {}).items()},
            unique_buildings=list(data.get("unique_buildings", [])),
            army_synergies=list(data.get("army_synergies", [])),
            heroes=[dict(h) for h in data.get("heroes", [])],
        )
        factions[fdef.id] = fdef
        if fdef.unique_buildings:
            register_faction_buildings(ctx, fdef.unique_buildings)

    return factions


__all__ = ["load_factions"]

