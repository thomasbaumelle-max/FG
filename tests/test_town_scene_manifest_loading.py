from pathlib import Path

from loaders.town_scene_loader import load_town_scene


def test_load_towns_red_knights_scene():
    path = Path("assets/towns/red_knights/town.json")

    calls = []

    class DummyAssets:
        def get(self, key, default=None):
            calls.append(key)
            return object()

    scene = load_town_scene(str(path), DummyAssets())

    assert scene.size == (1920, 1080)
    assert [layer.id for layer in scene.layers] == [
        "sky",
        "background",
        "foreground",
    ]
    ids = {b.id for b in scene.buildings}
    assert {"barracks", "archery_range", "mage_guild"} <= ids
    assert set(calls) >= {
        "layers/00_sky.png",
        "layers/10_background.png",
        "layers/90_foreground.png",
        "buildings_scaled/barracks_unbuilt.png",
        "buildings_scaled/barracks_built.png",
        "../../buildings/red_knights/barracks.png",
    }
