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
        "towns/red_knights/midground.png",
        "towns/red_knights/background.png",
        "towns/red_knights/foreground.png",
        "towns/red_knights/buildings_scaled/barracks_unbuilt.png",
        "towns/red_knights/buildings_scaled/barracks_built.png",
    }
