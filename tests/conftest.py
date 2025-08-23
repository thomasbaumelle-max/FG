import importlib.util
import os
import sys
import pytest

# Ensure the project root is on the path so modules can be imported in tests
ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Provide a lightweight pygame stub so tests run without the real library
_STUB = os.path.join(os.path.dirname(__file__), "pygame_stub", "__init__.py")
spec = importlib.util.spec_from_file_location("pygame", _STUB)
pygame = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pygame)
# Override any existing pygame module so tests always use the stub
sys.modules["pygame"] = pygame


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

