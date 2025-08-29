"""Loader for boss manifest files.

The manifest describes unique boss encounters and mirrors the structure used
for regular unit definitions.  Each entry provides an ``id`` along with
combat ``stats`` and additional metadata.  This loader converts the raw JSON
data into :class:`core.bosses.Boss` instances.
"""

from __future__ import annotations

from typing import Dict, Iterable, List

from core.entities import UnitStats
from .core import Context, read_json, require_keys


def load_bosses(ctx: Context, manifest: str = "units_boss.json") -> Dict[str, "Boss"]:
    """Load boss definitions from ``manifest``.

    Returns a mapping of boss identifier to :class:`core.bosses.Boss` objects.
    Any errors during parsing simply result in an empty mapping.  The manifest
    may either be a list at the root or wrapped inside a mapping under the
    ``"bosses"`` key.
    """

    data: List[dict]
    try:
        raw = read_json(ctx, manifest)
    except Exception:  # pragma: no cover - simple error propagation
        return {}

    if isinstance(raw, dict):
        data = list(raw.get("bosses", []))
    else:
        data = list(raw)

    from core.bosses import Boss  # imported lazily to avoid circular imports

    bosses: Dict[str, Boss] = {}
    for entry in data:
        require_keys(
            entry,
            ["id", "name", "realm", "spawn_chance", "stats", "drop", "image"],
        )

        stats = UnitStats(**entry["stats"])

        drop = entry.get("drop", [])
        if isinstance(drop, (str, int)):
            drop = [str(drop)]
        else:
            drop = [str(d) for d in drop]

        boss = Boss(
            id=str(entry["id"]),
            name=str(entry["name"]),
            realm=str(entry.get("realm", "")),
            spawn_chance=float(entry.get("spawn_chance", 0.0)),
            stats=stats,
            drop=drop,
            image=str(entry.get("image", "")),
        )
        bosses[boss.id] = boss

    return bosses


__all__ = ["load_bosses"]

