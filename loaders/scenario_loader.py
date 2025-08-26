"""Simple loader for scenario definitions.

A scenario file describes special units, objectives and optional scripts that
should be applied when a new game starts.  The format is intentionally light
weight and uses JSON for ease of authoring::

    {
        "name": "example",
        "units": [{"type": "Swordsman", "x": 1, "y": 1, "count": 5}],
        "objectives": ["Explore the world"],
        "scripts": []
    }

Only the fields that are understood by the engine are processed; unknown keys
are ignored to allow forward compatible extensions.

For tests and demonstrations a small scenario is bundled with the project at
``assets/scenarios/demo.json``.  It can be loaded directly::

    from loaders.scenario_loader import load_scenario
    data = load_scenario("assets/scenarios/demo.json")
"""

from __future__ import annotations

from typing import Any, Dict
import json


def load_scenario(path: str) -> Dict[str, Any]:
    """Return the parsed JSON scenario from ``path``.

    The function simply reads and returns the JSON data.  Any IO or JSON
    errors are allowed to propagate to the caller so they can be handled in a
    context appropriate manner.
    """

    with open(path, "r", encoding="utf-8") as fh:
        data: Dict[str, Any] = json.load(fh)
    return data
