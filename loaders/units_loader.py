"""Example adapter for loading unit definitions."""
from __future__ import annotations

from typing import Dict, List, Sequence

from core.entities import UnitStats
from .core import Context, read_json, require_keys


def _parse_abilities(items: Sequence[str]) -> List[Dict[str, object]]:
    """Convert a sequence of ``"name:arg"`` strings into a structured list."""

    abilities: List[Dict[str, object]] = []
    for item in items:
        parts = item.split(":")
        name = parts[0]
        args = parts[1:] if len(parts) > 1 else []
        abilities.append({"name": name, "args": args})
    return abilities


def load_units(
    ctx: Context, manifest: str = "units/units.json", section: str | None = None
) -> Dict[str, dict]:
    """Load unit or creature definitions from ``manifest``.

    The JSON file may either contain a list at the root or be wrapped in a
    mapping with a list stored under ``section`` (e.g. ``"units"`` or
    ``"creatures"``).  Abilities may be supplied either as a list of strings or
    a mapping where the keys are ability names.
    """

    try:
        data = read_json(ctx, manifest)
    except Exception:
        return {}

    if isinstance(data, dict):
        if section is not None:
            data = data.get(section, [])
        else:
            # Fall back to common section names if the caller did not specify
            # one explicitly.
            data = data.get("units") or data.get("creatures") or []

    units: Dict[str, dict] = {}
    for entry in data:
        require_keys(entry, ["id", "stats"])
        unit = dict(entry)
        abilities_src = entry.get("abilities", [])
        if isinstance(abilities_src, dict):
            ability_names = list(abilities_src.keys())
        else:
            ability_names = list(abilities_src)
        unit["abilities"] = _parse_abilities(ability_names)
        # ``battlefield_scale`` may be defined either inside the ``stats``
        # mapping or at the root of the unit entry.  Ensure the value ends up
        # in the ``UnitStats`` constructor regardless of where it is specified.
        bfs = unit.pop("battlefield_scale", None)
        stats = dict(entry["stats"])
        if bfs is not None:
            stats["battlefield_scale"] = bfs
        stats.setdefault("battlefield_scale", 1.0)
        # If the abilities were provided as a list/dict on the entry, also
        # populate the ``UnitStats`` abilities list for convenience.
        stats.setdefault("abilities", ability_names if ability_names else [])
        unit["stats"] = UnitStats(**stats)
        units[unit["id"]] = unit
    return units
