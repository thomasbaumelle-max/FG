import sys
import types


class Rect:
    def __init__(self, x, y, w, h):
        self.x, self.y, self.width, self.height = x, y, w, h
        self.bottom = y + h

    def collidepoint(self, pos):
        return False


class DummySurface:
    def convert_alpha(self):
        return self

    def get_width(self):
        return 10

    def get_height(self):
        return 10

    def get_rect(self):
        return Rect(0, 0, 10, 10)

    def blit(self, *args, **kwargs):
        pass

    def fill(self, *args, **kwargs):
        pass


def load(path):
    return DummySurface()


def test_coast_assets_loaded(tmp_path, monkeypatch):
    monkeypatch.setenv("FG_FAST_TESTS", "1")

    pygame_stub = types.SimpleNamespace(
        image=types.SimpleNamespace(load=load),
        transform=types.SimpleNamespace(
            scale=lambda surf, size: surf, smoothscale=lambda surf, size: surf
        ),
        Surface=lambda size, flags=0: DummySurface(),
        SRCALPHA=1,
        Rect=Rect,
        draw=types.SimpleNamespace(
            ellipse=lambda surf, color, rect: None, rect=lambda *a, **k: None
        ),
        time=types.SimpleNamespace(
            Clock=lambda: types.SimpleNamespace(tick=lambda fps: None)
        ),
        event=types.SimpleNamespace(get=lambda: []),
        display=types.SimpleNamespace(flip=lambda: None),
        init=lambda: None,
        quit=lambda: None,
    )

    monkeypatch.setitem(sys.modules, "pygame", pygame_stub)
    monkeypatch.setitem(
        sys.modules,
        "audio",
        types.SimpleNamespace(init=lambda: None, play_sound=lambda *a, **k: None),
    )

    from core.game import Game

    map_path = tmp_path / "map.txt"
    map_path.write_text("G.W.\nG.W.\n")
    screen = types.SimpleNamespace(get_width=lambda: 100, get_height=lambda: 100)
    game = Game(screen, map_file=str(map_path))
    edge_names = {f"mask_{d}.png" for d in ("n", "e", "s", "w")}
    corner_names = {f"mask_{c}.png" for c in ("ne", "nw", "se", "sw")}
    assert edge_names <= set(game.assets)
    assert corner_names <= set(game.assets)
