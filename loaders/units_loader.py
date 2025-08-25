"""Example adapter for loading unit definitions."""
from __future__ import annotations

from typing import Dict, List

from core.entities import UnitStats
from .core import Context, read_json, require_keys


def _parse_abilities(items: List[str]) -> List[Dict[str, object]]:
    abilities: List[Dict[str, object]] = []
    for item in items:
        parts = item.split(":")
        name = parts[0]
        args = parts[1:] if len(parts) > 1 else []
        abilities.append({"name": name, "args": args})
    return abilities


def load_units(ctx: Context, manifest: str = "units/units.json") -> Dict[str, dict]:
    """Load unit statistics and abilities from ``manifest``."""

    try:
        data = read_json(ctx, manifest)
    except Exception:
        return {}

    units: Dict[str, dict] = {}
    for entry in data:
        require_keys(entry, ["id", "stats"])
        unit = dict(entry)
        unit["abilities"] = _parse_abilities(entry.get("abilities", []))
        # ``battlefield_scale`` may be defined either inside the ``stats``
        # mapping or at the root of the unit entry.  Ensure the value ends up
        # in the ``UnitStats`` constructor regardless of where it is specified.
        bfs = unit.pop("battlefield_scale", None)
        stats = dict(entry["stats"])
        if bfs is not None:
            stats["battlefield_scale"] = bfs
        stats.setdefault("battlefield_scale", 1.0)
        unit["stats"] = UnitStats(**stats)
        units[unit["id"]] = unit
    return units
