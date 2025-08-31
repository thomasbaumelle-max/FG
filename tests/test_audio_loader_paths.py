from pathlib import Path

import loaders.audio_loader as audio_loader


def test_audio_loader_paths(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    root.mkdir()
    (root / "assets").mkdir()

    env_dir = tmp_path / "env"
    env_dir.mkdir()
    parent_assets = tmp_path / "assets"
    parent_assets.mkdir()

    for d, tag in ((env_dir, "env"), (parent_assets, "parent")):
        audio_dir = d / "audio"
        audio_dir.mkdir()
        (audio_dir / "foo.wav").write_bytes(b"\0")
        (audio_dir / "sounds.json").write_text(f'{{"source": "{tag}"}}')

    monkeypatch.setattr(audio_loader, "_ROOT", root)
    monkeypatch.setenv("FG_ASSETS_DIR", str(env_dir))

    found = audio_loader.find_audio_file("audio/foo.wav")
    assert Path(found) == env_dir / "audio" / "foo.wav"

    (env_dir / "audio" / "foo.wav").unlink()
    found = audio_loader.find_audio_file("audio/foo.wav")
    assert Path(found) == parent_assets / "audio" / "foo.wav"

    manifest = audio_loader.load_manifest("sounds.json")
    assert manifest == {"source": "env"}

    (env_dir / "audio" / "sounds.json").unlink()
    manifest = audio_loader.load_manifest("sounds.json")
    assert manifest == {"source": "parent"}
