"""Faction definition model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class FactionDef:
    """Data-driven description of a faction.

    Parameters mirror the structure of JSON manifests loaded by
    :func:`loaders.faction_loader.load_factions`.
    """

    id: str
    name: str
    doctrine: Dict[str, int] = field(default_factory=dict)
    favored_spells: List[str] = field(default_factory=list)
    unit_tags: Dict[str, List[str]] = field(default_factory=dict)
    unique_buildings: List[str] = field(default_factory=list)
    army_synergies: List[Dict[str, object]] = field(default_factory=list)


__all__ = ["FactionDef"]

