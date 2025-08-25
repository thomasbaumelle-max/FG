"""Validate the icon manifest and look for unresolved identifiers."""
from __future__ import annotations

import ast
import json
import re
from pathlib import Path
from typing import Set


def _gather_used_ids(root: Path) -> Set[str]:
    """Return icon identifiers referenced in key source files."""

    prefixes = (
        "action_",
        "status_",
        "nav_",
        "poi_",
        "resource_",
        "round_",
        "stat_",
    )
    singles = {
        "end_turn",
        "town",
        "journal",
        "options",
        "stats_tab",
        "inventory_tab",
        "skills_tab",
    }

    used: Set[str] = set()
    search_paths = list((root / "ui").rglob("*.py"))
    search_paths.append(root / "core" / "combat_screen.py")
    search_paths.append(root / "render" / "world_renderer.py")
    for path in search_paths:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        for node in ast.walk(tree):
            value = None
            if isinstance(node, ast.Str):  # Py <3.8
                value = node.s
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                value = node.value
            if not value:
                continue
            if not re.fullmatch(r"[a-z_]+", value):
                continue
            if value.endswith("_"):
                continue
            if value in singles or any(value.startswith(p) for p in prefixes):
                used.add(value)
    return used


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    manifest_file = repo_root / "assets" / "icons" / "icons.json"
    with manifest_file.open("r", encoding="utf-8") as fh:
        data = json.load(fh)

    missing_files = []
    for icon_id, filename in data.items():
        if not (repo_root / filename).is_file():
            missing_files.append(f"{icon_id}: {filename}")

    used_ids = _gather_used_ids(repo_root)
    unresolved = sorted(used_ids - set(data.keys()))

    if missing_files:
        print("Missing icon files:")
        for item in missing_files:
            print(" -", item)
    if unresolved:
        print("Unresolved icon identifiers:")
        for item in unresolved:
            print(" -", item)
    if missing_files or unresolved:
        return 1
    print("All icon files exist and identifiers resolved.")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
