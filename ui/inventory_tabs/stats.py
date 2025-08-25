"""Render the stats tab for :class:`InventoryScreen`."""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Optional
import json
import os
from pathlib import Path

import pygame
import constants
from core.combat import Combat
from ..inventory_screen import (
    COLOR_TEXT,
    COLOR_SLOT_BG,
    COLOR_SLOT_BD,
    COLOR_ACCENT,
)

# ---------------------------------------------------------------------------
# Icon loading

_ICON_CACHE: Dict[str, Optional[pygame.Surface]] = {}
try:
    with open(os.path.join("assets", "icons", "icons.json"), "r", encoding="utf8") as fh:
        _ICON_MANIFEST = json.load(fh)
except Exception:  # pragma: no cover - file missing or invalid
    _ICON_MANIFEST = {}

_STAT_ICON_IDS = {
    "HP": "status_regeneration",
    "Dmg": "round_attack_range",
    "Spd": "status_haste",
    "Init": "resource_speed",
    "Def Melee": "action_defend",
    "Def Ranged": "action_shoot",
    "Def Magic": "round_defence_magic",
    "Morale": "round_morale",
    "Luck": "round_luck",
}


def _load_icon(name: str, size: int) -> Optional[pygame.Surface]:
    """Load icon ``name`` at ``size`` pixels using the manifest."""
    if name in _ICON_CACHE:
        return _ICON_CACHE[name]
    info = _ICON_MANIFEST.get(name)
    img_mod = getattr(pygame, "image", None)
    transform = getattr(pygame, "transform", None)
    try:
        if isinstance(info, str):
            path = Path(info)
            if img_mod and hasattr(img_mod, "load") and os.path.exists(path):
                icon = img_mod.load(path)
                if hasattr(icon, "convert_alpha"):
                    icon = icon.convert_alpha()
                if transform and hasattr(transform, "scale"):
                    icon = transform.scale(icon, (size, size))
                _ICON_CACHE[name] = icon
                return icon
        elif isinstance(info, dict) and "file" in info:
            path = Path(info["file"])
            if img_mod and hasattr(img_mod, "load") and os.path.exists(path):
                icon = img_mod.load(path)
                if hasattr(icon, "convert_alpha"):
                    icon = icon.convert_alpha()
                if transform and hasattr(transform, "scale"):
                    icon = transform.scale(icon, (size, size))
                _ICON_CACHE[name] = icon
                return icon
        elif isinstance(info, dict) and "sheet" in info:
            sheet_path = Path(info["sheet"])
            coords = info.get("coords", [0, 0])
            tile = info.get("tile", [0, 0])
            if (
                img_mod
                and hasattr(img_mod, "load")
                and os.path.exists(sheet_path)
                and tile[0]
                and tile[1]
            ):
                sheet = img_mod.load(sheet_path)
                if hasattr(sheet, "convert_alpha"):
                    sheet = sheet.convert_alpha()
                rect = pygame.Rect(
                    coords[0] * tile[0],
                    coords[1] * tile[1],
                    tile[0],
                    tile[1],
                )
                icon = sheet.subsurface(rect)
                if transform and hasattr(transform, "scale"):
                    icon = transform.scale(icon, (size, size))
                _ICON_CACHE[name] = icon
                return icon
    except Exception:  # pragma: no cover - loading failed
        pass
    _ICON_CACHE[name] = None
    return None

if TYPE_CHECKING:  # pragma: no cover - only for type hints
    from ..inventory_screen import InventoryScreen


def draw(screen: "InventoryScreen") -> None:
    """Draw the content of the *Stats* tab."""
    y = screen.center_rect.y + 52
    x = screen.center_rect.x + 16

    # Portrait
    hero_img = screen.assets.get(constants.IMG_HERO_PORTRAIT)
    if hero_img:
        hero_img = pygame.transform.scale(hero_img, (120, 120))
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
    y2 = y + len(lines) * 26 + 8
    size = 24
    for j, (name, val) in enumerate(pairs):
        icon_id = _STAT_ICON_IDS.get(name)
        icon = _load_icon(icon_id, size) if icon_id else None
        if icon:
            screen.screen.blit(icon, (x, y2 + j * 24))
        else:
            placeholder = screen.font.render(name[:2], True, COLOR_TEXT)
            screen.screen.blit(placeholder, (x, y2 + j * 24))
        t1 = screen.font.render(name + ":", True, COLOR_TEXT)
        t2 = screen.font.render(str(val), True, COLOR_TEXT)
        screen.screen.blit(t1, (x + size + 4, y2 + j * 24))
        screen.screen.blit(t2, (x + size + 4 + 140, y2 + j * 24))

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
