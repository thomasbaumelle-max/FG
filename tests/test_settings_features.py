import json
import settings


def test_save_settings_persists_new_options(tmp_path, monkeypatch):
    cfg = tmp_path / "settings.json"
    monkeypatch.setattr(settings, "SETTINGS_FILE", cfg)
    settings.save_settings(animation_speed=2.0, tooltip_read_mode=True)
    data = json.loads(cfg.read_text(encoding="utf-8"))
    assert data["animation_speed"] == 2.0
    assert data["tooltip_read_mode"] is True


def test_remap_key_persists(tmp_path, monkeypatch):
    cfg = tmp_path / "settings.json"
    monkeypatch.setattr(settings, "SETTINGS_FILE", cfg)
    settings.KEYMAP = {}
    settings.remap_key("pan_left", ["K_f"])
    data = json.loads(cfg.read_text(encoding="utf-8"))
    assert data["keymap"]["pan_left"] == ["K_f"]
    assert settings.KEYMAP["pan_left"] == ["K_f"]
