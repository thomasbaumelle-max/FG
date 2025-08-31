"""
flora_loader.py — gestion des assets de flore (décals, collectibles, décors hauts),
chargement depuis un manifest JSON, placement (blue‑noise / type Poisson discret),
et dessin trié (baseline) compatible top‑down et futur rendu isométrique.

⚙️ Manifest attendu (exemple minimal) — assets/realms/<realm>/flora.json
[
  {
    "id": "scarlet_herb_a",
    "type": "collectible",                # "decal" | "collectible" | "tall"
    "biomes": ["scarletia_crimson_forest"],
    "footprint": [1,1],
    "anchor_px": [64,110],                 # bas‑centre sur le PNG
    "passable": true,
    "occludes": false,
    "path": "flora/collectibles/scarlet_herb_a",
    "variants": 3,
    "collectible": {"item":"scarlet_leaf","qty":[1,3]},
    "spawn": {"density": 0.02, "min_dist": 2, "avoid": ["road","water"]}
  },
  {
    "id": "scarlet_tree_a",
    "type": "tall",
    "biomes": ["scarletia_crimson_forest"],
    "footprint": [2,2],
    "anchor_px": [128,236],
    "passable": false,
    "occludes": true,
    "path": "flora/tall/scarlet_tree_a",  # utilise suffixes _0.._N‑1 si variants>1, sinon ".png"
    "variants": 2,
    "spawn": {"density": 0.006, "min_dist": 3}
  },
  {
    "id": "pebble_patch_a",
    "type": "decal",
    "biomes": ["scarletia_echo_plain","scarletia_volcanic"],
    "size_px": [64,64],
    "path": "flora/decals/pebble_patch_a",
    "variants": 4,
    "spawn": {"prob":0.12}
  }
]

💡 Intégration typique :
    loader = FloraLoader(ctx, tile_size=64)
    loader.load_manifest("realms/scarletia")

    # Placement automatique sur la carte (par biomes)
    props = loader.autoplace(biome_grid, tags_grid, rng_seed=42)

    # Dessin
    def grid_to_screen(x, y):
        # top‑down simple : coin bas de la tuile = (x*TILE, y*TILE)
        return x*64 + 32, y*64 + 64  # ancre sol = bas‑centre
    loader.draw_props(screen, props, grid_to_screen)

    # Picking (ex.: clic souris)
    hit = loader.pick_prop_at(props, mouse_pos, grid_to_screen)
"""
from __future__ import annotations
import os, random, glob
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Iterable

import pygame

from .core import Context, read_json, expand_variants
from .biomes import BiomeCatalog
import constants
from graphics.scale import scale_with_anchor

Vec2 = Tuple[int,int]

TYPE_DEFAULTS = {
    "decal": {"prob": 0.4},
    "tall": {"density": 0.2},
    "collectible": {"density": 0.1},
}

# Minimum counts per biome to ensure visible flora
MIN_COUNTS = {"collectible": 1, "tall": 2, "decal": 3}

# -----------------------------------------------------------------------------
# Données & modèles
# -----------------------------------------------------------------------------

@dataclass
class FloraAsset:
    id: str
    type: str                      # "decal" | "collectible" | "tall"
    biomes: List[str]
    footprint: Vec2                # (w,h) en cases — par défaut (1,1)
    anchor_px: Vec2                # (ax, ay) bas‑centre dans l'image
    passable: bool = True
    occludes: bool = False
    files: List[str] = field(default_factory=list)  # chemins relatifs PNG
    size_px: Optional[Vec2] = None          # pour décals
    collectible: Optional[dict] = None      # {item, qty:[a,b]}
    shadow_baked: bool = False
    spawn: dict = field(default_factory=dict)

@dataclass
class PropInstance:
    asset_id: str
    biome: str
    tile_xy: Vec2                  # case de l'ancre (x,y)
    variant: int
    footprint: Vec2
    anchor_px: Vec2
    passable: bool
    occludes: bool
    rect_world: pygame.Rect        # rect englobant en pixels "sol" (footprint)

