import random
from collections import Counter

from core.world import WorldMap
import constants


def test_resource_distribution_ratios():
    random.seed(0)
    wm = WorldMap(
        width=40,
        height=40,
        num_obstacles=0,
        num_treasures=0,
        num_enemies=0,
        num_resources=1,
        num_buildings=0,
        biome_weights={"scarletia_echo_plain": 1.0},
    )
    counts = Counter(
        tile.resource for row in wm.grid for tile in row if tile.resource
    )
    total = sum(counts.values())
    assert total > 0
    # Common resources should vastly outnumber rare ones
    high = counts["wood"] + counts["stone"]
    low = counts["crystal"] + counts["gold"] + counts["treasure"]
    assert high >= 2 * low
    assert counts["wood"] > counts["crystal"]
    assert counts["wood"] >= counts["gold"]
    assert counts["wood"] >= counts["treasure"]
    assert counts["stone"] > counts["crystal"]
    assert counts["stone"] >= counts["gold"]
    assert counts["stone"] >= counts["treasure"]

