"""User interface drawing for the combat screen."""

from __future__ import annotations
from typing import Dict, Tuple, Optional
import json
from pathlib import Path
import pygame
import theme
import settings

BUTTON_H = 28
# Slightly wider and taller panel to fit spells/statuses
PANEL_W = 300
PANEL_EXTRA_H = 120
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

        # Load icon manifest describing action/stat/status icons
        icons_file = (
            Path(__file__).resolve().parents[1]
            / "assets"
            / "icons"
            / "icons.json"
        )
        try:
            with icons_file.open("r", encoding="utf8") as fh:
                self._icon_manifest = json.load(fh)
        except Exception:
            self._icon_manifest = {}

        self._icon_cache: Dict[Tuple[str, int], Optional[pygame.Surface]] = {}

        # Preload commonly used action and stat icons
        self.action_icon_keys = {
            "move": "action_move",
            "melee": "action_attack",
            "ranged": "action_shoot",
            "spell": "action_cast",
            "wait": "action_wait",
        }
        self.stat_icon_keys = {
            "hp": "stat_hp",
            "mana": "round_mana",
            "attack": "round_attack_range",
            "defence": "round_defence_magic",
            "speed": "resource_speed",
            "initiative": "resource_speed",
            "morale": "round_morale",
            "luck": "round_luck",
        }

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

    def _load_icon(self, key: str, size: int) -> Optional[pygame.Surface]:
        """Return icon ``key`` scaled to ``size`` or ``None`` on failure."""
        cache_key = (key, size)
        if cache_key in self._icon_cache:
            return self._icon_cache[cache_key]

        info = self._icon_manifest.get(key)
        icon: Optional[pygame.Surface] = None
        try:
            if isinstance(info, dict):
                if "file" in info:
                    path = (
                        Path(__file__).resolve().parents[1]
                        / "assets"
                        / info["file"]
                    )
                    if path.exists() and hasattr(pygame.image, "load"):
                        icon = pygame.image.load(str(path))
                        if hasattr(icon, "convert_alpha"):
                            icon = icon.convert_alpha()
                elif "sheet" in info:
                    sheet_path = (
                        Path(__file__).resolve().parents[1]
                        / "assets"
                        / info["sheet"]
                    )
                    coords = info.get("coords", [0, 0])
                    tile = info.get("tile", [0, 0])
                    if (
                        sheet_path.exists()
                        and tile[0]
                        and tile[1]
                        and hasattr(pygame.image, "load")
                    ):
                        sheet = pygame.image.load(str(sheet_path))
                        if hasattr(sheet, "convert_alpha"):
                            sheet = sheet.convert_alpha()
                        rect = pygame.Rect(
                            coords[0] * tile[0],
                            coords[1] * tile[1],
                            tile[0],
                            tile[1],
                        )
                        icon = sheet.subsurface(rect)
            if icon and hasattr(pygame.transform, "scale"):
                icon = pygame.transform.scale(icon, (size, size))
        except Exception:
            icon = None

        self._icon_cache[cache_key] = icon
        return icon

    def _panel_rects(
        self,
        screen: pygame.Surface,
        grid_rect: pygame.Rect,
        combat,
    ) -> Tuple[pygame.Rect, pygame.Rect]:
        """Return rectangles for the side and bottom panels."""
        x = grid_rect.x + grid_rect.width + combat.side_margin + MARGIN
        right = pygame.Rect(
            x,
            grid_rect.y - combat.top_margin,
            PANEL_W,
            grid_rect.height + combat.top_margin + PANEL_EXTRA_H,
        )
        bottom = pygame.Rect(
            grid_rect.x,
            grid_rect.y + grid_rect.height + MARGIN,
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

            # Stats with icons
            stats = [
                ("hp", f"{unit.current_hp}/{unit.stats.max_hp}"),
                ("mana", f"{unit.mana}/{unit.max_mana}"),
                ("attack", f"{unit.stats.attack_min}-{unit.stats.attack_max}"),
                (
                    "defence",
                    f"M/R/Mg {unit.stats.defence_melee}/"
                    f"{unit.stats.defence_ranged}/{unit.stats.defence_magic}",
                ),
                ("speed", str(unit.stats.speed)),
                ("initiative", str(unit.stats.initiative)),
                ("morale", str(unit.stats.morale)),
                ("luck", str(unit.stats.luck)),
            ]
            y_stats = right.y + 42
            for name, value in stats:
                icon_key = self.stat_icon_keys.get(name, name)
                icon = self._load_icon(icon_key, 18)
                if icon:
                    screen.blit(icon, (right.x + 84, y_stats))
                    txt_x = right.x + 84 + icon.get_width() + 4
                    txt_val = value
                else:
                    # Fallback to text label when icon missing
                    txt_x = right.x + 84
                    txt_val = f"{name.title()} {value}"
                txt = self.font.render(txt_val, True, theme.PALETTE["text"])
                screen.blit(txt, (txt_x, y_stats))
                y_stats += 18

            # Spells available to the unit
            y = y_stats + 10
            spells = []
            for name, cost in combat.UNIT_SPELLS.get(unit.stats.name, {}).items():
                if name in combat.spells_by_name and unit.mana >= cost:
                    spells.append((name, cost))
            if spells:
                screen.blit(
                    self.small.render("Spells:", True, theme.PALETTE["text"]),
                    (right.x + 10, y),
                )
                y += 18
                for name, cost in spells:
                    txt = self.small.render(f"{name} ({cost})", True, theme.PALETTE["text"])
                    screen.blit(txt, (right.x + 20, y))
                    y += 18

            # Active statuses on the unit
            statuses = combat.statuses.get(unit, {})
            if statuses:
                y += 6
                screen.blit(
                    self.small.render("Status:", True, theme.PALETTE["text"]),
                    (right.x + 10, y),
                )
                y += 18
                for name, turns in statuses.items():
                    icon = self._load_icon(f"status_{name}", 18)
                    if icon:
                        screen.blit(icon, (right.x + 20, y))
                        txt = self.small.render(
                            str(turns), True, theme.PALETTE["text"]
                        )
                        screen.blit(
                            txt,
                            (
                                right.x + 20 + icon.get_width() + 4,
                                y + (icon.get_height() - txt.get_height()) // 2,
                            ),
                        )
                        y += icon.get_height() + 4
                    else:
                        txt = self.small.render(
                            f"{name} ({turns})", True, theme.PALETTE["text"]
                        )
                        screen.blit(txt, (right.x + 20, y))
                        y += 18

            # Turn order thumbnails
            y0 = y + 10
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
            size = bottom.height - 8
            icon_key = self.action_icon_keys.get(key, f"action_{key}")
            icon = self._load_icon(icon_key, size - 4)
            if icon:
                r = pygame.Rect(x, bottom.y + 4, size, size)
                pygame.draw.rect(screen, (52, 55, 63), r)
                pygame.draw.rect(screen, LINE, r, 1)
                screen.blit(icon, icon.get_rect(center=r.center))
            else:
                txt = self.small.render(label, True, theme.PALETTE["text"])
                w = max(40, txt.get_width() + 12)
                r = pygame.Rect(x, bottom.y + 4, w, size)
                pygame.draw.rect(screen, (52, 55, 63), r)
                pygame.draw.rect(screen, LINE, r, 1)
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
