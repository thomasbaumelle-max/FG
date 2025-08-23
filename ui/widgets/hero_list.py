from __future__ import annotations

"""Widget listing the player's heroes with basic interaction.

The list displays up to five hero "cards" stacked vertically.  Each card shows a
placeholder portrait, the hero's name and remaining action points.  Clicking a
card selects the hero and recenters the world renderer on their position.  When
more than five heroes exist the list can be scrolled using the mouse wheel.  A
simple tooltip describing the hovered hero is provided via :func:`get_tooltip`.

This module is intentionally lightweight; the portrait graphics are plain
coloured squares and many behaviours are stubs suitable for unit tests.
"""

from dataclasses import dataclass
from typing import Any, Callable, List, Optional, Sequence, Tuple

import pygame

import theme
from render.world_renderer import WorldRenderer
from state.event_bus import EVENT_BUS, ON_SELECT_HERO
from core.entities import UnitCarrier

# Fallback event type constants for environments with a pygame stub
MOUSEBUTTONDOWN = getattr(pygame, "MOUSEBUTTONDOWN", 1)
MOUSEMOTION = getattr(pygame, "MOUSEMOTION", 3)
MOUSEWHEEL = getattr(pygame, "MOUSEWHEEL", 4)


@dataclass
class _CarrierInfo:
    """Internal helper storing carrier reference and portrait surface."""

    actor: UnitCarrier
    portrait: pygame.Surface


