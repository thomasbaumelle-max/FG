"""Loading helper for artifact manifest."""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from .load_manifest import load_manifest


def load_artifact_manifest(repo_root: str, asset_manager: Optional[Any] = None) -> List[Dict[str, Any]]:
    """Load artifact entries from ``assets/artifacts.json``."""
    manifest = os.path.join("assets", "artifacts.json")
    return load_manifest(repo_root, manifest, asset_manager)
