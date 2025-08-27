"""Render the stats tab for :class:`InventoryScreen`."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pygame
import constants
from core.combat import Combat
from loaders import icon_loader as IconLoader
from ..inventory_screen import (
    COLOR_TEXT,
    COLOR_SLOT_BG,
    COLOR_SLOT_BD,
    COLOR_ACCENT,
)

_STAT_ICON_IDS = {
    "HP": "stat_hp",
    "Dmg": "stat_attack_range",
    "Spd": "stat_speed",
    "Init": "stat_initiative",
    "Def Melee": "stat_defence_melee",
    "Def Ranged": "stat_defence_ranged",
    "Def Magic": "stat_defence_magic",
    "Morale": "stat_morale",
    "Luck": "stat_luck",
    # Elemental resistances
    "fire": "status_burn",
    "ice": "status_freeze",
    "shock": "status_stun",
    "earth": "status_petrify",
    "water": "status_slow",
}

if TYPE_CHECKING:  # pragma: no cover - only for type hints
    from ..inventory_screen import InventoryScreen


def draw(screen: "InventoryScreen") -> None:
    """Draw the content of the *Stats* tab."""
    y = screen.center_rect.y + 52
    x = screen.center_rect.x + 16

    # Portrait (use hero.portrait with fallback to default asset)
    hero_img = getattr(screen.hero, "portrait", None)
    if hero_img is None:
        hero_img = screen.assets.get(constants.IMG_HERO_PORTRAIT)
    if hero_img:
        try:
            hero_img = pygame.transform.scale(hero_img, (120, 120))
        except (AttributeError, TypeError):
            pass
        screen.screen.blit(hero_img, (x, y))
        x += 140

    # Primary stats
    lines = [
        f"Level: {screen.hero.level}",
        f"Skill points: {screen.hero.skill_points}",
        f"AP: {screen.hero.ap}/{screen.hero.max_ap}",
        f"Mana: {screen.hero.mana}/{screen.hero.max_mana}",
    ]
    for i, line in enumerate(lines):
        t = screen.font.render(line, True, COLOR_TEXT)
        screen.screen.blit(t, (x, y + i * 26))

    stats = screen.hero.get_total_stats()
    pairs = [
        ("HP", stats.pv),
        ("Dmg", stats.dmg),
        ("Spd", stats.spd),
        ("Init", stats.init),
        ("Def Melee", stats.def_melee),
        ("Def Ranged", stats.def_ranged),
        ("Def Magic", stats.def_magic),
        ("Morale", stats.moral),
        ("Luck", stats.luck),
    ]
    # Elemental resistances
    resistances = screen.hero.get_resistances().as_dict()
    for school, value in resistances.items():
        pairs.append((school, f"{value}%"))
    y2 = y + len(lines) * 26 + 8
    size = 24
    screen.stat_rects = []
    for j, (key, val) in enumerate(pairs):
        icon_id = _STAT_ICON_IDS.get(key)
        icon = IconLoader.get(icon_id, size) if icon_id else None
        rect = pygame.Rect(x, y2 + j * 24, size, size)
        if icon:
            screen.screen.blit(icon, rect.topleft)
        else:
            placeholder = screen.font.render(str(key)[:2], True, COLOR_TEXT)
            screen.screen.blit(placeholder, rect.topleft)
        screen.stat_rects.append((key, rect))
        t2 = screen.font.render(str(val), True, COLOR_TEXT)
        screen.screen.blit(t2, (rect.x + size + 4, rect.y))

    # Army 7x1
    font_big = screen.font_big or screen.font
    if font_big:
        label = font_big.render("Hero Army", True, COLOR_TEXT)
        gy = screen.center_rect.y + screen.center_rect.height - 120
        screen.screen.blit(label, (screen.center_rect.x + 12, gy - 28))
    else:
        gy = screen.center_rect.y + screen.center_rect.height - 120
    screen.army_rects = []
    cell = 84
    for idx in range(7):
        rect = pygame.Rect(screen.center_rect.x + 12 + idx * (cell + 6), gy, cell, cell)
        try:
            pygame.draw.rect(screen.screen, COLOR_SLOT_BG, rect, border_radius=6)
            pygame.draw.rect(screen.screen, COLOR_SLOT_BD, rect, 2, border_radius=6)
        except TypeError:  # pragma: no cover - stub draw.rect
            pygame.draw.rect(screen.screen, COLOR_SLOT_BG, rect)
            pygame.draw.rect(screen.screen, COLOR_SLOT_BD, rect, 2)
        unit = screen.army_grid[idx]
        if unit:
            icon = screen.assets.get(unit.stats.sheet)
            if isinstance(icon, list):
                icon = Combat.get_unit_image(screen, unit, (cell - 4, cell - 4))
            elif icon:
                icon = pygame.transform.scale(icon, (cell - 4, cell - 4))
            if icon:
                screen.screen.blit(icon, (rect.x + 2, rect.y + 2))
            qty = screen.font.render(str(unit.count), True, COLOR_ACCENT)
            screen.screen.blit(
                qty,
                (
                    rect.x + rect.width - qty.get_width() - 4,
                    rect.y + rect.height - qty.get_height() - 4,
                ),
            )
        screen.army_rects.append((idx, rect))
