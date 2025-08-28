import os

from loaders.battlefield_loader import load_battlefields
from core.world import BIOME_CHAR_MAP


def test_battlefields_manifest_contains_all_biomes():
    path = os.path.join(os.path.dirname(__file__), "..", "assets", "battlefields", "battlefields.json")
    defs = load_battlefields(path)
    expected = set(BIOME_CHAR_MAP.values()) | {"default"}
    assert expected.issubset(defs.keys())
