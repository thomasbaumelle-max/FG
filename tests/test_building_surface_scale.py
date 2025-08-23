import os
import types

import pygame

import constants
from core.buildings import create_building
from loaders.asset_manager import AssetManager
from loaders.building_loader import BuildingAsset, get_surface


def test_high_res_building_scaled_width(monkeypatch):
    repo_root = os.path.dirname(os.path.dirname(__file__))
    mgr = AssetManager(repo_root)

    high_res = pygame.Surface((512, 256))
    mgr[os.path.splitext("foo.png")[0]] = high_res

    asset = BuildingAsset(id="big", path="foo.png", footprint=[(0, 0), (1, 0)])

    monkeypatch.setattr(
        pygame,
        "transform",
        types.SimpleNamespace(
            smoothscale=lambda s, size: pygame.Surface(size)
        ),
        raising=False,
    )

    surf, scale = get_surface(asset, mgr, constants.TILE_SIZE)
    assert surf.get_width() == 2 * constants.TILE_SIZE
    asset.scale = scale

    building = create_building("big", defs={"big": asset})
    ax, ay = asset.anchor_px
    assert building.anchor == (int(ax * scale), int(ay * scale))
