import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from loaders.town_scene_loader import TownScene, TownBuilding
from ui.town_scene_screen import TownSceneScreen


class DummyAssets:
    def get(self, *_):
        return pygame.Surface((1, 1))


class DummyTown:
    def __init__(self, units):
        self._units = units

    def is_structure_built(self, _sid):
        return True

    def recruitable_units(self, _sid):
        return list(self._units)


class DummyHero:
    gold = 0
    resources = {}
    army = []


class DummyGame:
    hero = DummyHero()


def _make_screen(units):
    pygame.init()
    screen = pygame.Surface((320, 200))
    scene = TownScene(size=(0, 0))
    town = DummyTown(units)
    game = DummyGame()
    return TownSceneScreen(screen, scene, DummyAssets(), game=game, town=town)


def test_multi_overlay_invoked(monkeypatch):
    screen = _make_screen(["A", "B"])
    called = {}

    def fake_multi(*args):
        called["multi"] = args

    def fake_single(*args):
        called["single"] = args

    monkeypatch.setattr("ui.multi_recruit_overlay.open", fake_multi)
    monkeypatch.setattr("ui.recruit_overlay.open", fake_single)

    building = TownBuilding(id="dwelling", layer="", pos=(0, 0), states={})
    screen.on_building_click(building)
    assert "multi" in called
    assert called["multi"][5] == "dwelling"
    assert called["multi"][6] == ["A", "B"]
    assert "single" not in called


def test_single_overlay_invoked(monkeypatch):
    screen = _make_screen(["A"])
    called = {}

    def fake_multi(*args):
        called["multi"] = args

    def fake_single(*args):
        called["single"] = args

    monkeypatch.setattr("ui.multi_recruit_overlay.open", fake_multi)
    monkeypatch.setattr("ui.recruit_overlay.open", fake_single)

    building = TownBuilding(id="dwelling", layer="", pos=(0, 0), states={})
    screen.on_building_click(building)
    assert "single" in called
    assert called["single"][5] == "dwelling"
    assert called["single"][6] == "A"
    assert "multi" not in called

