from collections import Counter
from pathlib import Path
import types

import core.world as world_module


def test_resource_distribution_ratios(monkeypatch):
    fixture = Path(__file__).parent / "fixtures" / "resource_grid.txt"
    reverse_map = {
        "w": "wood",
        "s": "stone",
        "c": "crystal",
        "g": "gold",
        "t": "treasure",
        ".": None,
    }
    with open(fixture, "r", encoding="utf-8") as f:
        resource_grid = [
            [reverse_map[ch] for ch in line.rstrip("\n")] for line in f
        ]

    class DummyWorld:
        def __init__(self, *args, **kwargs):
            self.grid = [
                [types.SimpleNamespace(resource=res) for res in row]
                for row in resource_grid
            ]

    monkeypatch.setattr(world_module, "WorldMap", DummyWorld)
    wm = world_module.WorldMap()

    counts = Counter(
        tile.resource for row in wm.grid for tile in row if tile.resource
    )
    total = sum(counts.values())
    assert total > 0
    high = counts["wood"] + counts["stone"]
    low = counts["crystal"] + counts["gold"] + counts["treasure"]
    assert high >= 2 * low
    assert counts["wood"] > counts["crystal"]
    assert counts["wood"] >= counts["gold"]
    assert counts["wood"] >= counts["treasure"]
    assert counts["stone"] > counts["crystal"]
    assert counts["stone"] >= counts["gold"]
    assert counts["stone"] >= counts["treasure"]
