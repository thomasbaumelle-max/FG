from __future__ import annotations
from typing import Optional, List, Dict, Tuple
import os
import logging
import pygame
from core import economy
from loaders import icon_loader as IconLoader
from . import market_screen
from core.entities import (
    Hero,
    HeroStats,
    Unit,
    UnitStats,
    SWORDSMAN_STATS,
    ARCHER_STATS,
    RECRUITABLE_UNITS,
    Army,
)

# ---------------------------------------------------------------------------

SLOT_COUNT = 7
SLOT_PAD = 6
ROW_H = 96
RESBAR_H = 36
TOPBAR_H = 40
GAP = 10

CARD_W = 220
CARD_H = 160
CARD_GAP = 12

FONT_NAME = None

COLOR_BG = (16, 18, 22)
COLOR_PANEL = (28, 30, 36)
COLOR_ACCENT = (210, 180, 80)
COLOR_TEXT = (240, 240, 240)
COLOR_DISABLED = (120, 120, 120)
COLOR_OK = (80, 190, 80)
COLOR_WARN = (210, 90, 70)
COLOR_SLOT_BG = (36, 38, 44)
COLOR_SLOT_BD = (80, 80, 90)

# ---------------------------------------------------------------------------

logger = logging.getLogger(__name__)

class TownScreen:
    def __init__(
        self,
        screen: pygame.Surface,
        game: "Game",
        town: "Town",
        army: Optional["Army"] = None,
        clock: Optional[pygame.time.Clock] = None,
        town_pos: Optional[Tuple[int, int]] = None,
    ) -> None:
        self.screen = screen
        self.game = game
        self.town = town
        self.hero = game.hero
        self.clock = clock or pygame.time.Clock()
        self.running = True
        self.town_pos = town_pos or (0, 0)
        if self.town_pos == (0, 0):
            logger.warning(
                "TownScreen initialised with default town_pos (0, 0); check caller"
            )
        self.army_obj: Optional[object] = army
        if army is not None:
            self.army_units = getattr(army, "units", getattr(army, "army", []))
        else:
            tx, ty = self.town_pos
            if abs(self.hero.x - tx) <= 1 and abs(self.hero.y - ty) <= 1:
                self.army_obj = self.hero
                self.army_units = self.hero.army
            else:
                self.army_units = []


        self.font = pygame.font.SysFont(FONT_NAME, 18)
        self.font_small = pygame.font.SysFont(FONT_NAME, 14)
        self.font_big = pygame.font.SysFont(FONT_NAME, 20, bold=True)

        self._res_icons = ["gold", "wood", "stone", "crystal"]

        self.building_images: Dict[str, Optional[pygame.Surface]] = {}
        max_w = CARD_W - 20
        max_h = CARD_H - 70
        for sid, info in self.town.structures.items():
            path = info.get("image") if isinstance(info, dict) else None
            surf: Optional[pygame.Surface] = None
            if path:
                try:
                    surf = pygame.image.load(os.path.join("assets", path)).convert_alpha()
                    w, h = surf.get_size()
                    scale = min(max_w / w, max_h / h, 1.0)
                    new_size = (int(w * scale), int(h * scale))
                    surf = pygame.transform.smoothscale(surf, new_size)
                except Exception:
                    surf = None
            self.building_images[sid] = surf

        # zones interactives
        self.hero_slots: List[pygame.Rect] = []
        self.garrison_slots: List[pygame.Rect] = []
        self.building_cards: List[Tuple[str, pygame.Rect]] = []
        self.building_scroll = 0

        # Drag & Drop
        self.drag_active = False
        self.drag_src = ("", -1)  # ("hero"/"garrison", index)
        self.drag_unit = None
        self.drag_offset = (0, 0)
        self.mouse_pos = (0, 0)
        self.tooltip: Optional[str] = None

        # Overlays
        self.recruit_open = False
        self.recruit_struct: Optional[str] = None
        self.recruit_unit: Optional[str] = None
        self.recruit_count = 1
        self.recruit_max = 0
        self.recruit_rect = pygame.Rect(0, 0, 360, 190)
        self.recruit_portrait: Optional[pygame.Surface] = None
        self.recruit_stats: Optional[UnitStats] = None
        self.btn_min = pygame.Rect(0, 0, 28, 28)
        self.btn_minus = pygame.Rect(0, 0, 28, 28)
        self.btn_plus = pygame.Rect(0, 0, 28, 28)
        self.btn_max = pygame.Rect(0, 0, 28, 28)
        self.slider_rect = pygame.Rect(0, 0, 72, 8)
        self.btn_buy = pygame.Rect(0, 0, 120, 32)
        self.btn_close = pygame.Rect(0, 0, 24, 24)

        self.market_open = False
        self.market_rect = pygame.Rect(0, 0, 420, 220)
        self.market_from = "gold"
        self.market_to = "wood"
        self.market_amount = 1
        self.market_btn_do = pygame.Rect(0, 0, 120, 32)

        self.castle_open = False
        self.castle_rect = pygame.Rect(0, 0, 860, 520)  # grand panneau
        self.castle_unit_cards: List[Tuple[str, pygame.Rect]] = []  # (unit_id, rect)

        self.tavern_open = False
        self.tavern_rect = pygame.Rect(0, 0, 420, 260)
        self.tavern_cards: List[Tuple[int, pygame.Rect]] = []
        self.tavern_msg = ""
        self.tavern_heroes = [
            {
                "name": "Bran",
                "cost": 1500,
                "stats": HeroStats(1, 1, 0, 0, 0, 0, 0, 0, 0),
                "army": [Unit(SWORDSMAN_STATS, 10, "hero")],
            },
            {
                "name": "Luna",
                "cost": 2500,
                "stats": HeroStats(0, 0, 1, 1, 0, 0, 0, 0, 0),
                "army": [Unit(ARCHER_STATS, 10, "hero")],
            },
        ]
        # Sélection des unités à envoyer en caravane
        self.send_queue: List[Unit] = []

    def launch_caravan(self, dest: "Town", units: Optional[List["Unit"]] = None) -> bool:
        """Envoyer une caravane depuis cette ville vers ``dest``.

        Quand ``units`` est ``None``, toutes les unités de la garnison sont
        envoyées.  La méthode renvoie ``True`` si une caravane a été créée.
        """

        if units is None:
            units = list(self.town.garrison)
        if not units:
            return False
        world = getattr(self.game, "world", None)
        return self.town.send_caravan(dest, units, world)

    def select_unit(self, index: int) -> None:
        """(Dé)sélectionner une unité de la garnison pour une future caravane.

        Les sélections sont accumulées dans :attr:`send_queue` afin de pouvoir
        lancer l'envoi plus tard via :meth:`send_queued_caravan`.
        """

        if 0 <= index < len(self.town.garrison):
            unit = self.town.garrison[index]
            if unit in self.send_queue:
                self.send_queue.remove(unit)
            else:
                self.send_queue.append(unit)

    def send_queued_caravan(self, dest: "Town") -> bool:
        """Envoyer les unités actuellement sélectionnées vers ``dest``.

        La file est vidée uniquement si la caravane est créée avec succès.
        """

        if not self.send_queue:
            return False
        units = list(self.send_queue)
        if self.launch_caravan(dest, units):
            self.send_queue.clear()
            return True
        return False

    # ------------------------------------------------------------------ utils
    def _compute_layout(self) -> Dict[str, pygame.Rect]:
        W, H = self.screen.get_size()
        rects: Dict[str, pygame.Rect] = {}
        rects["top_bar"] = pygame.Rect(0, 0, W, TOPBAR_H)
        rects["resbar"] = pygame.Rect(0, H - RESBAR_H, W, RESBAR_H)
        rects["hero_row"] = pygame.Rect(20, H - RESBAR_H - GAP - ROW_H, W - 40, ROW_H)
        rects["garrison_row"] = pygame.Rect(20, rects["hero_row"].y - GAP - ROW_H, W - 40, ROW_H)
        rects["center"] = pygame.Rect(20, TOPBAR_H + 20, W - 40, rects["garrison_row"].y - (TOPBAR_H + 30))
        return rects

    def _resources_dict(self) -> Dict[str, int]:
        return {
            "gold": getattr(self.hero, "gold", 0),
            "wood": self.hero.resources.get("wood", 0),
            "stone": self.hero.resources.get("stone", 0),
            "crystal": self.hero.resources.get("crystal", 0),
        }

    def _advance_week(self) -> None:
        state = getattr(self.game, "state", None)
        econ_state = getattr(state, "economy", None) if state else None
        if econ_state is not None:
            economy.advance_week(econ_state)
        if hasattr(self.town, "next_week"):
            self.town.next_week()
        notify = getattr(self.game, "_notify", None)
        if notify:
            notify("A new week begins.")

    # ----------------------------------------------------------------- drawing
    def draw(self) -> None:
        self.screen.fill(COLOR_BG)
        R = self._compute_layout()
        self.tooltip = None
        pygame.draw.rect(self.screen, COLOR_PANEL, R["top_bar"])
        pygame.draw.rect(self.screen, COLOR_PANEL, R["garrison_row"])
        pygame.draw.rect(self.screen, COLOR_PANEL, R["hero_row"])
        self._draw_label(self.town.name, pygame.Rect(R["top_bar"].x + 20, R["top_bar"].y + 8, 0, 0))
        self._draw_label("Garrison", R["garrison_row"].inflate(-8, -ROW_H + 24).move(8, 4))
        self._draw_label("Visiting Hero", R["hero_row"].inflate(-8, -ROW_H + 24).move(8, 4))

        self.garrison_slots = self._draw_army_row(self.town.garrison, R["garrison_row"])
        self.hero_slots = self._draw_army_row(self.army_units, R["hero_row"])

        self._draw_buildings_panel(R["center"])

        self._draw_resbar(R["resbar"])

        # overlays
        if self.recruit_open:
            self._draw_recruit_overlay()
        if self.market_open:
            self._draw_market_overlay()
        if self.castle_open:
            self._draw_castle_overlay()
        if self.tavern_open:
            self._draw_tavern_overlay()

        # tooltip detection for buildings when no overlay open
        if not self._overlay_active():
            for sid, rc in self.building_cards:
                if (
                    rc.collidepoint(self.mouse_pos)
                    and not self.town.is_structure_built(sid)
                    and not self.town.built_today
                ):
                    cost = self.town.structure_cost(sid)
                    if cost and not self._can_afford(self.hero, cost):
                        self.tooltip = self._format_cost_tooltip(cost)
                    break
        else:
            if self.recruit_open and self.btn_buy.collidepoint(self.mouse_pos):
                cost = self._unit_cost(self.recruit_unit, self.recruit_count)
                if cost and not self._can_afford(self.hero, cost):
                    self.tooltip = self._format_cost_tooltip(cost)

        self._draw_tooltip()

        # drag ghost
        if self.drag_active and self.drag_unit:
            mx, my = self.mouse_pos
            gx, gy = mx - self.drag_offset[0], my - self.drag_offset[1]
            ghost = pygame.Rect(gx, gy, 140, 64)
            pygame.draw.rect(self.screen, (60, 64, 80, 230), ghost, border_radius=6)
            pygame.draw.rect(self.screen, (120, 120, 140), ghost, 2, border_radius=6)
            name = getattr(self.drag_unit.stats, "name", "Unit")
            cnt = getattr(self.drag_unit, "count", 1)
            self.screen.blit(self.font.render(name, True, COLOR_TEXT), (ghost.x + 8, ghost.y + 8))
            self.screen.blit(self.font_small.render(f"x{cnt}", True, COLOR_ACCENT), (ghost.x + 8, ghost.y + 34))

    def _draw_resbar(self, rect: pygame.Rect) -> None:
        pygame.draw.rect(self.screen, (20, 20, 24), rect)
        x = rect.x + 12
        y_center = rect.y + rect.height // 2
        for key in self._res_icons:
            val = self._resources_dict().get(key, 0)
            icon = IconLoader.get(f"resource_{key}", 36)
            self.screen.blit(icon, (x, y_center - icon.get_height() // 2))
            x += icon.get_width() + 4
            txt = self.font.render(str(val), True, COLOR_TEXT)
            self.screen.blit(txt, (x, y_center - txt.get_height() // 2))
            x += txt.get_width() + 28

    def _draw_label(self, text: str, rect: pygame.Rect) -> None:
        self.screen.blit(self.font_big.render(text, True, COLOR_TEXT), (rect.x, rect.y))

    def _draw_army_row(self, army, rect: pygame.Rect) -> List[pygame.Rect]:
        slots: List[pygame.Rect] = []
        w = (rect.width - (SLOT_COUNT + 1) * SLOT_PAD) // SLOT_COUNT
        h = rect.height - 2 * SLOT_PAD
        y = rect.y + SLOT_PAD
        x = rect.x + SLOT_PAD
        for i in range(SLOT_COUNT):
            r = pygame.Rect(x, y, w, h)
            slots.append(r)
            pygame.draw.rect(self.screen, COLOR_SLOT_BG, r, border_radius=6)
            pygame.draw.rect(self.screen, COLOR_SLOT_BD, r, 2, border_radius=6)
            if i < len(army):
                u = army[i]
                name = getattr(u.stats, "name", "Unit")
                count = getattr(u, "count", 1)
                self.screen.blit(self.font.render(name, True, COLOR_TEXT), (r.x + 6, r.y + 6))
                self.screen.blit(self.font_small.render(f"x{count}", True, COLOR_ACCENT),
                                 (r.right - 28, r.bottom - 20))
            x += w + SLOT_PAD
        return slots

    def _draw_buildings_panel(self, rect: pygame.Rect) -> None:
        pygame.draw.rect(self.screen, (26, 28, 34), rect)
        cols = max(3, min(4, rect.width // (CARD_W + CARD_GAP)))
        order = getattr(self.town, "ui_order", list(self.town.structures.keys()))

        total_rows = (len(order) + cols - 1) // cols
        content_h = CARD_GAP + total_rows * (CARD_H + CARD_GAP)
        min_scroll = min(0, rect.height - content_h)
        if self.building_scroll > 0:
            self.building_scroll = 0
        if self.building_scroll < min_scroll:
            self.building_scroll = min_scroll

        self.screen.set_clip(rect)
        x = rect.x + CARD_GAP
        y = rect.y + CARD_GAP + self.building_scroll
        self.building_cards = []
        for idx, sid in enumerate(order):
            card = pygame.Rect(x, y, CARD_W, CARD_H)
            if rect.contains(card):
                self._draw_building_card(sid, card)
                self.building_cards.append((sid, card))
            if (idx + 1) % cols == 0:
                x = rect.x + CARD_GAP
                y += CARD_H + CARD_GAP
            else:
                x += CARD_W + CARD_GAP

        if self.building_scroll < 0:
            pygame.draw.polygon(
                self.screen,
                COLOR_ACCENT,
                [
                    (rect.centerx, rect.y + 6),
                    (rect.centerx - 10, rect.y + 16),
                    (rect.centerx + 10, rect.y + 16),
                ],
            )
        if self.building_scroll > min_scroll:
            pygame.draw.polygon(
                self.screen,
                COLOR_ACCENT,
                [
                    (rect.centerx, rect.bottom - 6),
                    (rect.centerx - 10, rect.bottom - 16),
                    (rect.centerx + 10, rect.bottom - 16),
                ],
            )
        self.screen.set_clip(None)

    def _draw_building_card(self, sid: str, card: pygame.Rect) -> None:
        built = self.town.is_structure_built(sid)
        locked = not built and self.town.built_today
        pygame.draw.rect(self.screen, (44, 46, 54), card, border_radius=8)
        pygame.draw.rect(self.screen, (100, 100, 110), card, 2, border_radius=8)
        title = sid.replace("_", " ").title()
        self.screen.blit(self.font_big.render(title, True, COLOR_TEXT), (card.x + 10, card.y + 8))
        img = self.building_images.get(sid)
        desc_y = card.y + 36
        if img:
            rect = img.get_rect()
            rect.center = (card.x + CARD_W / 2, card.y + 74)
            self.screen.blit(img, rect)
            desc_y = rect.bottom + 4
        desc = self.town.structures.get(sid, {}).get("desc", "")
        if desc:
            self._blit_wrapped(self.font_small, desc, (card.x + 10, desc_y), card.width - 20, COLOR_TEXT)

        if built:
            lab = self.font.render("Built", True, COLOR_OK)
            self.screen.blit(lab, (card.x + 10, card.bottom - 28))
            units = self.town.recruitable_units(sid)
            counts = self.town.available_units(sid)
            if counts:
                stock_txt = " / ".join(f"{k}:{v}" for k, v in counts.items())
                self.screen.blit(self.font_small.render(stock_txt, True, COLOR_TEXT), (card.x + 10, card.bottom - 44))
            hint_text = None
            if sid == "market":
                hint_text = "Click to trade"
            elif sid == "castle":
                hint_text = "Manage all recruits"
            elif sid == "tavern":
                hint_text = "Hire hero"
            elif sid == "bounty_board":
                hint_text = "View quests"
            elif sid == "magic_school":
                hint_text = "Study spells"
            elif units:
                hint_text = "Click to recruit"
            if hint_text:
                hint = self.font_small.render(hint_text, True, COLOR_ACCENT)
                self.screen.blit(hint, (card.right - hint.get_width() - 8, card.bottom - 24))
        elif locked:
            lab = self.font.render("Locked", True, COLOR_DISABLED)
            self.screen.blit(lab, (card.x + 10, card.bottom - 24))
        else:
            cost = self.town.structure_cost(sid)
            cost_txt = " / ".join(f"{k}:{v}" for k, v in cost.items()) if cost else "Free"
            col = COLOR_TEXT if self._can_afford(self.hero, cost) else COLOR_DISABLED
            self.screen.blit(self.font_small.render(f"Cost: {cost_txt}", True, col), (card.x + 10, card.bottom - 24))

    def _blit_wrapped(self, font: pygame.font.Font, text: str, topleft: Tuple[int,int], max_w: int, color) -> None:
        words = text.split()
        x, y = topleft
        line = ""
        for w in words:
            test = (line + " " + w).strip()
            if font.size(test)[0] <= max_w:
                line = test
            else:
                if line:
                    self.screen.blit(font.render(line, True, color), (x, y))
                y += font.get_linesize()
                line = w
        if line:
            self.screen.blit(font.render(line, True, color), (x, y))

    # ------------------------------------------------------------- interactions
    def run(self) -> None:
        while self.running:
            for evt in pygame.event.get():
                t = getattr(evt, "type", None)
                if t == pygame.QUIT:
                    self.running = False
                elif t == pygame.KEYDOWN:
                    if evt.key in (pygame.K_ESCAPE, pygame.K_b):
                        self._close_all_overlays()
                        self.running = False
                    elif evt.key == pygame.K_w and not self._overlay_active():
                        self._advance_week()
                elif t == pygame.MOUSEMOTION:
                    self.mouse_pos = evt.pos
                elif t == pygame.MOUSEWHEEL:
                    if not self._overlay_active():
                        self.building_scroll += evt.y * 20
                elif t == pygame.MOUSEBUTTONDOWN:
                    self._on_mousedown(evt.pos, evt.button)
                elif t == pygame.MOUSEBUTTONUP:
                    self._on_mouseup(evt.pos, evt.button)

            self.draw()
            pygame.display.flip()
            self.clock.tick(60)

    def _on_mousedown(self, pos: Tuple[int,int], button: int) -> None:
        if self._overlay_active():
            self._on_overlay_mousedown(pos, button)
            return

        # DRAG start?
        for i, r in enumerate(self.hero_slots):
            if r.collidepoint(pos) and i < len(self.army_units):
                self.drag_active = True
                self.drag_src = ("hero", i)
                self.drag_unit = self.army_units[i]
                self.drag_offset = (pos[0] - r.x, pos[1] - r.y)
                return
        for i, r in enumerate(self.garrison_slots):
            if r.collidepoint(pos) and i < len(self.town.garrison):
                self.drag_active = True
                self.drag_src = ("garrison", i)
                self.drag_unit = self.town.garrison[i]
                self.drag_offset = (pos[0] - r.x, pos[1] - r.y)
                return

        # Cards click
        for sid, rc in self.building_cards:
            if rc.collidepoint(pos):
                if not self.town.is_structure_built(sid):
                    if self.town.built_today:
                        return
                    cost = self.town.structure_cost(sid)
                    if self._can_afford(self.hero, cost):
                        self.town.build_structure(sid, self.hero)
                        self._publish_resources()
                else:
                    if sid == "market":
                        market_screen.open(self.screen, self.game, self.town, self.hero, self.clock)
                    elif sid == "castle":
                        self._open_castle_overlay()
                    elif sid == "tavern":
                        self._open_tavern_overlay()
                    elif sid == "bounty_board":
                        self._open_bounty_overlay()
                    elif sid == "magic_school":
                        self._open_spellbook_overlay()
                    else:
                        units = self.town.recruitable_units(sid)
                        if units:
                            self._open_recruit_overlay(sid, units[0])
                return

    def _on_mouseup(self, pos: Tuple[int,int], button: int) -> None:
        if self._overlay_active():
            self._on_overlay_mouseup(pos, button)
            return
        if not self.drag_active or not self.drag_unit:
            return
        # drop target?
        dropped = False
        for i, r in enumerate(self.hero_slots):
            if r.collidepoint(pos):
                dropped = True
                self._drop_to("hero", i)
                break
        if not dropped:
            for i, r in enumerate(self.garrison_slots):
                if r.collidepoint(pos):
                    dropped = True
                    self._drop_to("garrison", i)
                    break
        # cancel drag
        self.drag_active = False
        self.drag_unit = None
        self.drag_src = ("", -1)

    def _drop_to(self, target_row: str, index: int) -> None:
        src_row, src_idx = self.drag_src
        if src_row not in ("hero", "garrison") or src_idx < 0:
            return
        if target_row == src_row and index == src_idx:
            return
        src_list = self.army_units if src_row == "hero" else self.town.garrison
        dst_list = self.army_units if target_row == "hero" else self.town.garrison
        if index > SLOT_COUNT - 1:
            index = SLOT_COUNT - 1
        unit = src_list[src_idx]
        merge_target = None
        for u in dst_list:
            if dst_list is src_list and u is unit:
                continue
            if u.stats is unit.stats:
                merge_target = u
                break
        if merge_target:
            merge_target.count += unit.count
            src_list.pop(src_idx)
            if src_row == "hero" or target_row == "hero":
                if self.army_obj is self.hero:
                    self.hero.apply_bonuses_to_army()
            if isinstance(self.army_obj, Army):
                self.army_obj.update_portrait()
            return
        if len(dst_list) < SLOT_COUNT:
            unit = src_list.pop(src_idx)
            if target_row == src_row and src_idx < index:
                index -= 1
            if index <= len(dst_list):
                dst_list.insert(index, unit)
            else:
                dst_list.append(unit)
        else:
            dst_list[index], src_list[src_idx] = src_list[src_idx], dst_list[index]
        if src_row == "hero" or target_row == "hero":
            if self.army_obj is self.hero:
                self.hero.apply_bonuses_to_army()
        if self.army_obj is None and self.army_units:
            new_army = Army(
                self.town_pos[0],
                self.town_pos[1],
                self.army_units,
                ap=self.game.hero.max_ap,
            )
            new_army.update_portrait()
            self.game.world.player_armies.append(new_army)
            self.army_obj = new_army
            heroes = getattr(self.game.state, "heroes", [])
            self.game.main_screen.hero_list.set_heroes(
                list(heroes) + self.game.world.player_armies
            )
            if hasattr(self.game, "_update_player_visibility"):
                self.game._update_player_visibility(new_army)
        elif isinstance(self.army_obj, Army):
            if self.army_units:
                self.army_obj.update_portrait()
            else:
                try:
                    self.game.world.player_armies.remove(self.army_obj)
                except ValueError:
                    pass
                self.army_obj = None
                heroes = getattr(self.game.state, "heroes", [])
                self.game.main_screen.hero_list.set_heroes(
                    list(heroes) + self.game.world.player_armies
                )
        if hasattr(self.game, "refresh_army_list"):
            self.game.refresh_army_list()

    # ------------------------------------------------------- recruit overlay UI
    def _open_recruit_overlay(self, struct_id: str, unit_id: str) -> None:
        self.recruit_open = True
        self.recruit_struct = struct_id
        self.recruit_unit = unit_id
        self.recruit_max = self.town.stock.get(unit_id, 0)
        self.recruit_count = min(1, self.recruit_max)
        portrait_path = os.path.join(
            "assets",
            "units",
            "portrait",
            f"{unit_id.lower()}_portrait.png",
        )
        try:
            self.recruit_portrait = pygame.image.load(portrait_path).convert_alpha()
        except Exception:
            self.recruit_portrait = None
        self.recruit_stats = RECRUITABLE_UNITS.get(unit_id)
        W, H = self.screen.get_size()
        self.recruit_rect.center = (W // 2, H // 2)
        y = self.recruit_rect.y + self.recruit_rect.height - 44
        x = self.recruit_rect.x + 16
        self.btn_min.topleft = (x, y)
        self.btn_minus.topleft = (x + 32, y)
        self.slider_rect.topleft = (x + 64, y + 10)
        self.btn_plus.topleft = (self.slider_rect.right + 8, y)
        self.btn_max.topleft = (self.btn_plus.right + 4, y)
        self.btn_buy.topleft = (self.recruit_rect.right - self.btn_buy.width - 16, y)
        self.btn_close.topleft = (self.recruit_rect.right - 28, self.recruit_rect.y + 8)

    def _draw_recruit_overlay(self) -> None:
        s = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        s.fill((0, 0, 0, 160))
        self.screen.blit(s, (0, 0))
        r = self.recruit_rect
        pygame.draw.rect(self.screen, (40, 42, 50), r, border_radius=8)
        pygame.draw.rect(self.screen, (110, 110, 120), r, 2, border_radius=8)
        title = f"Recruit {self.recruit_unit} – {self.recruit_struct.replace('_',' ').title()}"
        self.screen.blit(self.font_big.render(title, True, COLOR_TEXT), (r.x + 16, r.y + 12))
        portrait_rect = pygame.Rect(r.x + 16, r.y + 40, 72, 72)
        if self.recruit_portrait:
            portrait = self.recruit_portrait
            if portrait.get_size() != (72, 72):
                portrait = pygame.transform.scale(portrait, (72, 72))
            self.screen.blit(portrait, portrait_rect)
        else:
            pygame.draw.rect(self.screen, (70, 72, 84), portrait_rect)
        st = self.recruit_stats
        if st:
            lines = [
                f"HP {st.max_hp}",
                f"DMG {st.attack_min}-{st.attack_max}",
                f"DEF M/R/Mg {st.defence_melee}/{st.defence_ranged}/{st.defence_magic}",
                f"SPD {st.speed}  INIT {st.initiative}",
            ]
            yy = portrait_rect.y
            for line in lines:
                self.screen.blit(self.font_small.render(line, True, COLOR_TEXT), (portrait_rect.right + 10, yy))
                yy += 18
        cost = self._unit_cost(self.recruit_unit, self.recruit_count)
        cost_str = " / ".join(f"{k}:{v}" for k, v in cost.items()) if cost else "Free"
        can_afford = self._can_afford(self.hero, cost)
        col = COLOR_TEXT if can_afford else COLOR_WARN
        self.screen.blit(
            self.font.render(f"Cost x{self.recruit_count}: {cost_str}", True, col),
            (r.x + 16, r.y + 120),
        )
        pygame.draw.rect(self.screen, (60, 62, 72), self.btn_min, border_radius=4)
        pygame.draw.rect(self.screen, (60, 62, 72), self.btn_minus, border_radius=4)
        pygame.draw.rect(self.screen, (60, 62, 72), self.slider_rect, border_radius=4)
        if self.recruit_max > 0:
            filled = int(self.slider_rect.width * self.recruit_count / self.recruit_max)
            pygame.draw.rect(
                self.screen,
                (80, 160, 80),
                pygame.Rect(self.slider_rect.x, self.slider_rect.y, filled, self.slider_rect.height),
                border_radius=4,
            )
        pygame.draw.rect(self.screen, (60, 62, 72), self.btn_plus, border_radius=4)
        pygame.draw.rect(self.screen, (60, 62, 72), self.btn_max, border_radius=4)
        btn_col = (70, 140, 70) if self.recruit_count > 0 and can_afford else COLOR_DISABLED
        pygame.draw.rect(self.screen, btn_col, self.btn_buy, border_radius=4)
        self.screen.blit(self.font_small.render("min", True, COLOR_TEXT), (self.btn_min.x + 3, self.btn_min.y + 5))
        self.screen.blit(self.font_big.render("-", True, COLOR_TEXT), (self.btn_minus.x + 8, self.btn_minus.y + 2))
        self.screen.blit(self.font_big.render("+", True, COLOR_TEXT), (self.btn_plus.x + 6, self.btn_plus.y + 2))
        self.screen.blit(self.font_small.render("max", True, COLOR_TEXT), (self.btn_max.x + 2, self.btn_max.y + 5))
        self.screen.blit(self.font_big.render("Recruit", True, COLOR_TEXT), (self.btn_buy.x + 12, self.btn_buy.y + 2))
        pygame.draw.rect(self.screen, (90, 50, 50), self.btn_close, border_radius=4)
        self.screen.blit(self.font.render("x", True, COLOR_TEXT), (self.btn_close.x + 7, self.btn_close.y + 3))

    def _on_overlay_mousedown(self, pos: Tuple[int,int], button: int) -> None:
        if self.recruit_open:
            if self.btn_close.collidepoint(pos):
                self.recruit_open = False
                return
            if self.btn_min.collidepoint(pos):
                self.recruit_count = 0
                return
            if self.btn_minus.collidepoint(pos):
                self.recruit_count = max(0, self.recruit_count - 1)
                return
            if self.btn_plus.collidepoint(pos):
                self.recruit_count = min(self.recruit_max, self.recruit_count + 1)
                return
            if self.btn_max.collidepoint(pos):
                self.recruit_count = self.recruit_max
                return
            if self.slider_rect.collidepoint(pos) and self.slider_rect.width > 0 and self.recruit_max > 0:
                ratio = (pos[0] - self.slider_rect.x) / self.slider_rect.width
                self.recruit_count = max(0, min(self.recruit_max, int(self.recruit_max * ratio + 0.5)))
                return
            if self.btn_buy.collidepoint(pos) and self.recruit_unit:
                cost = self._unit_cost(self.recruit_unit, self.recruit_count)
                if self.recruit_count > 0 and self._can_afford(self.hero, cost):
                    target_units = (
                        getattr(self.army_obj, "units", self.town.garrison)
                        if self.army_obj is not None and self.army_obj is not self.hero
                        else self.town.garrison
                    )
                    if self.town.recruit_units(
                        self.recruit_unit,
                        self.hero,
                        self.recruit_count,
                        target_units,
                    ):
                        if getattr(self.army_obj, "apply_bonuses_to_army", None):
                            self.army_obj.apply_bonuses_to_army()  # type: ignore[attr-defined]
                        self._publish_resources()
                        self.recruit_open = False
            return
        if self.market_open:
            self._market_click(pos); return
        if self.castle_open:
            # clic sur une carte unité → ouvrir mini-recrutement
            for uid, rc in self.castle_unit_cards:
                if rc.collidepoint(pos):
                    self._open_recruit_overlay("castle", uid)
                    break
            return
        if self.tavern_open:
            self._tavern_click(pos)
            return

    def _on_overlay_mouseup(self, pos: Tuple[int,int], button: int) -> None:
        pass

    def _unit_cost(self, unit_id: str, count: int) -> Dict[str, int]:
        try:
            import constants
            base = dict(getattr(constants, "UNIT_RECRUIT_COSTS", {}).get(unit_id, {}))
        except Exception:
            base = {}
        return {k: v * count for k, v in base.items()}

    @staticmethod
    def _can_afford(hero: "Hero", cost: Dict[str, int]) -> bool:
        g = cost.get("gold", 0)
        if hero.gold < g: return False
        for k, v in cost.items():
            if k == "gold": continue
            if hero.resources.get(k, 0) < v: return False
        return True

    def _format_cost_tooltip(self, cost: Dict[str, int]) -> str:
        parts = []
        for res in ["gold", "wood", "stone", "crystal"]:
            if res in cost:
                parts.append(f"{res}:{cost[res]}")
        return "Requires " + ", ".join(parts)

    def _draw_tooltip(self) -> None:
        if not self.tooltip:
            return
        tip = self.tooltip
        surf = self.font_small.render(tip, True, COLOR_TEXT)
        rect = surf.get_rect()
        rect.topleft = (self.mouse_pos[0] + 12, self.mouse_pos[1] + 12)
        bg = rect.inflate(8, 8)
        pygame.draw.rect(self.screen, (0, 0, 0, 180), bg)
        pygame.draw.rect(self.screen, (110, 110, 120), bg, 1)
        self.screen.blit(surf, rect)

    def _publish_resources(self) -> None:
        if hasattr(self.game, "_publish_resources"):
            self.game._publish_resources()

    def _overlay_active(self) -> bool:
        return (
            self.recruit_open
            or self.market_open
            or self.castle_open
            or self.tavern_open
        )

    def _close_all_overlays(self) -> None:
        self.recruit_open = False
        self.market_open = False
        self.castle_open = False
        self.tavern_open = False

    # ------------------------------------------------------------ Market overlay
    def _open_market_overlay(self) -> None:
        self.market_open = True
        W, H = self.screen.get_size()
        self.market_rect.center = (W // 2, H // 2)
        self.market_btn_do.topleft = (self.market_rect.right - 140, self.market_rect.bottom - 44)

    def _draw_market_overlay(self) -> None:
        s = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        s.fill((0, 0, 0, 160)); self.screen.blit(s, (0, 0))
        r = self.market_rect
        pygame.draw.rect(self.screen, (40, 42, 50), r, border_radius=8)
        pygame.draw.rect(self.screen, (110, 110, 120), r, 2, border_radius=8)

        self.screen.blit(self.font_big.render("Market – Trade Resources", True, COLOR_TEXT), (r.x + 16, r.y + 12))

        # simple UI: deux listes déroulantes "from"/"to" simulées par cycles par clic
        opts = ["gold", "wood", "stone", "crystal"]
        # boutons pour cycler
        btn_from = pygame.Rect(r.x + 24, r.y + 60, 160, 28)
        btn_to   = pygame.Rect(r.x + 24, r.y + 100, 160, 28)
        pygame.draw.rect(self.screen, (60, 62, 72), btn_from, border_radius=4)
        pygame.draw.rect(self.screen, (60, 62, 72), btn_to, border_radius=4)
        self.screen.blit(self.font.render(f"Give: {self.market_from}", True, COLOR_TEXT), (btn_from.x + 8, btn_from.y + 4))
        self.screen.blit(self.font.render(f"Get : {self.market_to}", True, COLOR_TEXT), (btn_to.x + 8, btn_to.y + 4))

        # amount
        amt_rect = pygame.Rect(r.x + 220, r.y + 80, 120, 28)
        pygame.draw.rect(self.screen, (60, 62, 72), amt_rect, border_radius=4)
        self.screen.blit(self.font.render(f"Amount: {self.market_amount}", True, COLOR_TEXT), (amt_rect.x + 8, amt_rect.y + 4))

        # bouton trade
        pygame.draw.rect(self.screen, (70, 140, 70), self.market_btn_do, border_radius=4)
        self.screen.blit(self.font_big.render("Trade", True, COLOR_TEXT), (self.market_btn_do.x + 20, self.market_btn_do.y + 2))

        # info taux
        rate = self.town.market_rates.get((self.market_from, self.market_to))
        info = f"Rate: {rate} {self.market_from} -> 1 {self.market_to}" if rate else "No rate"
        self.screen.blit(self.font_small.render(info, True, COLOR_ACCENT), (r.x + 24, r.bottom - 36))

        # sauver rects pour clics
        self._market_btn_from, self._market_btn_to, self._market_btn_amt = btn_from, btn_to, amt_rect

    def _market_click(self, pos: Tuple[int,int]) -> None:
        if self._market_btn_from.collidepoint(pos):
            order = ["gold", "wood", "stone", "crystal"]
            i = (order.index(self.market_from) + 1) % len(order)
            self.market_from = order[i]; return
        if self._market_btn_to.collidepoint(pos):
            order = ["gold", "wood", "stone", "crystal"]
            i = (order.index(self.market_to) + 1) % len(order)
            self.market_to = order[i]; return
        if self._market_btn_amt.collidepoint(pos):
            self.market_amount = 1 if self.market_amount >= 50 else self.market_amount + 1; return
        if self.market_btn_do.collidepoint(pos):
            if self.market_from == self.market_to: 
                return
            if self.town.can_trade(self.market_from, self.market_to, self.market_amount, self.hero):
                if self.town.trade(self.market_from, self.market_to, self.market_amount, self.hero):
                    self._publish_resources()
        # clic hors panneau pour fermer ?
        if not self.market_rect.collidepoint(pos):
            self.market_open = False

    # ----------------------------------------------------------- Tavern overlay
    def _open_tavern_overlay(self) -> None:
        self.tavern_open = True
        self.tavern_msg = ""
        W, H = self.screen.get_size()
        self.tavern_rect.center = (W // 2, H // 2)

    def _draw_tavern_overlay(self) -> None:
        s = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        s.fill((0, 0, 0, 160))
        self.screen.blit(s, (0, 0))
        r = self.tavern_rect
        pygame.draw.rect(self.screen, (40, 42, 50), r, border_radius=8)
        pygame.draw.rect(self.screen, (110, 110, 120), r, 2, border_radius=8)
        self.screen.blit(self.font_big.render("Tavern – Hire Heroes", True, COLOR_TEXT), (r.x + 16, r.y + 12))
        card_w = 180
        card_h = 180
        gap = 20
        x = r.x + 20
        y = r.y + 60
        self.tavern_cards = []
        for idx, info in enumerate(self.tavern_heroes):
            card = pygame.Rect(x + idx * (card_w + gap), y, card_w, card_h)
            pygame.draw.rect(self.screen, (60, 62, 72), card, border_radius=6)
            pygame.draw.rect(self.screen, (110, 110, 120), card, 2, border_radius=6)
            portrait = pygame.Rect(card.x + 8, card.y + 8, 64, 64)
            pygame.draw.rect(self.screen, (80, 80, 90), portrait)
            pygame.draw.rect(self.screen, (110, 110, 120), portrait, 2)
            name = info["name"]
            cost = info["cost"]
            self.screen.blit(self.font.render(name, True, COLOR_TEXT), (card.x + 8, card.y + 80))
            self.screen.blit(self.font_small.render(f"Cost: {cost}", True, COLOR_ACCENT), (card.x + 8, card.y + 110))
            btn = pygame.Rect(card.x + 40, card.bottom - 40, 100, 28)
            pygame.draw.rect(self.screen, (70, 140, 70), btn, border_radius=4)
            self.screen.blit(self.font_small.render("Hire", True, COLOR_TEXT), (btn.x + 28, btn.y + 6))
            self.tavern_cards.append((idx, btn))

        if self.tavern_msg:
            msg_surf = self.font_small.render(self.tavern_msg, True, COLOR_WARN)
            msg_rect = msg_surf.get_rect()
            msg_rect.midtop = (r.centerx, r.bottom - 30)
            self.screen.blit(msg_surf, msg_rect)

    def _tavern_click(self, pos: Tuple[int,int]) -> None:
        for idx, btn in self.tavern_cards:
            if btn.collidepoint(pos):
                info = self.tavern_heroes[idx]
                cost = info["cost"]
                if self.hero.gold >= cost:
                    self.hero.gold -= cost
                    new_hero = Hero(self.town.origin[0], self.town.origin[1], info["army"], info["stats"])
                    new_hero.name = info["name"]
                    self.game.add_hero(new_hero)
                    self._publish_resources()
                    self.tavern_open = False
                else:
                    self.tavern_msg = "Not enough gold"
                return
        if not self.tavern_rect.collidepoint(pos):
            self.tavern_open = False

    # ----------------------------------------------------------- Bounty overlay
    def _open_bounty_overlay(self) -> None:
        # Reuse the game's quest overlay
        self.game.open_journal(self.screen)

    # -------------------------------------------------------- Spellbook overlay
    def _open_spellbook_overlay(self) -> None:
        try:  # pragma: no cover - allow running without package context
            from ui.spellbook_overlay import SpellbookOverlay
        except ImportError:  # pragma: no cover
            from .spellbook_overlay import SpellbookOverlay  # type: ignore

        overlay = SpellbookOverlay(self.screen, town=True)
        clock = pygame.time.Clock()
        running = True
        while running:
            for event in pygame.event.get():
                if overlay.handle_event(event):
                    running = False
                    break
            overlay.draw()
            pygame.display.flip()
            clock.tick(60)

    # ----------------------------------------------------------- Castle overlay
    def _open_castle_overlay(self) -> None:
        self.castle_open = True
        W, H = self.screen.get_size()
        self.castle_rect.center = (W // 2, H // 2)

    def _draw_castle_overlay(self) -> None:
        s = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        s.fill((0, 0, 0, 170)); self.screen.blit(s, (0, 0))
        r = self.castle_rect
        pygame.draw.rect(self.screen, (36, 38, 46), r, border_radius=8)
        pygame.draw.rect(self.screen, (120, 120, 130), r, 2, border_radius=8)
        self.screen.blit(self.font_big.render("Castle – Recruitment Overview", True, COLOR_TEXT), (r.x + 16, r.y + 10))

        # cartes unités (toutes débloquées)
        units = self.town.list_all_recruitables()
        from core.entities import RECRUITABLE_UNITS
        cols = 2
        cw, ch = (r.width - 3 * 16) // cols, 130
        x = r.x + 16; y = r.y + 48
        self.castle_unit_cards = []
        for i, uid in enumerate(units):
            card = pygame.Rect(x, y, cw, ch)
            pygame.draw.rect(self.screen, (48, 50, 58), card, border_radius=8)
            pygame.draw.rect(self.screen, (100, 100, 110), card, 2, border_radius=8)
            # header
            self.screen.blit(self.font_big.render(uid, True, COLOR_TEXT), (card.x + 10, card.y + 6))
            # “building” placeholder (gauche) + “unit portrait” placeholder (droite)
            bh = pygame.Rect(card.x + 10, card.y + 34, 72, 72)
            uh = pygame.Rect(card.right - 82, card.y + 34, 72, 72)
            pygame.draw.rect(self.screen, (70, 72, 84), bh)
            pygame.draw.rect(self.screen, (70, 72, 84), uh)
            # stats
            st = RECRUITABLE_UNITS.get(uid)
            if st:
                lines = [
                    f"HP {st.max_hp}",
                    f"DMG {st.attack_min}-{st.attack_max}",
                    f"DEF M/R/Mg {st.defence_melee}/{st.defence_ranged}/{st.defence_magic}",
                    f"SPD {st.speed}  INIT {st.initiative}",
                ]
                yy = card.y + 34
                for line in lines:
                    self.screen.blit(self.font_small.render(line, True, COLOR_TEXT), (bh.right + 10, yy))
                    yy += 18
            # hint
            hint = self.font_small.render("Click to recruit", True, COLOR_ACCENT)
            self.screen.blit(hint, (card.right - hint.get_width() - 8, card.bottom - 22))

            self.castle_unit_cards.append((uid, card))

            # advance layout
            if (i % cols) == cols - 1:
                x = r.x + 16; y += ch + 12
            else:
                x += cw + 16

        # close hint
        info = self.font_small.render("Esc to close", True, COLOR_DISABLED)
        self.screen.blit(info, (r.right - info.get_width() - 10, r.bottom - 20))
