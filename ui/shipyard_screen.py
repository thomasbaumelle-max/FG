from __future__ import annotations

import os
import pygame
from typing import Dict, List, Tuple

import theme
import constants
from loaders.boat_loader import BoatDef
from core.entities import Hero
from core.buildings import Shipyard

# Layout constants similar to town_screen
SLOT_COUNT = 7
SLOT_SIZE = 80
SLOT_GAP = 10
PANEL_PAD = 20
BUTTON_H = 28
FONT_NAME = None


class ShipyardScreen:
    """Simple purchasing interface for shipyards.

    Displays available :class:`BoatDef` entries in a 7\u00d71 grid allowing the
    hero to buy one if they have enough resources.  Inspired by the town
    management screen but greatly simplified for the training project.
    """

    def __init__(
        self,
        screen: pygame.Surface,
        game: "Game",
        shipyard: Shipyard,
        clock: pygame.time.Clock | None = None,
    ) -> None:
        self.screen = screen
        self.game = game
        self.shipyard = shipyard
        self.clock = clock or pygame.time.Clock()
        self.font = theme.get_font(16) or pygame.font.SysFont(FONT_NAME, 16)
        self.font_small = theme.get_font(14) or pygame.font.SysFont(FONT_NAME, 14)
        self.running = True

        # Precompute slot rects (7x1 grid)
        panel_w = SLOT_COUNT * SLOT_SIZE + (SLOT_COUNT - 1) * SLOT_GAP + PANEL_PAD * 2
        panel_h = SLOT_SIZE + 80
        self.panel_rect = pygame.Rect(0, 0, panel_w, panel_h)
        self.panel_rect.center = (
            self.screen.get_width() // 2,
            self.screen.get_height() // 2,
        )

        self.slot_rects: List[Tuple[pygame.Rect, pygame.Rect]] = []
        start_x = self.panel_rect.x + PANEL_PAD
        y = self.panel_rect.y + PANEL_PAD
        for i in range(SLOT_COUNT):
            rect = pygame.Rect(start_x + i * (SLOT_SIZE + SLOT_GAP), y, SLOT_SIZE, SLOT_SIZE)
            btn_rect = pygame.Rect(rect.x, rect.bottom + 32, SLOT_SIZE, BUTTON_H)
            self.slot_rects.append((rect, btn_rect))

        self.background = screen.copy()

    # ------------------------------------------------------------------ utils
    def _can_afford(self, cost: Dict[str, int]) -> bool:
        """Return ``True`` if hero has enough resources for ``cost``."""

        hero = self.game.hero
        for res, amt in cost.items():
            if hero.resources.get(res, 0) < amt:
                return False
        return True

    def _buy_boat(self, bdef: BoatDef) -> None:
        """Deduct cost and grant the boat to the hero."""

        hero: Hero = self.game.hero
        for res, amt in bdef.cost.items():
            hero.resources[res] = hero.resources.get(res, 0) - int(amt)
        hero.naval_unit = bdef.id

    # ---------------------------------------------------------------- drawing
    def draw(self) -> None:
        self.screen.blit(self.background, (0, 0))
        dim = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        dim.fill((*theme.PALETTE["background"], 200))
        self.screen.blit(dim, (0, 0))
        pygame.draw.rect(self.screen, theme.PALETTE["panel"], self.panel_rect)
        pygame.draw.rect(
            self.screen,
            theme.PALETTE["accent"],
            self.panel_rect,
            theme.FRAME_WIDTH,
        )

        boats = list(self.game.boat_defs.values())
        asset_loader = getattr(self.game.ctx, "asset_loader", None)

        for idx, (slot, btn) in enumerate(self.slot_rects):
            if idx < len(boats):
                bdef = boats[idx]
                surf = None
                if asset_loader is not None:
                    try:
                        surf = asset_loader.get(bdef.id)
                    except Exception:
                        surf = None
                if isinstance(surf, pygame.Surface):
                    size = min(slot.width, slot.height)
                    if surf.get_size() != (size, size):
                        surf = pygame.transform.smoothscale(surf, (size, size))
                    self.screen.blit(surf, surf.get_rect(center=slot.center))
                pygame.draw.rect(self.screen, theme.PALETTE["accent"], slot, theme.FRAME_WIDTH)
                y = slot.bottom + 4
                move_txt = self.font_small.render(
                    f"Move: {bdef.movement}", True, theme.PALETTE["text"]
                )
                self.screen.blit(move_txt, (slot.x, y))
                y += 16
                cap_txt = self.font_small.render(
                    f"Cap: {bdef.capacity}", True, theme.PALETTE["text"]
                )
                self.screen.blit(cap_txt, (slot.x, y))
                cost_line = ", ".join(f"{r}: {v}" for r, v in bdef.cost.items())
                cost_txt = self.font_small.render(cost_line, True, theme.PALETTE["text"])
                self.screen.blit(cost_txt, (btn.x, btn.y - 20))
                pygame.draw.rect(self.screen, theme.PALETTE["accent"], btn)
                pygame.draw.rect(self.screen, theme.PALETTE["text"], btn, theme.FRAME_WIDTH)
                label = self.font_small.render("Buy", True, theme.PALETTE["text"])
                self.screen.blit(label, label.get_rect(center=btn.center))
            else:
                pygame.draw.rect(self.screen, theme.PALETTE["accent"], slot, theme.FRAME_WIDTH)

        pygame.display.flip()

    # ----------------------------------------------------------------- events
    def handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.running = False
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                boats = list(self.game.boat_defs.values())
                for idx, (_, btn) in enumerate(self.slot_rects):
                    if idx >= len(boats):
                        continue
                    if btn.collidepoint(event.pos) and self._can_afford(boats[idx].cost):
                        self._buy_boat(boats[idx])
                        self.running = False
                        break

    def run(self) -> None:
        test_mode = "PYTEST_CURRENT_TEST" in os.environ
        while self.running:
            self.handle_events()
            self.draw()
            if test_mode:
                break
            self.clock.tick(getattr(constants, "FPS", 30))


def open(
    screen: pygame.Surface,
    game: "Game",
    shipyard: Shipyard,
    clock: pygame.time.Clock | None = None,
) -> None:
    """Convenience function to open the shipyard UI."""
    # Skip opening the UI when no display surface is active (e.g. during tests)
    if not pygame.display.get_init() or pygame.display.get_surface() is None:
        return

    ShipyardScreen(screen, game, shipyard, clock).run()
