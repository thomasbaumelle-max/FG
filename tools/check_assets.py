#!/usr/bin/env python3
"""Check asset files referenced in JSON manifests.

This script scans `assets/**/*.json` for entries containing `path` or `files`
fields and verifies that the referenced files exist inside directories listed
in the `FG_ASSETS_DIR` environment variable.

Missing files or parsing errors are printed to stdout.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Iterable, List


def _load_manifest(path: str) -> Iterable[dict]:
    """Load a manifest file stripping ``//`` comments."""

    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read()
    text = re.sub(r"//.*", "", text)
    data = json.loads(text)
    return data if isinstance(data, list) else []


def _expected_files(entry: dict) -> List[str]:
    """Return file paths referenced by a manifest entry."""

    files = entry.get("files")
    if files:
        return list(files)

    base = entry.get("path")
    if not base:
        return []

    variants = int(entry.get("variants", 1))
    if variants > 1:
        return [f"{base}_{i}.png" for i in range(variants)]
    return [base if base.endswith(".png") else f"{base}.png"]


def main() -> int:
    env = os.environ.get("FG_ASSETS_DIR")
    if not env:
        print("FG_ASSETS_DIR is not set", file=sys.stderr)
        return 1

    search_paths = [os.path.abspath(p) for p in env.split(os.pathsep)]

    repo_root = Path(__file__).resolve().parent.parent
    manifests = repo_root.joinpath("assets").rglob("*.json")

    missing: List[str] = []
    for manifest in sorted(manifests):
        try:
            entries = _load_manifest(str(manifest))
        except Exception as exc:  # pragma: no cover - robust against bad files
            print(f"{manifest}: parse error ({exc})")
            continue
        for entry in entries:
            for rel in _expected_files(entry):
                if any(Path(base, rel).is_file() for base in search_paths):
                    continue
                missing.append(f"{rel} (from {manifest})")

    if missing:
        print("Missing assets:")
        for item in missing:
            print(" -", item)
        return 1

    print("All assets referenced in manifests exist.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
