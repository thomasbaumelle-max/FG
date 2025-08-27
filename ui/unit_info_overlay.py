from __future__ import annotations

import sys
import pygame
import theme
import constants
from loaders import icon_loader as IconLoader


class UnitInfoOverlay:
    """Display detailed information about a unit in combat."""

    BG = theme.PALETTE.get("background", (40, 42, 50))
    PANEL = theme.PALETTE.get("panel", (32, 34, 40))
    TEXT = theme.PALETTE.get("text", (230, 230, 230))

    STAT_ICONS = {
        "hp": "stat_hp",
        "mana": "stat_mana",
        "attack": "stat_attack_range",
        "defence": "stat_defence_magic",
        "speed": "stat_speed",
        "initiative": "stat_initiative",
        "morale": "stat_morale",
        "luck": "stat_luck",
        "fire": "status_burn",
        "ice": "status_freeze",
        "shock": "status_stun",
        "earth": "status_petrify",
        "water": "status_slow",
    }

    def __init__(self, screen: pygame.Surface, unit) -> None:
        self.screen = screen
        self.unit = unit
        self.font = theme.get_font(24) or pygame.font.SysFont(None, 24)
        self.big = theme.get_font(32) or pygame.font.SysFont(None, 32)
        w, h = screen.get_size()
        self.rect = pygame.Rect(0, 0, 420, 440)
        self.rect.center = (w // 2, h // 2)

    # ------------------------------------------------------------------ events
    def handle_event(self, event: pygame.event.Event) -> bool:
        """Return ``True`` to close the overlay."""
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return True
        return False

    # ------------------------------------------------------------------ drawing helpers
    def _draw_bar(self, rect: pygame.Rect, current: int, maximum: int, colour) -> None:
        pygame.draw.rect(self.screen, constants.BLACK, rect)
        if maximum > 0:
            ratio = max(0.0, min(1.0, current / maximum))
            inner = rect.copy()
            inner.width = int(rect.width * ratio)
            pygame.draw.rect(self.screen, colour, inner)
        pygame.draw.rect(self.screen, self.TEXT, rect, 1)

    # ------------------------------------------------------------------ drawing
    def draw(self) -> None:
        overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        overlay.fill((*self.BG, 200))
        self.screen.blit(overlay, (0, 0))
        pygame.draw.rect(self.screen, self.PANEL, self.rect)
        pygame.draw.rect(self.screen, self.TEXT, self.rect, 2)

        # Name
        name = self.big.render(self.unit.stats.name, True, self.TEXT)
        self.screen.blit(name, (self.rect.x + 20, self.rect.y + 20))

        x = self.rect.x + 20
        y = self.rect.y + 80
        bar_w = self.rect.width - 40
        bar_h = 20
        # HP bar
        hp_rect = pygame.Rect(x, y, bar_w, bar_h)
        self._draw_bar(hp_rect, self.unit.current_hp, self.unit.stats.max_hp, constants.GREEN)
        y += bar_h + 10
        # Mana bar
        mana_rect = pygame.Rect(x, y, bar_w, bar_h)
        self._draw_bar(mana_rect, self.unit.mana, self.unit.max_mana, constants.BLUE)
        y += bar_h + 20

        # Stats list with icons
        stats = [
            ("hp", f"{self.unit.current_hp}/{self.unit.stats.max_hp}"),
            ("mana", f"{self.unit.mana}/{self.unit.max_mana}"),
            ("attack", f"{self.unit.stats.attack_min}-{self.unit.stats.attack_max}"),
            (
                "defence",
                f"M/R/Mg {self.unit.stats.defence_melee}/{self.unit.stats.defence_ranged}/{self.unit.stats.defence_magic}",
            ),
            ("speed", str(self.unit.stats.speed)),
            ("initiative", str(self.unit.stats.initiative)),
            ("morale", str(self.unit.stats.morale)),
            ("luck", str(self.unit.stats.luck)),
        ]
        for school, value in self.unit.resistances.as_dict().items():
            stats.append((school, f"{value}%"))
        for key, value in stats:
            icon = IconLoader.get(self.STAT_ICONS.get(key, key), 32)
            self.screen.blit(icon, (x, y))
            txt = self.font.render(value, True, self.TEXT)
            self.screen.blit(txt, (x + icon.get_width() + 8, y + (icon.get_height() - txt.get_height()) // 2))
            y += icon.get_height() + 6

        # Active status effects
        effects = [e for e in getattr(self.unit, "effects", []) if e.duration > 0]
        if effects:
            y += 10
            x_eff = x
            for eff in effects:
                icon_id = eff.icon or f"status_{eff.name}"
                icon = IconLoader.get(icon_id, 32)
                self.screen.blit(icon, (x_eff, y))
                x_eff += 36

    # ------------------------------------------------------------------ public API
    def run(self) -> None:
        clock = pygame.time.Clock()
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if self.handle_event(event):
                    running = False
                    break
            self.draw()
            pygame.display.flip()
            clock.tick(constants.FPS)
