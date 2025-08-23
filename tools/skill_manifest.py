"""Load skill definitions from ``assets/skills.json``."""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List


def load_skill_manifest(repo_root: str) -> List[Dict[str, Any]]:
    """Return raw skill entries from the JSON manifest."""
    manifest_path = os.path.join(repo_root, "assets", "skills.json")
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            data: List[Dict[str, Any]] = json.load(f)
    except Exception:
        return []
    return data
