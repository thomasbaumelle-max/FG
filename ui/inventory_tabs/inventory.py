"""Inventory tab helpers for :class:`InventoryScreen`."""

from __future__ import annotations

from dataclasses import asdict
from typing import TYPE_CHECKING, List, Tuple
import pygame
import constants
from core.entities import Item, EquipmentSlot
from ..inventory_screen import (
    COLOR_TEXT,
    COLOR_SLOT_BG,
    COLOR_SLOT_BD,
    COLOR_ACCENT,
    RARITY_ORDER,
)

if TYPE_CHECKING:  # pragma: no cover
    from ..inventory_screen import InventoryScreen


def filtered_inventory(screen: "InventoryScreen") -> List[Tuple[int, Item]]:
    """Return inventory filtered and sorted according to current settings."""
    items: List[Tuple[int, Item]] = []
    query = screen.search_text.lower()
    for idx, item in enumerate(screen.hero.inventory):
        if screen.active_filter == "Armor" and item.slot in (None, EquipmentSlot.WEAPON):
            continue
        if screen.active_filter == "Weapons" and item.slot != EquipmentSlot.WEAPON:
            continue
        if screen.active_filter == "Consumables" and not (item.slot is None and item.stackable):
            continue
        if screen.active_filter == "Quest" and not (item.slot is None and not item.stackable):
            continue
        if query and query not in item.name.lower():
            continue
        items.append((idx, item))
    if screen.sort_mode == "Name":
        items.sort(key=lambda x: x[1].name.lower())
    elif screen.sort_mode == "Rarity":
        items.sort(key=lambda x: RARITY_ORDER.get(x[1].rarity.lower(), 0), reverse=True)
    elif screen.sort_mode == "Newest":
        items.sort(key=lambda x: x[1].id, reverse=True)
    return items


def draw(screen: "InventoryScreen") -> None:
    """Draw the content of the *Inventory* tab."""
    # Controls
    for name, rect in screen.filter_rects.items():
        col = (60, 62, 72) if name == screen.active_filter else (46, 48, 56)
        pygame.draw.rect(screen.screen, col, rect, border_radius=5)
        pygame.draw.rect(screen.screen, COLOR_SLOT_BD, rect, 1, border_radius=5)
        t = screen.font.render(name, True, COLOR_TEXT)
        screen.screen.blit(t, (rect.x + (rect.width - t.get_width()) // 2, rect.y + 4))
    for name, rect in screen.sort_rects.items():
        col = (60, 62, 72) if name == screen.sort_mode else (46, 48, 56)
        pygame.draw.rect(screen.screen, col, rect, border_radius=5)
        pygame.draw.rect(screen.screen, COLOR_SLOT_BD, rect, 1, border_radius=5)
        t = screen.font.render(name, True, COLOR_TEXT)
        screen.screen.blit(t, (rect.x + (rect.width - t.get_width()) // 2, rect.y + 4))

    pygame.draw.rect(screen.screen, COLOR_TEXT, screen.search_rect, 2, border_radius=4)
    if screen.search_active:
        pygame.draw.rect(screen.screen, COLOR_ACCENT, screen.search_rect, 2, border_radius=4)
    t = screen.font.render(screen.search_text or "Search...", True, COLOR_TEXT)
    screen.screen.blit(t, (screen.search_rect.x + 6, screen.search_rect.y + 6))

    # Items list
    items = filtered_inventory(screen)
    start = screen.inventory_offset
    screen.item_rects = []
    for i in range(20):
        idx = start + i
        rect = pygame.Rect(screen.center_rect.x + 12, screen.center_rect.y + 120 + i * 36, 420, 32)
        pygame.draw.rect(screen.screen, COLOR_SLOT_BG, rect)
        pygame.draw.rect(screen.screen, COLOR_SLOT_BD, rect, 1)
        if idx < len(items):
            inv_idx, item = items[idx]
            icon = screen.assets.get(item.icon or "")
            if icon:
                icon = pygame.transform.scale(icon, (28, 28))
                screen.screen.blit(icon, (rect.x + 2, rect.y + 2))
            name = screen.font.render(item.name, True, COLOR_TEXT)
            screen.screen.blit(name, (rect.x + 36, rect.y + 6))
            qty = "" if not item.stackable else f" x{item.qty}"
            if qty:
                q = screen.font.render(qty, True, COLOR_TEXT)
                screen.screen.blit(q, (rect.right - q.get_width() - 6, rect.y + 6))
            screen.item_rects.append((inv_idx, rect))
        else:
            screen.item_rects.append((None, rect))


def item_tooltip(screen: "InventoryScreen", item: Item, equip: bool = True) -> List[Tuple[str, Tuple[int, int, int]]]:
    """Return tooltip lines for an item, simulating equip/unequip."""
    lines: List[Tuple[str, Tuple[int, int, int]]] = [
        (item.name, COLOR_TEXT),
        (f"Rarity: {item.rarity}", COLOR_TEXT),
    ]
    total = screen.hero.get_total_stats()
    new_stats = asdict(total)
    if equip:
        current = screen.hero.equipment.get(item.slot)
        if current:
            for stat, value in asdict(current.modifiers).items():
                new_stats[stat] -= value
        for stat, value in asdict(item.modifiers).items():
            new_stats[stat] += value
    else:
        for stat, value in asdict(item.modifiers).items():
            new_stats[stat] -= value
    for stat in new_stats:
        old = getattr(total, stat)
        new = new_stats[stat]
        diff = new - old
        if diff:
            col = constants.GREEN if diff > 0 else constants.RED
            lines.append((f"{stat}: {new} ({diff:+})", col))
    return lines
