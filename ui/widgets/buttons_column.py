from __future__ import annotations

"""Vertical column of fixed-size buttons with hotkeys and tooltips.

The widget manages a simple list of buttons stacked vertically.  Each button
invokes a callback when clicked or when its associated keyboard shortcut is
pressed.  The visual representation is intentionally minimal and suitable for
unit tests – buttons are drawn as coloured rectangles with their labels.

A button can be disabled which greys it out and prevents the callback from
running.  ``get_tooltip`` returns a short description for the button at a given
mouse position, allowing the :class:`ui.widgets.desc_bar.DescBar` to display
information about hovered buttons.
"""

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple

import json
import os
from pathlib import Path

import pygame

from .. import theme, audio

# Pygame event type fallbacks
MOUSEBUTTONDOWN = getattr(pygame, "MOUSEBUTTONDOWN", 1)
MOUSEMOTION = getattr(pygame, "MOUSEMOTION", 3)
KEYDOWN = getattr(pygame, "KEYDOWN", 2)


@dataclass
class _Button:
    """Internal description of a button."""

    name: str
    label: str
    callback: Optional[Callable[[], None]]
    hotkey: int
    tooltip: str
    enabled: bool = True


class ButtonsColumn:
    """Display a vertical column of buttons.

    Parameters
    ----------
    on_end_turn:
        Callback for the "end turn" button.
    open_town, open_options:
        Callbacks for other buttons.  All callbacks are optional.
    """

    BUTTON_SIZE = (48, 48)
    PADDING = 4

    def __init__(
        self,
        on_end_turn: Optional[Callable[[], None]] = None,
        open_town: Optional[Callable[[], None]] = None,
        open_journal: Optional[Callable[[], None]] = None,
        open_options: Optional[Callable[[], None]] = None,
        actions: Optional[List[str]] = None,
        action_callbacks: Optional[Dict[str, Callable[[], None]]] = None,
    ) -> None:
        self.font = theme.get_font(20)
        self.hotkey_font = theme.get_font(12)

        # Load icon manifest describing where to find each icon
        icons_file = os.path.join("assets", "icons", "icons.json")
        try:
            with open(icons_file, "r", encoding="utf8") as fh:
                self._icons = json.load(fh)
        except Exception:  # pragma: no cover - file missing or invalid
            self._icons = {}

        self.buttons: List[_Button] = [
            _Button(
                name="end_turn",
                label="T",
                callback=on_end_turn,
                hotkey=getattr(pygame, "K_t", ord("t")),
                tooltip="End turn (T)",
            ),
            _Button(
                name="town",
                label="B",
                callback=open_town,
                hotkey=getattr(pygame, "K_b", ord("b")),
                tooltip="Open town (B)",
            ),
            _Button(
                name="journal",
                label="J",
                callback=open_journal,
                hotkey=getattr(pygame, "K_j", ord("j")),
                tooltip="Open journal (J)",
            ),
            _Button(
                name="options",
                label="O",
                callback=open_options,
                hotkey=getattr(pygame, "K_o", ord("o")),
                tooltip="Options (O)",
            ),
        ]

        # Definitions for optional turn-action buttons
        self._action_defs: Dict[str, str] = {
            "move": "M",
            "wait": "W",
            "defend": "D",
            "attack": "A",
            "shoot": "S",
            "cast": "C",
            "use_ability": "U",
            "swap": "X",
            "flee": "F",
            "surrender": "R",
            "auto_resolve": "A",
            "next_unit": "N",
        }
        if actions:
            self.add_actions(actions, action_callbacks)

        self.hover_index: Optional[int] = None
        # Cache rendered button surfaces keyed by (name, enabled)
        self._cache: Dict[Tuple[str, bool], pygame.Surface] = {}
        for btn in self.buttons:
            self._cache[(btn.name, True)] = self._render_button(btn, True)
            self._cache[(btn.name, False)] = self._render_button(btn, False)

    # ------------------------------------------------------------------
    # Layout helpers
    def _all_rects(self, rect: pygame.Rect) -> List[pygame.Rect]:
        """Return rectangles for all buttons inside ``rect``.

        The buttons simply stack vertically, each taking the full width of the
        provided ``rect`` with padding between them.  This keeps the layout
        logic straightforward and lets the caller decide how wide the column
        should be.
        """

        rects: List[pygame.Rect] = []
        y = rect.y
        for _ in self.buttons:
            rects.append(pygame.Rect(rect.x, y, rect.width, self.BUTTON_SIZE[1]))
            y += self.BUTTON_SIZE[1] + self.PADDING
        return rects

    def _button_rect(self, index: int, rect: pygame.Rect) -> pygame.Rect:
        """Return rectangle for button ``index`` within ``rect``."""
        return self._all_rects(rect)[index]

    def _render_button(self, btn: _Button, enabled: bool) -> pygame.Surface:
        """Create a cached surface for ``btn`` in the given state."""
        surf = pygame.Surface(self.BUTTON_SIZE, pygame.SRCALPHA)
        try:
            surf = surf.convert_alpha()
        except Exception:  # pragma: no cover - stub surface
            pass
        surf.fill(theme.PALETTE["panel"])
        if hasattr(pygame, "draw") and hasattr(pygame.draw, "rect"):
            frame_col = (
                theme.FRAME_COLOURS["normal"]
                if enabled
                else theme.FRAME_COLOURS["disabled"]
            )
            pygame.draw.rect(
                surf, frame_col, surf.get_rect(), theme.FRAME_WIDTH
            )

        icon_drawn = False
        info = self._icons.get(btn.name) or self._icons.get(f"action_{btn.name}")
        if isinstance(info, dict):
            img_mod = getattr(pygame, "image", None)
            transform = getattr(pygame, "transform", None)
            try:
                if "file" in info:
                    full_path = Path("assets") / info["file"]
                    if img_mod and hasattr(img_mod, "load") and os.path.exists(full_path):
                        icon = img_mod.load(full_path)
                        if hasattr(icon, "convert_alpha"):
                            icon = icon.convert_alpha()
                        if transform and hasattr(transform, "scale"):
                            icon = transform.scale(
                                icon,
                                (self.BUTTON_SIZE[0] - 8, self.BUTTON_SIZE[1] - 8),
                            )
                        surf.blit(icon, (4, 4))
                        icon_drawn = True
                elif "sheet" in info:
                    sheet_path = Path("assets") / info["sheet"]
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
                            icon = transform.scale(
                                icon,
                                (self.BUTTON_SIZE[0] - 8, self.BUTTON_SIZE[1] - 8),
                            )
                        surf.blit(icon, (4, 4))
                        icon_drawn = True
            except Exception:  # pragma: no cover - loading failed
                icon_drawn = False

        if not icon_drawn:
            pass

        if self.hotkey_font:
            hk = self.hotkey_font.render(btn.label, True, theme.PALETTE["text"])
            surf.blit(
                hk,
                (
                    surf.get_width() - hk.get_width() - 2,
                    surf.get_height() - hk.get_height() - 2,
                ),
            )
        return surf

    def _button_at(self, pos: Tuple[int, int], rect: pygame.Rect) -> Optional[int]:
        """Return index of button at ``pos`` or ``None``."""
        for i, brect in enumerate(self._all_rects(rect)):
            if brect.collidepoint(pos):
                return i
        return None

    # ------------------------------------------------------------------
    # Public API
    def add_actions(
        self,
        names: List[str],
        callbacks: Optional[Dict[str, Callable[[], None]]] = None,
    ) -> None:
        """Add action buttons listed in ``names``.

        ``callbacks`` maps names to callables. Buttons are appended and cached
        when possible.
        """

        for name in names:
            label = self._action_defs.get(name, name[:1].upper())
            key = getattr(pygame, f"K_{label.lower()}", ord(label.lower()))
            cb = callbacks.get(name) if callbacks and name in callbacks else None
            btn = _Button(
                name=name,
                label=label,
                callback=cb,
                hotkey=key,
                tooltip=f"{name.replace('_', ' ').title()} ({label})",
            )
            self.buttons.append(btn)
            if hasattr(self, "_cache"):
                self._cache[(btn.name, True)] = self._render_button(btn, True)
                self._cache[(btn.name, False)] = self._render_button(btn, False)

    def set_enabled(self, name: str, enabled: bool) -> None:
        """Enable or disable a button by ``name``."""
        for btn in self.buttons:
            if btn.name == name:
                btn.enabled = enabled
                break

    def handle_event(self, event: object, rect: pygame.Rect) -> None:
        """Handle a Pygame-style event."""
        etype = getattr(event, "type", None)
        if etype == MOUSEBUTTONDOWN and getattr(event, "button", 0) == 1:
            idx = self._button_at(getattr(event, "pos", (0, 0)), rect)
            if idx is not None:
                btn = self.buttons[idx]
                if btn.enabled and btn.callback:
                    audio.play_sound('click')
                    btn.callback()
        elif etype == MOUSEMOTION:
            idx = self._button_at(getattr(event, "pos", (0, 0)), rect)
            if idx != self.hover_index:
                if idx is not None and self.buttons[idx].enabled:
                    audio.play_sound('hover')
                self.hover_index = idx
        elif etype == KEYDOWN:
            key = getattr(event, "key", None)
            for btn in self.buttons:
                if btn.hotkey == key and btn.enabled and btn.callback:
                    audio.play_sound('click')
                    btn.callback()
                    break

    def get_tooltip(self, pos: Tuple[int, int], rect: pygame.Rect) -> Optional[str]:
        """Return tooltip text for the button at ``pos``."""
        idx = self._button_at(pos, rect)
        if idx is None:
            return None
        return self.buttons[idx].tooltip

    def draw(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        """Draw the button column to ``surface`` within ``rect``."""
        for i, (btn, brect) in enumerate(zip(self.buttons, self._all_rects(rect))):
            img = self._cache[(btn.name, btn.enabled)]
            surface.blit(img, brect.topleft)
            if (
                i == self.hover_index
                and btn.enabled
                and hasattr(pygame, "draw")
                and hasattr(pygame.draw, "rect")
            ):
                pygame.draw.rect(
                    surface,
                    theme.FRAME_COLOURS["highlight"],
                    brect,
                    theme.FRAME_WIDTH,
                )
