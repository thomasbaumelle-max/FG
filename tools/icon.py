# ui/icons.py
from __future__ import annotations
import os, json
from dataclasses import dataclass
from typing import Dict, Tuple, Optional, List
import pygame

# Cherche "FG_ASSETS_DIR" sinon chemins relatifs au projet.
ASSETS_ROOT = os.environ.get("FG_ASSETS_DIR", "")

def _resolve(path: str) -> str:
    if os.path.isabs(path):
        return path
    if ASSETS_ROOT:
        candidate = os.path.join(ASSETS_ROOT, path)
        if os.path.exists(candidate):
            return candidate
    return path  # relatif au cwd si pas d'env

@dataclass
class IconSlice:
    sheet_key: str       # clé de feuille
    rect: pygame.Rect    # position/tailles dans la feuille

class IconAtlasManager:
    """
    - load_atlas(json_path): enregistre un atlas (grid ou freeform)
    - get_icon(name, size): Surface Pygame mise à l'échelle (mise en cache)
    - blit_icon(surface, name, pos, size): blitte directement
    - export_all(out_dir, sizes): optionnel, pour générer des PNG unitaires
    """
    def __init__(self) -> None:
        self.sheets: Dict[str, pygame.Surface] = {}     # sheet_key -> Surface
        self.slices: Dict[str, IconSlice] = {}          # name -> IconSlice
        self.cache: Dict[Tuple[str, int, int], pygame.Surface] = {}  # (name,w,h) -> Surface

    # ---------- chargement ----------
    def load_atlas(self, json_path: str) -> None:
        json_path_resolved = _resolve(json_path)
        with open(json_path_resolved, "r", encoding="utf-8") as f:
            meta = json.load(f)

        image_rel = meta["image"]
        image_path = _resolve(image_rel)
        sheet_key = image_rel  # utilise le chemin logique comme clé

        if sheet_key not in self.sheets:
            img = pygame.image.load(image_path).convert_alpha()
            self.sheets[sheet_key] = img

        atlas_type = meta.get("type", "grid")

        if atlas_type == "grid":
            self._register_grid(sheet_key, meta)
        elif atlas_type == "freeform":
            self._register_freeform(sheet_key, meta)
        else:
            raise ValueError(f"Atlas type inconnu: {atlas_type}")

    def _register_grid(self, sheet_key: str, meta: dict) -> None:
        tile_w = meta["tile_w"]
        tile_h = meta["tile_h"]
        rows   = meta["rows"]
        cols   = meta["cols"]
        names: List[List[str]] = meta["names"]

        if len(names) != rows or any(len(row) != cols for row in names):
            raise ValueError("Dimension 'names' ne correspond pas à rows/cols")

        for r in range(rows):
            for c in range(cols):
                name = names[r][c]
                if not name:
                    continue
                rect = pygame.Rect(c * tile_w, r * tile_h, tile_w, tile_h)
                self.slices[name] = IconSlice(sheet_key, rect)

    def _register_freeform(self, sheet_key: str, meta: dict) -> None:
        # {"type":"freeform","image":"...","icons":[{"name":"hp","rect":[x,y,w,h]}, ...]}
        for it in meta["icons"]:
            name = it["name"]
            x, y, w, h = it["rect"]
            rect = pygame.Rect(x, y, w, h)
            self.slices[name] = IconSlice(sheet_key, rect)

    # ---------- accès ----------
    def get_icon(self, name: str, size: Optional[int | Tuple[int, int]] = None) -> pygame.Surface:
        """
        size: int  -> carré (w=h)
              (w,h)-> sur mesure
              None -> taille native
        """
        if name not in self.slices:
            raise KeyError(f"Icone '{name}' inconnue. Atlas chargés: {len(self.slices)}")

        slice_ = self.slices[name]
        sheet = self.sheets[slice_.sheet_key]
        surf = sheet.subsurface(slice_.rect).copy()

        if size is None:
            return surf

        if isinstance(size, int):
            w = h = size
        else:
            w, h = size

        key = (name, w, h)
        if key in self.cache:
            return self.cache[key]

        if (w, h) == (surf.get_width(), surf.get_height()):
            out = surf
        else:
            out = pygame.transform.smoothscale(surf, (w, h))
        self.cache[key] = out
        return out

    def blit_icon(self, dest_surface: pygame.Surface, name: str, pos: Tuple[int, int],
                  size: Optional[int | Tuple[int, int]] = None) -> None:
        ic = self.get_icon(name, size)
        dest_surface.blit(ic, pos)

    # ---------- utilitaire ----------
    def export_all(self, out_dir: str, size: Optional[int | Tuple[int, int]] = None) -> None:
        os.makedirs(out_dir, exist_ok=True)
        for name in self.slices.keys():
            surf = self.get_icon(name, size)
            pygame.image.save(surf, os.path.join(out_dir, f"{name}.png"))
