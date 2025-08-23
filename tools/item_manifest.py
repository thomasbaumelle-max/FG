"""Loading helper for the item manifest.

This thin wrapper delegates to :func:`tools.load_manifest.load_manifest` to
read the item manifest and optionally load the referenced images into an
:class:`~asset_manager.AssetManager`.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from .load_manifest import load_manifest


def load_item_manifest(repo_root: str, asset_manager: Optional[Any] = None) -> List[Dict[str, Any]]:
    """Load item entries from ``assets/items/items.json``.

    Parameters
    ----------
    repo_root:
        Base path of the repository used to locate the manifest file.
    asset_manager:
        Optional :class:`~asset_manager.AssetManager` used to load and cache
        the item images.
    """

    manifest = os.path.join("assets", "items", "items.json")
    return load_manifest(repo_root, manifest, asset_manager)
