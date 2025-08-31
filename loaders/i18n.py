from __future__ import annotations

"""Lightweight helpers for loading translation strings.

The project keeps locale files in :mod:`assets/i18n` using a simple
``key -> value`` mapping per language.  This module exposes a small helper
that merges the default (French) strings with the requested language so
missing keys gracefully fall back to the French text.
"""

from typing import Dict, List
import os

from .core import Context, read_json


def load_locale(language: str, default: str = "fr") -> Dict[str, str]:
    """Return a dictionary of translation strings for ``language``.

    ``default`` specifies the base language to fall back to when a key is not
    present in the requested locale file.  The locale files are expected to
    live in ``assets/i18n/<lang>.json`` relative to the repository root.
    Missing files or parse errors result in an empty mapping so callers always
    receive a dictionary.
    """

    repo_root = os.path.dirname(os.path.dirname(__file__))
    search_paths: List[str] = []
    extra = os.environ.get("FG_ASSETS_DIR")
    if extra:
        search_paths.extend(
            os.path.join(p, "i18n") for p in extra.split(os.pathsep) if p
        )
    search_paths.append(os.path.join(repo_root, "assets", "i18n"))
    ctx = Context(repo_root=repo_root, search_paths=search_paths)

    try:
        data = read_json(ctx, f"{default}.json")
    except Exception:  # pragma: no cover - treated as empty fallback
        data = {}

    strings: Dict[str, str] = dict(data)
    if language != default:
        try:
            extra = read_json(ctx, f"{language}.json")
        except Exception:  # pragma: no cover - ignore missing locales
            extra = {}
        strings.update(extra)
    return strings
