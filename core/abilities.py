"""Ability parsing and runtime execution for combat effects."""

from __future__ import annotations
import re
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple, Optional

# --------- Effect types returned to the combat engine ----------
# Example effects:
# {"type": "damage", "target": tid, "value": 7, "element": "fire"}
# {"type": "status", "target": tid, "status": "burn", "duration": 2}
# {"type": "projectile", "asset": "fireball", "from": (sx, sy), "to": (tx, ty)}
# {"type": "knockback", "target": tid, "dx": 1, "dy": 0}
# {"type": "heal", "target": uid, "value": 6}
# {"type": "fx", "asset": "wail_ring", "pos": (x, y)}

Effect = Dict[str, Any]

# --------- Parsing strings ``"name(arg1, key=val, ...)"`` ----------
_value_rx = re.compile(r"^(-?\d+(\.\d+)?)%?$", re.IGNORECASE)

def _coerce(token: str) -> Any:
    """Convert a token to int/float/bool while handling ``%`` and quotes."""
    t = token.strip()
    if t.lower() in ("true", "false"):
        return t.lower() == "true"
    m = _value_rx.match(t)
    if m:
        # handle 25% -> 0.25 ; 2 -> 2 ; 2.5 -> 2.5
        if t.endswith("%"):
            return float(m.group(1)) / 100.0
        if "." in t:
            return float(t)
        return int(t)
    # strip optional quotes
    if (t.startswith("'") and t.endswith("'")) or (t.startswith('"') and t.endswith('"')):
        return t[1:-1]
    return t  # keyword (e.g. fire, mind)

@dataclass
class AbilitySpec:
    """Parsed representation of an ability declaration."""

    name: str
    args: List[Any] = field(default_factory=list)
    kwargs: Dict[str, Any] = field(default_factory=dict)

def parse_ability_string(s: str) -> AbilitySpec:
    """Parse a string of the form ``"name(arg1, key=val, ...)"``."""
    s = s.strip()
    m = re.match(r"^([a-zA-Z_]\w*)\s*(?:\((.*)\))?$", s)
    if not m:
        return AbilitySpec(name=s)
    name = m.group(1)
    inner = (m.group(2) or "").strip()
    if not inner:
        return AbilitySpec(name=name)
    parts = [p.strip() for p in inner.split(",") if p.strip()]
    args: List[Any] = []
    kwargs: Dict[str, Any] = {}
    for p in parts:
        if "=" in p:
            k, v = p.split("=", 1)
            kwargs[k.strip()] = _coerce(v)
        else:
            args.append(_coerce(p))
    return AbilitySpec(name=name, args=args, kwargs=kwargs)

def parse_abilities(listing: List[str]) -> List[AbilitySpec]:
    """Parse a list of ability declaration strings."""
    out: List[AbilitySpec] = []
    for s in listing:
        out.append(parse_ability_string(s))
    return out

# --------- Runtime state per unit (cooldowns, turn flags) ----------
@dataclass
class AbilityState:
    """Track cooldown state for a single ability."""

    spec: AbilitySpec
    cooldown_max: int = 0
    cooldown: int = 0  # turns remaining

@dataclass
class UnitRuntime:
    """Mutable per-unit runtime data used during combat."""

    unit_id: int
    tile: Tuple[int, int] = (0, 0)
    moved_tiles_this_turn: int = 0
    hidden_this_turn: bool = False
    ability_states: Dict[str, AbilityState] = field(default_factory=dict)

# --------- Utility helpers ----------
def _kw(spec: AbilitySpec, key: str, default: Any) -> Any:
    """Return ``spec.kwargs[key]`` with ``default`` fallback."""
    return spec.kwargs.get(key, default)

def _positional(spec: AbilitySpec, index: int, default: Any) -> Any:
    """Return positional argument ``index`` from ``spec`` or ``default``."""
    return spec.args[index] if index < len(spec.args) else default

