import json
import pytest
from loaders.biomes import BiomeCatalog
from loaders.core import Context
from loaders.asset_manager import AssetManager
import constants
from core import world as core_world


def test_missing_biome_image_raises(tmp_path):
    assets_root = tmp_path / "assets"
    (assets_root / "biomes").mkdir(parents=True)
    manifest = [
        {
            "id": "missing",
            "type": "forest",
            "description": "",
            "path": "./biomes/missing",
            "variants": 1,
            "colour": [0, 0, 0],
            "flora": [],
        }
    ]
    with open(assets_root / "biomes" / "biomes.json", "w", encoding="utf-8") as fh:
        json.dump(manifest, fh)

    ctx = Context(
        repo_root=str(tmp_path),
        search_paths=[str(assets_root)],
        asset_loader=AssetManager(repo_root=str(tmp_path)),
    )

    old_biomes = BiomeCatalog._biomes
    old_base = constants.BIOME_BASE_IMAGES
    old_weights = constants.DEFAULT_BIOME_WEIGHTS
    old_prio = constants.BIOME_PRIORITY
    try:
        with pytest.raises(FileNotFoundError) as exc:
            BiomeCatalog.load(ctx)
        assert "missing" in str(exc.value)
        assert "biomes/biomes/missing.png" in str(exc.value)
        assert str(assets_root) in str(exc.value)
    finally:
        BiomeCatalog._biomes = old_biomes
        constants.BIOME_BASE_IMAGES = old_base
        constants.DEFAULT_BIOME_WEIGHTS = old_weights
        constants.BIOME_PRIORITY = old_prio
        core_world.init_biome_images()
