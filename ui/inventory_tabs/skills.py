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
    """Draw all skill branches simultaneously."""
    pts = screen.font.render(
        f"Skill Points: {screen.hero.skill_points}", True, COLOR_TEXT
    )
    screen.screen.blit(pts, (screen.center_rect.x + 14, screen.center_rect.y + 44))

    cols = max(1, len(screen.SKILL_TABS))
    rows = 4
    label_h = screen.font.render("X", True, COLOR_TEXT).get_height()
    gy = screen.center_rect.y + 74 + label_h + 8
    available_h = screen.center_rect.bottom - 40 - gy
    cell = min(100, available_h // rows)
    grid_w = cols * cell
    gx = screen.center_rect.x + (screen.center_rect.width - grid_w) // 2

    for i, name in enumerate(screen.SKILL_TABS):
        label = screen.font.render(name, True, COLOR_TEXT)
        screen.screen.blit(
            label,
            (
                gx + i * cell + (cell - label.get_width()) // 2,
                gy - label_h - 4,
            ),
        )

    def node_center(nid: str) -> Tuple[int, int]:
        branch = screen.skill_branch_of[nid]
        c, r = screen.skill_positions[branch][nid]
        rect = pygame.Rect(gx + c * cell + 8, gy + r * cell + 8, cell - 16, cell - 16)
        return (rect.centerx, rect.centery)

    for branch, nodes in screen.skill_trees.items():
        for node in nodes:
            for pre in node.requires:
                if pre in screen.skill_branch_of and screen.skill_branch_of[pre] == branch:
                    p0 = node_center(pre)
                    p1 = node_center(node.id)
                    pygame.draw.line(screen.screen, COLOR_LINK, p0, p1, 3)

    screen.skill_rects.clear()
    for branch, nodes in screen.skill_trees.items():
        learned_set = screen.hero.learned_skills.get(branch, set())
        for node in nodes:
            c, r = screen.skill_positions[branch][node.id]
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

            icon = screen.assets.get(node.icon) if node.icon else None
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
    tree = screen.skill_branch_of.get(node.id, "")
    lines: List[Tuple[str, Tuple[int, int, int]]] = [
        (f"{node.name} ({tree})", COLOR_TEXT),
        (node.desc, COLOR_TEXT),
        (f"Cost: {node.cost}", COLOR_TEXT),
    ]
    if node.requires:
        lines.append((f"Requires: {', '.join(node.requires)}", COLOR_TEXT))
    learned = screen.hero.learned_skills.get(tree, set())
    if node.id in learned:
        lines.append(("Learned", COLOR_OK))
    else:
        ok = screen.hero.skill_points >= node.cost and all(
            req in learned for req in node.requires
        )
        lines.append(("Available" if ok else "Locked", COLOR_OK if ok else COLOR_DISABLED))
    return lines


def check_tab_click(screen: "InventoryScreen", pos: Tuple[int, int]) -> bool:
    """Skill tabs are no longer used."""
    return False


def dependents_of(screen: "InventoryScreen", tree: str, nid: str) -> Set[str]:
    """Return set of dependent skill node ids for ``nid`` in ``tree``."""
    deps: Set[str] = set()
    for n in screen.skill_trees.get(tree, []):
        if nid in n.requires:
            deps.add(n.id)
    return deps


def can_refund(screen: "InventoryScreen", tree: str, nid: str) -> bool:
    """Check if a skill node can be safely refunded."""
    learned = screen.hero.learned_skills.get(tree, set())
    if nid not in learned:
        return False
    for dep in dependents_of(screen, tree, nid):
        if dep in learned:
            return False
    return True
