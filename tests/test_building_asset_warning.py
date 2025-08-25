import logging
import os
import pygame
from core.game import Game
from loaders.core import Context


def test_missing_building_sprite_logs_warning(caplog, asset_manager):
    repo_root = os.path.dirname(os.path.dirname(__file__))
    game = Game.__new__(Game)
    game.assets = asset_manager
    game.ctx = Context(
        repo_root=repo_root,
        search_paths=[os.path.join(repo_root, "assets")],
        asset_loader=asset_manager,
    )
    with caplog.at_level(logging.WARNING, logger="loaders.asset_manager"):
        Game.load_assets(game)
    assert any("Missing asset" in rec.message for rec in caplog.records)
