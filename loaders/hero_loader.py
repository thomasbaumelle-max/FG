"""Loader for hero definitions."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Any

from .core import Context, read_json, require_keys


@dataclass(slots=True)
class HeroDef:
    id: str
    name: str
    faction: str
    overworld: Dict[str, Any] = field(default_factory=dict)
    combat: Dict[str, Any] = field(default_factory=dict)
    starting_army: List[Tuple[str, int]] = field(default_factory=list)
    starting_skills: List[Dict[str, Any]] = field(default_factory=list)
    known_spells: List[str] = field(default_factory=list)
    portrait: str | None = None
    overworld_sprite: str | None = None
    battlefield_sprite: str | None = None


def _parse_army(items: List[Any]) -> List[Tuple[str, int]]:
    army: List[Tuple[str, int]] = []
    for entry in items:
        if isinstance(entry, dict):
            unit = entry.get("unit") or entry.get("id")
            if not unit:
                continue
            count = int(entry.get("count", 1))
            army.append((unit, count))
        elif isinstance(entry, str):
            army.append((entry, 1))
    return army


def load_heroes(ctx: Context, manifest: str = "units/heroes.json") -> Dict[str, HeroDef]:
    """Load hero definitions from ``manifest``.

    The manifest should be a JSON array describing heroes. Each hero entry may
    specify ``starting_army`` as a list of unit identifiers or objects with
    ``unit``/``id`` and ``count`` fields.
    """

    try:
        data = read_json(ctx, manifest)
    except Exception:
        return {}

    heroes: Dict[str, HeroDef] = {}
    for entry in data:
        try:
            require_keys(entry, ["id", "faction"])
        except Exception:
            continue
        hero = HeroDef(
            id=entry["id"],
            name=entry.get("name", entry["id"]),
            faction=entry.get("faction", ""),
            overworld=dict(entry.get("overworld", {})),
            combat=dict(entry.get("combat", {})),
            starting_army=_parse_army(entry.get("starting_army", [])),
            starting_skills=[dict(s) for s in entry.get("starting_skills", [])],
            known_spells=list(entry.get("known_spells", [])),
            portrait=entry.get("PortraitSprite"),
            overworld_sprite=entry.get("OverWorldSprite"),
            battlefield_sprite=entry.get("BattlefieldSprite"),
        )
        heroes[hero.id] = hero
    return heroes


__all__ = ["HeroDef", "load_heroes"]
