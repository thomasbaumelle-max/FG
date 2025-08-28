import gc
import gc
import gc
import types

import graphics.scale as scale_mod


def _patched_scale(monkeypatch):
    calls = []

    def fake_scale(surface, size):
        calls.append((id(surface), size))
        return scale_mod.pygame.Surface(size)

    stub = types.SimpleNamespace(
        Surface=scale_mod.pygame.Surface,
        transform=types.SimpleNamespace(scale=fake_scale, smoothscale=fake_scale),
    )
    monkeypatch.setattr(scale_mod, "pygame", stub)
    return stub, calls


def test_scale_surface_uses_cache(monkeypatch):
    stub, calls = _patched_scale(monkeypatch)

    surf = stub.Surface((10, 10))
    scaled1 = scale_mod.scale_surface(surf, (5, 5))
    scaled2 = scale_mod.scale_surface(surf, (5, 5))

    assert scaled1 is scaled2
    assert len(calls) == 1


def test_scale_surface_invalidates_on_free(monkeypatch):
    stub, calls = _patched_scale(monkeypatch)

    surf = stub.Surface((10, 10))
    scale_mod.scale_surface(surf, (5, 5))
    del surf
    gc.collect()

    surf2 = stub.Surface((10, 10))
    scale_mod.scale_surface(surf2, (5, 5))

    assert len(calls) == 2
