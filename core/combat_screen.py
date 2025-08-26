"""User interface drawing for the combat screen."""

from __future__ import annotations
from typing import Callable, Dict, Tuple, Optional, List
import json
from pathlib import Path
import pygame
import theme
import settings
from ui.widgets.icon_button import IconButton
from loaders import icon_loader as IconLoader

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

        # Preload commonly used action and stat icons
        self.action_icon_keys = {
            "move": "action_move",
            "melee": "action_attack",
            "ranged": "action_shoot",
            "spell": "action_cast",
            "wait": "action_wait",
            "ability": "action_use_ability",
            "flee": "action_flee",
            "surrender": "action_surrender",
            "auto": "action_auto_resolve",
            "next": "action_next_unit",
        }

        self.hotkeys = {
            "action_move": getattr(pygame, "K_m", ord("m")),
            "action_attack": getattr(pygame, "K_a", ord("a")),
            "action_shoot": getattr(pygame, "K_s", ord("s")),
            "action_cast": getattr(pygame, "K_c", ord("c")),
            "action_wait": getattr(pygame, "K_w", ord("w")),
            "action_use_ability": getattr(pygame, "K_u", ord("u")),
            "action_flee": getattr(pygame, "K_f", ord("f")),
            "action_surrender": getattr(pygame, "K_r", ord("r")),
            "action_auto_resolve": getattr(pygame, "K_z", ord("z")),
            "action_auto_combat": getattr(pygame, "K_h", ord("h")),
            "action_next_unit": getattr(pygame, "K_n", ord("n")),
        }
        self.stat_icon_keys = {
            "hp": "stat_hp",
            "mana": "stat_mana",
            "attack": "stat_attack_range",
            "defence": "stat_defence_magic",
            "speed": "stat_speed",
            "initiative": "stat_initiative",
            "morale": "stat_morale",
            "luck": "stat_luck",
            # Elemental resistances
            "fire": "status_burn",
            "ice": "status_freeze",
            "shock": "status_stun",
            "earth": "status_petrify",
            "water": "status_slow",
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
    ) -> Tuple[Dict[str, IconButton], Optional[IconButton]]:
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

        action_buttons: Dict[str, IconButton] = {}
        auto_button: Optional[IconButton] = None

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
            # Elemental resistances
            for school, value in unit.resistances.as_dict().items():
                stats.append((school, f"{value}%"))
            y_stats = right.y + 42
            for name, value in stats:
                icon_key = self.stat_icon_keys.get(name, name)
                icon = IconLoader.get(icon_key, 18)
                screen.blit(icon, (right.x + 84, y_stats))
                txt_x = right.x + 84 + icon.get_width() + 4
                txt_val = value
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

            # Active status effects on the unit (displayed as icons with tooltips)
            effects = getattr(unit, "effects", [])
            if effects:
                y += 6
                screen.blit(
                    self.small.render("Status:", True, theme.PALETTE["text"]),
                    (right.x + 10, y),
                )
                y += 18
                x_stat = right.x + 20
                for idx, eff in enumerate(effects):
                    icon_id = eff.icon or f"status_{eff.name}"
                    rect = pygame.Rect(x_stat + idx * 22, y, 18, 18)
                    btn = IconButton(
                        rect,
                        icon_id,
                        lambda: None,
                        tooltip=f"{eff.name} ({eff.duration})",
                        enabled=False,
                    )
                    btn.draw(screen)
                    action_buttons[f"status_{idx}"] = btn
                y += 22

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
            auto_rect = pygame.Rect(right.x + 10, y, right.width - 20, BUTTON_H)
            auto_resolve_btn = IconButton(
                auto_rect,
                "action_auto_resolve",
                combat.auto_resolve,
                hotkey=self.hotkeys.get("action_auto_resolve"),
                tooltip="Auto resolve",
            )
            auto_resolve_btn.draw(screen)
            action_buttons["auto_resolve"] = auto_resolve_btn
            y = auto_rect.bottom + 6

            auto_combat_rect = pygame.Rect(right.x + 10, y, right.width - 20, BUTTON_H)
            auto_button = IconButton(
                auto_combat_rect,
                "action_auto_combat",
                combat.auto_combat,
                hotkey=self.hotkeys.get("action_auto_combat"),
                tooltip="Auto combat",
            )
            auto_button.draw(screen)
            y = auto_combat_rect.bottom + 6

            spell_rect = pygame.Rect(right.x + 10, y, right.width - 20, BUTTON_H)
            spell_btn = IconButton(
                spell_rect,
                "action_cast",
                lambda: combat.hero_spells and combat.show_spellbook(),
                hotkey=getattr(pygame, "K_s", ord("s")),
                tooltip="Spellbook",
                enabled=bool(combat.hero_spells),
            )
            spell_btn.draw(screen)
            action_buttons["spellbook"] = spell_btn
        # ---- Action bar (bottom) ----
        x = bottom.x + 8

        def add_btn(icon_id: str, callback: Callable[[], None]) -> None:
            nonlocal x
            size = bottom.height - 8
            rect = pygame.Rect(x, bottom.y + 4, size, size)
            label_key = icon_id.replace("action_", "")
            tooltip = self.action_labels.get(
                label_key, label_key.replace("_", " ").title()
            )
            btn = IconButton(
                rect,
                icon_id,
                callback,
                hotkey=self.hotkeys.get(icon_id),
                tooltip=tooltip,
            )
            btn.draw(screen)
            action_buttons[icon_id] = btn
            x = rect.x + rect.width + 6

        current = combat.turn_order[combat.current_index]

        def wait_action() -> None:
            current.acted = True
            combat.advance_turn()
            combat.selected_unit = None
            combat.selected_action = None

        callbacks = {
            "action_move": lambda: setattr(combat, "selected_action", "move"),
            "action_attack": lambda: setattr(combat, "selected_action", "melee"),
            "action_shoot": lambda: setattr(combat, "selected_action", "ranged"),
            "action_cast": lambda: setattr(combat, "selected_action", "spell"),
            "action_wait": wait_action,
            "action_use_ability": combat.use_ability,
            "action_flee": combat.flee,
            "action_surrender": combat.surrender,
            "action_auto_resolve": combat.auto_resolve,
            "action_next_unit": combat.select_next_unit,
        }

        actions = combat.get_available_actions(current)
        # Stable ordering for readability
        wanted = ["move", "melee", "ranged", "spell", "wait"]
        for a in wanted:
            if a in actions:
                icon = self.action_icon_keys.get(a, f"action_{a}")
                add_btn(icon, callbacks[icon])

        extras = [
            "action_use_ability",
            "action_flee",
            "action_surrender",
            "action_next_unit",
        ]
        for icon in extras:
            add_btn(icon, callbacks[icon])

        # Spell submenu when "spell" is selected
        if combat.selected_action == "spell":
            spells = sorted(combat.spells_by_name.keys())
            # Only show spells usable by the current unit
            caster = current
            allow = set(combat.UNIT_SPELLS.get(caster.stats.name, {}).keys())
            spells = [s for s in spells if s in allow]
            # Fold-out menu
            x2 = x
            for s in spells:
                rect = pygame.Rect(x2, bottom.y + 4, 140, bottom.height - 8)
                btn = IconButton(
                    rect,
                    "action_cast",
                    lambda s=s: combat.start_spell(caster, s),
                    tooltip=s,
                )
                btn.draw(screen)
                txt = self.small.render(s, True, theme.PALETTE["text"])
                screen.blit(txt, txt.get_rect(center=rect.center))
                action_buttons[s] = btn
                x2 = rect.x + rect.width + 4
            # Back button
            rect = pygame.Rect(x2, bottom.y + 4, 70, bottom.height - 8)
            back_btn = IconButton(
                rect,
                "action_move",
                lambda: setattr(combat, "selected_action", None),
                tooltip="Back",
            )
            back_btn.draw(screen)
            txt = self.small.render("Back", True, theme.PALETTE["text"])
            screen.blit(txt, txt.get_rect(center=rect.center))
            action_buttons["back"] = back_btn

        return action_buttons, auto_button
