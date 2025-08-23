from loaders.biomes import Biome, BiomeCatalog
from core.world import WorldMap
from core.vision import compute_vision


class DummyActor:
    def __init__(self, x: int, y: int) -> None:
        self.x = x
        self.y = y


def test_vision_bonus_extends_visibility(monkeypatch):
    bonus_biome = Biome(
        id="bonus",
        type="plain",
        description="",
        path="",
        variants=1,
        colour=(0, 0, 0),
        flora=[],
        terrain_cost=1,
        passable=True,
        overlays=[],
        vision_bonus=2,
    )
    monkeypatch.setattr(BiomeCatalog, "_biomes", {"bonus": bonus_biome})
    wm = WorldMap(
        width=10,
        height=1,
        biome_weights={"bonus": 1.0},
        num_obstacles=0,
        num_treasures=0,
        num_enemies=0,
    )
    actor = DummyActor(0, 0)
    visible = compute_vision(wm, actor)
    assert (6, 0) in visible
    assert (7, 0) not in visible
