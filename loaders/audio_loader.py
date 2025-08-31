"""Utilities for locating audio assets with consistent project root handling."""

from __future__ import annotations

import os
from typing import Optional, Sequence, Any

from .core import Context, find_file, read_json


def _build_context(search_paths: Sequence[str]) -> Context:
    repo_root = os.path.dirname(os.path.dirname(__file__))
    return Context(repo_root=repo_root, search_paths=search_paths, asset_loader=None)


def find_audio_file(filename: str, search_paths: Sequence[str] | None = None) -> Optional[str]:
    """Return absolute path to ``filename`` searching ``search_paths``.

    ``search_paths`` defaults to ``["assets"]`` relative to the repository root.
    ``None`` is returned when the file is not found.
    """

    if search_paths is None:
        search_paths = ["assets"]
    ctx = _build_context(search_paths)
    try:
        return find_file(ctx, filename)
    except FileNotFoundError:
        return None


def load_manifest(name: str, search_paths: Sequence[str] | None = None) -> Any:
    """Load an audio manifest JSON file under ``assets/audio``."""

    if search_paths is None:
        search_paths = ["assets"]
    ctx = _build_context(search_paths)
    try:
        return read_json(ctx, os.path.join("audio", name))
    except Exception:
        return []


__all__ = ["find_audio_file", "load_manifest"]
