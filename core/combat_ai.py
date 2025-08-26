from __future__ import annotations

from typing import List, Tuple, Dict, Optional

import heapq
import constants
from core import combat_rules
from core.entities import Unit, apply_defence


def choose_target(combat, unit: Unit, enemies: List[Unit]) -> Unit:
    """Select a target taking objective value into account."""

    def score(enemy: Unit) -> Tuple[int, int]:
        dist = combat.hex_distance((enemy.x, enemy.y), (unit.x, unit.y))
        # Base threat based on offensive potential
        threat = enemy.stats.attack_max * enemy.count
        # Fragile units are attractive targets
        threat += max(0, 30 - enemy.stats.max_hp)
        # Targets already weakened are more attractive
        if enemy.current_hp < enemy.stats.max_hp * enemy.count:
            threat += 10
        # Melee units prefer foes that cannot retaliate
        if unit.stats.attack_range <= 1 and combat_rules.can_retaliate(enemy):
            threat -= 5
        # Units guarding treasure are particularly valuable
        if getattr(enemy.stats, "treasure", False):
            threat -= 20
        # Simple flank detection – enemies with adjacent allies are worth more
        for nx, ny in combat.hex_neighbors(enemy.x, enemy.y):
            other = combat.grid[ny][nx]
            if other and getattr(other, "side", None) == enemy.side:
                threat -= 5
                break
        diff = {"Novice": 0.5, "Intermédiaire": 0.75, "Avancé": 1.0}.get(
            constants.AI_DIFFICULTY, 1.0
        )
        return dist, int(-threat * diff)

    return min(enemies, key=score)


def select_spell(unit: Unit, enemies: List[Unit], combat) -> Optional[Tuple[str, object]]:
    """Return ``(spell_id, target)`` for the best spell to cast or ``None``.

    ``target`` is either a ``(x, y)`` tuple for offensive spells or a ``Unit``
    instance for ally-targeted spells like ``heal``.  The heuristic favours
    spells that hit the most enemies while respecting mana and range limits.
    """

    best: Optional[Tuple[str, object]] = None
    best_score = 0
    book = combat.spellbooks.get(unit, {})
    if not book:
        return None

    # Allies are needed when considering healing spells
    allies = combat.hero_units if unit.side == "hero" else combat.enemy_units
    for sid, spell_def in book.items():
        if unit.mana < spell_def.cost_mana:
            continue
        # Healing spell: select ally with most missing HP
        if sid == "heal":
            for ally in allies:
                if not ally.is_alive or ally.current_hp == ally.stats.max_hp:
                    continue
                dist = abs(ally.x - unit.x) + abs(ally.y - unit.y)
                if dist > spell_def.range:
                    continue
                missing = ally.stats.max_hp - ally.current_hp
                if missing > best_score:
                    best_score = missing
                    best = (sid, ally)
            continue

        # Offensive spell: evaluate each enemy position
        for enemy in enemies:
            if not enemy.is_alive:
                continue
            dist = abs(enemy.x - unit.x) + abs(enemy.y - unit.y)
            if dist > spell_def.range:
                continue
            score = 1
            radius = spell_def.data.get("area_radius")
            if radius is not None:
                cnt = 0
                for e in enemies:
                    if (e.x - enemy.x) ** 2 + (e.y - enemy.y) ** 2 <= radius ** 2:
                        cnt += 1
                score = cnt
            if score > best_score:
                best_score = score
                best = (sid, (enemy.x, enemy.y))

    return best


def _a_star(
    start: Tuple[int, int],
    goal: Tuple[int, int],
    blocked: set[Tuple[int, int]],
) -> List[Tuple[int, int]]:
    """Compute an A* path on the combat grid."""

    def offset_to_axial(x: int, y: int) -> Tuple[int, int]:
        q = x
        r = y - (x - (x & 1)) // 2
        return q, r

    def axial_to_offset(q: int, r: int) -> Tuple[int, int]:
        x = q
        y = r + (q - (q & 1)) // 2
        return x, y

    def hex_neighbors(x: int, y: int) -> List[Tuple[int, int]]:
        q, r = offset_to_axial(x, y)
        directions = [(1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1)]
        result: List[Tuple[int, int]] = []
        for dq, dr in directions:
            nq, nr = q + dq, r + dr
            nx, ny = axial_to_offset(nq, nr)
            if 0 <= nx < constants.COMBAT_GRID_WIDTH and 0 <= ny < constants.COMBAT_GRID_HEIGHT:
                result.append((nx, ny))
        return result

    def hex_distance(a: Tuple[int, int], b: Tuple[int, int]) -> int:
        aq, ar = offset_to_axial(*a)
        bq, br = offset_to_axial(*b)
        return (abs(aq - bq) + abs(ar - br) + abs(aq + ar - bq - br)) // 2

    frontier: List[Tuple[int, Tuple[int, int]]] = [(0, start)]
    came_from: Dict[Tuple[int, int], Optional[Tuple[int, int]]] = {start: None}
    cost_so_far: Dict[Tuple[int, int], int] = {start: 0}

    while frontier:
        _, current = heapq.heappop(frontier)
        if current == goal:
            break
        for nx, ny in hex_neighbors(*current):
            if (nx, ny) in blocked:
                continue
            new_cost = cost_so_far[current] + 1
            if (nx, ny) not in cost_so_far or new_cost < cost_so_far[(nx, ny)]:
                cost_so_far[(nx, ny)] = new_cost
                priority = new_cost + hex_distance((nx, ny), goal)
                heapq.heappush(frontier, (priority, (nx, ny)))
                came_from[(nx, ny)] = current
    else:
        return []

    path: List[Tuple[int, int]] = []
    cur = goal
    while cur != start:
        path.append(cur)
        cur = came_from.get(cur)
        if cur is None:
            return []
        
    path.reverse()
    return path


