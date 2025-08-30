"""Spell definitions and casting helpers."""

from __future__ import annotations
import json, math, os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple, Optional

import constants
try:
    import pygame
except Exception:  # pragma: no cover - optional in tests
    pygame = None
from loaders.asset_manager import AssetManager
from core.fx import FXQueue, AnimatedFX, load_animation

Effect = Dict[str, Any]

@dataclass
class Spell:
    """Container for loaded spell data."""

    id: str
    name: str = ""
    faction: Optional[str] = None
    type: str = ""
    school: Optional[str] = None
    cost_mana: int = 0
    cooldown: int = 0
    range: int = 0
    area: Optional[str] = None
    target: Optional[str] = None
    duration: Optional[str] = None
    effects: List[Any] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    fx_asset: Optional[str] = None
    passive: bool = False
    level: int = 1
    data: Dict[str, Any] = field(default_factory=dict)

def _strip_comments(text: str) -> str:
    """Return ``text`` with C/JS style comments removed."""
    import re

    pattern = re.compile(r"/\*.*?\*/", re.DOTALL)
    return re.sub(pattern, "", text)


def load_spells(path: str) -> Dict[str, Spell]:
    """Load spell definitions from *path*.

    The game can be launched with varying working directories.  Resolve the
    provided *path* relative to this module so ``assets/spells/spells.json`` is
    found no matter where the process is started from.
    """

    if not os.path.isabs(path):
        path = os.path.join(os.path.dirname(__file__), "..", path)
    path = os.path.normpath(path)
    with open(path, "r", encoding="utf-8") as f:
        raw = _strip_comments(f.read())
        data = json.loads(raw or "{}")

    schools = data.get("schools", {})
    aliases = data.get("aliases", {})

    out: Dict[str, Spell] = {}
    for school, levels in schools.items():
        for lvl, kinds in levels.items():
            for group, rows in kinds.items():
                for row in rows:
                    try:
                        rng = int(row.get("range", 4) or 0)
                    except (TypeError, ValueError):
                        rng = 999
                    s = Spell(
                        id=row.get("id", ""),
                        name=row.get("name", ""),
                        faction=row.get("faction"),
                        type=row.get("type", ""),
                        school=row.get("school", school),
                        cost_mana=int(row.get("cost", 0) or 0),
                        cooldown=int(row.get("cooldown", 0) or 0),
                        range=rng,
                        area=row.get("area"),
                        target=row.get("target"),
                        duration=row.get("duration"),
                        effects=list(row.get("effects", [])),
                        tags=list(row.get("tags", [])),
                        fx_asset=row.get("fx_asset"),
                        passive=group == "passive"
                        or row.get("type") in ("passive", "aura")
                        or row.get("duration") == "passive",
                        level=int(lvl),
                        data={k: v for k, v in row.items()},
                    )
                    out[s.id] = s

    for alias, target in aliases.items():
        if target in out:
            out[alias] = out[target]

    return out

