from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, Tuple
import random
RNG = random.Random()

@dataclass
class UnitView:
    # Vue minimale d'une unité en combat
    side: str            # "hero" / "enemy"
    stats: Any           # ton UnitStats (max_hp, attack_min/max, def.*, morale, luck, etc.)
    x: int               # position sur la grille de combat
    y: int
    retaliations_left: int = 1
    facing: Tuple[int,int] = (0, 1)  # optionnel: orientation (dx,dy)

# ---- Morale & Chance ----
def roll_morale(morale: int) -> str:
    """retourne 'extra', 'penalty' ou 'normal'."""
    table = {0: 0.0, 1: 1 / 24, 2: 2 / 24, 3: 3 / 24}
    m = max(-3, min(3, morale))
    p = table[abs(m)]
    r = random.random()
    if m > 0 and r < p:
        return "extra"
    if m < 0 and r < p:
        return "penalty"
    return "normal"

def roll_luck(luck: int) -> float:
    """retourne multiplicateur de dégâts (0.5, 1.0, 1.5)."""
    table = {0: 0.0, 1: 1 / 24, 2: 2 / 24}
    L = max(-2, min(2, luck))
    p = table[abs(L)]
    r = random.random()
    if L > 0 and r < p:
        return 1.5
    if L < 0 and r < p:
        return 0.5
    return 1.0

# ---- Géométrie hexagonale ----
def _offset_to_axial(x: int, y: int) -> Tuple[int, int]:
    q = x
    r = y - (x - (x & 1)) // 2
    return q, r


def _axial_to_offset(q: int, r: int) -> Tuple[int, int]:
    x = q
    y = r + (q - (q & 1)) // 2
    return x, y


def _hex_distance(a: Tuple[int, int], b: Tuple[int, int]) -> int:
    aq, ar = _offset_to_axial(*a)
    bq, br = _offset_to_axial(*b)
    return int((abs(aq - bq) + abs(ar - br) + abs(aq + ar - bq - br)) / 2)


def blocking_squares(a: Tuple[int, int], b: Tuple[int, int]) -> list[Tuple[int, int]]:
    """Retourne les cases strictement entre ``a`` et ``b`` sur la grille hex."""

    start = _offset_to_axial(*a)
    end = _offset_to_axial(*b)
    steps = _hex_distance(a, b)
    if steps <= 1:
        return []

    def axial_to_cube(q: int, r: int) -> Tuple[int, int, int]:
        return q, r, -q - r

    def cube_lerp(a: Tuple[float, float, float], b: Tuple[float, float, float], t: float) -> Tuple[float, float, float]:
        return (
            a[0] + (b[0] - a[0]) * t,
            a[1] + (b[1] - a[1]) * t,
            a[2] + (b[2] - a[2]) * t,
        )

    def cube_round(c: Tuple[float, float, float]) -> Tuple[int, int, int]:
        rx, ry, rz = round(c[0]), round(c[1]), round(c[2])
        x_diff, y_diff, z_diff = abs(rx - c[0]), abs(ry - c[1]), abs(rz - c[2])
        if x_diff > y_diff and x_diff > z_diff:
            rx = -ry - rz
        elif y_diff > z_diff:
            ry = -rx - rz
        else:
            rz = -rx - ry
        return rx, ry, rz

    a_cube = axial_to_cube(*start)
    b_cube = axial_to_cube(*end)
    cells: list[Tuple[int, int]] = []
    for i in range(1, steps):
        t = i / steps
        cube = cube_round(cube_lerp(a_cube, b_cube, t))
        q, r, _ = cube
        cells.append(_axial_to_offset(q, r))
    return cells

# ---- Mitigation & bonus ----
def mitigate(attack: int, defence: int) -> float:
    """Calcule un multiplicateur basé sur l'écart Att/Def.

    * +5% de dégâts par point d'Attaque supérieur à la Défense (cap à 300%).
    * -2% de dégâts par point d'Attaque inférieur à la Défense (plancher à ~30%).
    """

    diff = attack - defence
    if diff > 0:
        mult = 1.0 + 0.05 * diff
    elif diff < 0:
        mult = 1.0 + 0.02 * diff  # diff est négatif
    else:
        mult = 1.0
    # Plafond 300% et plancher ~30%
    return max(0.3, min(3.0, mult))

def flanking_bonus(attacker: UnitView, defender: UnitView) -> float:
    """Renvoie un multiplicateur basé sur l'orientation du défenseur."""

    ax, ay = attacker.x, attacker.y
    dx, dy = defender.facing
    # vecteur de l'attaquant vers le défenseur
    v = (defender.x - ax, defender.y - ay)
    dot = v[0] * dx + v[1] * dy
    if dot > 0:
        # Attaque par l'arrière
        return 1.2
    if dot == 0:
        # Attaque de flanc
        return 1.1
    return 1.0

# ---- Dégâts ----
def roll_base_damage(attacker_stats) -> int:
    import random
    return random.randint(attacker_stats.attack_min, attacker_stats.attack_max)

def compute_damage(attacker: UnitView, defender: UnitView, *,
                   attack_type: str = "melee", distance: int = 1,
                   obstacles: set[Tuple[int, int]] | None = None) -> Dict[str, Any]:
    """Calcule un coup standard. attack_type: 'melee'/'ranged'/'magic'."""
    # Base roll + bonus from hero skills
    base = roll_base_damage(attacker.stats) + getattr(attacker, "attack_bonus", 0)
    # Stack size
    dmg = base * getattr(attacker, "count", 1)
    luck_mul = roll_luck(attacker.stats.luck)
    dmg = int(round(dmg * luck_mul))

    # Pénalités/bonus
    min_range = getattr(attacker.stats, "min_range", 1)
    if attack_type == "ranged":
        defence = defender.stats.defence_ranged
        if distance < max(2, min_range):
            dmg = int(round(dmg * 0.75))  # pénalité tir trop proche
        if obstacles:
            path = blocking_squares((attacker.x, attacker.y), (defender.x, defender.y))
            if any(p in obstacles for p in path):
                dmg = int(round(dmg * 0.5))  # obstacle sur la trajectoire
    elif attack_type == "magic":
        defence = defender.stats.defence_magic
    else:
        defence = defender.stats.defence_melee
        flank_mul = flanking_bonus(attacker, defender)
        dmg = int(round(dmg * flank_mul))

    # Calcul du multiplicateur Att/Def
    attack_value = getattr(attacker, "attack", getattr(attacker, "attack_bonus", 0))
    dmg = int(round(dmg * mitigate(attack_value, defence)))
    return {"type": "damage", "target": id(defender), "value": max(0, dmg), "luck": luck_mul}

# ---- Riposte ----
def can_retaliate(unit: UnitView) -> bool:
    return unit.retaliations_left > 0

def consume_retaliation(unit: UnitView) -> None:
    unit.retaliations_left = max(0, unit.retaliations_left - 1)

def start_round_reset_retaliations(units: list[UnitView]) -> None:
    for u in units:
        u.retaliations_left = getattr(u.stats, "retaliations_per_round", 1)
