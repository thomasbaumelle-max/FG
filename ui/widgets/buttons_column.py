from __future__ import annotations

"""Vertical column of fixed-size buttons using :class:`IconButton`."""

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple

import pygame

from .. import audio
from .icon_button import IconButton

MOUSEMOTION = getattr(pygame, "MOUSEMOTION", 3)


@dataclass
class ButtonEntry:
    name: str
    button: IconButton


class ButtonsColumn:
    """Display a vertical column of :class:`IconButton` widgets."""

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
        self.buttons: List[ButtonEntry] = []
        self.hover_index: Optional[int] = None

        def add_button(
            name: str,
            icon_id: str,
            callback: Optional[Callable[[], None]],
            hotkey: int,
            tooltip: str,
        ) -> None:
            rect = pygame.Rect(0, len(self.buttons) * (self.BUTTON_SIZE[1] + self.PADDING), *self.BUTTON_SIZE)
            btn = IconButton(
                rect,
                icon_id,
                callback or (lambda: None),
                hotkey=hotkey,
                tooltip=tooltip,
                size=self.BUTTON_SIZE,
            )
            self.buttons.append(ButtonEntry(name, btn))

        add_button(
            "end_turn",
            "end_turn",
            on_end_turn,
            getattr(pygame, "K_t", ord("t")),
            "End turn (T)",
        )
        add_button(
            "town",
            "town",
            open_town,
            getattr(pygame, "K_b", ord("b")),
            "Open town (B)",
        )
        add_button(
            "journal",
            "journal",
            open_journal,
            getattr(pygame, "K_j", ord("j")),
            "Open journal (J)",
        )
        add_button(
            "options",
            "options",
            open_options,
            getattr(pygame, "K_o", ord("o")),
            "Options (O)",
        )

        self._action_hotkeys = {
            "move": getattr(pygame, "K_m", ord("m")),
            "wait": getattr(pygame, "K_w", ord("w")),
            "defend": getattr(pygame, "K_d", ord("d")),
            "attack": getattr(pygame, "K_a", ord("a")),
            "shoot": getattr(pygame, "K_s", ord("s")),
            "cast": getattr(pygame, "K_c", ord("c")),
            "use_ability": getattr(pygame, "K_u", ord("u")),
            "swap": getattr(pygame, "K_x", ord("x")),
            "flee": getattr(pygame, "K_f", ord("f")),
            "surrender": getattr(pygame, "K_r", ord("r")),
            "auto_resolve": getattr(pygame, "K_a", ord("a")),
            "next_unit": getattr(pygame, "K_n", ord("n")),
            "end_turn": getattr(pygame, "K_t", ord("t")),
        }
        if actions:
            self.add_actions(actions, action_callbacks)

    # ------------------------------------------------------------------
    def add_actions(
        self,
        names: List[str],
        callbacks: Optional[Dict[str, Callable[[], None]]] = None,
    ) -> None:
        for name in names:
            hotkey = self._action_hotkeys.get(name)
            cb = callbacks.get(name) if callbacks and name in callbacks else None
            tooltip = name.replace("_", " ").title()
            rect = pygame.Rect(0, len(self.buttons) * (self.BUTTON_SIZE[1] + self.PADDING), *self.BUTTON_SIZE)
            btn = IconButton(
                rect,
                f"action_{name}",
                cb or (lambda: None),
                hotkey=hotkey,
                tooltip=tooltip,
                size=self.BUTTON_SIZE,
            )
            self.buttons.append(ButtonEntry(name, btn))

    def set_enabled(self, name: str, enabled: bool) -> None:
        for entry in self.buttons:
            if entry.name == name:
                entry.button.enabled = enabled
                break

    def _position_buttons(self, rect: pygame.Rect) -> None:
        y = rect.y
        for entry in self.buttons:
            entry.button.rect.topleft = (rect.x, y)
            entry.button.rect.size = self.BUTTON_SIZE
            y += self.BUTTON_SIZE[1] + self.PADDING

    def handle_event(self, event: object, rect: pygame.Rect) -> None:
        self._position_buttons(rect)
        if getattr(event, "type", None) == MOUSEMOTION:
            idx: Optional[int] = None
            for i, entry in enumerate(self.buttons):
                if entry.button.collidepoint(getattr(event, "pos", (0, 0))):
                    idx = i
                    break
            if idx != self.hover_index:
                if idx is not None and self.buttons[idx].button.enabled:
                    audio.play_sound("hover")
                self.hover_index = idx
        else:
            for entry in self.buttons:
                if entry.button.handle(event):
                    audio.play_sound("click")
                    break

    def get_tooltip(self, pos: Tuple[int, int], rect: pygame.Rect) -> Optional[str]:
        self._position_buttons(rect)
        for entry in self.buttons:
            if entry.button.collidepoint(pos) and entry.button.enabled:
                return entry.button.tooltip
        return None

    def draw(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        self._position_buttons(rect)
        for entry in self.buttons:
            entry.button.draw(surface)