def ai_take_turn(combat, unit: Unit, enemies: List[Unit]) -> None:
    """Execute a simple turn for ``unit`` against ``enemies``.

    The logic prefers the closest and most threatening enemy, moving towards
    them if necessary and attacking when in range. Units with the ``charge``
    or ``flying`` abilities move farther.  This function mirrors the previous
    inline AI but lives in its own module so both enemy and allied units can
    share it.
    """
    if not enemies:
        return

    target = choose_target(combat, unit, enemies)
    dist = combat.hex_distance((unit.x, unit.y), (target.x, target.y))

    # Consider spell casting before moving or attacking
    spell_choice = select_spell(unit, enemies, combat)
    if spell_choice:
        sid, tgt = spell_choice
        cast = getattr(combat, f"spell_{sid}", None)
        spell_def = combat.spellbooks.get(unit, {}).get(sid)
        if cast and spell_def:
            try:
                cast(unit, tgt, 1)
                unit.mana -= spell_def.cost_mana
                return
            except Exception:
                pass

    did_kite = False
    if unit.stats.attack_range > 1:
        nearest = min(
            enemies, key=lambda e: combat.hex_distance((unit.x, unit.y), (e.x, e.y))
        )
        nearest_dist = combat.hex_distance((unit.x, unit.y), (nearest.x, nearest.y))
        if nearest_dist <= 1:
            blocked = set(combat.obstacles) | set(combat.ice_walls)
            for y, row in enumerate(combat.grid):
                for x, other in enumerate(row):
                    if other is not None and other is not unit:
                        blocked.add((x, y))
            options = []
            for nx, ny in combat.hex_neighbors(unit.x, unit.y):
                if (nx, ny) in blocked:
                    continue
                d = combat.hex_distance((nx, ny), (nearest.x, nearest.y))
                options.append((d, nx, ny))
            if options:
                options.sort(reverse=True)
                best_d, bx, by = options[0]
                if best_d > nearest_dist:
                    combat.move_unit(unit, bx, by)
                    dist = combat.hex_distance((unit.x, unit.y), (target.x, target.y))
                    did_kite = True

    if dist <= 1:
        attack_type = "melee"
    elif (
        unit.stats.min_range < dist <= unit.stats.attack_range
        and combat.has_line_of_sight(unit.x, unit.y, target.x, target.y)
    ):
        attack_type = "ranged"
    else:
        attack_type = None
    if attack_type:
        dmg = unit.damage_output()
        combat.animate_attack(unit, target, attack_type)
        dmg = apply_defence(dmg, target, attack_type)
        combat.log_damage(unit, target, dmg)
        target.take_damage(dmg)
        if "multi_shot" in unit.stats.abilities and target.is_alive:
            dmg2 = unit.damage_output()
            combat.animate_attack(unit, target, attack_type)
            dmg2 = apply_defence(dmg2, target, attack_type)
            combat.log_damage(unit, target, dmg2)
            target.take_damage(dmg2)
        if not target.is_alive:
            combat.remove_unit_from_grid(target)
        return

    if did_kite:
        return

    move_speed = unit.stats.speed
    if "charge" in unit.stats.abilities:
        move_speed *= 2
    if "flying" in unit.stats.abilities:
        move_speed = constants.COMBAT_GRID_WIDTH + constants.COMBAT_GRID_HEIGHT
    # Difficulty affects how far the AI is willing to move
    move_speed = max(
        1,
        int(
            move_speed
            * {
                "Novice": 0.5,
                "Intermédiaire": 0.75,
                "Avancé": 1.0,
            }.get(constants.AI_DIFFICULTY, 1.0)
        ),
    )

    blocked = set(combat.obstacles) | set(combat.ice_walls)
    for y, row in enumerate(combat.grid):
        for x, other in enumerate(row):
            if other is not None and other is not unit:
                blocked.add((x, y))
    blocked.discard((target.x, target.y))
    path = _a_star((unit.x, unit.y), (target.x, target.y), blocked)
    if path and path[-1] == (target.x, target.y):
        path = path[:-1]
    for nx, ny in path[:move_speed]:
        combat.move_unit(unit, nx, ny)

    dist = combat.hex_distance((unit.x, unit.y), (target.x, target.y))
    if dist <= 1:
        attack_type = "melee"
    elif (
        unit.stats.min_range < dist <= unit.stats.attack_range
        and combat.has_line_of_sight(unit.x, unit.y, target.x, target.y)
    ):
        attack_type = "ranged"
    else:
        return
    dmg = unit.damage_output()
    combat.animate_attack(unit, target, attack_type)
    dmg = apply_defence(dmg, target, attack_type)
    combat.log_damage(unit, target, dmg)
    target.take_damage(dmg)
    if "multi_shot" in unit.stats.abilities and target.is_alive:
        dmg2 = unit.damage_output()
        combat.animate_attack(unit, target, attack_type)
        dmg2 = apply_defence(dmg2, target, attack_type)
        combat.log_damage(unit, target, dmg2)
        target.take_damage(dmg2)
    if not target.is_alive:
        combat.remove_unit_from_grid(target)


def enemy_ai_turn(combat, unit: Unit) -> None:
    """Execute an AI turn for an enemy unit."""
    living_heroes = [u for u in combat.hero_units if u.is_alive]
    ai_take_turn(combat, unit, living_heroes)


def allied_ai_turn(combat, unit: Unit) -> None:
    """Execute an AI turn for an allied unit when auto combat is enabled."""
    living_enemies = [u for u in combat.enemy_units if u.is_alive]
    ai_take_turn(combat, unit, living_enemies)
