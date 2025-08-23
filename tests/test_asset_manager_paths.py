import importlib
import sys
import types


def _make_stub(loaded):
    class DummySurface:
        def convert_alpha(self):
            return self

        def fill(self, *args, **kwargs):
            pass

    def load(path):
        loaded.append(path)
        return DummySurface()

    return types.SimpleNamespace(
        image=types.SimpleNamespace(load=load),
        Surface=lambda size, flags=0: DummySurface(),
        SRCALPHA=1,
    )


def test_build_index_normalizes_paths(tmp_path, monkeypatch):
    loaded: list[str] = []
    pygame_stub = _make_stub(loaded)
    monkeypatch.setitem(sys.modules, "pygame", pygame_stub)
    import loaders.asset_manager as asset_manager
    importlib.reload(asset_manager)

    flora_dir = tmp_path / "assets" / "flora"
    flora_dir.mkdir(parents=True)
    (flora_dir / "tree.png").write_text("x")

    orig_rel = asset_manager.os.path.relpath
    monkeypatch.setattr(asset_manager.os, "sep", "\\")
    monkeypatch.setattr(
        asset_manager.os.path, "relpath", lambda p, b: orig_rel(p, b).replace("/", "\\"),
    )

    am = asset_manager.AssetManager(str(tmp_path))
    assert "flora/tree.png" in am._index


def test_get_handles_backslashes(tmp_path, monkeypatch):
    loaded: list[str] = []
    pygame_stub = _make_stub(loaded)
    monkeypatch.setitem(sys.modules, "pygame", pygame_stub)
    import loaders.asset_manager as asset_manager
    importlib.reload(asset_manager)

    flora_dir = tmp_path / "assets" / "flora"
    flora_dir.mkdir(parents=True)
    file_path = flora_dir / "tree.png"
    file_path.write_text("x")

    am = asset_manager.AssetManager(str(tmp_path))
    am.search_paths = []
    am._index["flora/tree.png"] = str(file_path)

    monkeypatch.setattr(asset_manager.os, "sep", "\\")
    monkeypatch.setattr(asset_manager.os.path, "isfile", lambda p: True)

    surf = am.get("flora\\tree")
    assert surf is not am._fallback
    assert loaded == [str(file_path)]


def test_get_is_case_insensitive(tmp_path, monkeypatch):
    loaded: list[str] = []
    pygame_stub = _make_stub(loaded)
    monkeypatch.setitem(sys.modules, "pygame", pygame_stub)
    import loaders.asset_manager as asset_manager
    importlib.reload(asset_manager)

    target_dir = tmp_path / "assets" / "FOO"
    target_dir.mkdir(parents=True)
    file_path = target_dir / "MyImage.PNG"
    file_path.write_text("x")

    am = asset_manager.AssetManager(str(tmp_path))
    am.search_paths = []

    surf = am.get("foo/myimage")
    assert surf is not am._fallback
    assert loaded == [str(file_path)]


def test_progress_callback_fires(tmp_path, monkeypatch):
    loaded: list[str] = []
    pygame_stub = _make_stub(loaded)
    monkeypatch.setitem(sys.modules, "pygame", pygame_stub)
    import loaders.asset_manager as asset_manager
    importlib.reload(asset_manager)

    asset_dir = tmp_path / "assets"
    asset_dir.mkdir(parents=True)
    (asset_dir / "test.png").write_text("x")

    progress: list[tuple[int, int]] = []

    def cb(done: int, total: int) -> None:
        progress.append((done, total))

    asset_manager.AssetManager(str(tmp_path), progress_callback=cb)

    assert progress
    assert progress[-1][0] == progress[-1][1]
    assert len(progress) == progress[-1][1]
