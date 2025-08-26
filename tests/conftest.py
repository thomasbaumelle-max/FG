import importlib.util
import os
import sys
import math
import random
import pytest
from types import SimpleNamespace

os.environ.setdefault("FG_FAST_TESTS", "1")

# Ensure specific environment variables for tests
@pytest.fixture(scope="session", autouse=True)
def _configure_test_environment():
    os.environ.setdefault("FG_FAST_TESTS", "1")
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    yield

# Provide a lightweight pygame stub so tests run without the real library
_STUB = os.path.join(os.path.dirname(__file__), "pygame_stub", "__init__.py")
spec = importlib.util.spec_from_file_location("pygame", _STUB)
pygame = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pygame)
# Override any existing pygame module so tests always use the stub
sys.modules["pygame"] = pygame

# Ensure the project root is on the path so modules can be imported in tests
ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import constants
from core.combat import Combat, water_battlefield_template
from state.event_bus import EVENT_BUS
from loaders.asset_manager import AssetManager


@pytest.fixture
def pygame_stub(monkeypatch):
    """Return a configurable pygame stub module.

    The returned callable reloads the base stub and applies attribute
    overrides passed as keyword arguments using dotted paths.  The created
    module is installed into ``sys.modules`` as ``pygame`` and returned so
    tests can further monkeypatch or inspect it.
    """

    def _factory(**overrides):
        spec = importlib.util.spec_from_file_location("pygame", _STUB)
        stub = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(stub)
        for name, value in overrides.items():
            target = stub
            parts = name.split(".")
            for part in parts[:-1]:
                target = getattr(target, part)
            setattr(target, parts[-1], value)
        monkeypatch.setitem(sys.modules, "pygame", stub)
        # Expose stub attributes on the factory for convenience
        for attr in ("Surface", "Rect", "draw"):
            setattr(_factory, attr, getattr(stub, attr))
        return stub

    return _factory


@pytest.fixture(autouse=True)
def _restore_pygame_module():
    """Ensure the pygame stub is present for each test.

    Some tests replace ``sys.modules['pygame']`` with their own simplified
    objects.  Resetting it before and after each test isolates such changes and
    keeps later tests from accidentally using an unexpected stub.
    """

    sys.modules["pygame"] = pygame
    yield
    sys.modules["pygame"] = pygame


@pytest.fixture(scope="session")
def asset_manager():
    """Provide a reusable :class:`AssetManager` instance for tests."""

    import pygame

    if not hasattr(pygame, "image"):
        pygame.image = SimpleNamespace(load=lambda path: pygame.Surface((1, 1)))

    mgr = AssetManager(repo_root=".")
    yield mgr
    if hasattr(mgr, "close"):
        mgr.close()


@pytest.fixture(autouse=True)
def _reset_event_bus():
    """Isolate global event subscriptions for parallel tests."""

    EVENT_BUS.reset()
    yield
    EVENT_BUS.reset()


@pytest.fixture(autouse=True)
def _restore_ai_difficulty():
    """Reset :data:`constants.AI_DIFFICULTY` after each test."""

    saved = constants.AI_DIFFICULTY
    yield
    constants.AI_DIFFICULTY = saved


@pytest.fixture
def rng():
    """Return a deterministic random number generator."""

    return random.Random(0)


@pytest.fixture
def simple_combat(monkeypatch):
    """Return a factory that builds a minimal :class:`Combat` instance.

    The created combat uses a reduced 5×5 battlefield so tests can run quickly
    without needing any :class:`WorldMap` generation.  The factory accepts
    optional ``hero_units`` and ``enemy_units`` lists and forwards any extra
    keyword arguments to :class:`Combat`.
    """

    def _factory(hero_units=None, enemy_units=None, *, screen=None, assets=None,
                 combat_map=None, **kwargs):
        import pygame

        # Shrink the combat grid for the duration of the test
        monkeypatch.setattr(constants, "COMBAT_GRID_WIDTH", 5)
        monkeypatch.setattr(constants, "COMBAT_GRID_HEIGHT", 5)

        pygame.init()
        if screen is None:
            hex_w = constants.COMBAT_HEX_SIZE
            hex_h = int(constants.COMBAT_HEX_SIZE * math.sqrt(3) / 2)
            screen = pygame.Surface(
                (
                    int(hex_w + (constants.COMBAT_GRID_WIDTH - 1) * hex_w * 3 / 4),
                    int(hex_h * constants.COMBAT_GRID_HEIGHT + hex_h / 2),
                )
            )
        if assets is None:
            assets = {}
        if combat_map is None:
            combat_map = [["ocean"] * constants.COMBAT_GRID_WIDTH for _ in range(constants.COMBAT_GRID_HEIGHT)]
        return Combat(
            screen,
            assets,
            hero_units or [],
            enemy_units or [],
            combat_map=combat_map,
            **kwargs,
        )

    return _factory

