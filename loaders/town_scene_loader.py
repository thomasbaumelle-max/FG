"""Loader for town scene manifests.

This module provides a small helper to read town scene definitions from a
JSON manifest. Each manifest describes the scene size, ordered image layers
and buildings with their possible state images. All referenced images are
preloaded via the provided :class:`~loaders.asset_manager.AssetManager`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Any
import os

from .core import Context, read_json


@dataclass
class TownLayer:
    """Represents a single visual layer within a town scene."""

    id: str
    image: str


@dataclass
class TownBuilding:
    """Definition of a building displayed within the town scene."""

    id: str
    layer: str
    pos: Tuple[int, int]
    states: Dict[str, str]
    hotspot: List[Tuple[int, int]] = field(default_factory=list)
    tooltip: str = ""
    z_index: int = 0
    cost: Dict[str, int] = field(default_factory=dict)
    prereq: List[str] = field(default_factory=list)
    dwelling: Dict[str, int] = field(default_factory=dict)
    image: str | None = None
    desc: str = ""


@dataclass
class TownScene:
    """Container for a fully parsed town scene."""

    size: Tuple[int, int]
    layers: List[TownLayer] = field(default_factory=list)
    buildings: List[TownBuilding] = field(default_factory=list)


# ---------------------------------------------------------------------------

def load_town_scene(path: str, assets: Any | None = None) -> TownScene:
    """Load a :class:`TownScene` definition from ``path``.

    Parameters
    ----------
    path:
        Path to the JSON manifest describing the town scene.
    assets:
        Optional asset manager used to preload all referenced images.

    Returns
    -------
    TownScene
        Parsed town scene with layers and buildings.
    """

    path = os.path.abspath(path)
    ctx = Context(repo_root=os.path.dirname(path), search_paths=[""], asset_loader=None)
    try:
        data = read_json(ctx, os.path.basename(path))
    except Exception:
        return TownScene(size=(0, 0))

    size = tuple(data.get("size", [0, 0]))

    layers: List[TownLayer] = []
    for entry in data.get("layers", []):
        image = entry.get("image", "")
        if assets is not None and image:
            try:
                assets.get(image)
            except Exception:
                pass
        layers.append(TownLayer(id=entry.get("id", ""), image=image))

    buildings: List[TownBuilding] = []
    for entry in data.get("buildings", []):
        states = dict(entry.get("states", {}))
        img_path = entry.get("image")
        if assets is not None:
            for img in states.values():
                try:
                    assets.get(img)
                except Exception:
                    pass
        pos_list = entry.get("pos", [0, 0])
        pos = (int(pos_list[0]), int(pos_list[1])) if len(pos_list) >= 2 else (0, 0)
        hs = entry.get("hotspot")
        hotspot = [tuple(p) for p in hs] if hs else []

        cost = entry.get("cost", {})
        if isinstance(cost, dict):
            cost = {k: int(v) for k, v in cost.items()}
        else:
            cost = {}
        prereq = entry.get("prereq", entry.get("requires", []))
        prereq = list(prereq) if isinstance(prereq, (list, tuple)) else []
        dwelling = entry.get("dwelling", {})
        if isinstance(dwelling, dict):
            dwelling = {k: int(v) for k, v in dwelling.items()}
        else:
            dwelling = {}

        z_index = int(entry.get("z_index", 0))
        buildings.append(
            TownBuilding(
                id=entry.get("id", ""),
                layer=entry.get("layer", ""),
                pos=pos,
                states=states,
                hotspot=hotspot,
                tooltip=entry.get("tooltip", ""),
                z_index=z_index,
                cost=cost,
                prereq=prereq,
                dwelling=dwelling,
                image=img_path,
                desc=entry.get("desc", ""),
            )
        )

    return TownScene(size=size, layers=layers, buildings=buildings)


__all__ = [
    "TownLayer",
    "TownBuilding",
    "TownScene",
    "load_town_scene",
]
