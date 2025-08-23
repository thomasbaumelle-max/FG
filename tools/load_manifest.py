"""Generic helper to load JSON asset manifests.

This utility reads a manifest file describing assets and optionally loads
referenced images into an :class:`asset_manager.AssetManager`.  The manifest
is expected to be a JSON array with entries containing at least ``id`` and
``image`` fields.  Additional fields are preserved and returned to the caller.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional


def load_manifest(repo_root: str, manifest: str, asset_manager: Optional[Any] = None) -> List[Dict[str, Any]]:
    """Load entries from ``manifest``.

    Parameters
    ----------
    repo_root:
        Base path of the repository used to resolve the manifest path.
    manifest:
        Relative path to the manifest file from ``repo_root``.
    asset_manager:
        Optional :class:`~asset_manager.AssetManager` used to resolve image
        paths.  When provided, each entry's image is loaded and cached under
        its ``id``.

    Returns
    -------
    list of dict
        Parsed manifest entries or an empty list when the file is missing or
        malformed.
    """

    manifest_path = os.path.join(repo_root, manifest)
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            entries: List[Dict[str, Any]] = json.load(f)
    except Exception:
        return []

    if asset_manager is not None:
        for entry in entries:
            try:
                surf = asset_manager.get(entry["image"])
                asset_manager[entry["id"]] = surf
            except Exception:
                continue

    return entries