class HeroList:
    """Display and interact with a vertical list of unit carriers."""

    CARD_SIZE = 72  # Size of the square portrait area
    PADDING = 4
    MAX_VISIBLE = 5

    def __init__(
        self,
        renderer: Optional[WorldRenderer] = None,
        on_select: Optional[Callable[[UnitCarrier], None]] = None,
    ) -> None:
        self.renderer = renderer
        self.on_select = on_select
        self._heroes: List[_CarrierInfo] = []
        self.scroll = 0
        self.hover_index: Optional[int] = None
        self.selected_index: Optional[int] = None
        self.font = theme.get_font(16)
        # React to hero selection events published elsewhere
        EVENT_BUS.subscribe(ON_SELECT_HERO, self._on_select_hero)

    # ------------------------------------------------------------------
    # Public API
    def set_heroes(self, heroes: Sequence[UnitCarrier]) -> None:
        """Provide the heroes or armies to be displayed."""
        self._heroes = []
        for h in heroes:
            portrait = getattr(h, "portrait", None)
            if isinstance(portrait, str):
                try:
                    portrait = pygame.image.load(portrait).convert_alpha()
                except Exception:  # pragma: no cover - loading may fail
                    portrait = None
            surf_type = getattr(pygame, "Surface", None)
            if surf_type and isinstance(surf_type, type) and isinstance(portrait, surf_type):
                size_fn = getattr(portrait, "get_size", None)
                if size_fn:
                    width, height = size_fn()
                else:
                    width, height = portrait.get_width(), portrait.get_height()
                if (width, height) != (self.CARD_SIZE, self.CARD_SIZE):
                    try:
                        portrait = pygame.transform.scale(
                            portrait, (self.CARD_SIZE, self.CARD_SIZE)
                        )
                    except Exception:  # pragma: no cover - scaling may fail
                        portrait = None
            if portrait is None:
                portrait = self._make_portrait()
            self._heroes.append(_CarrierInfo(actor=h, portrait=portrait))
        self.scroll = 0
        self.selected_index = None

    # ------------------------------------------------------------------
    def _make_portrait(self) -> pygame.Surface:
        surf = pygame.Surface((self.CARD_SIZE, self.CARD_SIZE), pygame.SRCALPHA)
        try:
            surf = surf.convert_alpha()
        except Exception:  # pragma: no cover
            pass
        surf.fill(theme.PALETTE["panel"])
        if hasattr(pygame, "draw") and hasattr(pygame.draw, "rect"):
            pygame.draw.rect(surf, theme.FRAME_COLOURS["normal"], surf.get_rect(), theme.FRAME_WIDTH)
        return surf

    def _card_rect(self, visible_index: int, rect: pygame.Rect) -> pygame.Rect:
        """Return the rectangle for the ``visible_index`` on screen."""
        y = rect.y + visible_index * (self.CARD_SIZE + self.PADDING)
        return pygame.Rect(rect.x, y, rect.width, self.CARD_SIZE)

    def _hero_at(self, pos: Tuple[int, int], rect: pygame.Rect) -> Optional[int]:
        x, y = pos
        if not (
            rect.x <= x < rect.x + rect.width
            and rect.y <= y < rect.y + rect.height
        ):
            return None
        rel_y = y - rect.y
        idx = rel_y // (self.CARD_SIZE + self.PADDING)
        absolute = self.scroll + int(idx)
        if 0 <= absolute < len(self._heroes):
            return absolute
        return None

    def handle_event(self, evt: object, rect: pygame.Rect) -> None:
        """Handle a Pygame-style event."""
        etype = getattr(evt, "type", None)
        if etype == MOUSEBUTTONDOWN:
            if getattr(evt, "button", 0) == 1:
                idx = self._hero_at(getattr(evt, "pos", (0, 0)), rect)
                if idx is not None:
                    # Record the selection locally so the UI highlights it even
                    # for non-hero armies.
                    self.selected_index = idx
                    actor = self._heroes[idx].actor
                    if self.renderer:
                        self.renderer.center_on((actor.x, actor.y))
                    # Notify listeners about the selection
                    EVENT_BUS.publish(ON_SELECT_HERO, actor)
                    if self.on_select:
                        self.on_select(actor)
            elif getattr(evt, "button", 0) in (4, 5) and len(self._heroes) > self.MAX_VISIBLE:
                step = -1 if evt.button == 4 else 1
                self.scroll = int(
                    max(0, min(self.scroll + step, len(self._heroes) - self.MAX_VISIBLE))
                )
        elif etype == MOUSEWHEEL and len(self._heroes) > self.MAX_VISIBLE:
            y = getattr(evt, "y", 0)
            self.scroll = int(
                max(0, min(self.scroll - y, len(self._heroes) - self.MAX_VISIBLE))
            )
        elif etype == MOUSEMOTION:
            self.hover_index = self._hero_at(getattr(evt, "pos", (0, 0)), rect)

    # ------------------------------------------------------------------
    def _on_select_hero(self, hero: UnitCarrier) -> None:
        """Update selection when another widget selects a carrier."""

        for idx, info in enumerate(self._heroes):
            if info.actor is hero:
                self.selected_index = idx
                if self.renderer:
                    self.renderer.center_on((hero.x, hero.y))
                break

    def get_tooltip(self, pos: Tuple[int, int], rect: pygame.Rect) -> Optional[str]:
        """Return tooltip text for the hero at ``pos``."""
        idx = self._hero_at(pos, rect)
        if idx is None:
            return None
        hero = self._heroes[idx].actor
        name = getattr(hero, "name", "Hero")
        return f"{name} – ({hero.x}, {hero.y})\nGo to"

    def draw(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        """Draw the hero list to ``surface`` within ``rect``."""
        start = self.scroll
        end = min(start + self.MAX_VISIBLE, len(self._heroes))
        for i, info in enumerate(self._heroes[start:end], start=start):
            idx_on_screen = i - start
            card = self._card_rect(idx_on_screen, rect)
            surface.blit(info.portrait, card.topleft)
            colour = theme.FRAME_COLOURS["highlight"] if i == self.selected_index else theme.FRAME_COLOURS["normal"]
            if hasattr(pygame, "draw") and hasattr(pygame.draw, "rect"):
                pygame.draw.rect(surface, colour, card, theme.FRAME_WIDTH)
            if self.font:
                name = getattr(info.actor, "name", "Hero")
                name_surf = self.font.render(name, True, theme.PALETTE["text"])
                surface.blit(name_surf, (card.x + self.CARD_SIZE + 4, card.y + 4))
                ap = getattr(info.actor, "ap", 0)
                ap_surf = self.font.render(str(ap), True, theme.PALETTE["text"])
                surface.blit(ap_surf, (card.x + self.CARD_SIZE + 4, card.bottom - ap_surf.get_height() - 4))
