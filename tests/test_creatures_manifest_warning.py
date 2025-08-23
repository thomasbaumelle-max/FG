import logging
import os
import builtins

from core import world


def test_missing_creatures_manifest_logs_warning(monkeypatch, caplog):
    path = os.path.abspath(
        os.path.join(os.path.dirname(world.__file__), "..", "assets", "units", "creatures.json")
    )

    real_open = builtins.open

    def fake_open(file, *args, **kwargs):
        if os.path.abspath(file) == path:
            raise FileNotFoundError("manifest missing")
        return real_open(file, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", fake_open)

    with caplog.at_level(logging.WARNING, logger="core.world"):
        world._load_creatures_by_biome()

    assert any(path in rec.message and "manifest missing" in rec.message for rec in caplog.records)
