import json
from pathlib import Path


def test_towns_red_knights_manifest_schema() -> None:
    path = Path("assets/towns/towns_red_knights.json")
    data = json.loads(path.read_text())

    assert data["size"] == [1920, 1080]

    layers = data["layers"]
    assert isinstance(layers, list) and layers
    layer_ids = set()
    for layer in layers:
        assert "id" in layer and "image" in layer
        assert isinstance(layer["id"], str)
        assert isinstance(layer["image"], str)
        layer_ids.add(layer["id"])

    buildings = data["buildings"]
    assert isinstance(buildings, list)
    for b in buildings:
        for key in ["id", "layer", "pos", "states", "hotspot"]:
            assert key in b
        if "tooltip" in b:
            assert isinstance(b["tooltip"], str)
        assert b["layer"] in layer_ids
        assert isinstance(b["pos"], list) and len(b["pos"]) == 2
        assert all(isinstance(v, int) for v in b["pos"])
        assert isinstance(b["states"], dict) and b["states"]
        assert all(isinstance(v, str) for v in b["states"].values())
        assert isinstance(b["hotspot"], list) and b["hotspot"]
        assert all(
            isinstance(pt, list)
            and len(pt) == 2
            and all(isinstance(v, int) for v in pt)
            for pt in b["hotspot"]
        )
