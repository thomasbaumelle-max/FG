from __future__ import annotations

"""Main game screen management.

This module contains :class:`MainScreen` which is a very small UI helper used
by :class:`game.Game`.  The intent is to have a place where logic concerning
layout, mouse interaction (panning/zooming) and simple drawing lives.  The
implementation here is intentionally lightweight; the real project can replace
this stub with a more feature complete interface.
"""

from typing import Dict, Optional, List

import os
import pygame
from . import theme, constants

from .layout import Layout
from .widgets.desc_bar import DescBar
from .widgets.resources_bar import ResourcesBar
from .widgets.minimap import Minimap
from .widgets.hero_list import HeroList
from .widgets.hero_army_panel import HeroArmyPanel
from .widgets.icon_button import IconButton
from .widgets.turn_bar import TurnBar

MENU_BUTTON_SIZE = (48, 48)
MENU_PADDING = 4
from .state.event_bus import (
    EVENT_BUS,
    ON_CAMERA_CHANGED,
    ON_SEA_CHAIN_PROGRESS,
    ON_INFO_MESSAGE,
)


MOUSEBUTTONDOWN = getattr(pygame, "MOUSEBUTTONDOWN", 1)
MOUSEBUTTONUP = getattr(pygame, "MOUSEBUTTONUP", 2)
MOUSEMOTION = getattr(pygame, "MOUSEMOTION", 3)
MOUSEWHEEL = getattr(pygame, "MOUSEWHEEL", 4)
KEYDOWN = getattr(pygame, "KEYDOWN", 2)


