from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Sequence
import json
import os
import re


@dataclass
class Context:
    repo_root: str
    search_paths: Sequence[str]
    asset_loader: Any | None = None


def _resolve_search_path(ctx: Context, base: str) -> str:
    return base if os.path.isabs(base) else os.path.join(ctx.repo_root, base)


def find_file(ctx: Context, rel_path: str) -> str:
    for base in ctx.search_paths:
        candidate = os.path.join(_resolve_search_path(ctx, base), rel_path)
        if os.path.isfile(candidate):
            return candidate
    raise FileNotFoundError(rel_path)


def read_json(ctx: Context, rel_path: str) -> Any:
    path = find_file(ctx, rel_path)
    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read()
    text = re.sub(r"//.*", "", text)
    return json.loads(text)


def require_keys(data: Dict[str, Any], keys: Iterable[str]) -> None:
    missing = [k for k in keys if k not in data]
    if missing:
        raise KeyError(f"Missing keys: {', '.join(missing)}")


def expand_variants(entry: Dict[str, Any], key: str = "path", variants: str = "variants") -> List[str]:
    if "files" in entry:
        return list(entry["files"])
    base = entry.get(key)
    if not base:
        return []
    var = int(entry.get(variants, 0))
    if var <= 1:
        return [base if base.endswith(".png") else f"{base}.png"]
    return [f"{base}_{i}.png" for i in range(var)]
