"""Skill tab helpers for :class:`InventoryScreen`."""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Tuple, Set
import pygame
from ..inventory_screen import (
    COLOR_TEXT,
    COLOR_SLOT_BG,
    COLOR_SLOT_BD,
    COLOR_ACCENT,
    COLOR_DISABLED,
    COLOR_OK,
    COLOR_LINK,
)
from core.entities import SkillNode

if TYPE_CHECKING:  # pragma: no cover
    from ..inventory_screen import InventoryScreen


def draw(screen: "InventoryScreen") -> None:
    """Draw the content of the *Skills* tab."""
    # Top skill tabs
    for name, rect in screen.skill_tab_buttons.items():
        col = (60, 62, 72) if name == screen.active_skill_tab else (46, 48, 56)
        pygame.draw.rect(screen.screen, col, rect, border_radius=5)
        pygame.draw.rect(screen.screen, COLOR_SLOT_BD, rect, 1, border_radius=5)
        t = screen.font.render(name.title(), True, COLOR_TEXT)
        screen.screen.blit(t, (rect.x + (rect.width - t.get_width()) // 2, rect.y + 4))

    pts = screen.font.render(
        f"Skill Points: {screen.hero.skill_points}", True, COLOR_TEXT
    )
    screen.screen.blit(pts, (screen.center_rect.x + 14, screen.center_rect.y + 90))

    nodes = screen.skill_trees.get(screen.active_skill_tab, [])
    positions = screen.skill_positions.get(screen.active_skill_tab, {})

    # Grid & connectors (single column, four ranks)
    cols, rows = 1, 4
    gy = screen.center_rect.y + 110
    available_h = screen.center_rect.bottom - 40 - gy
    cell = min(100, available_h // rows)
    grid_w = cols * cell
    gx = screen.center_rect.x + (screen.center_rect.width - grid_w) // 2

    # Draw links first
    def node_center(nid: str) -> Tuple[int, int]:
        c, r = positions[nid]
        rect = pygame.Rect(gx + c * cell + 8, gy + r * cell + 8, cell - 16, cell - 16)
        return (rect.centerx, rect.centery)

    for node in nodes:
        for pre in node.requires:
            p0 = node_center(pre)
            p1 = node_center(node.id)
            pygame.draw.line(screen.screen, COLOR_LINK, p0, p1, 3)

    # Draw nodes
    screen.skill_rects.clear()
    learned_set = screen.hero.learned_skills.get(screen.active_skill_tab, set())
    for node in nodes:
        c, r = positions[node.id]
        rect = pygame.Rect(gx + c * cell + 8, gy + r * cell + 8, cell - 16, cell - 16)
        learned = node.id in learned_set
        available = (screen.hero.skill_points >= node.cost) and all(
            req in learned_set for req in node.requires
        )

        state_col = (
            COLOR_OK if learned else ((60, 120, 200) if available else COLOR_DISABLED)
        )
        pygame.draw.rect(screen.screen, COLOR_SLOT_BG, rect, border_radius=8)
        pygame.draw.rect(screen.screen, state_col, rect, 3, border_radius=8)

        # branch icon
        icon = screen.assets.get(node.icon)
        if icon:
            icon = pygame.transform.smoothscale(
                icon, (rect.width - 12, rect.height - 46)
            )
            screen.screen.blit(icon, (rect.x + 6, rect.y + 6))

        label = screen.font_small.render(node.rank, True, COLOR_TEXT)
        screen.screen.blit(
            label,
            (
                rect.centerx - label.get_width() // 2,
                rect.bottom - label.get_height() - 6,
            ),
        )

        screen.skill_rects[node.id] = rect

    # Hints
    hint = screen.font_small.render(
        "Left-click: Learn • Right-click: Refund (if no dependents)", True, COLOR_ACCENT
    )
    screen.screen.blit(
        hint, (screen.center_rect.x + 14, screen.center_rect.bottom - 26)
    )


def skill_tooltip(
    screen: "InventoryScreen", node: SkillNode
) -> List[Tuple[str, Tuple[int, int, int]]]:
    """Return tooltip lines for a skill node."""
    lines: List[Tuple[str, Tuple[int, int, int]]] = [
        (node.name, COLOR_TEXT),
        (node.desc, COLOR_TEXT),
        (f"Cost: {node.cost}", COLOR_TEXT),
    ]
    if node.requires:
        lines.append((f"Requires: {', '.join(node.requires)}", COLOR_TEXT))
    learned = screen.hero.learned_skills.get(screen.active_skill_tab, set())
    if node.id in learned:
        lines.append(("Learned", COLOR_OK))
    else:
        ok = screen.hero.skill_points >= node.cost and all(
            req in learned for req in node.requires
        )
        lines.append(
            ("Available" if ok else "Locked", COLOR_OK if ok else COLOR_DISABLED)
        )
    return lines


def check_tab_click(screen: "InventoryScreen", pos: Tuple[int, int]) -> bool:
    """Handle click on skill sub-tab buttons."""
    for name, rect in screen.skill_tab_buttons.items():
        if rect.collidepoint(pos):
            screen.active_skill_tab = name
            return True
    return False


def dependents_of(screen: "InventoryScreen", tree: str, nid: str) -> Set[str]:
    """Return set of dependent skill node ids for ``nid`` in ``tree``."""
    deps: Set[str] = set()
    for n in screen.skill_trees.get(tree, []):
        if nid in n.requires:
            deps.add(n.id)
    return deps


def can_refund(screen: "InventoryScreen", nid: str) -> bool:
    """Check if a skill node can be safely refunded."""
    learned = screen.hero.learned_skills.get(screen.active_skill_tab, set())
    if nid not in learned:
        return False
    for dep in dependents_of(screen, screen.active_skill_tab, nid):
        if dep in learned:
            return False
    return True