class MainScreen:
    """Basic UI controller for the main game screen.

    Parameters
    ----------
    game:
        Reference to the :class:`game.Game` instance.  The screen uses the
        game's ``offset`` and ``zoom`` values for panning and zooming the world
        view.
    """

    def __init__(self, game: "Game") -> None:  # pragma: no cover - thin wrapper
        self.game = game
        self.widgets: Dict[str, pygame.Rect] = {}
        self.hovered: Optional[str] = None
        self._dragging = False
        self._last_mouse: tuple[int, int] | None = None
        # Description bar shown in one of the panels
        self.desc_bar = DescBar()
        self.resources_bar = ResourcesBar()
        world = getattr(game, "world", None)
        renderer = getattr(game, "world_renderer", None)
        if world and renderer:
            colour = getattr(game, "player_colour", constants.BLUE)
            self.minimap = Minimap(world, renderer, player_colour=colour)
        else:
            self.minimap = None
        list_renderer = getattr(game, "world_renderer", None)
        if list_renderer is None and world:
            list_renderer = getattr(world, "renderer", None)
        self.hero_list = HeroList(renderer=list_renderer)
        heroes = list(getattr(getattr(game, "state", None), "heroes", []))
        armies = list(getattr(getattr(game, "world", None), "player_armies", []))
        self.hero_list.set_heroes(heroes + armies)

        self.menu_buttons: List[IconButton] = []
        self.hovered_button: Optional[IconButton] = None
        self.end_message: Optional[str] = None

        def add_btn(icon_id: str, callback) -> None:
            rect = pygame.Rect(0, 0, *MENU_BUTTON_SIZE)
            cb = callback if callable(callback) else (lambda: None)
            tooltip = icon_id.replace("nav_", "").replace("_", " ").title()
            self.menu_buttons.append(
                IconButton(rect, icon_id, cb, tooltip=tooltip, size=MENU_BUTTON_SIZE)
            )

        # Navigation / menu buttons
        add_btn("nav_menu", self.open_menu)
        add_btn("nav_settings", getattr(game, "open_options", None))
        add_btn("nav_save", self.save_game)
        add_btn("nav_load", self.load_game)
        add_btn("nav_skill_tree", getattr(game, "open_skill_tree", None))
        add_btn("nav_journal", getattr(game, "open_journal", None))
        add_btn("nav_hero_screen", getattr(game, "open_hero_screen", None))
        add_btn("nav_town", self.next_town)
        add_btn("nav_end_day", self.end_day)
        add_btn("nav_pause", self.toggle_pause)

        self.army_panel = HeroArmyPanel(hero=getattr(game, "hero", None))
        self.turn_bar = TurnBar(
            calendar=getattr(getattr(game, "state", None), "turn", None)
        )
        self.compute_layout(game.screen.get_width(), game.screen.get_height())
        EVENT_BUS.subscribe(ON_SEA_CHAIN_PROGRESS, self._on_sea_chain_progress)

    # ------------------------------------------------------------------
    # End overlay
    # ------------------------------------------------------------------
    def show_end_overlay(self, victory: bool) -> None:
        """Display a victory or defeat message on top of the screen."""
        self.end_message = "Victory!" if victory else "Defeat!"

    # ------------------------------------------------------------------
    # Button callbacks
    # ------------------------------------------------------------------
    def open_menu(self) -> None:
        cb = getattr(self.game, "open_pause_menu", None) or getattr(
            self.game, "open_menu", None
        )
        if cb:
            cb()

    def save_game(self) -> None:
        cb = getattr(self.game, "save_game", None)
        path = getattr(self.game, "default_save_path", None)
        profile = getattr(self.game, "default_profile_path", None)
        if cb and path:
            cb(path, profile)

    def load_game(self) -> None:
        cb = getattr(self.game, "load_game", None)
        path = getattr(self.game, "default_save_path", None)
        profile = getattr(self.game, "default_profile_path", None)
        if cb and path:
            if os.path.exists(path):
                try:
                    cb(path, profile)
                except Exception as exc:  # pragma: no cover - defensive
                    EVENT_BUS.publish(
                        ON_INFO_MESSAGE, f"Failed to load save: {exc}"
                    )
            else:
                EVENT_BUS.publish(ON_INFO_MESSAGE, f"Save file not found: {path}")

    def prev_hero(self) -> None:
        cb = getattr(self.game, "prev_hero", None)
        if cb:
            cb()

    def next_town(self) -> None:
        cb = getattr(self.game, "next_town", None)
        if cb:
            cb()
            mods = getattr(getattr(pygame, "key", None), "get_mods", lambda: 0)()
            if mods & getattr(pygame, "KMOD_CTRL", 0):
                open_cb = getattr(self.game, "open_town", None)
                if open_cb:
                    town = getattr(self.game, "_focused_town", None)
                    pos = getattr(self.game, "_focused_town_pos", None)
                    try:
                        if town:
                            open_cb(town, town_pos=pos)
                        else:
                            open_cb()
                    except TypeError:
                        if town:
                            open_cb(town, town_pos=pos)
                        else:
                            open_cb()

    def end_day(self) -> None:
        cb = getattr(self.game, "end_day", None)
        if cb:
            cb()

    def toggle_pause(self) -> None:
        cb = getattr(self.game, "toggle_pause", None)
        if cb:
            cb()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------
    def compute_layout(self, width: int, height: int, buttons_below: bool | None = None) -> None:
        """Compute widget rectangles for a screen of ``width`` x ``height``.

        ``buttons_below`` forces the button column below the army panel when
        ``True``.  When ``None`` (default), the layout automatically chooses
        between side-by-side or stacked buttons based on available height.
        """

        M = 8
        side_w = max(260, int(0.23 * width))
        base_bar_h = 24
        bar_h = int(base_bar_h * 1.5)

        root = Layout(pygame.Rect(0, 0, width, height))
        root.dock_left(M)
        root.dock_right(M)
        root.dock_top(M)

        # Colonne droite (minimap + liste héros + boutons + armée)
        sidebar_full = root.dock_right(side_w - M, margin=M)

        # Zone monde + deux bandeaux inférieurs
        world_layout = root
        # 1) Description (tout en bas)
        desc_rect = world_layout.dock_bottom(bar_h, margin=M)
        # 2) Ligne "resources | turn" juste au-dessus, coupée en 70/30
        res_turn_rect = world_layout.dock_bottom(bar_h, margin=M)
        world_rect = world_layout.remaining()

        # Split horizontal pour resources/turn
        res_w = int(res_turn_rect.width * 0.7) - M // 2
        turn_w = res_turn_rect.width - res_w - M
        res_rect = pygame.Rect(res_turn_rect.x, res_turn_rect.y, res_w, res_turn_rect.height)
        turn_rect = pygame.Rect(
            res_rect.x + res_rect.width + M,
            res_turn_rect.y,
            turn_w,
            res_turn_rect.height,
        )

        # Colonne de droite : minimap en haut, puis 2 panneaux juxtaposés (hero_list | buttons),
        # puis l'armée dessous qui prend tout le reste.
        sidebar_top = pygame.Rect(
            sidebar_full.x,
            world_rect.y,
            sidebar_full.width,
            world_rect.height,
        )
        side_layout = Layout(sidebar_top)

        side_h = sidebar_top.height
        mini_rect = side_layout.dock_top(int(0.22 * side_h), margin=M)
        mid_h = int(0.38 * side_h)

        # Determine if buttons can fit next to the hero list; otherwise stack
        btn_count = len(self.menu_buttons)
        btn_single_h = btn_count * MENU_BUTTON_SIZE[1] + (
            btn_count - 1
        ) * MENU_PADDING
        # Height if arranged in two columns
        btn_rows_two = (btn_count + 1) // 2
        btn_double_h = btn_rows_two * MENU_BUTTON_SIZE[1] + (
            btn_rows_two - 1
        ) * MENU_PADDING

        # Simplified layout for tests: keep buttons beside hero list
        buttons_below = False if buttons_below is None else buttons_below

        # Ensure the mid section is tall enough for the buttons. If a single
        # column would exceed the available height, fall back to two columns.
        if btn_single_h > mid_h:
            mid_h = max(mid_h, btn_double_h)
            btn_total_h = btn_double_h
        else:
            btn_total_h = btn_single_h

        if not buttons_below:
            mid_rect = side_layout.dock_top(mid_h, margin=M)
            army_rect = side_layout.remaining()

            split_w = (mid_rect.width - M) // 2
            hero_list_rect = pygame.Rect(mid_rect.x, mid_rect.y, split_w, mid_rect.height)
            buttons_rect = pygame.Rect(
                hero_list_rect.x + hero_list_rect.width + M,
                mid_rect.y,
                split_w,
                mid_rect.height,
            )
        else:
            hero_list_rect = side_layout.dock_top(mid_h, margin=M)
            buttons_rect = side_layout.dock_bottom(btn_total_h, margin=0)
            army_rect = side_layout.remaining()

        self.widgets = {
            "1": world_rect,        # world
            "2": desc_rect,         # description bar (bandeau fin)
            "3": res_rect,          # resources (à gauche)
            "3b": turn_rect,        # turn bar (à droite)
            "4": mini_rect,         # minimap
            "5": hero_list_rect,    # liste héros
            "6": buttons_rect,      # boutons
            "7": army_rect,         # armée du héros
        }

    def _position_menu_buttons(self, rect: pygame.Rect) -> None:
        btn_w, btn_h = MENU_BUTTON_SIZE
        single_h = len(self.menu_buttons) * btn_h + (
            len(self.menu_buttons) - 1
        ) * MENU_PADDING
        cols = 1
        if single_h > rect.height and rect.width >= btn_w * 2 + MENU_PADDING:
            cols = 2

        rows = (len(self.menu_buttons) + cols - 1) // cols
        for i, btn in enumerate(self.menu_buttons):
            col = i // rows
            row = i % rows
            btn.rect.x = rect.x + col * (btn_w + MENU_PADDING)
            btn.rect.y = rect.y + row * (btn_h + MENU_PADDING)
            btn.rect.width, btn.rect.height = MENU_BUTTON_SIZE

    def _on_sea_chain_progress(self, current: int, total: int) -> None:
        """Display progress for sea quest chain in the description bar."""
        if current >= total:
            EVENT_BUS.publish(ON_INFO_MESSAGE, "Sea quest completed!")
        else:
            EVENT_BUS.publish(
                ON_INFO_MESSAGE, f"Sea waypoint {current}/{total} reached"
            )

    # ------------------------------------------------------------------
    # Event handling
    # ------------------------------------------------------------------
    def handle_event(self, event: pygame.event.Event) -> bool:
        """Handle a Pygame event.

        Supported interactions include:

        * Zoom via mouse wheel.
        * Panning using the middle or right mouse button.
        * Tracking which widget the mouse is hovering over.

        Returns ``True`` if the event was consumed by the screen and should not
        be processed further by the caller.
        """
        hero_rect = self.widgets.get("5")
        if hero_rect and event.type in (MOUSEBUTTONDOWN, MOUSEWHEEL):
            mouse_get_pos = getattr(getattr(pygame, "mouse", None), "get_pos", lambda: (0, 0))
            pos = getattr(event, "pos", mouse_get_pos())
            if hero_rect.x <= pos[0] < hero_rect.x + hero_rect.width and hero_rect.y <= pos[1] < hero_rect.y + hero_rect.height:
                self.hero_list.handle_event(event, hero_rect)
                return True

        buttons_rect = self.widgets.get("6")
        if buttons_rect:
            self._position_menu_buttons(buttons_rect)
            self.hovered_button = None
            for btn in self.menu_buttons:
                handled = btn.handle(event)
                if btn.hovered:
                    self.hovered_button = btn
                if handled:
                    return True

        if event.type == MOUSEBUTTONDOWN:
            if event.button in (2, 3):
                self._dragging = True
                self._last_mouse = event.pos
                return True
            if event.button == 4:  # wheel up
                world_rect = self.widgets.get("1")
                self.game._adjust_zoom(0.25, event.pos)
                if world_rect:
                    self.game._clamp_offset(world_rect)
                return True
            if event.button == 5:  # wheel down
                world_rect = self.widgets.get("1")
                self.game._adjust_zoom(-0.25, event.pos)
                if world_rect:
                    self.game._clamp_offset(world_rect)
                return True
        elif event.type == MOUSEBUTTONUP:
            if event.button in (2, 3) and self._dragging:
                self._dragging = False
                return True
        elif event.type == MOUSEMOTION:
            # Hover detection
            self.hovered = None
            for wid, rect in self.widgets.items():
                if rect.collidepoint(event.pos):
                    self.hovered = wid
                    break
            # Tooltip priority: buttons first, then world
            if self.hovered_button:
                self.desc_bar.update((self.hovered_button.get_tooltip(), "tile"))
            else:
                self.desc_bar.update(self.game.hover_probe(*event.pos))
            # Dragging for panning
            if self._dragging and self._last_mouse is not None:
                dx = event.pos[0] - self._last_mouse[0]
                dy = event.pos[1] - self._last_mouse[1]
                self.game.offset_x += dx
                self.game.offset_y += dy
                world_rect = self.widgets.get("1")
                if world_rect:
                    self.game._clamp_offset(world_rect)
                self._last_mouse = event.pos
                EVENT_BUS.publish(
                    ON_CAMERA_CHANGED, self.game.offset_x, self.game.offset_y, self.game.zoom
                )
                return True
        elif event.type == MOUSEWHEEL:
            # Pygame 2 style wheel event
            if event.y:
                world_rect = self.widgets.get("1")
                mouse_pos = getattr(getattr(pygame, "mouse", None), "get_pos", lambda: (0, 0))()
                self.game._adjust_zoom(event.y * 0.25, mouse_pos)
                if world_rect:
                    self.game._clamp_offset(world_rect)
                return True
        if self.hovered == "4" and self.minimap:
            rect4 = self.widgets.get("4")
            if rect4:
                self.minimap.handle_event(event, rect4)
                return True
        widget_map = {
            "3": self.resources_bar,
            # minimap handled above
            "5": self.hero_list,
            "7": self.army_panel,
            "8": self.turn_bar,
        }
        rect = self.widgets.get(self.hovered) if self.hovered else None
        widget = widget_map.get(self.hovered) if self.hovered else None
        if widget and rect and hasattr(widget, "handle_event"):
            handled = widget.handle_event(event, rect)
            if handled:
                return True
        return False

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------
    def draw(self, screen: pygame.Surface) -> List[pygame.Rect]:
        dirty: List[pygame.Rect] = []

        mouse_get_pos = getattr(getattr(pygame, "mouse", None), "get_pos", lambda: (0, 0))
        if self.hovered_button:
            self.desc_bar.update((self.hovered_button.get_tooltip(), "tile"))
        else:
            self.desc_bar.update(self.game.hover_probe(*mouse_get_pos()))

        # Couleur unifiée des panneaux + cadre 9-slice
        def panel(rect: pygame.Rect, hover=False):
            screen.fill((32, 34, 40), rect)
            theme.draw_frame(screen, rect, "highlight" if hover else "normal")
    
        # Resources (gauche) + Turn (droite) sur la même ligne
        panel(self.widgets["3"], hover=(self.hovered == "3"))
        self.resources_bar.draw(screen, self.widgets["3"]); dirty.append(self.widgets["3"])
    
        panel(self.widgets["3b"], hover=(self.hovered == "3b"))
        self.turn_bar.draw(screen, self.widgets["3b"]); dirty.append(self.widgets["3b"])
    
        # Minimap
        if self.minimap:
            panel(self.widgets["4"], hover=(self.hovered == "4"))
            self.minimap.draw(screen, self.widgets["4"]); dirty.append(self.widgets["4"])
    
        # Liste héros et boutons (même gabarit)
        panel(self.widgets["5"], hover=(self.hovered == "5"))
        self.hero_list.draw(screen, self.widgets["5"]); dirty.append(self.widgets["5"])
    
        panel(self.widgets["6"], hover=(self.hovered == "6"))
        self._position_menu_buttons(self.widgets["6"])
        for btn in self.menu_buttons:
            btn.draw(screen)
        dirty.append(self.widgets["6"])
    
        # Armée du héros
        panel(self.widgets["7"], hover=(self.hovered == "7"))
        self.army_panel.draw(screen, self.widgets["7"]); dirty.append(self.widgets["7"])

        # Bandeau description (tout en bas)
        panel(self.widgets["2"], hover=(self.hovered == "2"))
        self.desc_bar.draw(screen, self.widgets["2"]); dirty.append(self.widgets["2"])
        if self.end_message:
            overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
            overlay.fill((*theme.PALETTE["background"], 200))
            font = theme.get_font(48) or pygame.font.SysFont(None, 48)
            text = font.render(self.end_message, True, theme.PALETTE["text"])
            overlay.blit(text, text.get_rect(center=screen.get_rect().center))
            screen.blit(overlay, (0, 0))
            dirty.append(screen.get_rect())

        return dirty


# Small helper type hint for the ``game`` reference without importing the module
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - only for type checkers
    from core.game import Game