# ---- Casting helpers ----
def _dist(a: Tuple[int, int], b: Tuple[int, int]) -> int:
    """Manhattan distance (adjust if using another metric)."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])



def _trigger_fx(fx_queue: FXQueue | None, assets: AssetManager | None, asset: str, pos: Tuple[int, int]) -> None:
    """Render an FX animation at grid ``pos`` if possible."""
    if not fx_queue or not assets or pygame is None:
        return
    frame_time = 1 / constants.FPS
    frames = load_animation(assets, asset, constants.COMBAT_TILE_SIZE, constants.COMBAT_TILE_SIZE)
    if not frames:
        return
    px = pos[0] * constants.COMBAT_TILE_SIZE + constants.COMBAT_TILE_SIZE // 2
    py = pos[1] * constants.COMBAT_TILE_SIZE + constants.COMBAT_TILE_SIZE // 2
    img_pos = pygame.math.Vector2(px, py) if hasattr(pygame, "math") else (px, py)
    duration = frame_time * len(frames)
    fx_queue.add(AnimatedFX(pos=img_pos, duration=duration, frames=frames, frame_time=frame_time, z=200))

def cast_fireball(spell: Spell, caster_xy: Tuple[int, int], power: int, target_xy: Tuple[int, int],
                  units_at: List[Tuple[int, Tuple[int, int]]], fx_queue: FXQueue | None = None, assets: AssetManager | None = None) -> List[Effect]:
    """Cast a fireball and return resulting effects.

    ``units_at`` is ``[(unit_id, xy), ...]`` for all units on the battlefield.
    """
    A = spell.data.get("area_radius", 1)
    base = spell.data["damage"]["base"]; per = spell.data["damage"]["per_power"]
    elem = spell.data["damage"]["type"]
    fx: List[Effect] = []
    fx.append({"type": "projectile", "asset": spell.data.get("projectile_asset", "effects/fireball"),
               "from": caster_xy, "to": target_xy})
    # Damage inside the disk
    for uid, xy in units_at:
        if (xy[0]-target_xy[0])**2 + (xy[1]-target_xy[1])**2 <= A*A:
            val = int(base + per*power)
            fx.append({"type": "damage", "target": uid, "value": val, "element": elem})
    fx.append({"type": "fx", "asset": spell.data.get("fx_asset","effects/explosion_small"), "pos": target_xy})
    _trigger_fx(fx_queue, assets, spell.data.get("fx_asset", "effects/explosion_small"), target_xy)
    return fx

def cast_chain_lightning(spell: Spell, caster_xy: Tuple[int, int], power: int, first_target_id: int,
                         units_pos: Dict[int, Tuple[int, int]]) -> List[Effect]:
    """Cast chain lightning starting from ``first_target_id``."""
    base = spell.data["damage"]["base"]; per = spell.data["damage"]["per_power"]
    max_jumps = int(spell.data.get("max_jumps", 4))
    jump_range = int(spell.data.get("jump_range", 3))
    fx: List[Effect] = [{"type": "fx", "asset": spell.data.get("fx_asset", "effects/chain_lightning"),
                         "path": []}]
    visited = set()
    cur = first_target_id
    for _ in range(max_jumps):
        visited.add(cur)
        fx.append({"type": "damage", "target": cur, "value": int(base + per*power), "element": "shock"})
        # Find next target
        cand = None
        dmin = 999
        for uid, pos in units_pos.items():
            if uid in visited:
                continue
            if _dist(units_pos[cur], pos) <= jump_range and _dist(caster_xy, pos) <= spell.range:
                d = _dist(units_pos[cur], pos)
                if d < dmin:
                    dmin = d
                    cand = uid
        if cand is None:
            break
        fx[0]["path"].append((units_pos[cur], units_pos[cand]))
        cur = cand
    return fx

def cast_heal(spell: Spell, power: int, target_id: int) -> List[Effect]:
    """Apply a healing spell to ``target_id``."""
    if "heal" in spell.data and isinstance(spell.data["heal"], dict):
        base = float(spell.data["heal"].get("base", 0))
        per = float(spell.data["heal"].get("per_power", 0))
        val = int(base + per * power)
    else:
        base = 0
        for eff in spell.effects:
            if isinstance(eff, str) and eff.startswith("heal:"):
                try:
                    base = float(eff.split(":", 1)[1])
                except ValueError:
                    base = 0
                break
        val = int(base)
    return [
        {"type": "heal", "target": target_id, "value": val},
        {
            "type": "fx",
            "asset": spell.data.get("fx_asset", "effects/heal_wave"),
            "target": target_id,
        },
    ]

def cast_ice_wall(spell: Spell, target_line: List[Tuple[int, int]], fx_queue: FXQueue | None = None, assets: AssetManager | None = None) -> List[Effect]:
    """Spawn an ice wall along ``target_line`` (length <= wall_length)."""
    fx: List[Effect] = [{"type": "fx", "asset": spell.data.get("fx_asset", "effects/ice_wall"),
                         "tiles": target_line}]
    for tile in target_line:
        _trigger_fx(fx_queue, assets, spell.data.get("fx_asset", "effects/ice_wall"), tile)
    for xy in target_line[: int(spell.data.get("wall_length", 3))]:
        fx.append({"type": "spawn", "entity": "ice_wall", "pos": xy,
                   "hp": int(spell.data.get("spawn", {}).get("hp", 20)),
                   "blocks": bool(spell.data.get("spawn", {}).get("blocks", True))})
    return fx

def cast_shield(spell: Spell, target_id: int) -> List[Effect]:
    """Apply a protective status to ``target_id``."""
    st = spell.data["status"]
    icon = st.get("icon", "status_shield")
    return [
        {
            "type": "status",
            "target": target_id,
            "status": st.get("name", "shielded"),
            "duration": int(st.get("duration", 2)),
            "reduction": float(st.get("reduction", 0.25)),
            "icon": icon,
        },
        {
            "type": "fx",
            "asset": spell.data.get("fx_asset", "effects/shield_glow"),
            "target": target_id,
        },
    ]
