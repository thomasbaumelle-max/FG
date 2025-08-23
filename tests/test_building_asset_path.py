from loaders.building_loader import BUILDINGS, BuildingAsset


def test_building_file_list_uses_manifest_path():
    """Building assets should expose their image path as declared in the manifest."""
    asset = BUILDINGS["mine"]
    assert asset.path == "buildings/mine/mine_0.png"
    assert asset.file_list() == ["buildings/mine/mine_0.png"]


def test_building_file_list_accepts_png_path():
    """An explicit ``.png`` path should be returned as-is."""
    asset = BuildingAsset(id="custom", path="foo/bar.png")
    assert asset.file_list() == ["foo/bar.png"]
