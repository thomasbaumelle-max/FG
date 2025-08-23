"""Spell definitions and casting helpers."""

from __future__ import annotations
import json, math, os
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

Effect = Dict[str, Any]

@dataclass
class Spell:
    """Container for loaded spell data."""

    id: str
    school: str
    cost_mana: int
    cooldown: int
    range: int
    passive: bool
    data: Dict[str, Any]

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
        arr = json.load(f)
    out: Dict[str, Spell] = {}
    for row in arr:
        s = Spell(
            id=row["id"],
            school=row.get("school", "neutral"),
            cost_mana=int(row.get("cost_mana", 0)),
            cooldown=int(row.get("cooldown", 0)),
            range=int(row.get("range", 4)),
            passive=bool(row.get("passive", False)),
            data={k: v for k, v in row.items() if k not in ("id","school","cost_mana","cooldown","range","passive")}
        )
        out[s.id] = s
    return out

# ---- Casting helpers ----
def _dist(a: Tuple[int, int], b: Tuple[int, int]) -> int:
    """Manhattan distance (adjust if using another metric)."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

def cast_fireball(spell: Spell, caster_xy: Tuple[int, int], power: int, target_xy: Tuple[int, int],
                  units_at: List[Tuple[int, Tuple[int, int]]]) -> List[Effect]:
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
    base = spell.data["heal"]["base"]; per = spell.data["heal"]["per_power"]
    val = int(base + per*power)
    return [{"type": "heal", "target": target_id, "value": val},
            {"type": "fx", "asset": spell.data.get("fx_asset", "effects/heal_wave"), "target": target_id}]

def cast_ice_wall(spell: Spell, target_line: List[Tuple[int, int]]) -> List[Effect]:
    """Spawn an ice wall along ``target_line`` (length <= wall_length)."""
    fx: List[Effect] = [{"type": "fx", "asset": spell.data.get("fx_asset", "effects/ice_wall"),
                         "tiles": target_line}]
    for xy in target_line[: int(spell.data.get("wall_length", 3))]:
        fx.append({"type": "spawn", "entity": "ice_wall", "pos": xy,
                   "hp": int(spell.data.get("spawn", {}).get("hp", 20)),
                   "blocks": bool(spell.data.get("spawn", {}).get("blocks", True))})
    return fx

def cast_shield(spell: Spell, target_id: int) -> List[Effect]:
    """Apply a protective status to ``target_id``."""
    st = spell.data["status"]
    return [{"type": "status", "target": target_id, "status": st.get("name", "shielded"),
             "duration": int(st.get("duration", 2)), "reduction": float(st.get("reduction", 0.25))},
            {"type": "fx", "asset": spell.data.get("fx_asset", "effects/shield_glow"), "target": target_id}]
