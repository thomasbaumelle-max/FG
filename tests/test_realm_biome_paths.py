import base64
import json


PNG_1x1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAAAAAA6fptVAAAAC0lEQVR42mP8/x8AAwMB/kwAXzAAAAAASUVORK5CYII="
)


def test_manifest_relative_paths_resolved(tmp_path):
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
    (assets_root / "realms" / "testrealm" / "biomes" / "test_biome.png").write_bytes(PNG_1x1)
    manifest = [
        {
            "id": "test_biome",
            "type": "forest",
            "description": "",
            "path": "./biomes/test_biome",
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
        biome = BiomeCatalog.get("test_biome")
        assert biome is not None
        assert biome.path == "realms/testrealm/biomes/test_biome"
    finally:
        BiomeCatalog._biomes = old_biomes
        constants.BIOME_BASE_IMAGES = old_base
        constants.DEFAULT_BIOME_WEIGHTS = old_weights
        constants.BIOME_PRIORITY = old_prio
        core_world.init_biome_images()


def test_realm_biome_variants_loaded(tmp_path, caplog):
    import logging
    from loaders.biomes import BiomeCatalog, load_tileset
    from loaders.core import Context
    from loaders.asset_manager import AssetManager
    import constants
    from core import world as core_world

    repo_root = tmp_path
    assets_root = tmp_path / "assets"
    (assets_root / "biomes").mkdir(parents=True)
    with open(assets_root / "biomes" / "biomes.json", "w", encoding="utf-8") as fh:
        json.dump([], fh)
    (assets_root / "realms" / "testrealm" / "biomes").mkdir(parents=True)
    (assets_root / "realms" / "testrealm" / "biomes" / "test_biome.png").write_bytes(
        PNG_1x1
    )
    for i in range(3):
        (
            assets_root
            / "realms"
            / "testrealm"
            / "biomes"
            / f"test_biome_{i}.png"
        ).write_bytes(PNG_1x1)
    manifest = [
        {
            "id": "test_biome",
            "type": "forest",
            "description": "",
            "path": "./biomes/test_biome",
            "variants": 3,
            "colour": [0, 0, 0],
            "flora": [],
        }
    ]
    with open(assets_root / "realms" / "testrealm" / "biomes.json", "w", encoding="utf-8") as fh:
        json.dump(manifest, fh)

    ctx_no_asset = Context(
        repo_root=str(repo_root), search_paths=[str(assets_root)], asset_loader=None
    )
    ctx = Context(
        repo_root=str(repo_root),
        search_paths=[str(assets_root)],
        asset_loader=AssetManager(repo_root=str(repo_root)),
    )

    old_biomes = BiomeCatalog._biomes
    old_base = constants.BIOME_BASE_IMAGES
    old_weights = constants.DEFAULT_BIOME_WEIGHTS
    old_prio = constants.BIOME_PRIORITY
    try:
        BiomeCatalog.load(ctx_no_asset, "testrealm")
        biome = BiomeCatalog.get("test_biome")
        assert biome is not None
        with caplog.at_level(logging.WARNING, logger="loaders.asset_manager"):
            tileset = load_tileset(ctx, biome)
        assert tileset.variants == 3
        assert len(tileset.surfaces) == 3
        assert not any("Missing asset" in rec.message for rec in caplog.records)
    finally:
        BiomeCatalog._biomes = old_biomes
        constants.BIOME_BASE_IMAGES = old_base
        constants.DEFAULT_BIOME_WEIGHTS = old_weights
        constants.BIOME_PRIORITY = old_prio
        core_world.init_biome_images()
