import json


def test_single_variant_base_image_without_suffix(tmp_path):
    from loaders.biomes import BiomeCatalog
    from loaders.core import Context
    import constants
    from core import world as core_world

    repo_root = tmp_path
    assets_root = tmp_path / "assets"
    (assets_root / "biomes").mkdir(parents=True)
    with open(assets_root / "biomes" / "biomes.json", "w", encoding="utf-8") as fh:
        json.dump([], fh)
    (assets_root / "realms" / "testrealm" / "biomes").mkdir(parents=True)
    (assets_root / "realms" / "testrealm" / "biomes" / "foo.png").write_text("")
    manifest = [
        {
            "id": "foo",
            "type": "",
            "description": "",
            "path": "biomes/foo",
            "variants": 1,
            "colour": [0, 0, 0],
            "flora": [],
        }
    ]
    with open(assets_root / "realms" / "testrealm" / "biomes.json", "w", encoding="utf-8") as fh:
        json.dump(manifest, fh)

    ctx = Context(repo_root=str(repo_root), search_paths=[str(assets_root)], asset_loader=None)

    old_biomes = BiomeCatalog._biomes
    old_base = constants.BIOME_BASE_IMAGES
    old_weights = constants.DEFAULT_BIOME_WEIGHTS
    old_prio = constants.BIOME_PRIORITY
    try:
        BiomeCatalog.load(ctx, "testrealm")
        assert constants.BIOME_BASE_IMAGES["foo"] == ["realms/testrealm/biomes/foo.png"]
    finally:
        BiomeCatalog._biomes = old_biomes
        constants.BIOME_BASE_IMAGES = old_base
        constants.DEFAULT_BIOME_WEIGHTS = old_weights
        constants.BIOME_PRIORITY = old_prio
        core_world.init_biome_images()