# -----------------------------------------------------------------------------
# Loader principal
# -----------------------------------------------------------------------------

class FloraLoader:
    def __init__(self, ctx: Context, tile_size: int = 64):
        self.ctx = ctx
        self.assets_root = (
            ctx.search_paths[0] if ctx.search_paths else ctx.repo_root
        )
        self.am = ctx.asset_loader   # optionnel : instance avec .get(key,size)->Surface
        self.tile = tile_size
        self.assets: Dict[str, FloraAsset] = {}
        self._surf_cache: Dict[
            Tuple[str, int], Tuple[pygame.Surface, Tuple[int, int]]
        ] = {}

    # ---------- Chargement manifest ----------
    def load_manifest(self, manifest_path: str) -> None:
        """Load flora definitions from a file or directory.

        ``manifest_path`` may be a single JSON file or a directory containing
        one or more ``flora*.json`` files.  All matching files are merged.
        """
        manifest_files: List[str] = []
        for base in self.ctx.search_paths:
            base_abs = (
                base if os.path.isabs(base) else os.path.join(self.ctx.repo_root, base)
            )
            candidate = os.path.join(base_abs, manifest_path)
            if os.path.isdir(candidate):
                pattern = os.path.join(candidate, "flora*.json")
                for fn in sorted(glob.glob(pattern)):
                    manifest_files.append(
                        os.path.relpath(fn, base_abs).replace(os.sep, "/")
                    )
            elif os.path.isfile(candidate):
                manifest_files.append(
                    os.path.relpath(candidate, base_abs).replace(os.sep, "/")
                )
        if not manifest_files:
            manifest_files.append(manifest_path)

        for path in manifest_files:
            data = read_json(self.ctx, path)
            base_dir = os.path.dirname(path)
            for entry in data:
                entry_path = entry.get("path")
                if entry_path:
                    entry_path = os.path.normpath(
                        entry_path
                        if os.path.isabs(entry_path)
                        else os.path.join(base_dir, entry_path)
                    )
                    entry["path"] = entry_path.replace(os.sep, "/")
                if "files" in entry:
                    new_files = []
                    for f in entry["files"]:
                        f = os.path.normpath(
                            f if os.path.isabs(f) else os.path.join(base_dir, f)
                        ).replace(os.sep, "/")
                        new_files.append(f)
                    entry["files"] = new_files
                biomes = entry.get("biomes", [])
                for b in biomes:
                    if BiomeCatalog.get(b) is None:
                        raise ValueError(f"Unknown biome '{b}' in flora manifest")
                spawn_defaults = TYPE_DEFAULTS.get(entry["type"], {})
                spawn_data = {**spawn_defaults, **entry.get("spawn", {})}
                asset_files = expand_variants(entry)
                a = FloraAsset(
                    id=entry["id"],
                    type=entry["type"],
                    biomes=biomes,
                    footprint=tuple(entry.get("footprint", [1, 1])) or (1, 1),
                    anchor_px=tuple(entry.get("anchor_px", [self.tile // 2, self.tile]))
                    or (self.tile // 2, self.tile),
                    passable=bool(entry.get("passable", True)),
                    occludes=bool(entry.get("occludes", False)),
                    files=asset_files,
                    size_px=tuple(entry.get("size_px", [])) or None,
                    collectible=entry.get("collectible"),
                    shadow_baked=bool(entry.get("shadow_baked", False)),
                    spawn=spawn_data,
                )
                self.assets[a.id] = a

    # ---------- Surfaces ----------
    def get_surface(
        self, asset_id: str, variant: int = 0
    ) -> Tuple[pygame.Surface, Tuple[int, int]]:
        key = (asset_id, variant)
        if key in self._surf_cache:
            return self._surf_cache[key]
        a = self.assets[asset_id]
        files = a.files
        if not files:
            surf = self._placeholder()
        else:
            file_rel = files[variant % len(files)]
            surf = self._load_surface(file_rel)
        target_w = max(1, a.footprint[0] * self.tile)
        scale = target_w / surf.get_width() if surf.get_width() else 1.0
        if scale != 1.0:
            new_size = (
                int(surf.get_width() * scale),
                int(surf.get_height() * scale),
            )
            surf, anchor = scale_with_anchor(
                surf, new_size, a.anchor_px, smooth=True
            )
        else:
            anchor = a.anchor_px
        self._surf_cache[key] = (surf, anchor)
        return surf, anchor

    def _load_surface(self, rel_path: str) -> pygame.Surface:
        # Via AssetManager si fourni (clé logique = chemin relatif sans extension)
        key_no_ext = rel_path[:-4] if rel_path.lower().endswith(".png") else rel_path
        if self.am is not None and hasattr(self.am, "get"):
            try:
                return self.am.get(key_no_ext)  # laisse l'AM gérer convert_alpha / scale et fallback
            except Exception:
                return self._placeholder()
        # Fallback disque
        full = os.path.join(self.assets_root, rel_path)
        try:
            img = pygame.image.load(full).convert_alpha()
            return img
        except Exception:
            return self._placeholder()

    def _placeholder(self) -> pygame.Surface:
        s = pygame.Surface((self.tile*2, self.tile*2), pygame.SRCALPHA)
        s.fill((255,0,255,120))
        pygame.draw.rect(s, (0,0,0,200), s.get_rect(), 2)
        return s

    # ------------------------------------------------------------------
    # Placement automatique — approche "blue‑noise" sur grille
    # ------------------------------------------------------------------
    def autoplace(
        self,
        biome_grid: List[List[str]],
        tags_grid: Optional[List[List[str]]] = None,
        rng_seed: int = 0,
        allowed_flora: Optional[Dict[str, Iterable[str]]] = None,
    ) -> List[PropInstance]:
        """
        Place automatiquement la flore selon le biome et les règles de spawn.
        - biome_grid[y][x]: nom de biome pour chaque case
        - tags_grid[y][x]: tag optionnel ("road", "water", ...) pour éviter certains emplacements
        - allowed_flora: dict optionnel {biome: [asset_id,...]} pour restreindre la flore par biome
        Retourne une liste de PropInstance (sans collision fine multi‑cases: on vérifie footprint et min_dist).
        """
        H = len(biome_grid)
        W = len(biome_grid[0]) if H else 0
        rng = random.Random(rng_seed)

        # Occupation et dernière position pour contrainte de min_dist par asset
        occupied = [[False]*W for _ in range(H)]
        props: List[PropInstance] = []

        # Indexer assets par biome, en option filtrer par ``allowed_flora``
        allowed_sets = (
            {k: set(v) for k, v in allowed_flora.items()} if allowed_flora else {}
        )
        by_biome: Dict[str, List[FloraAsset]] = {}
        for a in self.assets.values():
            for b in a.biomes:
                if allowed_sets and b in allowed_sets and a.id not in allowed_sets[b]:
                    continue
                by_biome.setdefault(b, []).append(a)

        # Regrouper les coordonnées par biome
        coords_by_biome: Dict[str, List[Vec2]] = {}
        for y in range(H):
            for x in range(W):
                b = biome_grid[y][x]
                coords_by_biome.setdefault(b, []).append((x, y))

        def can_place(a: FloraAsset, x: int, y: int, check_occ: bool = True) -> bool:
            w, h = a.footprint
            if x < 0 or y < 0 or x + w > W or y + h > H:
                return False
            avoid = set(a.spawn.get("avoid", []))
            if tags_grid is not None and avoid:
                for yy in range(y, y + h):
                    for xx in range(x, x + w):
                        if tags_grid[yy][xx] in avoid:
                            return False
            if check_occ:
                for yy in range(y, y + h):
                    for xx in range(x, x + w):
                        if occupied[yy][xx]:
                            return False
            return True

        # k‑distant constraint (min_dist) sur grille (Manhattan ~ Euclid discret)
        def too_close(x: int, y: int, min_d: int) -> bool:
            if min_d <= 0:
                return False
            x0 = max(0, x - min_d)
            x1 = min(W - 1, x + min_d)
            y0 = max(0, y - min_d)
            y1 = min(H - 1, y + min_d)
            for p in props:
                px, py = p.tile_xy
                if x0 <= px <= x1 and y0 <= py <= y1:
                    dx, dy = px - x, py - y
                    if dx * dx + dy * dy <= min_d * min_d:
                        return True
            return False

        for biome, coord_list in coords_by_biome.items():
            alist = by_biome.get(biome, [])
            if not alist:
                continue
            for a in alist:
                coords = coord_list[:]
                rng.shuffle(coords)
                sp = a.spawn or {}
                if a.type == "decal":
                    prob = float(sp.get("prob", 0.0))
                    for (x, y) in coords:
                        if not can_place(a, x, y, check_occ=False):
                            continue
                        if rng.random() > prob:
                            continue
                        fw, fh = a.footprint
                        rect_world = pygame.Rect(x * self.tile, y * self.tile, fw * self.tile, fh * self.tile)
                        var = rng.randrange(max(1, len(a.files)))
                        props.append(
                            PropInstance(
                                a.id,
                                biome,
                                (x, y),
                                var,
                                a.footprint,
                                a.anchor_px,
                                a.passable,
                                a.occludes,
                                rect_world,
                            )
                        )
                    continue

                density = float(sp.get("density", 0.0))
                min_d = int(sp.get("min_dist", 0))
                for (x, y) in coords:
                    if density > 0 and rng.random() > density:
                        continue
                    if too_close(x, y, min_d):
                        continue
                    if not can_place(a, x, y):
                        continue
                    fw, fh = a.footprint
                    for yy in range(y, y + fh):
                        for xx in range(x, x + fw):
                            occupied[yy][xx] = True
                    rect_world = pygame.Rect(x * self.tile, y * self.tile, fw * self.tile, fh * self.tile)
                    var = rng.randrange(max(1, len(a.files)))
                    props.append(
                        PropInstance(
                            a.id,
                            biome,
                            (x, y),
                            var,
                            a.footprint,
                            a.anchor_px,
                            a.passable,
                            a.occludes,
                            rect_world,
                        )
                    )
        # Ensure minimum counts per biome and type
        counts: Dict[Tuple[str, str], int] = {}
        for p in props:
            t = self.assets[p.asset_id].type
            key = (p.biome, t)
            counts[key] = counts.get(key, 0) + 1

        for biome, coord_list in coords_by_biome.items():
            alist = by_biome.get(biome, [])
            if not alist:
                continue
            for t, min_cnt in MIN_COUNTS.items():
                need = min_cnt - counts.get((biome, t), 0)
                if need <= 0:
                    continue
                candidates = [a for a in alist if a.type == t]
                if not candidates:
                    continue
                coords = coord_list[:]
                rng.shuffle(coords)
                for x, y in coords:
                    if need <= 0:
                        break
                    a = rng.choice(candidates)
                    sp = a.spawn or {}
                    if t == "decal":
                        if not can_place(a, x, y, check_occ=False):
                            continue
                        fw, fh = a.footprint
                        rect_world = pygame.Rect(x * self.tile, y * self.tile, fw * self.tile, fh * self.tile)
                        var = rng.randrange(max(1, len(a.files)))
                        props.append(PropInstance(a.id, biome, (x, y), var, a.footprint, a.anchor_px, a.passable, a.occludes, rect_world))
                        counts[(biome, t)] = counts.get((biome, t), 0) + 1
                        need -= 1
                    else:
                        min_d = int(sp.get("min_dist", 0))
                        if too_close(x, y, min_d):
                            continue
                        if not can_place(a, x, y):
                            continue
                        fw, fh = a.footprint
                        for yy in range(y, y + fh):
                            for xx in range(x, x + fw):
                                occupied[yy][xx] = True
                        rect_world = pygame.Rect(x * self.tile, y * self.tile, fw * self.tile, fh * self.tile)
                        var = rng.randrange(max(1, len(a.files)))
                        props.append(PropInstance(a.id, biome, (x, y), var, a.footprint, a.anchor_px, a.passable, a.occludes, rect_world))
                        counts[(biome, t)] = counts.get((biome, t), 0) + 1
                        need -= 1

        return props

    # ------------------------------------------------------------------
    # Rendu & picking
    # ------------------------------------------------------------------
    def draw_props(
        self,
        surface: pygame.Surface | Dict[int, pygame.Surface],
        props: Iterable[PropInstance],
        grid_to_screen,
        shadow_surf: Optional[pygame.Surface] = None,
    ) -> None:
        """Dessine les props triés par profondeur.
        - ``surface`` peut être soit une surface unique, soit un dict ``{layer: surf}``
          permettant de répartir automatiquement les props sur les couches
          définies dans :mod:`constants`.
        - grid_to_screen(x,y)->(sx,sy) doit renvoyer la position **sol** (bas‑centre)
          du tile (x,y)
        - shadow_surf (optionnel) : ombre ovale réutilisable, ancrée sous le pied
        """
        drawlist = []
        for p in props:
            a = self.assets[p.asset_id]
            img, (ax, ay) = self.get_surface(p.asset_id, p.variant)
            # position du pied (bas‑centre) : case d'origine du footprint
            foot_x, foot_y = p.tile_xy
            # Si footprint > 1x1, ancrer sur le coin bas‑centre de l'empreinte
            fw, fh = p.footprint
            anchor_tile = (foot_x + fw // 2, foot_y + fh - 1)
            sx, sy = grid_to_screen(anchor_tile[0], anchor_tile[1])
            # position image = (pied - ancre_px)
            px = int(sx - ax)
            py = int(sy - ay)
            baseline = sy  # sert pour tri (similaire à iso painter)
            if isinstance(surface, dict):
                dest = surface[
                    constants.LAYER_DECALS
                    if a.type == "decal"
                    else constants.LAYER_FLORA
                ]
            else:
                dest = surface
            shadow = None if a.shadow_baked else shadow_surf
            drawlist.append((baseline, dest, shadow, (sx, sy), img, (px, py)))

        # tri par baseline ascendant
        drawlist.sort(key=lambda t: t[0])
        for _, dest, shad, foot, img, pos in drawlist:
            if shad is not None:
                # placer l'ombre centrée sous le pied
                sh_rect = shad.get_rect(center=foot)
                dest.blit(shad, sh_rect.topleft)
            dest.blit(img, pos)

    def pick_prop_at(self, props: Iterable[PropInstance], mouse_pos: Vec2, grid_to_screen) -> Optional[PropInstance]:
        """Retourne le prop top‑most sous la souris (rect image + tri profondeur)."""
        # Construire une liste avec bounding box écran
        picks = []
        for p in props:
            img, (ax, ay) = self.get_surface(p.asset_id, p.variant)
            fw, fh = p.footprint
            foot_x, foot_y = p.tile_xy
            anchor_tile = (foot_x + fw//2, foot_y + fh - 1)
            sx, sy = grid_to_screen(anchor_tile[0], anchor_tile[1])
            px = int(sx - ax)
            py = int(sy - ay)
            rect = img.get_rect(topleft=(px,py))
            if rect.collidepoint(mouse_pos):
                picks.append((sy, p))
        if not picks:
            return None
        # renvoyer le plus "haut" en profondeur (sy le plus grand)
        picks.sort(key=lambda t: t[0], reverse=True)
        return picks[0][1]

# -----------------------------------------------------------------------------
# Utilitaires : petite ombre ovale réutilisable
# -----------------------------------------------------------------------------

def make_shadow_oval(w: int = 56, h: int = 18, alpha: int = 120) -> pygame.Surface:
    s = pygame.Surface((w,h), pygame.SRCALPHA)
    pygame.draw.ellipse(s, (0,0,0,alpha), s.get_rect())
    return s
