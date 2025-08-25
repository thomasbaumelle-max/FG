# loaders/icon_loader.py
from __future__ import annotations
from pathlib import Path
import os, json
import pygame

def _detect_project_root() -> Path:
    # Remonte depuis ce fichier jusqu’à trouver 'assets'
    start = Path(__file__).resolve()
    for p in (start, *start.parents):
        if (p / "assets").is_dir():
            return p
    return Path.cwd()

_ROOT = _detect_project_root()

def _candidate_asset_dirs() -> list[Path]:
    dirs: list[Path] = []
    # 1) Override explicite
    env = os.environ.get("FG_ASSETS_DIR")
    if env:
        p = Path(env).expanduser().resolve()
        dirs.append(p)
    # 2) assets du projet
    dirs.append((_ROOT / "assets").resolve())
    # 3) assets au niveau parent (ton cas : D:\FG_v0\assets)
    parent_assets = (_ROOT.parent / "assets").resolve()
    if parent_assets.is_dir():
        dirs.append(parent_assets)
    # Uniques en gardant l’ordre
    seen = set()
    out = []
    for d in dirs:
        if d not in seen:
            out.append(d); seen.add(d)
    return out

_ASSET_DIRS = _candidate_asset_dirs()

# Manifest
def _load_icon_map() -> dict[str, str]:
    # on lit le manifest depuis le premier assets/* qui a icons/icons.json
    for assets in _ASSET_DIRS:
        manifest = assets / "icons" / "icons.json"
        if manifest.is_file():
            data = json.loads(manifest.read_text(encoding="utf-8"))
            # cleanup de base
            return {k: (v.strip() if isinstance(v, str) else v) for k, v in data.items()}
    print(f"[icon_loader] icons.json introuvable dans: {', '.join(map(str,_ASSET_DIRS))}")
    return {}

_ICON_MAP = _load_icon_map()

def _placeholder_surface(sz: int = 32) -> pygame.Surface:
    s = pygame.Surface((sz, sz), pygame.SRCALPHA); s.fill((128,128,128,255)); return s

def _resolve_icon_path(filename: str | None) -> Path | None:
    if not filename:
        return None
    name = Path(filename).name  # on tolère 'assets/icons/x.png' ou juste 'x.png'
    candidates = []
    for assets in _ASSET_DIRS:
        candidates += [
            assets / "icons" / name,            # x.png
            assets / Path(filename),            # assets/icons/x.png
        ]
    for c in candidates:
        if c.is_file():
            return c
    return None

def get(icon_id: str, size: int = 32) -> pygame.Surface:
    filename = _ICON_MAP.get(icon_id)
    path = _resolve_icon_path(filename)
    try:
        if path:
            surf = pygame.image.load(path)
        else:
            print(f"[icon_loader] Missing file for '{icon_id}': {filename!r} | search={_ASSET_DIRS}")
            surf = _placeholder_surface(size)
    except Exception as e:
        print(f"[icon_loader] Error loading '{icon_id}' from {path}: {e}")
        surf = _placeholder_surface(size)
    return pygame.transform.smoothscale(surf, (size, size))

def verify_all(verbose: bool = True) -> list[str]:
    missing = []
    for icon_id, filename in _ICON_MAP.items():
        if not (_resolve_icon_path(filename) or filename is None):
            missing.append(f"{icon_id} -> {filename}")
    if verbose:
        if missing:
            print("[icon_loader] Missing icons (searched in):", ", ".join(map(str,_ASSET_DIRS)))
            for m in missing: print(" -", m)
        else:
            print("[icon_loader] All icons present.")
    return missing
