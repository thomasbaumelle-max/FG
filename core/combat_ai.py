from __future__ import annotations

from typing import List, Tuple, Dict, Optional

import heapq
import constants
from core.entities import Unit, apply_defence


def choose_target(combat, unit: Unit, enemies: List[Unit]) -> Unit:
    """Select a target taking objective value into account."""

    def score(enemy: Unit) -> Tuple[int, int]:
        dist = abs(enemy.x - unit.x) + abs(enemy.y - unit.y)
        # Base threat based on offensive potential
        threat = enemy.stats.attack_max * enemy.count
        # Targets already weakened are more attractive
        if enemy.current_hp < enemy.stats.max_hp * enemy.count:
            threat -= 10
        # Units guarding treasure are particularly valuable
        if getattr(enemy.stats, "treasure", False):
            threat -= 20
        # Simple flank detection – enemies with adjacent allies are worth more
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = enemy.x + dx, enemy.y + dy
            if 0 <= nx < constants.COMBAT_GRID_WIDTH and 0 <= ny < constants.COMBAT_GRID_HEIGHT:
                other = combat.grid[ny][nx]
                if other and getattr(other, "side", None) == enemy.side:
                    threat -= 5
                    break
        diff = {"Novice": 0.5, "Intermédiaire": 0.75, "Avancé": 1.0}.get(
            constants.AI_DIFFICULTY, 1.0
        )
        return dist, int(-threat * diff)

    return min(enemies, key=score)


def _a_star(
    start: Tuple[int, int],
    goal: Tuple[int, int],
    blocked: set[Tuple[int, int]],
) -> List[Tuple[int, int]]:
    """Compute an A* path on the combat grid."""

    frontier: List[Tuple[int, Tuple[int, int]]] = [(0, start)]
    came_from: Dict[Tuple[int, int], Optional[Tuple[int, int]]] = {start: None}
    cost_so_far: Dict[Tuple[int, int], int] = {start: 0}

    while frontier:
        _, current = heapq.heappop(frontier)
        if current == goal:
            break
        for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            nx, ny = current[0] + dx, current[1] + dy
            if not (
                0 <= nx < constants.COMBAT_GRID_WIDTH
                and 0 <= ny < constants.COMBAT_GRID_HEIGHT
            ):
                continue
            if (nx, ny) in blocked:
                continue
            new_cost = cost_so_far[current] + 1
            if (nx, ny) not in cost_so_far or new_cost < cost_so_far[(nx, ny)]:
                cost_so_far[(nx, ny)] = new_cost
                priority = new_cost + abs(goal[0] - nx) + abs(goal[1] - ny)
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
    dist = abs(target.x - unit.x) + abs(target.y - unit.y)

    # Attempt spell usage for very basic casters
    if getattr(unit.stats, "name", "") == "Mage" and dist > unit.stats.attack_range:
        # Mages lob a fireball at the target's position when available
        try:
            combat.spell_fireball(unit, (target.x, target.y), 1)
            return
        except Exception:
            pass

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

    dist = abs(target.x - unit.x) + abs(target.y - unit.y)
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
