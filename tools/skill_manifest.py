"""Load skill definitions from the project assets.

The original project stored all skills in a single ``assets/skills.json`` file.
Recent work introduced per‑faction skill files under ``assets/skills``.  This
loader now combines the legacy file with any additional manifests found in that
directory.  For branch based trees the loader automatically links the four
ranks (``N``, ``A``, ``E`` and ``M``) so that each rank requires the previous
one.  The function returns a flat list of entry dictionaries ready for
consumption by :mod:`core.entities`.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List

from tools.icon import get_icon


def load_skill_manifest(
    repo_root: str,
    assets: Dict[str, Any] | None = None,
    faction_id: str | None = None,
) -> List[Dict[str, Any]]:
    """Return raw skill entries from JSON manifests.

    Parameters
    ----------
    repo_root:
        Path to the repository root.  The function looks for ``assets/skills.json``
        (legacy flat list) and for additional ``*.json`` files under
        ``assets/skills``.  When ``faction_id`` is provided only the
        corresponding ``skills_<faction_id>.json`` file is loaded from this
        directory.
    assets:
        Optional mapping where extracted icons will be stored.  When provided
        the loader expects each manifest to specify a ``sheet`` key pointing to
        a spritesheet containing the skill icons.
    faction_id:
        Optional faction identifier limiting which modern manifest is loaded.
    """

    entries: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------ legacy
    legacy_path = os.path.join(repo_root, "assets", "skills.json")
    try:
        with open(legacy_path, "r", encoding="utf-8") as fh:
            data: List[Dict[str, Any]] = json.load(fh)
            entries.extend(data)
    except Exception:
        pass

    # ------------------------------------------------------------------ modern
    skills_dir = os.path.join(repo_root, "assets", "skills")
    rank_order = ["N", "A", "E", "M"]
    if os.path.isdir(skills_dir):
        if faction_id:
            fnames = [f"skills_{faction_id}.json"]
        else:
            fnames = sorted(f for f in os.listdir(skills_dir) if f.endswith(".json"))

        for fname in fnames:
            if not fname.endswith(".json"):
                continue
            path = os.path.join(skills_dir, fname)
            if not os.path.exists(path):
                continue
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
            except Exception:  # pragma: no cover - invalid file
                continue

            sheet_name = data.pop("sheet", None)
            sheet_path = os.path.join(repo_root, "assets", sheet_name) if sheet_name else ""

            for branch, ranks in data.items():
                prev_id = None
                for rank in rank_order:
                    if rank not in ranks:
                        continue
                    entry: Dict[str, Any] = ranks[rank]
                    entry.setdefault("id", f"{branch}_{rank}")
                    entry.setdefault("name", entry["id"])
                    entry.setdefault("desc", "")
                    entry.setdefault("cost", 1)
                    entry.setdefault("effects", [])
                    entry.setdefault("icon", "")
                    entry["branch"] = branch
                    entry["rank"] = rank
                    reqs = entry.get("requires", [])
                    if not isinstance(reqs, list):
                        reqs = [reqs]
                    if prev_id and prev_id not in reqs:
                        reqs.append(prev_id)
                    entry["requires"] = reqs

                    if assets is not None and sheet_path and entry.get("coords") is not None:
                        assets[entry["id"]] = get_icon(sheet_path, tuple(entry["coords"]))
                        entry["icon"] = entry["id"]

                    entries.append(entry)
                    prev_id = entry["id"]

    return entries
