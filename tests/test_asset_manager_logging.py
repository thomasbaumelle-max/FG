import logging
import os


def test_missing_asset_logs_details(caplog, asset_manager):
    missing = "missing.png"
    expected_path = os.path.join(asset_manager.search_paths[0], missing)
    with caplog.at_level(logging.WARNING, logger="loaders.asset_manager"):
        asset_manager.get(missing, biome_id="test_biome")
    assert caplog.records, "No warning logged for missing asset"
    message = caplog.records[0].message
    assert "search_paths" in message
    assert "candidates" in message
    assert "biome=test_biome" in message
    assert expected_path in message

