from loaders.town_scene_loader import TownScene
from ui.town_scene_screen import TownSceneScreen


def test_run_exits_on_invalid_scene(monkeypatch):
    import pygame

    monkeypatch.setenv("FG_FAST_TESTS", "0")
    screen = pygame.Surface((1, 1))
    scene = TownScene(size=(0, 0), layers=[], buildings=[])
    screen_wrapper = TownSceneScreen(screen, scene, assets={})

    calls = {"n": 0}

    def fake_get():
        calls["n"] += 1
        if calls["n"] > 2:
            raise RuntimeError("event.get called repeatedly")
        return []

    monkeypatch.setattr(pygame.event, "get", fake_get)

    screen_wrapper.run()
    assert calls["n"] == 0
