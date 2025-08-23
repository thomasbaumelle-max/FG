"""Small wrapper around asset dictionary providing a fallback surface.

The ``AssetManager`` behaves mostly like a standard ``dict`` mapping asset
names to :class:`pygame.Surface` objects.  The :meth:`get` method however
returns a placeholder surface instead of ``None`` when an asset is missing,
which simplifies rendering code and avoids repeated ``None`` checks.
"""

from __future__ import annotations

import os
import logging
from typing import Any, Callable, List

import pygame

import constants
import theme
from state.event_bus import EVENT_BUS, ON_ASSET_LOAD_PROGRESS

logger = logging.getLogger(__name__)


MASK_NAMES = [
    "mask_n.png",
    "mask_e.png",
    "mask_s.png",
    "mask_w.png",
    "mask_ne.png",
    "mask_nw.png",
    "mask_se.png",
    "mask_sw.png",
]


class AssetManager(dict):
    """Dictionary-like container for images with a built-in fallback."""

    def __init__(
        self,
        repo_root: str,
        *args: Any,
        progress_callback: Callable[[int, int], None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)

        self.search_paths: List[str] = []
        env = os.environ.get("FG_ASSETS_DIR")
        if env:
            self.search_paths.extend(env.split(os.pathsep))
        self.search_paths.append(os.path.join(repo_root, "assets"))

        self._progress_callback = progress_callback
        self._progress_done = 0
        self._progress_total = self._count_index_files() + len(MASK_NAMES)

        # Optional index mapping lowercase relative paths to actual files for
        # faster case-insensitive lookups.  The index is populated once at
        # startup and reused for subsequent ``get`` calls.
        self._index: dict[str, str] = {}
        self._build_index()

        # Generic fallback surface used when an image is missing.
        size = constants.TILE_SIZE
        self._fallback = pygame.Surface((size, size), pygame.SRCALPHA)
        self._fallback.fill(theme.PALETTE["panel"])

        # Pre-load generic alpha masks used for biome blending.  Missing files
        # are replaced with blank placeholder surfaces so lookups always
        # succeed even in minimal test environments without actual image
        # assets.
        self._load_alpha_masks()

    def get(self, key: str, default: Any = None) -> Any:
        """Return the image for ``key`` or a placeholder if missing."""

        if default is None:
            default = self._fallback

        name, ext = os.path.splitext(key)
        cache_key = name if ext else key

        if cache_key not in self:
            fname = key if ext else key + ".png"
            fname = fname.replace(os.sep, "/")
            candidates = [fname, fname.lower(), fname.upper()]

            # First try the case-insensitive index built at startup.
            path = self._index.get(fname.lower())
            if path and os.path.isfile(path):
                try:
                    surf = pygame.image.load(path).convert_alpha()
                except Exception:  # pragma: no cover - robustness
                    surf = default
                self[cache_key] = surf
            else:
                # Fall back to searching each candidate in the configured paths.
                for base in self.search_paths:
                    for candidate in candidates:
                        path = os.path.join(base, candidate)
                        if os.path.isfile(path):
                            try:
                                surf = pygame.image.load(path).convert_alpha()
                            except Exception:  # pragma: no cover - robustness
                                surf = default
                            self[cache_key] = surf
                            # Update the index for faster future lookups.
                            self._index.setdefault(fname.lower(), path)
                            break
                    if cache_key in self:
                        break
            if cache_key not in self:
                self[cache_key] = default
                logger.warning("Missing asset %s", fname)

        return super().get(cache_key, default)

    # ------------------------------------------------------------------
    def _load_alpha_masks(self) -> None:
        """Load directional alpha mask images into the manager."""

        size = constants.TILE_SIZE
        for fname in MASK_NAMES:
            surf: pygame.Surface | None = None
            for base in self.search_paths:
                path = os.path.join(base, "overlays", fname)
                if os.path.isfile(path):
                    try:
                        surf = pygame.image.load(path).convert_alpha()
                    except Exception:  # pragma: no cover - robustness
                        surf = pygame.Surface((size, size), pygame.SRCALPHA)
                    break
            if surf is None:
                surf = pygame.Surface((size, size), pygame.SRCALPHA)
            key = os.path.splitext(fname)[0]
            self[key] = surf
            self[fname] = surf
            self._report_progress()

    # ------------------------------------------------------------------
    def _build_index(self) -> None:
        """Index all available asset files using lowercase paths."""

        for base in self.search_paths:
            if not os.path.isdir(base):
                continue
            for root, _dirs, files in os.walk(base):
                for fname in files:
                    rel = os.path.relpath(os.path.join(root, fname), base).replace(
                        os.sep, "/"
                    )
                    self._index.setdefault(rel.lower(), os.path.join(root, fname))
                    self._report_progress()

    def _report_progress(self) -> None:
        """Notify listeners about loading progress."""

        self._progress_done += 1
        if self._progress_callback:
            self._progress_callback(self._progress_done, self._progress_total)
        EVENT_BUS.publish(
            ON_ASSET_LOAD_PROGRESS, self._progress_done, self._progress_total
        )

    def _count_index_files(self) -> int:
        count = 0
        for base in self.search_paths:
            if not os.path.isdir(base):
                continue
            for _root, _dirs, files in os.walk(base):
                count += len(files)
        return count
