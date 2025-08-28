"""Example adapter for loading unit definitions."""
from __future__ import annotations

from dataclasses import asdict
from typing import Dict, List, Sequence, Tuple

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
) -> Tuple[Dict[str, UnitStats], Dict[str, dict]]:
    """Load unit or creature definitions from ``manifest``.

    The manifest may contain a ``templates`` mapping providing default values
    for entries.  Data can either be stored directly as a list at the root or
    wrapped in a mapping under ``section`` (e.g. ``"units"`` or
    ``"creatures"``).

    Returns a tuple ``(stats, extras)`` where ``stats`` maps unit identifiers to
    ``UnitStats`` objects and ``extras`` contains any remaining information such
    as images or behaviour.
    """

    try:
        data = read_json(ctx, manifest)
    except Exception:
        return {}, {}

    templates: Dict[str, dict] = {}
    entries: List[dict] = []

    if isinstance(data, dict):
        templates = data.get("templates", {})
        if section is not None:
            entries = data.get(section, [])
        else:
            # Fall back to common section names if the caller did not specify
            # one explicitly.
            entries = data.get("units") or data.get("creatures") or []
    else:
        entries = list(data)

    # Default values for any missing ``UnitStats`` fields
    DEFAULT_STATS = asdict(
        UnitStats(
            name="",
            max_hp=1,
            attack_min=0,
            attack_max=0,
            defence_melee=0,
            defence_ranged=0,
            defence_magic=0,
            speed=1,
            attack_range=1,
            initiative=0,
            sheet="",
            hero_frames=(0, 0),
            enemy_frames=(0, 0),
        )
    )

    units: Dict[str, UnitStats] = {}
    extras: Dict[str, dict] = {}

    for entry in entries:
        require_keys(entry, ["id", "stats"])
        entry = dict(entry)

        # Merge entry with template if referenced
        tmpl_name = entry.get("template")
        ability_names: List[str] = []
        if tmpl_name and tmpl_name in templates:
            tmpl = templates[tmpl_name]
            merged = dict(tmpl)
            # merge stats
            stats = {**tmpl.get("stats", {}), **entry.get("stats", {})}
            merged.update(entry)
            merged["stats"] = stats
            entry = merged
            for src in (tmpl.get("abilities"), entry.get("abilities")):
                if not src:
                    continue
                if isinstance(src, dict):
                    names = list(src.keys())
                else:
                    names = list(src)
                for n in names:
                    if n not in ability_names:
                        ability_names.append(n)
        else:
            abilities_src = entry.get("abilities", [])
            if isinstance(abilities_src, dict):
                ability_names = list(abilities_src.keys())
            else:
                ability_names = list(abilities_src)

        parsed_abilities = _parse_abilities(ability_names)

        # ``battlefield_scale`` may be defined either inside the ``stats``
        # mapping or at the root of the unit entry.  Ensure the value ends up
        # in the ``UnitStats`` constructor regardless of where it is specified.
        bfs = entry.pop("battlefield_scale", None)
        stats = dict(entry["stats"])
        if bfs is not None:
            stats["battlefield_scale"] = bfs
        stats.setdefault("battlefield_scale", 1.0)

        # Merge abilities collected from templates/entry into the stats block
        stats_abilities = list(stats.get("abilities", []))
        for name in ability_names:
            if name not in stats_abilities:
                stats_abilities.append(name)
        stats["abilities"] = stats_abilities

        merged_stats = {**DEFAULT_STATS, **stats}
        units[entry["id"]] = UnitStats(**merged_stats)

        extra = {k: v for k, v in entry.items() if k not in {"id", "stats"}}
        extra["abilities"] = parsed_abilities
        extras[entry["id"]] = extra

    return units, extras
