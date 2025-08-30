import json

from loaders.town_scene_loader import load_town_scene


def test_load_town_scene_loads_assets(tmp_path):
    manifest = {
        "size": [100, 80],
        "layers": [{"id": "bg", "image": "background.png"}],
        "buildings": [
            {
                "id": "b1",
                "layer": "bg",
                "pos": [10, 20],
                "states": {
                    "built": "b1.png",
                    "upgraded": "b1_up.png",
                },
                "image": "icon.png",
                "cost": {"gold": 100},
                "prereq": ["tavern"],
                "dwelling": {"Peasant": 1},
            }
        ],
    }
    path = tmp_path / "scene.json"
    path.write_text(json.dumps(manifest))

    calls = []

    class DummyAssets:
        def get(self, key, default=None):
            calls.append(key)
            return object()

    scene = load_town_scene(str(path), DummyAssets())

    assert scene.size == (100, 80)
    assert [layer.id for layer in scene.layers] == ["bg"]
    building = scene.buildings[0]
    assert building.states["built"] == "b1.png"
    assert building.cost == {"gold": 100}
    assert building.prereq == ["tavern"]
    assert building.dwelling == {"Peasant": 1}
    assert building.image == "icon.png"
    assert set(calls) == {"background.png", "b1.png", "b1_up.png"}
