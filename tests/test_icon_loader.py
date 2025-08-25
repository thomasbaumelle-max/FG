from types import SimpleNamespace
from pathlib import Path

import pygame

import loaders.icon_loader as icon_loader


def _prepare_pygame(monkeypatch):
    """Install minimal image and transform modules for the pygame stub."""

    def load(_path: str) -> pygame.Surface:
        return pygame.Surface((8, 8))

    def smoothscale(surf: pygame.Surface, size: tuple[int, int]) -> pygame.Surface:
        return pygame.Surface(size)

    monkeypatch.setattr(pygame, "image", SimpleNamespace(load=load), raising=False)
    monkeypatch.setattr(
        pygame, "transform", SimpleNamespace(smoothscale=smoothscale), raising=False
    )


def test_get_and_reload(monkeypatch):
    pygame.init()
    _prepare_pygame(monkeypatch)

    # ensure test icon exists
    icon_dir = Path("assets/icons")
    icon_dir.mkdir(parents=True, exist_ok=True)
    img_path = icon_dir / "end_turn.png"
    img_path.touch()

    icon_loader.reload()

    surf1 = icon_loader.get("end_turn", 32)
    assert isinstance(surf1, pygame.Surface)
    assert surf1.get_size() == (32, 32)

    def raise_load(path):
        raise AssertionError("should not load again")

    monkeypatch.setattr(pygame.image, "load", raise_load)
    surf2 = icon_loader.get("end_turn", 16)
    assert surf2.get_size() == (16, 16)

    icon_loader.reload()
    loaded = False

    def fake_load(path):
        nonlocal loaded
        loaded = True
        return pygame.Surface((8, 8))

    monkeypatch.setattr(pygame.image, "load", fake_load)
    surf3 = icon_loader.get("end_turn", 24)
    assert loaded
    assert surf3.get_size() == (24, 24)


def test_missing_icon_placeholder(monkeypatch):
    pygame.init()
    _prepare_pygame(monkeypatch)
    icon_loader.reload()
    surf = icon_loader.get("unknown", 20)
    assert surf.get_size() == (20, 20)
