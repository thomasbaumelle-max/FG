import types

import pygame

from loaders.core import Context
from loaders.flora_loader import FloraLoader, FloraAsset


class DummyAM(dict):
    def get(self, key):  # pragma: no cover - simple dictionary access
        return self[key]


def test_flora_get_surface_scales_anchor(monkeypatch):
    surf = pygame.Surface((128, 128))
    am = DummyAM()
    am["big"] = surf
    ctx = Context(repo_root="", search_paths=[""], asset_loader=am)
    loader = FloraLoader(ctx, tile_size=64)
    asset = FloraAsset(
        id="big",
        type="tall",
        biomes=[],
        footprint=(1, 1),
        anchor_px=(64, 96),
        passable=True,
        occludes=False,
        files=["big.png"],
        size_px=None,
        collectible=None,
        shadow_baked=False,
        spawn={},
    )
    loader.assets["big"] = asset

    monkeypatch.setattr(
        pygame,
        "transform",
        types.SimpleNamespace(smoothscale=lambda s, size: pygame.Surface(size)),
        raising=False,
    )

    scaled, anchor = loader.get_surface("big")
    assert scaled.get_width() == 64 and scaled.get_height() == 64
    assert anchor == (32, 48)

