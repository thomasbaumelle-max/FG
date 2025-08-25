"""User interface drawing for the combat screen."""

from __future__ import annotations
from typing import Dict, Tuple, Optional
import json
from pathlib import Path
import pygame
import theme
import settings

BUTTON_H = 28
PANEL_W = 260
MARGIN = 10
LINE = (74, 76, 86)


class CombatHUD:
    """Draws the combat interface and exposes clickable action regions."""
    def __init__(self) -> None:
        """Initialise fonts and load localized action labels."""
        self.font = pygame.font.SysFont(None, 18)
        self.small = pygame.font.SysFont(None, 16)
        self.title = pygame.font.SysFont(None, 22)
        self.action_labels = self._load_action_labels(settings.LANGUAGE)

    def _load_action_labels(self, language: str) -> Dict[str, str]:
        """Load translated action labels from ``assets/i18n/action_labels.json``."""
        default = "en"
        path = (
            Path(__file__).resolve().parents[1]
            / "assets"
            / "i18n"
            / "action_labels.json"
        )
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}
        labels = data.get(default, {})
        if language != default:
            labels.update(data.get(language, {}))
        return labels

    def _panel_rects(
        self,
        screen: pygame.Surface,
        grid_rect: pygame.Rect,
        combat,
    ) -> Tuple[pygame.Rect, pygame.Rect]:
        """Return rectangles for the side and bottom panels."""
        right = pygame.Rect(
            grid_rect.x + grid_rect.width + MARGIN,
            grid_rect.y - combat.top_margin,
            PANEL_W,
            grid_rect.height + combat.top_margin,
        )
        bottom = pygame.Rect(
            grid_rect.x,
            grid_rect.y - combat.top_margin + grid_rect.height + MARGIN,
            grid_rect.width,
            BUTTON_H + 8,
        )
        return right, bottom

    def draw(
        self, screen: pygame.Surface, combat
    ) -> Tuple[Dict[str, pygame.Rect], Optional[pygame.Rect]]:
        """Draw the HUD and return ``(action_buttons, auto_button)``."""
        # Determine the grid area from current offsets and zoom
        grid_w = int(combat.grid_pixel_width * combat.zoom)
        grid_h = int(combat.grid_pixel_height * combat.zoom)
        grid_rect = pygame.Rect(combat.offset_x, combat.offset_y, grid_w, grid_h)

        right, bottom = self._panel_rects(screen, grid_rect, combat)

        # Backgrounds
        screen.fill(theme.PALETTE.get("panel", (32, 34, 40)), right)
        pygame.draw.rect(screen, LINE, right, 1)
        screen.fill(theme.PALETTE.get("panel", (32, 34, 40)), bottom)
        pygame.draw.rect(screen, LINE, bottom, 1)

        action_buttons: Dict[str, pygame.Rect] = {}
        auto_button: Optional[pygame.Rect] = None

        # ---- Right panel: unit card and turn order ----
        if combat.turn_order:
            unit = combat.turn_order[combat.current_index]
            # Title
            title = self.title.render(unit.stats.name, True, theme.PALETTE["text"])
            screen.blit(title, (right.x + 10, right.y + 8))

            # Portrait (or scaled sprite)
            # Use whichever image the engine prefers
            img = combat.get_unit_image(unit, (64, 64))
            if img:
                screen.blit(img, (right.x + 10, right.y + 36))

            # Stats
            lines = [
                f"HP {unit.current_hp}/{unit.stats.max_hp}",
                f"Mana {unit.mana}/{unit.max_mana}",
                f"ATK {unit.stats.attack_min}-{unit.stats.attack_max}",
                (
                    f"DEF M/R/Mg {unit.stats.defence_melee}/"
                    f"{unit.stats.defence_ranged}/{unit.stats.defence_magic}"
                ),
                f"Spd {unit.stats.speed}  Init {unit.stats.initiative}",
            ]
            for i, s in enumerate(lines):
                txt = self.font.render(s, True, theme.PALETTE["text"])
                screen.blit(txt, (right.x + 84, right.y + 42 + i * 18))

            # Turn order thumbnails
            y0 = right.y + 150
            screen.blit(
                self.small.render("Next:", True, theme.PALETTE["text"]),
                (right.x + 10, y0),
            )
            y = y0 + 18
            upcoming = (
                combat.turn_order[combat.current_index + 1:]
                + combat.turn_order[:combat.current_index]
            )
            for u in upcoming[:6]:
                sw = 34
                r = pygame.Rect(right.x + 10, y, sw, sw)
                pygame.draw.rect(screen, LINE, r, 1)
                im = combat.get_unit_image(u, (sw - 2, sw - 2))
                if im:
                    screen.blit(im, (r.x + 1, r.y + 1))
                name = self.small.render(u.stats.name, True, theme.PALETTE["text"])
                screen.blit(name, (r.x + r.width + 6, y + 8))
                y += sw + 6

            # Buttons below the turn order
            y += 10
            auto_button = pygame.Rect(right.x + 10, y, right.width - 20, BUTTON_H)
            pygame.draw.rect(screen, (52, 55, 63), auto_button)
            pygame.draw.rect(screen, LINE, auto_button, 1)
            lab = self.small.render(
                "AUTO" if not combat.auto_mode else "HUMAN",
                True,
                theme.PALETTE["text"],
            )
            screen.blit(lab, lab.get_rect(center=auto_button.center))
            y = auto_button.bottom + 6

            r = pygame.Rect(right.x + 10, y, right.width - 20, BUTTON_H)
            colour = (52, 55, 63) if combat.hero_spells else (40, 42, 48)
            pygame.draw.rect(screen, colour, r)
            pygame.draw.rect(screen, LINE, r, 1)
            txt = self.small.render("Spellbook", True, theme.PALETTE["text"])
            screen.blit(txt, txt.get_rect(center=r.center))
            action_buttons["spellbook"] = r
        # ---- Action bar (bottom) ----
        x = bottom.x + 8

        def add_btn(key: str, label: str) -> None:
            nonlocal x
            r = pygame.Rect(x, bottom.y + 4, 110, bottom.height - 8)
            pygame.draw.rect(screen, (52, 55, 63), r)
            pygame.draw.rect(screen, LINE, r, 1)
            txt = self.small.render(label, True, theme.PALETTE["text"])
            screen.blit(txt, txt.get_rect(center=r.center))
            action_buttons[key] = r
            x = r.x + r.width + 6

        actions = combat.get_available_actions(
            combat.turn_order[combat.current_index]
        )
        # Stable ordering for readability
        wanted = ["move", "melee", "ranged", "spell", "wait"]
        for a in wanted:
            if a in actions:
                add_btn(a, self.action_labels.get(a, a.title()))

        # Spell submenu when "spell" is selected
        if combat.selected_action == "spell":
            spells = sorted(combat.spells_by_name.keys())
            # Only show spells usable by the current unit
            caster = combat.turn_order[combat.current_index]
            allow = set(combat.UNIT_SPELLS.get(caster.stats.name, {}).keys())
            spells = [s for s in spells if s in allow]
            # Fold-out menu
            x2 = x
            for s in spells:
                r = pygame.Rect(x2, bottom.y + 4, 140, bottom.height - 8)
                pygame.draw.rect(screen, (70, 72, 82), r)
                pygame.draw.rect(screen, LINE, r, 1)
                txt = self.small.render(s, True, theme.PALETTE["text"])
                screen.blit(txt, txt.get_rect(center=r.center))
                action_buttons[s] = r
                x2 = r.x + r.width + 4
            # Back button
            r = pygame.Rect(x2, bottom.y + 4, 70, bottom.height - 8)
            pygame.draw.rect(screen, (70, 72, 82), r)
            pygame.draw.rect(screen, LINE, r, 1)
            txt = self.small.render("Back", True, theme.PALETTE["text"])
            screen.blit(txt, txt.get_rect(center=r.center))
            action_buttons["back"] = r

        return action_buttons, auto_button
