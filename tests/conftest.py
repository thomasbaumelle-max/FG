import importlib.util
import importlib.util
import os
import sys
import math
import pytest

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
def simple_combat():
    """Return a factory that builds a minimal :class:`Combat` instance.

    The factory accepts optional ``hero_units`` and ``enemy_units`` lists and
    any additional keyword arguments forwarded to :class:`Combat`.  A dummy
    ``pygame.Surface`` and empty assets are used by default and a basic water
    battlefield grid is supplied so no ``WorldMap`` interaction is required.
    """

    def _factory(hero_units=None, enemy_units=None, *, screen=None, assets=None,
                 combat_map=None, **kwargs):
        import pygame

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
            combat_map = water_battlefield_template()
        return Combat(
            screen,
            assets,
            hero_units or [],
            enemy_units or [],
            combat_map=combat_map,
            **kwargs,
        )

    return _factory

