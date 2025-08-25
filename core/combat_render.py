"""Utility functions for rendering the combat interface."""

from __future__ import annotations

from typing import Tuple

import pygame
import constants
import theme
from .combat_screen import PANEL_W, BUTTON_H, MARGIN as HUD_MARGIN


def draw_hex(
    surface: pygame.Surface,
    rect: pygame.Rect,
    colour: Tuple[int, int, int],
    alpha: int,
    width: int = 0,
) -> None:
    """Draw a hexagon inside ``rect`` on ``surface``.

    The hexagon can be rendered filled or as an outline by adjusting ``width``.
    ``alpha`` controls the transparency of the drawn shape.
    """

    w = rect.width
    h = rect.height
    points = [
        (rect.x + w * 0.25, rect.y),
        (rect.x + w * 0.75, rect.y),
        (rect.x + w, rect.y + h / 2),
        (rect.x + w * 0.75, rect.y + h),
        (rect.x + w * 0.25, rect.y + h),
        (rect.x, rect.y + h / 2),
    ]
    draw = getattr(pygame, "draw", None)
    if draw and hasattr(draw, "polygon"):
        draw.polygon(surface, (*colour, alpha), points, width)


def draw(combat, frame: int = 0) -> None:
    """Render the combat grid and units to the screen.

    When unit sprites are provided as sprite sheets, ``frame`` selects the
    current animation frame within the ranges specified by each unit's
    :class:`~entities.UnitStats`.
    """
    # Start with a clean slate so the world map isn't visible behind the
    # combat grid.  Fill the surface with the panel colour so leftover space
    # matches the UI theme.
    combat.screen.fill(theme.PALETTE["panel"])

    screen_w, screen_h = combat.screen.get_size()
    bottom_min = BUTTON_H + 8
    combat.zoom = 1.0
    tile_w = int(combat.hex_width * combat.zoom)
    tile_h = int(combat.hex_height * combat.zoom)
    grid_w = int(combat.grid_pixel_width * combat.zoom)
    grid_h = int(combat.grid_pixel_height * combat.zoom)
    side_margin = 64
    top_margin = 128
    combat.offset_x = HUD_MARGIN + side_margin
    combat.offset_y = screen_h - bottom_min - HUD_MARGIN - grid_h
    shadow_surf = pygame.Surface((tile_w, tile_h), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow_surf, (0, 0, 0, 100), shadow_surf.get_rect())
    overlay = pygame.Surface(combat.screen.get_size(), pygame.SRCALPHA)

    # Draw battlefield background
    bg = getattr(combat, "_battlefield_bg", None)
    if bg is None:
        path = getattr(combat.battlefield, "image", "")
        if path:
            try:
                bg = pygame.image.load(path).convert_alpha()
            except Exception:
                bg = None
        else:
            bg = None
        combat._battlefield_bg = bg
    if bg:
        if bg.get_size() != (grid_w + 2 * side_margin, grid_h + top_margin):
            bg = pygame.transform.scale(
                bg, (grid_w + 2 * side_margin, grid_h + top_margin)
            )
        combat.screen.blit(
            bg, (combat.offset_x - side_margin, combat.offset_y - top_margin)
        )
    else:
        combat.screen.fill(
            constants.GREEN,
            pygame.Rect(
                combat.offset_x - side_margin,
                combat.offset_y - top_margin,
                grid_w + 2 * side_margin,
                grid_h + top_margin,
            ),
        )

    if getattr(combat, "hero", None):
        img = getattr(combat.hero, "battlefield_image", None)
        if isinstance(img, pygame.Surface):
            w, h = img.get_size()
            target_h = int(
                combat.hex_width * constants.HERO_HEX_FACTOR * combat.zoom
            )
            if h != target_h:
                scale = target_h / h
                img = pygame.transform.scale(img, (int(w * scale), target_h))
                w, h = img.get_size()
            hx, hy = getattr(combat.battlefield, "hero_pos", (0, 0))
            if 0 <= hx <= 1 and 0 <= hy <= 1:
                hx *= grid_w
                hy *= grid_h
            else:
                hx *= combat.zoom
                hy *= combat.zoom
            x = combat.offset_x + int(hx)
            base_h = int(combat.hex_width * combat.zoom)
            y = combat.offset_y + int(hy) - (h - base_h)
            combat.screen.blit(img, (x, y))

    # Hex grid overlay
    for x in range(constants.COMBAT_GRID_WIDTH):
        for y in range(constants.COMBAT_GRID_HEIGHT):
            rect = combat.cell_rect(x, y)
            draw_hex(overlay, rect, constants.WHITE, 40, width=1)

    # Highlight reachable squares when preparing a movement action
    if (
        combat.selected_unit
        and not combat.casting_spell
        and combat.selected_action == "move"
    ):
        reachable = combat.reachable_squares(combat.selected_unit)
        highlight_img = combat.assets.get("move_overlay")
        for (cx, cy) in reachable:
            rect = combat.cell_rect(cx, cy)
            if highlight_img:
                img = highlight_img
                if rect.size != highlight_img.get_size():
                    img = pygame.transform.scale(highlight_img, rect.size)
                overlay.blit(img, rect.topleft)
            else:
                draw_hex(overlay, rect, constants.GREEN, 100)
    # Highlight potential targets when preparing a spell
    if combat.casting_spell and combat.spell_caster and combat.selected_spell:
        targets: list[tuple[int, int]] = []
        if combat.selected_spell.target == "ally":
            targets = [
                (u.x, u.y)
                for u in combat.units
                if u.is_alive and u.side == combat.spell_caster.side
            ]
        elif combat.selected_spell.target == "cell":
            targets = [
                (x, y)
                for y in range(constants.COMBAT_GRID_HEIGHT)
                for x in range(constants.COMBAT_GRID_WIDTH)
            ]
        elif combat.selected_spell.target == "ally_cell":
            if combat.teleport_unit is None:
                targets = [
                    (u.x, u.y)
                    for u in combat.units
                    if u.is_alive and u.side == combat.spell_caster.side
                ]
            else:
                targets = [
                    (x, y)
                    for y in range(constants.COMBAT_GRID_HEIGHT)
                    for x in range(constants.COMBAT_GRID_WIDTH)
                    if combat.grid[y][x] is None and (x, y) not in combat.obstacles
                ]
        highlight_img = combat.assets.get("spell_overlay")
        for (cx, cy) in targets:
            rect = combat.cell_rect(cx, cy)
            if highlight_img:
                img = highlight_img
                if rect.size != highlight_img.get_size():
                    img = pygame.transform.scale(highlight_img, rect.size)
                overlay.blit(img, rect.topleft)
            else:
                draw_hex(overlay, rect, constants.BLUE, 100)

    # Highlight attackable squares when preparing an attack action
    if (
        combat.selected_unit
        and not combat.casting_spell
        and combat.selected_action in ("melee", "ranged")
    ):
        targets = combat.attackable_squares(
            combat.selected_unit, combat.selected_action
        )
        if combat.selected_action == "melee":
            highlight_img = (
                combat.assets.get("melee_overlay")
                or combat.assets.get("melee_range")
            )
            colour = constants.RED
        else:
            highlight_img = (
                combat.assets.get("ranged_overlay")
                or combat.assets.get("ranged_range")
            )
            colour = constants.YELLOW
        for (cx, cy) in targets:
            rect = combat.cell_rect(cx, cy)
            if highlight_img:
                img = highlight_img
                if rect.size != highlight_img.get_size():
                    img = pygame.transform.scale(highlight_img, rect.size)
                overlay.blit(img, rect.topleft)
            else:
                draw_hex(overlay, rect, colour, 100)

    blend = getattr(pygame, "BLEND_RGBA_ADD", 0)
    try:
        combat.screen.blit(overlay, (0, 0), special_flags=blend)
    except TypeError:
        combat.screen.blit(overlay, (0, 0))

    # Draw obstacles
    for (cx, cy) in combat.obstacles:
        rect = combat.cell_rect(cx, cy)
        img = combat.assets.get(constants.IMG_OBSTACLE)
        if img and rect.size != img.get_size():
            img = pygame.transform.scale(img, rect.size)
        if img:
            combat.screen.blit(img, rect.topleft)
        else:
            pygame.draw.rect(combat.screen, theme.PALETTE["panel"], rect)

    # Draw active ice walls
    for (cx, cy) in combat.ice_walls:
        rect = combat.cell_rect(cx, cy)
        img = combat.assets.get("ice_wall")
        if img:
            if rect.size != img.get_size():
                img = pygame.transform.scale(img, rect.size)
            combat.screen.blit(img, rect.topleft)
        else:
            pygame.draw.rect(combat.screen, constants.WHITE, rect)

    # Render transient effects before updating the unit grid so animation
    # frames for movement appear ahead of the final unit placement.
    combat.fx_queue.update_and_draw(combat.screen)

    # Draw units
    combat.units.sort(key=lambda u: (u.y, u.x))
    for unit in combat.units:
        if not unit.is_alive:
            continue
        rect = combat.cell_rect(unit.x, unit.y)
        img = None
        # Retrieve an explicit mapping for this unit and side if available;
        # otherwise default to the unit's ``stats.name`` asset id.
        key = combat.UNIT_IMAGE_KEYS.get(unit.stats.name, {}).get(
            unit.side, unit.stats.name
        )
        img = combat.assets.get(key)
        if img is None:
            frames = combat.assets.get(unit.stats.sheet)
            if isinstance(frames, list) and frames:
                start, end = (
                    unit.stats.hero_frames
                    if unit.side == "hero"
                    else unit.stats.enemy_frames
                )
                index = start + (frame % (end - start + 1))
                if 0 <= index < len(frames):
                    img = frames[index]
        if img:
            target_h = int(
                combat.hex_width * unit.stats.battlefield_scale * combat.zoom
            )
            w, h = img.get_size()
            if h != target_h:
                scale = target_h / h
                img = pygame.transform.scale(img, (int(w * scale), target_h))
                w, h = img.get_size()
            x = rect.center[0] - w // 2
            y = rect.bottom - h
            if not combat.unit_shadow_baked.get(key or "", False):
                combat.screen.blit(shadow_surf, rect.topleft)
            combat.screen.blit(img, (x, y))
        else:
            colour = (
                combat.hero_colour if unit.side == "hero" else constants.RED
            )
            pygame.draw.circle(combat.screen, colour, rect.center, rect.width // 3)
        font = pygame.font.SysFont(None, int(18 * combat.zoom))
        text = font.render(str(unit.count), True, constants.WHITE)
        combat.screen.blit(
            text, (rect.x + int(2 * combat.zoom), rect.y + int(2 * combat.zoom))
        )

    # Highlight the unit whose turn it is with a visual overlay
    if combat.turn_order:
        current = combat.turn_order[combat.current_index]
        if current.is_alive:
            rect = combat.cell_rect(current.x, current.y)
            overlay_img = combat.assets.get("active_unit")
            flag = getattr(pygame, "BLEND_RGBA_ADD", None)
            if overlay_img and flag is not None:
                if rect.size != overlay_img.get_size():
                    img = pygame.transform.scale(overlay_img, rect.size)
                else:
                    img = overlay_img
                try:
                    combat.screen.blit(img, rect.topleft, special_flags=flag)
                except pygame.error:
                    pygame.draw.rect(combat.screen, constants.YELLOW, rect, 3)
            else:
                pygame.draw.rect(combat.screen, constants.YELLOW, rect, 3)

    font = pygame.font.SysFont(None, 20)
    if combat.turn_order and len(getattr(combat, "assets", {})) > len(combat.units):
        current = combat.turn_order[combat.current_index]
        # --- HUD (panneau + barre actions) ---
        combat.action_buttons, combat.auto_button = combat.hud.draw(
            combat.screen, combat
        )


def handle_button_click(combat, current_unit, pos: Tuple[int, int]) -> bool:
    """Handle clicks on combat action buttons.

    Returns ``True`` if the click was consumed by the UI.
    """
    mx, my = pos
    if combat.auto_button and combat.auto_button.collidepoint(mx, my):
        combat.auto_mode = not combat.auto_mode
        return True

    for action, rect in combat.action_buttons.items():
        if rect.collidepoint(mx, my):
            if action == "spellbook":
                combat.show_spellbook()
            elif combat.selected_action == "spell":
                if action == "back":
                    combat.selected_action = None
                    break
                combat.start_spell(current_unit, action)
            elif action == "wait":
                current_unit.acted = True
                combat.advance_turn()
                combat.selected_unit = None
                combat.selected_action = None
            else:
                combat.selected_action = action
            return True
    return False
