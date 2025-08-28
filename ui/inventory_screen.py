# inventory_screen.py
"""
Inventory & Hero screen – HoMM-like look:
- Bottom resource bar (consistent with town_screen).
- Left vertical tabs (Stats / Inventory / Skills).
- Center panel depends on tab.
- Right equipment panel with slots.
- Improved Skills: node states, connectors, tooltips, safe refund by right-click.
"""

from __future__ import annotations
from typing import Callable, Dict, List, Optional, Tuple, Set
import os
import pygame

import constants
import theme
from .widgets.icon_button import IconButton
from core.entities import (
    EquipmentSlot,
    Hero,
    Item,
    SkillNode,
    Unit,
    SKILL_CATALOG,
    REPO_ROOT,
    build_skill_catalog,
)
from .inventory_interface import InventoryInterface

# --------------------------------------------------------------------------- #
# Style (aligné avec town_screen)
# --------------------------------------------------------------------------- #

RESBAR_H = 36
GAP = 10
TAB_W_RATIO = 0.16
EQUIP_W_RATIO = 0.28

COLOR_BG = (16, 18, 22)
COLOR_PANEL = (28, 30, 36)
COLOR_ACCENT = (210, 180, 80)
COLOR_TEXT = (240, 240, 240)
COLOR_DISABLED = (120, 120, 120)
COLOR_OK = (80, 190, 80)
COLOR_WARN = (210, 90, 70)
COLOR_SLOT_BG = (36, 38, 44)
COLOR_SLOT_BD = (80, 80, 90)
COLOR_LINK = (120, 120, 150)

RARITY_ORDER = {"common": 0, "uncommon": 1, "rare": 2, "epic": 3, "legendary": 4}
DOUBLECLICK_MS = 300

from .inventory_tabs import stats as stats_tab  # noqa: E402
from .inventory_tabs import inventory as inv_tab  # noqa: E402
from .inventory_tabs import skills as skills_tab  # noqa: E402

# --------------------------------------------------------------------------- #


