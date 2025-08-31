"""Utilities for locating audio assets with consistent project root handling."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional, Sequence

from .core import Context, find_file, read_json


_ROOT = Path(__file__).resolve().parents[1]


def _candidate_asset_dirs() -> list[Path]:
    dirs: list[Path] = []
    env = os.environ.get("FG_ASSETS_DIR")
    if env:
        for part in env.split(os.pathsep):
            if part:
                p = Path(part).expanduser()
                if not p.is_absolute():
                    p = _ROOT / p
                dirs.append(p.resolve())
    dirs.append((_ROOT / "assets").resolve())
    parent_assets = (_ROOT.parent / "assets").resolve()
    if parent_assets.is_dir():
        dirs.append(parent_assets)
    seen: set[Path] = set()
    out: list[Path] = []
    for d in dirs:
        if d not in seen:
            out.append(d)
            seen.add(d)
    return out


def _build_context(extra_paths: Sequence[str | os.PathLike[str]] | None = None) -> Context:
    dirs = _candidate_asset_dirs()
    if extra_paths:
        for p in extra_paths:
            q = Path(p).expanduser()
            if not q.is_absolute():
                q = _ROOT / q
            q = q.resolve()
            if q not in dirs:
                dirs.append(q)
    return Context(repo_root=str(_ROOT), search_paths=[str(d) for d in dirs], asset_loader=None)


def find_audio_file(filename: str, search_paths: Sequence[str | os.PathLike[str]] | None = None) -> Optional[str]:
    """Return absolute path to ``filename`` searching ``search_paths``.

    ``search_paths`` augments the default candidate asset directories.
    ``None`` is returned when the file is not found.
    """

    ctx = _build_context(search_paths)
    try:
        return find_file(ctx, str(filename))
    except FileNotFoundError:
        return None


def load_manifest(name: str, search_paths: Sequence[str | os.PathLike[str]] | None = None) -> Any:
    """Load an audio manifest JSON file under ``assets/audio``."""

    ctx = _build_context(search_paths)
    rel = Path("audio") / name
    try:
        return read_json(ctx, str(rel))
    except Exception:
        return []


__all__ = ["find_audio_file", "load_manifest"]
