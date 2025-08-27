"""Inventory tab helpers for :class:`InventoryScreen`."""

from __future__ import annotations

from dataclasses import asdict
from typing import TYPE_CHECKING, List, Tuple
import pygame
import constants
import theme
from core.entities import Item, EquipmentSlot
from ..inventory_screen import (
    COLOR_TEXT,
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
        if screen.active_filter == "Armor" and item.slot in (
            None,
            EquipmentSlot.WEAPON,
        ):
            continue
        if screen.active_filter == "Weapons" and item.slot != EquipmentSlot.WEAPON:
            continue
        if screen.active_filter == "Consumables" and not (
            item.slot is None and item.stackable
        ):
            continue
        if screen.active_filter == "Quest" and not (
            item.slot is None and not item.stackable
        ):
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
        pygame.draw.rect(
            screen.screen, COLOR_ACCENT, screen.search_rect, 2, border_radius=4
        )
    t = screen.font.render(screen.search_text or "Search...", True, COLOR_TEXT)
    screen.screen.blit(t, (screen.search_rect.x + 6, screen.search_rect.y + 6))

    # Items grid 4x4 with pagination
    items = filtered_inventory(screen)
    start = screen.inventory_offset
    screen.item_rects = []
    gx = screen.center_rect.x + 12
    top_offset = 120
    # Each cell is bounded by both available width and height and capped at 64px
    btn_w, btn_h = 32, 24
    avail_w = screen.center_rect.width - 24
    avail_h = screen.center_rect.height - top_offset
    max_cell_w = avail_w // 4
    max_cell_h = max((avail_h - btn_h - 10) // 4, 1)
    cell = min(max_cell_w, max_cell_h, 64)
    grid_h = cell * 4
    # Center the grid vertically within the available space
    gy = screen.center_rect.y + top_offset + (avail_h - (grid_h + btn_h + 10)) // 2
    screen.inventory_grid_origin = (gx, gy)
    screen.inventory_cell_size = cell
    for row in range(4):
        for col in range(4):
            idx = start + row * 4 + col
            rect = pygame.Rect(gx + col * cell, gy + row * cell, cell, cell)
            pygame.draw.rect(screen.screen, theme.PALETTE["panel"], rect)
            theme.draw_frame(screen.screen, rect)
            if idx < len(items):
                inv_idx, item = items[idx]
                icon = screen.assets.get(item.icon or "")
                if icon:
                    icon = pygame.transform.scale(icon, (cell - 4, cell - 4))
                    screen.screen.blit(icon, (rect.x + 2, rect.y + 2))
                qty = "" if not item.stackable else f"x{item.qty}"
                if qty:
                    q = screen.font.render(qty, True, COLOR_TEXT)
                    screen.screen.blit(
                        q,
                        (
                            rect.right - q.get_width() - 4,
                            rect.bottom - q.get_height() - 4,
                        ),
                    )
                screen.item_rects.append((inv_idx, rect))
            else:
                screen.item_rects.append((None, rect))

    # Pagination buttons
    btn_y = gy + 4 * cell + 10
    prev_rect = pygame.Rect(gx, btn_y, btn_w, btn_h)
    next_rect = pygame.Rect(gx + 4 * cell - btn_w, btn_y, btn_w, btn_h)
    screen.prev_page_rect = prev_rect
    screen.next_page_rect = next_rect
    pygame.draw.rect(screen.screen, theme.PALETTE["panel"], prev_rect)
    pygame.draw.rect(screen.screen, COLOR_SLOT_BD, prev_rect, 1)
    pygame.draw.rect(screen.screen, theme.PALETTE["panel"], next_rect)
    pygame.draw.rect(screen.screen, COLOR_SLOT_BD, next_rect, 1)
    lt = screen.font.render("<", True, COLOR_TEXT)
    rt = screen.font.render(">", True, COLOR_TEXT)
    screen.screen.blit(
        lt,
        (prev_rect.centerx - lt.get_width() // 2, prev_rect.centery - lt.get_height() // 2),
    )
    screen.screen.blit(
        rt,
        (next_rect.centerx - rt.get_width() // 2, next_rect.centery - rt.get_height() // 2),
    )


def item_tooltip(
    screen: "InventoryScreen", item: Item, equip: bool = True
) -> List[Tuple[str, Tuple[int, int, int]]]:
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
