from __future__ import annotations
from typing import List, Tuple
import copy
import random

import pygame

import constants
import theme
from .entities import Unit, ARTIFACT_CATALOG, Item, Hero
from . import combat_rules
from ui import combat_summary


def _to_view(unit: Unit) -> combat_rules.UnitView:
    view = combat_rules.UnitView(side=unit.side, stats=unit.stats, x=0, y=0)
    view.count = unit.count
    view.attack_bonus = getattr(unit, "attack_bonus", 0)
    return view


def _apply_damage(unit: Unit, dmg: int) -> None:
    while dmg > 0 and unit.count > 0:
        if dmg >= unit.current_hp:
            dmg -= unit.current_hp
            unit.count -= 1
            unit.current_hp = unit.stats.max_hp
        else:
            unit.current_hp -= dmg
            dmg = 0


def _simulate(hero_units: List[Unit], enemy_units: List[Unit]) -> Tuple[List[Unit], List[Unit], bool, int]:
    """Simulate combat between ``hero_units`` and ``enemy_units``.

    Returns copies of all units (including dead ones) with ``damage_dealt`` and
    ``damage_taken`` attributes populated, a flag indicating whether the hero
    side won, and the experience gained from defeating enemies.
    """

    heroes = [copy.deepcopy(u) for u in hero_units]
    enemies = [copy.deepcopy(u) for u in enemy_units]

    for u in heroes + enemies:
        u.damage_dealt = 0  # type: ignore[attr-defined]
        u.damage_taken = 0  # type: ignore[attr-defined]

    living_heroes = heroes[:]
    living_enemies = enemies[:]
    rng = random.Random()

    while living_heroes and living_enemies:
        for attacker in list(living_heroes):
            if not living_enemies:
                break
            target = rng.choice(living_enemies)
            dmg = combat_rules.compute_damage(_to_view(attacker), _to_view(target))["value"]
            attacker.damage_dealt += dmg  # type: ignore[attr-defined]
            target.damage_taken += dmg  # type: ignore[attr-defined]
            _apply_damage(target, dmg)
            if target.count <= 0:
                living_enemies.remove(target)

        for attacker in list(living_enemies):
            if not living_heroes:
                break
            target = rng.choice(living_heroes)
            dmg = combat_rules.compute_damage(_to_view(attacker), _to_view(target))["value"]
            attacker.damage_dealt += dmg  # type: ignore[attr-defined]
            target.damage_taken += dmg  # type: ignore[attr-defined]
            _apply_damage(target, dmg)
            if target.count <= 0:
                living_heroes.remove(target)

    hero_wins = any(u.count > 0 for u in heroes)
    initial_enemy = sum(u.count for u in enemy_units)
    remaining_enemy = sum(u.count for u in enemies)
    exp_gained = max(0, (initial_enemy - remaining_enemy) * 10)
    return heroes, enemies, hero_wins, exp_gained


def _generate_loot(enemy_units: List[Unit]) -> List[Item]:
    """Generate artifact loot based on enemy strength.

    This mirrors :meth:`core.combat.Combat.generate_loot` so that auto-resolve
    battles award similar rewards.
    """

    power = sum(
        u.count * (u.stats.attack_min + u.stats.attack_max) for u in enemy_units
    )
    if power > 120:
        rarities = {"legendary": 0.1, "rare": 0.3, "uncommon": 0.4, "common": 0.2}
    elif power > 60:
        rarities = {"rare": 0.3, "uncommon": 0.5, "common": 0.2}
    elif power > 30:
        rarities = {"uncommon": 0.6, "common": 0.4}
    else:
        rarities = {"common": 1.0}

    candidates = [a for a in ARTIFACT_CATALOG if a.rarity in rarities]
    if not candidates:
        return []
    weights = [rarities[a.rarity] for a in candidates]
    chosen = random.choices(candidates, weights=weights, k=1)[0]
    return [copy.deepcopy(chosen)]


