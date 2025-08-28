from pathlib import Path

from loaders.town_scene_loader import load_town_scene


def test_load_towns_red_knights_scene():
    path = Path("assets/towns/towns_red_knights.json")

    calls = []

    class DummyAssets:
        def get(self, key, default=None):
            calls.append(key)
            return object()

    scene = load_town_scene(str(path), DummyAssets())

    assert scene.size == (1920, 1080)
    assert [layer.id for layer in scene.layers] == [
        "background",
        "midground",
        "foreground",
    ]
    assert {b.id for b in scene.buildings} == {"town_hall", "blacksmith"}
    assert set(calls) >= {
        "towns/red_knights/background.png",
        "towns/red_knights/midground.png",
        "towns/red_knights/foreground.png",
        "towns/red_knights/buildings/town_hall.png",
        "towns/red_knights/buildings/blacksmith.png",
    }
