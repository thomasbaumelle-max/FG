from __future__ import annotations

import os
from typing import List, Tuple

import pygame

import theme
import constants
from loaders import icon_loader as IconLoader


RESOURCE_ORDER = ["gold", "wood", "stone", "crystal"]

class MarketScreen:
    """Simple trading interface for the town market.

    The player's resources are shown on the left while the list of tradeable
    resources is displayed on the right.  Select the resource you want to give
    and the one you wish to receive then adjust the amount with the slider.
    Clicking *Exchange* performs the trade using ``Town.trade``.
    """

    def __init__(
        self,
        screen: pygame.Surface,
        game: "Game",
        town: "Town",
        hero: "Hero",
        clock: pygame.time.Clock | None = None,
    ) -> None:
        self.screen = screen
        self.game = game
        self.town = town
        self.hero = hero
        self.clock = clock or pygame.time.Clock()
        self.font = theme.get_font(16) or pygame.font.SysFont(None, 16)
        self.font_big = theme.get_font(20) or pygame.font.SysFont(None, 20, bold=True)
        self.running = True

        self.give_res = "gold"
        self.get_res = "wood"
        self.amount = 1

        # Layout
        self.panel_rect = pygame.Rect(0, 0, 420, 260)
        self.panel_rect.center = (
            self.screen.get_width() // 2,
            self.screen.get_height() // 2,
        )
        self.slider_rect = pygame.Rect(0, 0, 200, 14)
        self.slider_rect.midbottom = (self.panel_rect.centerx, self.panel_rect.bottom - 70)
        self.max_btn = pygame.Rect(self.panel_rect.x + 20, self.panel_rect.bottom - 60, 80, 28)
        self.trade_btn = pygame.Rect(self.panel_rect.right - 140, self.panel_rect.bottom - 60, 120, 32)

        size = 32
        gap = 10
        left_x = self.panel_rect.x + 30
        right_x = self.panel_rect.centerx + 30
        y = self.panel_rect.y + 60
        self.give_icons: List[Tuple[str, pygame.Rect]] = []
        self.get_icons: List[Tuple[str, pygame.Rect]] = []
        for res in RESOURCE_ORDER:
            r1 = pygame.Rect(left_x, y, size, size)
            r2 = pygame.Rect(right_x, y, size, size)
            self.give_icons.append((res, r1))
            self.get_icons.append((res, r2))
            y += size + gap

        self.background = screen.copy()

    # ------------------------------------------------------------------ utils
    def _max_amount(self) -> int:
        rate = self.town.market_rates.get((self.give_res, self.get_res))
        if rate is None or rate <= 0:
            return 0
        pool = self.hero.gold if self.give_res == "gold" else self.hero.resources.get(self.give_res, 0)
        return pool // rate

    def _publish_resources(self) -> None:
        pub = getattr(self.game, "_publish_resources", None)
        if callable(pub):
            pub()

    # ----------------------------------------------------------------- drawing
    def _draw_player_resources(self) -> None:
        x = self.panel_rect.x + 20
        y = self.panel_rect.y + 20
        for res in RESOURCE_ORDER:
            icon = IconLoader.get(f"resource_{res}", 24)
            val = self.hero.gold if res == "gold" else self.hero.resources.get(res, 0)
            self.screen.blit(icon, (x, y))
            txt = self.font.render(str(val), True, theme.PALETTE["text"])
            self.screen.blit(txt, (x + 30, y + 4))
            y += 28

    def draw(self) -> None:
        self.screen.blit(self.background, (0, 0))
        dim = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        dim.fill((*theme.PALETTE["background"], 200))
        self.screen.blit(dim, (0, 0))
        pygame.draw.rect(self.screen, theme.PALETTE["panel"], self.panel_rect, border_radius=8)
        pygame.draw.rect(self.screen, theme.PALETTE["accent"], self.panel_rect, theme.FRAME_WIDTH, border_radius=8)

        title = self.font_big.render("Market", True, theme.PALETTE["text"])
        self.screen.blit(title, (self.panel_rect.x + 16, self.panel_rect.y + 16))

        # Player resources
        self._draw_player_resources()

        # Selection icons
        for res, rect in self.give_icons:
            icon = IconLoader.get(f"resource_{res}", rect.width)
            self.screen.blit(icon, rect)
            if res == self.give_res:
                pygame.draw.rect(self.screen, theme.PALETTE["accent"], rect, 2)
        for res, rect in self.get_icons:
            icon = IconLoader.get(f"resource_{res}", rect.width)
            self.screen.blit(icon, rect)
            if res == self.get_res:
                pygame.draw.rect(self.screen, theme.PALETTE["accent"], rect, 2)

        # Slider
        pygame.draw.rect(self.screen, theme.PALETTE["accent"], self.slider_rect, 2)
        max_amt = self._max_amount()
        ratio = 0 if max_amt <= 0 else min(1.0, self.amount / max_amt)
        knob_x = int(self.slider_rect.x + ratio * self.slider_rect.width)
        knob = pygame.Rect(knob_x - 5, self.slider_rect.y - 4, 10, self.slider_rect.height + 8)
        pygame.draw.rect(self.screen, theme.PALETTE["accent"], knob)
        amt_txt = self.font.render(str(self.amount), True, theme.PALETTE["text"])
        self.screen.blit(amt_txt, (self.slider_rect.centerx - amt_txt.get_width() // 2, self.slider_rect.bottom + 6))

        # Buttons
        pygame.draw.rect(self.screen, theme.PALETTE["accent"], self.max_btn, border_radius=4)
        self.screen.blit(self.font.render("Max", True, theme.PALETTE["text"]), (self.max_btn.x + 18, self.max_btn.y + 6))
        pygame.draw.rect(self.screen, theme.PALETTE["accent"], self.trade_btn, border_radius=4)
        self.screen.blit(self.font.render("Exchange", True, theme.PALETTE["text"]), (self.trade_btn.x + 12, self.trade_btn.y + 6))

        # Rate information
        rate = self.town.market_rates.get((self.give_res, self.get_res))
        info = "" if rate is None else f"Rate: {rate} {self.give_res} -> 1 {self.get_res}"
        info_surf = self.font.render(info, True, theme.PALETTE["accent"])
        self.screen.blit(info_surf, (self.panel_rect.x + 20, self.panel_rect.bottom - 28))

        pygame.display.flip()

    # ----------------------------------------------------------------- events
    def _handle_click(self, pos: Tuple[int, int]) -> None:
        for res, rect in self.give_icons:
            if rect.collidepoint(pos):
                self.give_res = res
                self.amount = 1
                return
        for res, rect in self.get_icons:
            if rect.collidepoint(pos):
                self.get_res = res
                self.amount = 1
                return
        if self.slider_rect.collidepoint(pos):
            rel = (pos[0] - self.slider_rect.x) / self.slider_rect.width
            self.amount = max(1, int(self._max_amount() * rel))
            return
        if self.max_btn.collidepoint(pos):
            self.amount = max(1, self._max_amount())
            return
        if self.trade_btn.collidepoint(pos):
            if self.give_res != self.get_res and self.town.trade(self.give_res, self.get_res, self.amount, self.hero):
                self._publish_resources()
                self.running = False
            return
        if not self.panel_rect.collidepoint(pos):
            self.running = False

    def run(self) -> None:
        test_mode = "PYTEST_CURRENT_TEST" in os.environ
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    raise SystemExit
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.running = False
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self._handle_click(event.pos)
            self.draw()
            if test_mode:
                break
            self.clock.tick(getattr(constants, "FPS", 30))


def open(
    screen: pygame.Surface,
    game: "Game",
    town: "Town",
    hero: "Hero",
    clock: pygame.time.Clock | None = None,
) -> None:
    """Convenience function to open the market UI."""
    if not pygame.display.get_init() or pygame.display.get_surface() is None:
        return
    MarketScreen(screen, game, town, hero, clock).run()
