import logging
import os
from loaders.biomes import Biome, load_tileset
from loaders.core import Context


def test_tileset_warns_when_variants_missing(tmp_path, caplog):
    (tmp_path / "forest_0.png").write_text("")
    ctx = Context(repo_root=str(tmp_path), search_paths=[str(tmp_path)], asset_loader=None)
    biome = Biome(
        id="forest",
        type="",
        description="",
        path="forest",
        variants=3,
        colour=(0, 0, 0),
        flora=[],
    )
    with caplog.at_level(logging.WARNING, logger="loaders.biomes"):
        tileset = load_tileset(ctx, biome)
    assert tileset.variants == 1
    assert any("specifies 3 variants" in rec.message for rec in caplog.records)