def show_summary(
    screen: pygame.Surface,
    hero_units: List[Unit],
    enemy_units: List[Unit],
    hero_wins: bool,
    exp: int,
    hero: Hero | None,
) -> None:
    """Display a summary of an auto-resolved combat.

    Damage statistics are taken from attributes populated by ``_simulate``.
    Loot is generated for victories and added to ``hero.inventory``.
    """

    heading_font = theme.get_font(36) or pygame.font.SysFont(None, 36)
    font = theme.get_font(24) or pygame.font.SysFont(None, 24)

    overlay = combat_summary.build_overlay(screen)
    panel_rect = overlay()
    ok_rect = pygame.Rect(0, 0, 80, 40)
    ok_rect.center = (panel_rect.centerx, panel_rect.bottom - 40)

    damage_stats = {
        u: {"dealt": getattr(u, "damage_dealt", 0), "taken": getattr(u, "damage_taken", 0)}
        for u in hero_units + enemy_units
    }
    total_damage = sum(stats["dealt"] for stats in damage_stats.values())

    loot_items: List[Item] = []
    if hero_wins and hero is not None:
        loot_items = _generate_loot(enemy_units)
        for item in loot_items:
            hero.inventory.append(item)

    heading_text = "Victoire" if hero_wins else "Défaite"

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if ok_rect.collidepoint(event.pos):
                    return

        overlay()

        heading_surf = heading_font.render(heading_text, True, theme.PALETTE["text"])
        screen.blit(heading_surf, heading_surf.get_rect(center=(panel_rect.centerx, panel_rect.y + 30)))

        msg_lines = [
            f"Expérience gagnée : {exp}",
            f"Dégâts totaux infligés : {total_damage}",
        ]
        if loot_items:
            names = ", ".join(item.name for item in loot_items)
            msg_lines.append(f"Butin : {names}")
        for i, line in enumerate(msg_lines):
            msg_surf = font.render(line, True, theme.PALETTE["text"])
            screen.blit(msg_surf, msg_surf.get_rect(center=(panel_rect.centerx, panel_rect.y + 60 + i * 30)))

        left_x = panel_rect.x + 50
        right_x = panel_rect.centerx + 50
        header_y = panel_rect.y + 130
        ally_title = font.render("Alliés", True, theme.PALETTE["text"])
        enemy_title = font.render("Ennemis", True, theme.PALETTE["text"])
        screen.blit(ally_title, (left_x, header_y - 30))
        screen.blit(enemy_title, (right_x, header_y - 30))

        columns = [("Unité", 0), ("Infligés", 120), ("Subis", 220)]
        for text, offset in columns:
            surf = font.render(text, True, theme.PALETTE["text"])
            screen.blit(surf, (left_x + offset, header_y))
            screen.blit(surf, (right_x + offset, header_y))

        y_left = header_y + 40
        for unit in hero_units:
            stats = damage_stats.get(unit, {"dealt": 0, "taken": 0})
            name = font.render(unit.stats.name, True, theme.PALETTE["text"])
            dealt = font.render(str(stats["dealt"]), True, theme.PALETTE["text"])
            taken = font.render(str(stats["taken"]), True, theme.PALETTE["text"])
            screen.blit(name, (left_x, y_left))
            screen.blit(dealt, (left_x + 120, y_left))
            screen.blit(taken, (left_x + 220, y_left))
            y_left += 30

        y_right = header_y + 40
        for unit in enemy_units:
            stats = damage_stats.get(unit, {"dealt": 0, "taken": 0})
            name = font.render(unit.stats.name, True, theme.PALETTE["text"])
            dealt = font.render(str(stats["dealt"]), True, theme.PALETTE["text"])
            taken = font.render(str(stats["taken"]), True, theme.PALETTE["text"])
            screen.blit(name, (right_x, y_right))
            screen.blit(dealt, (right_x + 120, y_right))
            screen.blit(taken, (right_x + 220, y_right))
            y_right += 30

        pygame.draw.rect(screen, theme.PALETTE["accent"], ok_rect)
        pygame.draw.rect(screen, theme.PALETTE["text"], ok_rect, theme.FRAME_WIDTH)
        ok_text = font.render("OK", True, theme.PALETTE["text"])
        screen.blit(ok_text, ok_text.get_rect(center=ok_rect.center))
        pygame.display.flip()


def resolve(hero_units: List[Unit], enemy_units: List[Unit]) -> Tuple[bool, int, List[Unit], List[Unit]]:
    heroes, enemies, hero_wins, exp = _simulate(hero_units, enemy_units)
    return hero_wins, exp, heroes, enemies


def preview(
    hero_units: List[Unit],
    enemy_units: List[Unit],
    iterations: int = 50,
) -> Tuple[float, float, float]:
    """Return average casualties for both sides and experience gain.

    ``iterations`` controls how many simulated battles are averaged.  A higher
    number gives more accurate predictions at the cost of computation time.
    """

    total_hero_losses = 0
    total_enemy_losses = 0
    total_exp = 0
    initial_hero = sum(u.count for u in hero_units)
    initial_enemy = sum(u.count for u in enemy_units)
    for _ in range(iterations):
        heroes, enemies, hero_wins, exp = _simulate(hero_units, enemy_units)
        remaining_hero = sum(u.count for u in heroes)
        remaining_enemy = sum(u.count for u in enemies)
        total_hero_losses += initial_hero - remaining_hero
        total_enemy_losses += initial_enemy - remaining_enemy
        total_exp += exp
    avg_loss_hero = total_hero_losses / iterations if iterations else 0
    avg_loss_enemy = total_enemy_losses / iterations if iterations else 0
    avg_exp = total_exp / iterations if iterations else 0
    return avg_loss_hero, avg_loss_enemy, avg_exp
