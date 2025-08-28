from __future__ import annotations

from pathlib import Path

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

        # Pre-load and scale the unit image if available
        self.image: pygame.Surface | None = None
        try:
            root = Path(__file__).resolve().parent.parent
            name = getattr(unit.stats, "name", "").lower().replace(" ", "_") + ".png"
            path = root / "assets" / "units" / name
            if path.is_file():
                img = pygame.image.load(path).convert_alpha()
                max_size = min(self.rect.width - 40, 120)
                if hasattr(pygame.transform, "smoothscale"):
                    img = pygame.transform.smoothscale(img, (max_size, max_size))
                else:  # pragma: no cover - fallback when smoothscale missing
                    img = pygame.transform.scale(img, (max_size, max_size))
                self.image = img
        except Exception:  # pragma: no cover - robustness for missing assets
            self.image = None

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

        # Clip drawing to the panel rectangle
        prev_clip = self.screen.get_clip()
        self.screen.set_clip(self.rect)

        y = self.rect.y + 20

        # Unit image at top, centred
        if self.image:
            img_rect = self.image.get_rect()
            img_rect.midtop = (self.rect.centerx, y)
            self.screen.blit(self.image, img_rect.topleft)
            y = img_rect.bottom + 10

        # Name
        name = self.big.render(self.unit.stats.name, True, self.TEXT)
        name_rect = name.get_rect(midtop=(self.rect.centerx, y))
        self.screen.blit(name, name_rect.topleft)

        x = self.rect.x + 20
        y = name_rect.bottom + 20
        bar_w = self.rect.width - 40
        bar_h = 20
        bottom_limit = self.rect.bottom - 20

        # HP bar
        if y + bar_h <= bottom_limit:
            hp_rect = pygame.Rect(x, y, bar_w, bar_h)
            self._draw_bar(hp_rect, self.unit.current_hp, self.unit.stats.max_hp, constants.GREEN)
            y += bar_h + 10
        # Mana bar
        if y + bar_h <= bottom_limit:
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
            item_h = icon.get_height() + 6
            if y + item_h > bottom_limit:
                break
            self.screen.blit(icon, (x, y))
            txt = self.font.render(value, True, self.TEXT)
            self.screen.blit(
                txt,
                (x + icon.get_width() + 8, y + (icon.get_height() - txt.get_height()) // 2),
            )
            y += item_h

        # Active status effects arranged in two columns
        effects = [e for e in getattr(self.unit, "effects", []) if e.duration > 0]
        if effects and y + 32 <= bottom_limit:
            y += 10
            col_w = (self.rect.width - 40) // 2
            row_h = 36
            for idx, eff in enumerate(effects):
                row = idx // 2
                col = idx % 2
                cell_x = x + col * col_w
                cell_y = y + row * row_h
                if cell_y + row_h > bottom_limit:
                    break
                icon_id = eff.icon or f"status_{eff.name}"
                icon = IconLoader.get(icon_id, 32)
                self.screen.blit(icon, (cell_x, cell_y))
                label = f"{eff.name} ({eff.duration})"
                txt = self.font.render(label, True, self.TEXT)
                max_w = col_w - icon.get_width() - 4
                if txt.get_width() > max_w:
                    txt = pygame.transform.smoothscale(txt, (max_w, txt.get_height()))
                self.screen.blit(
                    txt,
                    (
                        cell_x + icon.get_width() + 4,
                        cell_y + (icon.get_height() - txt.get_height()) // 2,
                    ),
                )

        self.screen.set_clip(prev_clip)

