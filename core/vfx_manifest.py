from __future__ import annotations
from typing import Dict, Any

"""Shared VFX manifest cache.

This module provides a small registry where :mod:`core.game` can store the
loaded visual effects manifest so other modules such as :mod:`core.combat` and
:mod:`core.spell` can query metadata like frame dimensions and timings without
reloading the JSON file.
"""

_VFX_MANIFEST: Dict[str, Dict[str, Any]] = {}


def set_vfx_manifest(entries: Dict[str, Dict[str, Any]]) -> None:
    """Replace the global VFX manifest with ``entries``."""
    global _VFX_MANIFEST
    _VFX_MANIFEST = entries


def get_vfx_entry(asset: str) -> Dict[str, Any] | None:
    """Return the manifest entry for ``asset`` if available."""
    return _VFX_MANIFEST.get(asset)