class InventoryScreen:
    TAB_NAMES = ["stats", "inventory", "skills"]

    def __init__(
        self,
        screen: pygame.Surface,
        assets: Dict[str, pygame.Surface],
        hero: Hero,
        clock: Optional[pygame.time.Clock] = None,
        pause_cb: Optional[Callable[[], Tuple[bool, pygame.Surface]]] = None,
    ) -> None:
        self.screen = screen
        self.assets = assets
        self.hero = hero
        self.clock = clock or pygame.time.Clock()
        self.active_tab = "stats"
        self.active_skill_tab = ""
        self.open_pause_menu = pause_cb

        # Fonts
        font_path = os.path.join(REPO_ROOT, "fonts", "roboto.ttf")
        if hasattr(pygame, "font") and not pygame.font.get_init():
            pygame.font.init()

        def _load_font(size: int, bold: bool = False):
            f = theme.get_font(size)
            if f is None and hasattr(pygame, "font"):
                try:  # pragma: no cover
                    if hasattr(pygame.font, "Font"):
                        f = pygame.font.Font(font_path, size)
                    elif hasattr(pygame.font, "SysFont"):
                        f = pygame.font.SysFont("roboto", size)
                except Exception:  # pragma: no cover
                    f = None
            if f and bold and hasattr(f, "set_bold"):
                f.set_bold(True)
            return f

        self.font = _load_font(18)
        self.font_small = _load_font(14)
        self.font_big = _load_font(22, bold=True) or self.font
        self.font_title = _load_font(28, bold=True) or self.font_big or self.font

        # Offset of the panel within the main screen when run() uses an overlay
        self.offset = (0, 0)

        # Inventory state
        self.inventory_offset = 0
        self.item_rects: List[Tuple[Optional[int], pygame.Rect]] = []
        self.inventory_grid_origin: Tuple[int, int] = (0, 0)
        self.inventory_cell_size: int = 0
        self.prev_page_rect: Optional[pygame.Rect] = None
        self.next_page_rect: Optional[pygame.Rect] = None
        self.drag_item: Optional[Item] = None
        self.drag_origin: Optional[int] = None
        self.drag_icon_size: Optional[Tuple[int, int]] = None
        self._last_click_time: int = 0
        self._last_click_slot: Optional[Tuple[str, object]] = None
        self.context_menu: Optional[Dict[str, object]] = None
        self.filter_options = ["All", "Armor", "Weapons", "Consumables", "Quest"]
        self.sort_options = ["Rarity", "Name", "Newest"]
        self.active_filter = "All"
        self.sort_mode = "Rarity"
        self.search_text = ""
        self.search_active = False

        # Error messages
        self.error_message: Optional[str] = None
        self.error_timer: int = 0

        # Army (Stats tab – 7×1)
        self.army_grid: List[Optional[Unit]] = self.hero.army[:]
        while len(self.army_grid) < 7:
            self.army_grid.append(None)
        self.army_rects: List[Tuple[int, pygame.Rect]] = []
        self.drag_unit: Optional[Unit] = None
        self.drag_unit_origin: Optional[int] = None

        # Equipment
        self.slot_rects: Dict[EquipmentSlot, pygame.Rect] = {}

        # Stat icons (Stats tab)
        self.stat_rects: List[Tuple[str, pygame.Rect]] = []

        # Skills --------------------------------------------------------------
        self.skill_trees: Dict[str, List[SkillNode]] = {}
        self.skill_positions: Dict[str, Dict[str, Tuple[int, int]]] = {}
        self.skill_branch_of: Dict[str, str] = {}
        self.skill_nodes: Dict[str, SkillNode] = {}
        self.SKILL_TABS: List[str] = []
        self._build_skill_trees()
        self.active_skill_tab = self.SKILL_TABS[0] if self.SKILL_TABS else ""
        self.skill_rects: Dict[str, pygame.Rect] = {}

        # Layout
        self._recalc_layout()

    # ------------------------------------------------------------------ Skills
    def _build_skill_trees(self) -> None:
        """Populate skill trees and positions from the JSON manifest."""
        faction_id = self.hero.faction.id if self.hero.faction else None
        manifest = build_skill_catalog(faction_id)
        rank_order = ["N", "A", "E", "M"]
        order: List[str] = []
        for entry in manifest:
            branch = entry.get("branch", "")
            if branch and branch not in order:
                order.append(branch)
        self.SKILL_TABS = order
        self.skill_trees = {b: [] for b in order}
        self.skill_positions = {b: {} for b in order}
        self.skill_branch_of.clear()
        self.skill_nodes.clear()
        for entry in manifest:
            branch = entry.get("branch", "")
            nid = entry.get("id")
            node = SKILL_CATALOG.get(nid)
            if not node or branch not in self.skill_trees:
                continue
            self.skill_trees[branch].append(node)
            row = (
                rank_order.index(entry.get("rank", "N"))
                if entry.get("rank", "N") in rank_order
                else 0
            )
            col = order.index(branch)
            self.skill_positions[branch][nid] = (col, row)
            self.skill_branch_of[nid] = branch
            self.skill_nodes[nid] = node
        for branch in self.skill_trees:
            self.skill_trees[branch].sort(
                key=lambda n: rank_order.index(n.rank) if n.rank in rank_order else 0
            )

    # ------------------------------------------------------------------ Layout
    def _recalc_layout(self) -> None:
        W, H = self.screen.get_size()
        tab_w = int(W * TAB_W_RATIO)
        equip_w = int(W * EQUIP_W_RATIO)
        body_h = H - RESBAR_H

        self.resbar_rect = pygame.Rect(0, H - RESBAR_H, W, RESBAR_H)
        self.tabs_rect = pygame.Rect(0, 0, tab_w, body_h)
        self.center_rect = pygame.Rect(tab_w, 0, W - tab_w - equip_w, H)
        self.centre_rect = self.center_rect  # alias for compatibility
        self.equip_rect = pygame.Rect(W - equip_w, 0, equip_w, body_h)

        # Tab buttons
        self.tab_buttons: Dict[str, IconButton] = {}
        th = self.tabs_rect.height // len(self.TAB_NAMES)
        icon_map = {
            "stats": "nav_hero_screen",
            "inventory": "nav_inventory",
            "skills": "nav_skill_tree",
        }
        for i, name in enumerate(self.TAB_NAMES):
            rect = pygame.Rect(
                self.tabs_rect.x + 6,
                self.tabs_rect.y + i * th + 6,
                self.tabs_rect.width - 12,
                th - 12,
            )
            icon_id = icon_map.get(name, f"{name}_tab")
            btn = IconButton(
                rect,
                icon_id,
                lambda n=name: setattr(self, "active_tab", n),
                tooltip=name.title(),
            )
            self.tab_buttons[name] = btn

        # Equipment slot grid (silhouette)
        cols, rows = 3, 4
        if self.font_big:
            title_h = (
                self.font_big.render("Equipment", True, COLOR_TEXT).get_height() + 16
            )
        else:  # pragma: no cover - fallback when font unavailable
            title_h = 32
        cell_w = self.equip_rect.width // cols
        cell_h = (self.equip_rect.height - title_h) // rows
        slot_positions = {
            EquipmentSlot.HEAD: (1, 0),
            EquipmentSlot.NECK: (1, 1),
            EquipmentSlot.SHOULDERS: (0, 1),
            EquipmentSlot.RING: (2, 1),
            EquipmentSlot.OFFHAND: (0, 2),
            EquipmentSlot.TORSO: (1, 2),
            EquipmentSlot.WEAPON: (2, 2),
            EquipmentSlot.LEGS: (1, 3),
            EquipmentSlot.AMULET: (2, 3),
        }
        self.slot_rects.clear()
        for slot, (c, r) in slot_positions.items():
            self.slot_rects[slot] = pygame.Rect(
                self.equip_rect.x + c * cell_w + 10,
                self.equip_rect.y + title_h + r * cell_h + 10,
                cell_w - 20,
                cell_h - 20,
            )

        # Inventory controls (center)
        base_x = 20
        filter_y = 50
        self.filter_rects: Dict[str, pygame.Rect] = {}
        for i, name in enumerate(self.filter_options):
            self.filter_rects[name] = pygame.Rect(
                self.center_rect.x + base_x + i * 90,
                self.center_rect.y + filter_y,
                80,
                25,
            )
        sort_y = filter_y + 35
        self.sort_rects: Dict[str, pygame.Rect] = {}
        for i, name in enumerate(self.sort_options):
            self.sort_rects[name] = pygame.Rect(
                self.center_rect.x + base_x + i * 90,
                self.center_rect.y + sort_y,
                80,
                25,
            )
        self.search_rect = pygame.Rect(
            self.center_rect.x + base_x, self.center_rect.y + sort_y + 35, 220, 26
        )
        self.grid_origin = (
            self.center_rect.x + base_x,
            self.center_rect.y + sort_y + 35 + 40,
        )

        # Skill school tab buttons (top of skills panel)
        self.skill_tab_buttons: Dict[str, pygame.Rect] = {}
        tab_w, tab_h = 90, 32
        sx = self.center_rect.x + 14
        sy = self.center_rect.y + 44
        for i, name in enumerate(self.SKILL_TABS):
            self.skill_tab_buttons[name] = pygame.Rect(
                sx + i * (tab_w + 8), sy, tab_w, tab_h
            )

    # ------------------------------------------------------------------ Drawing
    def _mouse_pos(self) -> Tuple[int, int]:
        """Return mouse position adjusted for the current panel offset."""
        if hasattr(pygame, "mouse") and hasattr(pygame.mouse, "get_pos"):
            x, y = pygame.mouse.get_pos()
        else:  # pragma: no cover - when pygame.mouse is unavailable
            x, y = 0, 0
        return x - self.offset[0], y - self.offset[1]

    def draw(self, flip: bool = True) -> None:
        self.screen.fill(theme.PALETTE.get("background", COLOR_BG))

        self._draw_tabs()
        self._draw_center_panel()
        self._draw_equipment_panel()
        self._draw_resbar()

        # context menu
        if self.context_menu:
            rect = self.context_menu["rect"]
            surf = pygame.Surface(rect.size, pygame.SRCALPHA)
            surf.fill((*constants.BLACK, 220))
            for i, option in enumerate(self.context_menu["options"]):
                text = self.font.render(option, True, COLOR_TEXT)
                surf.blit(text, (8, 6 + i * 22))
            self.screen.blit(surf, rect.topleft)

        # transient error
        if self.error_message and pygame.time.get_ticks() > self.error_timer:
            self.error_message = None
        if self.error_message:
            txt = self.font.render(self.error_message, True, COLOR_WARN)
            self.screen.blit(
                txt, (10, self.screen.get_height() - RESBAR_H - txt.get_height() - 6)
            )

        # drag visuals
        if self.drag_item:
            icon = self.assets.get(self.drag_item.icon)
            if icon:
                if self.drag_icon_size:
                    try:
                        icon = pygame.transform.scale(icon, self.drag_icon_size)
                    except (
                        AttributeError
                    ):  # pragma: no cover - transform missing in stub
                        pass
                pos = self._mouse_pos()
                self.screen.blit(
                    icon,
                    (pos[0] - icon.get_width() // 2, pos[1] - icon.get_height() // 2),
                )
        if self.drag_unit:
            txt = self.font.render(
                f"{self.drag_unit.stats.name} x{self.drag_unit.count}", True, COLOR_TEXT
            )
            pos = self._mouse_pos()
            self.screen.blit(
                txt, (pos[0] - txt.get_width() // 2, pos[1] - txt.get_height() // 2)
            )

        # tooltips last
        self._draw_tooltip()
        if flip:
            pygame.display.flip()

    # Panels ------------------------------------------------------------------
    def _panel(self, rect: pygame.Rect) -> None:
        pygame.draw.rect(self.screen, COLOR_PANEL, rect)

    def _draw_tabs(self) -> None:
        self._panel(self.tabs_rect)
        for name, btn in self.tab_buttons.items():
            btn.pressed = name == self.active_tab
            btn.draw(self.screen)

    def _draw_resbar(self) -> None:
        pygame.draw.rect(self.screen, (20, 20, 24), self.resbar_rect)
        x = self.resbar_rect.x + 12
        items = [("Gold", getattr(self.hero, "gold", 0))]
        items += [
            (res.title(), self.hero.resources.get(res, 0))
            for res in constants.RESOURCES
        ]
        for name, val in items:
            t = self.font.render(f"{name}: {val}", True, COLOR_TEXT)
            self.screen.blit(
                t,
                (
                    x,
                    self.resbar_rect.y
                    + (self.resbar_rect.height - t.get_height()) // 2,
                ),
            )
            x += t.get_width() + 28

    # Backwards compatibility for older tests expecting this name
    def _draw_resource_bar(self) -> None:  # pragma: no cover - simple alias
        self._draw_resbar()

    def _draw_equipment_panel(self) -> None:
        self._panel(self.equip_rect)
        font_big = self.font_big or self.font
        if font_big:
            title = font_big.render("Equipment", True, COLOR_TEXT)
            self.screen.blit(title, (self.equip_rect.x + 10, self.equip_rect.y + 8))

        mouse_pos = self._mouse_pos()
        for slot, rect in self.slot_rects.items():
            colour = COLOR_SLOT_BD
            item = self.hero.equipment.get(slot)
            if self.drag_item and rect.collidepoint(mouse_pos):
                colour = (
                    constants.GREEN if self.drag_item.slot == slot else constants.RED
                )
            elif item:
                colour = constants.RARITY_COLOURS.get(item.rarity, COLOR_SLOT_BD)

            try:
                pygame.draw.rect(self.screen, COLOR_SLOT_BG, rect, border_radius=6)
                pygame.draw.rect(self.screen, colour, rect, 2, border_radius=6)
            except TypeError:  # pragma: no cover - stub draw.rect
                pygame.draw.rect(self.screen, COLOR_SLOT_BG, rect)
                pygame.draw.rect(self.screen, colour, rect, 2)
            if item:
                icon = self.assets.get(item.icon)
                if icon:
                    icon = pygame.transform.scale(icon, rect.size)
                    self.screen.blit(icon, rect.topleft)

    # Legacy alias for tests
    def _draw_equipment(self) -> None:  # pragma: no cover
        self._draw_equipment_panel()

    def _draw_center_panel(self) -> None:
        self._panel(self.center_rect)
        if self.font_title:
            title = self.font_title.render(self.active_tab.title(), True, COLOR_TEXT)
            self.screen.blit(title, (self.center_rect.x + 12, self.center_rect.y + 10))

        if self.active_tab == "stats":
            self._draw_stats_content()
        elif self.active_tab == "inventory":
            self._draw_inventory_content()
        else:
            self._draw_skills_content()

    # Legacy alias expected by some tests
    def _draw_centre(self) -> None:  # pragma: no cover
        self._draw_center_panel()

    # Content: Stats ----------------------------------------------------------
    def _draw_stats_content(self) -> None:
        stats_tab.draw(self)

    # Content: Inventory ------------------------------------------------------
    def _filtered_inventory(self) -> List[Tuple[int, Item]]:
        return inv_tab.filtered_inventory(self)

    def _draw_inventory_content(self) -> None:
        inv_tab.draw(self)

    # Content: Skills ---------------------------------------------------------
    def _draw_skills_content(self) -> None:
        skills_tab.draw(self)

    # ------------------------------------------------------------------ Tooltips
    def _item_tooltip(
        self, item: Item, equip: bool = True
    ) -> List[Tuple[str, Tuple[int, int, int]]]:
        return inv_tab.item_tooltip(self, item, equip)

    def _skill_tooltip(self, node: SkillNode) -> List[Tuple[str, Tuple[int, int, int]]]:
        return skills_tab.skill_tooltip(self, node)

    def _draw_tooltip(self) -> None:
        if self.drag_item:
            return
        mouse = self._mouse_pos()
        lines: List[Tuple[str, Tuple[int, int, int]]] = []

        # Tab button tooltips have priority
        for btn in self.tab_buttons.values():
            if btn.collidepoint(mouse):
                lines = [(btn.get_tooltip(), COLOR_TEXT)]
                break

        if not lines:
            if self.active_tab == "inventory":
                for idx, rect in self.item_rects:
                    if idx is not None and rect.collidepoint(mouse):
                        lines = self._item_tooltip(self.hero.inventory[idx], equip=True)
                        break
            elif self.active_tab == "skills":
                for nid, r in self.skill_rects.items():
                    if r and r.collidepoint(mouse):
                        node = self.skill_nodes.get(nid)
                        if node:
                            lines = self._skill_tooltip(node)
                        break
            elif self.active_tab == "stats":
                for name, rect in self.stat_rects:
                    if rect.collidepoint(mouse):
                        lines = [(name, COLOR_TEXT)]
                        break
                if not lines:
                    for slot, rect in self.slot_rects.items():
                        if rect.collidepoint(mouse):
                            item = self.hero.equipment.get(slot)
                            if item:
                                lines = self._item_tooltip(item, equip=False)
                            else:
                                lines = [(slot.name.title(), COLOR_TEXT)]
                            break
            else:
                for slot, rect in self.slot_rects.items():
                    if rect.collidepoint(mouse):
                        item = self.hero.equipment.get(slot)
                        if item:
                            lines = self._item_tooltip(item, equip=False)
                        else:
                            lines = [(slot.name.title(), COLOR_TEXT)]
                        break

        if not lines:
            return
        font = self.font or theme.get_font(18)
        if not font:
            return
        texts = [font.render(t, True, c) for t, c in lines]
        w = max(t.get_width() for t in texts) + 10
        h = sum(t.get_height() for t in texts) + 10
        tip = pygame.Surface((w, h), pygame.SRCALPHA)
        tip.fill((*constants.BLACK, 220))
        y = 5
        for t in texts:
            tip.blit(t, (5, y))
            y += t.get_height()
        sx, sy = mouse
        sw, sh = self.screen.get_size()
        if sx + w > sw:
            sx -= w
        if sy + h > sh:
            sy -= h
        self.screen.blit(tip, (sx, sy))

    # ------------------------------------------------------------------ Events
    def run(self) -> Tuple[bool, pygame.Surface]:
        """Main event loop drawing the inventory as an overlay panel."""
        orig_screen = self.screen
        background = orig_screen.copy()
        sw, sh = orig_screen.get_size()
        pw, ph = int(sw * 0.8), int(sh * 0.8)
        panel_rect = pygame.Rect(0, 0, pw, ph)
        panel_rect.center = (sw // 2, sh // 2)
        panel = pygame.Surface(panel_rect.size)
        self.screen = panel
        self._recalc_layout()
        self.offset = panel_rect.topleft

        def restore(screen_obj: pygame.Surface = orig_screen) -> None:
            self.screen = screen_obj
            self.offset = (0, 0)
            self._recalc_layout()

        while True:
            for e in pygame.event.get():
                if e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_ESCAPE:
                        if self.open_pause_menu:
                            restore(orig_screen)
                            quit_to_menu, new_screen = self.open_pause_menu()
                            restore(new_screen)
                            return quit_to_menu, self.screen
                        restore()
                        return False, self.screen
                    if e.key == pygame.K_i:
                        restore()
                        return False, self.screen
                    if self.search_active:
                        if e.key == pygame.K_BACKSPACE:
                            self.search_text = self.search_text[:-1]
                            self.inventory_offset = 0
                        elif e.key == pygame.K_RETURN:
                            self.search_active = False
                        else:
                            if e.unicode and e.unicode.isprintable():
                                self.search_text += e.unicode
                                self.inventory_offset = 0
                        continue

                if e.type == pygame.MOUSEBUTTONDOWN:
                    pos = (e.pos[0] - panel_rect.x, e.pos[1] - panel_rect.y)
                    if e.button == 1:
                        # Tabs
                        for name, btn in self.tab_buttons.items():
                            if btn.collidepoint(pos):
                                btn.callback()
                                break
                        else:
                            # No tab clicked
                            if (
                                self.active_tab == "skills"
                                and self._check_skill_tab_click(pos)
                            ):
                                pass
                            else:
                                self._on_lmb_down(pos)
                    elif e.button == 3 and self.active_tab == "inventory":
                        for idx, rect in self.item_rects:
                            if idx is not None and rect.collidepoint(pos):
                                item = self.hero.inventory[idx]
                                opts = ["Equip", "Drop"]
                                if item.stackable and item.qty > 1:
                                    opts.append("Split")
                                self.context_menu = {
                                    "index": idx,
                                    "options": opts,
                                    "rect": pygame.Rect(
                                        pos[0], pos[1], 96, 24 * len(opts)
                                    ),
                                }
                                break
                    elif e.button in (4, 5) and self.active_tab == "inventory":
                        items = self._filtered_inventory()
                        if e.button == 4:
                            self.inventory_offset = max(0, self.inventory_offset - 16)
                        else:
                            max_off = max(0, len(items) - 16)
                            self.inventory_offset = min(
                                max_off, self.inventory_offset + 16
                            )

                elif e.type == pygame.MOUSEBUTTONUP and e.button == 1:
                    pos = (e.pos[0] - panel_rect.x, e.pos[1] - panel_rect.y)
                    self._on_lmb_up(pos)

            orig_screen.blit(background, (0, 0))
            dim = pygame.Surface(orig_screen.get_size(), pygame.SRCALPHA)
            dim.fill((*theme.PALETTE["background"], 200))
            orig_screen.blit(dim, (0, 0))
            self.draw(flip=False)
            orig_screen.blit(self.screen, panel_rect.topleft)
            pygame.draw.rect(
                orig_screen, theme.PALETTE["accent"], panel_rect, theme.FRAME_WIDTH
            )
            pygame.display.flip()
            self.clock.tick(constants.FPS)

        restore()
        return False, self.screen

    # -------------------------- Mouse helpers -------------------------------

    def _check_skill_tab_click(self, pos: Tuple[int, int]) -> bool:
        return skills_tab.check_tab_click(self, pos)

    def _on_lmb_down(self, pos: Tuple[int, int]) -> None:
        # Context menu selection?
        if self.context_menu:
            if self.context_menu["rect"].collidepoint(pos):
                idx = self.context_menu["index"]
                item = self.hero.inventory[idx]
                opt_idx = (pos[1] - self.context_menu["rect"].y) // 24
                option = self.context_menu["options"][opt_idx]
                if option == "Equip":
                    prev = self.hero.equipment.get(item.slot)
                    self.hero.equipment[item.slot] = item
                    del self.hero.inventory[idx]
                    if prev:
                        self.hero.inventory.append(prev)
                elif option == "Drop":
                    if item.locked:
                        self._toast("Item is locked")
                    else:
                        del self.hero.inventory[idx]
                elif option == "Split":
                    half = item.qty // 2
                    if half > 0:
                        item.qty -= half
                        self.hero.inventory.append(
                            Item(
                                id=item.id,
                                name=item.name,
                                slot=item.slot,
                                rarity=item.rarity,
                                icon=item.icon,
                                stackable=item.stackable,
                                qty=half,
                                modifiers=item.modifiers,
                                locked=item.locked,
                            )
                        )
                self.context_menu = None
                return
            else:
                self.context_menu = None

        if self.active_tab == "inventory":
            # Controls
            if hasattr(
                self.search_rect, "collidepoint"
            ) and self.search_rect.collidepoint(pos):
                self.search_active = True
                return
            self.search_active = False
            for name, r in self.filter_rects.items():
                if hasattr(r, "collidepoint") and r.collidepoint(pos):
                    self.active_filter = name
                    self.inventory_offset = 0
                    return
            for name, r in self.sort_rects.items():
                if hasattr(r, "collidepoint") and r.collidepoint(pos):
                    self.sort_mode = name
                    self.inventory_offset = 0
                    return
            # Pagination buttons
            if self.prev_page_rect and self.prev_page_rect.collidepoint(pos):
                self.inventory_offset = max(0, self.inventory_offset - 16)
                return
            if self.next_page_rect and self.next_page_rect.collidepoint(pos):
                items = self._filtered_inventory()
                max_off = max(0, len(items) - 16)
                self.inventory_offset = min(max_off, self.inventory_offset + 16)
                return
            # Start drag from bag grid
            gx, gy = self.inventory_grid_origin
            size = self.inventory_cell_size
            if size and gx <= pos[0] < gx + size * 4 and gy <= pos[1] < gy + size * 4:
                col = (pos[0] - gx) // size
                row = (pos[1] - gy) // size
                slot = row * 4 + col
                items = self._filtered_inventory()
                idx = self.inventory_offset + slot
                if idx < len(items):
                    inv_idx, item = items[idx]
                    key = ("bag", inv_idx)
                    now = pygame.time.get_ticks()
                    if (
                        self._last_click_slot == key
                        and now - self._last_click_time < DOUBLECLICK_MS
                    ):
                        InventoryInterface(self.hero).equip(item)
                        del self.hero.inventory[inv_idx]
                        self.drag_item = None
                        self.drag_origin = None
                        self.drag_icon_size = None
                        self._last_click_slot = None
                        self._last_click_time = 0
                        return
                    self._last_click_slot = key
                    self._last_click_time = now
                    self.drag_item = self.hero.inventory[inv_idx]
                    self.drag_origin = inv_idx
                    self.drag_icon_size = (size - 4, size - 4)
                    return
            for slot, r in self.slot_rects.items():
                if r.collidepoint(pos):
                    key = ("equip", slot)
                    now = pygame.time.get_ticks()
                    if (
                        self._last_click_slot == key
                        and now - self._last_click_time < DOUBLECLICK_MS
                    ):
                        if (
                            self.drag_item
                            and self.drag_origin is None
                            and self.hero.equipment.get(slot) is None
                        ):
                            self.hero.equipment[slot] = self.drag_item
                        InventoryInterface(self.hero).unequip(slot)
                        self.drag_item = None
                        self.drag_icon_size = None
                        self._last_click_slot = None
                        self._last_click_time = 0
                        return
                    self._last_click_slot = key
                    self._last_click_time = now
                    item = self.hero.equipment.get(slot)
                    if item:
                        self.drag_item = item
                        self.drag_origin = None
                        self.drag_icon_size = r.size
                        del self.hero.equipment[slot]
                    return
            self._last_click_slot = None
            self._last_click_time = 0
            return

        elif self.active_tab == "stats":
            for idx, rect in self.army_rects:
                if rect.collidepoint(pos):
                    unit = self.army_grid[idx]
                    if unit:
                        self.drag_unit = unit
                        self.drag_unit_origin = idx
                    return

        elif self.active_tab == "skills":
            # Left-click learn; right-click refund handled in mouse down/up split
            for nid, rect in self.skill_rects.items():
                if rect and rect.collidepoint(pos):
                    node = self.skill_nodes[nid]
                    branch = self.skill_branch_of.get(nid, "")
                    if not self.hero.learn_skill(node, branch):
                        self._toast("Cannot learn")
                    return

    def _on_lmb_up(self, pos: Tuple[int, int]) -> None:
        if self.drag_item is not None:
            placed = False
            for slot, rect in self.slot_rects.items():
                if rect.collidepoint(pos) and self.drag_item.slot == slot:
                    prev = self.hero.equipment.get(slot)
                    self.hero.equipment[slot] = self.drag_item
                    if self.drag_origin is not None:
                        del self.hero.inventory[self.drag_origin]
                    if prev:
                        self.hero.inventory.append(prev)
                    placed = True
                    break
            if not placed and self.drag_origin is None:
                # Dropped from equipment back to inventory
                self.hero.inventory.append(self.drag_item)
            self.drag_item = None
            self.drag_origin = None
            self.drag_icon_size = None
            return

        if self.drag_unit is not None:
            target = None
            for idx, rect in self.army_rects:
                if rect.collidepoint(pos):
                    target = idx
                    break
            if target is None:
                target = self.drag_unit_origin
            if target is not None and self.drag_unit_origin is not None:
                self.army_grid[self.drag_unit_origin], self.army_grid[target] = (
                    self.army_grid[target],
                    self.army_grid[self.drag_unit_origin],
                )
                self.hero.army = [u for u in self.army_grid if u]
            self.drag_unit = None
            self.drag_unit_origin = None
            return

        # Skills: right-click refund (safe if no dependent learned)
        if self.active_tab == "skills" and pygame.mouse.get_pressed()[2]:
            pos_now = self._mouse_pos()
            for nid, rect in self.skill_rects.items():
                if rect and rect.collidepoint(pos_now):
                    node = self.skill_nodes[nid]
                    branch = self.skill_branch_of.get(nid, "")
                    if self._can_refund(branch, nid):
                        self.hero.refund_skill(node, branch)
                    else:
                        self._toast("Cannot refund (dependent skills)")
                    break

    # ------------------------------------------------------------------ Helpers
    def _toast(self, msg: str, dur_ms: int = 1800) -> None:
        self.error_message = msg
        self.error_timer = pygame.time.get_ticks() + dur_ms

    def _dependents_of(self, tree: str, nid: str) -> Set[str]:
        return skills_tab.dependents_of(self, tree, nid)

    def _can_refund(self, tree: str, nid: str) -> bool:
        return skills_tab.can_refund(self, tree, nid)