# --------- Engine: hooks to be called from the combat system ----------
class AbilityEngine:
    """Convert declared abilities into combat effects via hook methods."""

    def __init__(self, rng=None):
        self.rng = rng

    # ---- Unit initialization ----
    def init_unit(self, unit_id: int, ability_specs: List[AbilitySpec]) -> UnitRuntime:
        """Create runtime state for a unit based on its ability specs."""
        rt = UnitRuntime(unit_id=unit_id)
        for spec in ability_specs:
            cd = int(_kw(spec, "cd", 0) or 0)
            rt.ability_states[spec.name] = AbilityState(spec=spec, cooldown_max=cd, cooldown=0)
        return rt

    # ---- Cycle hooks ----
    def on_battle_start(self, rt: UnitRuntime) -> None:
        """Reset per-battle state for all abilities."""
        for st in rt.ability_states.values():
            st.cooldown = 0

    def on_turn_start(self, rt: UnitRuntime) -> None:
        """Advance cooldowns and mark the unit as hidden at turn start."""
        for st in rt.ability_states.values():
            if st.cooldown > 0:
                st.cooldown -= 1
        rt.moved_tiles_this_turn = 0
        rt.hidden_this_turn = True  # considered hidden until it acts or is targeted

    def on_unit_revealed(self, rt: UnitRuntime) -> None:
        """Clear the hidden flag when the unit is revealed."""
        rt.hidden_this_turn = False

    # ---- Damage calculations / mitigation ----
    def modify_outgoing_damage(self, rt: UnitRuntime, base: int, context: Dict[str, Any]) -> Tuple[int, List[Effect]]:
        """Called just before applying outgoing damage from this unit."""
        effects: List[Effect] = []
        dmg = base
        # gore_charge: bonus if it moved >= N tiles
        st = rt.ability_states.get("gore_charge")
        if st:
            min_move = int(_positional(st.spec, 0, 0) or 0)  # e.g. "+50% dmg after_move>=2, knockback=1"
            # by convention the first arg is "+50% dmg after_move>=2" -> read bonus from kwargs if available
            bonus = 0.5 if "+50% dmg after_move>=2" in "".join([str(a) for a in st.spec.args]) else float(_kw(st.spec, "bonus", 0.5))
            if rt.moved_tiles_this_turn >= min_move:
                dmg = int(round(dmg * (1.0 + bonus)))
                # knockback will be applied later in apply_on_hit to know the direction
        return dmg, effects

    def modify_incoming_damage(self, rt: UnitRuntime, base: int, dmg_type: str, is_melee: bool, tile_biome: Optional[str]) -> Tuple[int, List[Effect], Dict[str, Any]]:
        """Called before applying damage to this unit.

        Returns ``(new_damage, visual_effects, extra_flags)``.
        """
        effects: List[Effect] = []
        dmg = base
        info: Dict[str, Any] = {}

        # fire_resistance(x%)
        st = rt.ability_states.get("fire_resistance")
        if st and (dmg_type == "fire"):
            pct = float(_positional(st.spec, 0, 0.25))  # default 25% if "25%"
            dmg = int(round(dmg * (1.0 - pct)))

        # thick_hide(-20% melee_damage_taken)
        st = rt.ability_states.get("thick_hide")
        if st and is_melee:
            pct = 0.20
            dmg = int(round(dmg * (1.0 - pct)))

        # incorporeal(20% miss_physical)
        st = rt.ability_states.get("incorporeal")
        if st and (dmg_type in ("physical", "piercing", "slashing") or is_melee):
            miss_chance = float(_positional(st.spec, 0, 0.20))
            r = (self.rng.random() if self.rng else math.fmod(hash((rt.unit_id, base)), 100) / 100.0)
            if r < miss_chance:
                info["miss"] = True
                dmg = 0
                effects.append({"type": "fx", "asset": "ghost_flicker", "pos": None})
                return dmg, effects, info

        return dmg, effects, info

    # ---- Event reactions ----
    def on_attacked_by_melee(self, rt: UnitRuntime, attacker_id: int) -> List[Effect]:
        """Return effects triggered when this unit is hit in melee."""
        effects: List[Effect] = []
        st = rt.ability_states.get("heated_scales")
        if st:
            chance = float(_kw(st.spec, "burn_on_hit", 0.20))
            r = (self.rng.random() if self.rng else 0.17)  # deterministic if no RNG
            if r < chance:
                effects.append({"type": "status", "target": attacker_id, "status": "burn", "duration": 2})
                effects.append({"type": "fx", "asset": "ember_spark", "target": attacker_id})
        return effects

    def on_kill(self, rt: UnitRuntime, target_id: int) -> List[Effect]:
        """Return effects that occur when this unit kills an enemy."""
        effects: List[Effect] = []
        st = rt.ability_states.get("scavenge_on_kill")
        if st:
            heal = int(_kw(st.spec, "heal", 6))
            effects.append({"type": "heal", "target": rt.unit_id, "value": heal})
            effects.append({"type": "fx", "asset": "life_sip", "target": rt.unit_id})
        return effects

    # ---- Contextual bonuses ----
    def get_evasion_bonus(self, rt: UnitRuntime, tile_biome: Optional[str]) -> float:
        """Return an additive evasion bonus (0.20 = +20%)."""
        st = rt.ability_states.get("forest_camouflage")
        if st and tile_biome == "scarletia_crimson_forest":
            return 0.20
        return 0.0

    def has_first_strike(self, rt: UnitRuntime) -> bool:
        """Whether the unit gains first strike this turn."""
        st = rt.ability_states.get("stalk")
        return bool(st and rt.hidden_this_turn)

    def ignores_terrain_penalties(self, rt: UnitRuntime) -> bool:
        """Whether the unit ignores movement penalties from terrain."""
        return "hover" in rt.ability_states

    # ---- Active abilities usable by command ----
    def can_use(self, rt: UnitRuntime, name: str) -> Tuple[bool, str]:
        """Return ``(True, "")`` if ability ``name`` is usable, else ``(False, reason)``."""
        st = rt.ability_states.get(name)
        if not st:
            return False, "Ability not known"
        if st.cooldown > 0:
            return False, f"Recharge {st.cooldown} turn(s)"
        return True, ""

    def use_ember_spit(self, rt: UnitRuntime, src_xy: Tuple[int, int], dst_unit_id: int, dst_xy: Tuple[int, int]) -> List[Effect]:
        """Execute the ``ember_spit`` ability if available."""
        st = rt.ability_states.get("ember_spit")
        if not st:
            return []
        rng = int(_positional(st.spec, 0, 2))  # range
        elem = str(_positional(st.spec, 1, "fire"))
        # NOTE: range and line of sight are checked by the caller
        st.cooldown = st.cooldown_max
        return [
            {"type": "projectile", "asset": "fireball", "from": src_xy, "to": dst_xy},
            {"type": "damage", "target": dst_unit_id, "value": "roll", "element": elem},
            {"type": "status", "target": dst_unit_id, "status": "burn", "duration": 2},
        ]

    def use_wail(self, rt: UnitRuntime, src_xy: Tuple[int, int], targets: List[Tuple[int, Tuple[int, int]]]) -> List[Effect]:
        """``targets`` is ``[(unit_id, pos_xy), ...]`` already filtered within range=2."""
        st = rt.ability_states.get("wail")
        if not st:
            return []
        st.cooldown = st.cooldown_max
        effects: List[Effect] = [{"type": "fx", "asset": "wail_ring", "pos": src_xy}]
        for uid, pos in targets:
            effects.append({"type": "status", "target": uid, "status": "fear_-1", "duration": 1})
        return effects

    def apply_knockback_if_charge(self, rt: UnitRuntime, target_id: int, direction: Tuple[int, int]) -> List[Effect]:
        """Apply knockback if the ``gore_charge`` ability was triggered this turn."""
        st = rt.ability_states.get("gore_charge")
        if not st:
            return []
        if rt.moved_tiles_this_turn >= 2:
            kb = int(_kw(st.spec, "knockback", 1))
            dx, dy = direction
            return [{"type": "knockback", "target": target_id, "dx": dx * kb, "dy": dy * kb}]
        return []
