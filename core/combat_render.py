"""Utility functions for rendering the combat interface."""

from __future__ import annotations

from typing import Tuple

import os
import math
import pygame
import constants
import theme


def draw(combat, frame: int = 0) -> None:
    """Render the combat grid and units to the screen.

    When unit sprites are provided as sprite sheets, ``frame`` selects the
    current animation frame within the ranges specified by each unit's
    :class:`~entities.UnitStats`.
    """
    # Start with a clean slate so the world map isn't visible behind the
    # combat grid.  The background is simply filled with black.
    combat.screen.fill(constants.BLACK)

    screen_w, screen_h = combat.screen.get_size()
    margin = 10
    right_min = 200
    bottom_min = 60
    combat.zoom = min(
        (screen_w - right_min - margin * 3) / combat.grid_pixel_width,
        (screen_h - bottom_min - margin * 3) / combat.grid_pixel_height,
    )
    tile_w = int(constants.COMBAT_HEX_SIZE * combat.zoom)
    tile_h = int(constants.COMBAT_HEX_SIZE * combat.zoom * math.sqrt(3) / 2)
    grid_w = int(combat.grid_pixel_width * combat.zoom)
    grid_h = int(combat.grid_pixel_height * combat.zoom)
    combat.offset_x = margin
    combat.offset_y = margin
    panel_x = combat.offset_x + grid_w + margin
    panel_y = combat.offset_y
    panel_w = screen_w - panel_x - margin
    panel_h = grid_h
    bottom_x = combat.offset_x
    bottom_y = combat.offset_y + grid_h + margin
    bottom_w = grid_w
    bottom_h = screen_h - bottom_y - margin

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
        if bg.get_size() != (grid_w, grid_h):
            bg = pygame.transform.scale(bg, (grid_w, grid_h))
        combat.screen.blit(bg, (combat.offset_x, combat.offset_y))
    else:
        combat.screen.fill(
            constants.GREEN, pygame.Rect(combat.offset_x, combat.offset_y, grid_w, grid_h)
        )

    if getattr(combat, "hero", None):
        img = getattr(combat.hero, "battlefield_image", None)
        if isinstance(img, pygame.Surface):
            w, h = img.get_size()
            if combat.zoom != 1:
                img = pygame.transform.scale(img, (int(w * combat.zoom), int(h * combat.zoom)))
                w, h = img.get_size()
            hx, hy = getattr(combat.battlefield, "hero_pos", (0, 0))
            x = combat.offset_x + int(hx * combat.zoom)
            y = combat.offset_y + int(hy * combat.zoom)
            combat.screen.blit(img, (x, y))

    # Hex grid overlay
    for x in range(constants.COMBAT_GRID_WIDTH):
        for y in range(constants.COMBAT_GRID_HEIGHT):
            rect = combat.cell_rect(x, y)
            points = [
                (rect.x + rect.w * 0.25, rect.y),
                (rect.x + rect.w * 0.75, rect.y),
                (rect.x + rect.w, rect.y + rect.h / 2),
                (rect.x + rect.w * 0.75, rect.y + rect.h),
                (rect.x + rect.w * 0.25, rect.y + rect.h),
                (rect.x, rect.y + rect.h / 2),
            ]
            pygame.draw.polygon(overlay, (255, 255, 255, 40), points, 1)

    # Draw decorative flora if any
    if combat.flora_loader and combat.flora_props:

        def grid_to_screen(tx: int, ty: int) -> Tuple[int, int]:
            r = combat.cell_rect(tx, ty)
            return r.centerx, r.bottom

        decals = []
        others = []
        for p in combat.flora_props:
            a = combat.flora_loader.assets.get(p.asset_id)
            if a and a.type == "decal":
                decals.append(p)
            else:
                others.append(p)
        if decals:
            combat.flora_loader.draw_props(combat.screen, decals, grid_to_screen)
        if others:
            combat.flora_loader.draw_props(combat.screen, others, grid_to_screen)
    # Highlight reachable squares when preparing a movement action
    if (
        combat.selected_unit
        and not combat.casting_spell
        and combat.selected_action == "move"
    ):
        reachable = combat.reachable_squares(combat.selected_unit)
        highlight_img = combat.assets.get("highlight")
        for (cx, cy) in reachable:
            rect = combat.cell_rect(cx, cy)
            if highlight_img:
                if rect.size != highlight_img.get_size():
                    img = pygame.transform.scale(highlight_img, rect.size)
                else:
                    img = highlight_img
                overlay.blit(img, rect.topleft)
            else:
                s = pygame.Surface(rect.size, pygame.SRCALPHA)
                s.fill((0, 0, 255, 100))
                overlay.blit(s, rect.topleft)
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
        highlight_img = combat.assets.get("highlight")
        for (cx, cy) in targets:
            rect = combat.cell_rect(cx, cy)
            if highlight_img:
                if rect.size != highlight_img.get_size():
                    img = pygame.transform.scale(highlight_img, rect.size)
                else:
                    img = highlight_img
                overlay.blit(img, rect.topleft)
            else:
                s = pygame.Surface(rect.size, pygame.SRCALPHA)
                s.fill((255, 0, 0, 100))
                overlay.blit(s, rect.topleft)

    # Highlight attackable squares when preparing an attack action
    if (
        combat.selected_unit
        and not combat.casting_spell
        and combat.selected_action in ("melee", "ranged")
    ):
        targets = combat.attackable_squares(combat.selected_unit, combat.selected_action)
        key = "melee_range" if combat.selected_action == "melee" else "ranged_range"
        highlight_img = combat.assets.get(key)
        for (cx, cy) in targets:
            rect = combat.cell_rect(cx, cy)
            if highlight_img:
                if rect.size != highlight_img.get_size():
                    img = pygame.transform.scale(highlight_img, rect.size)
                else:
                    img = highlight_img
                overlay.blit(img, rect.topleft)
            else:
                colour = (
                    constants.RED
                    if combat.selected_action == "melee"
                    else constants.YELLOW
                )
                s = pygame.Surface(rect.size, pygame.SRCALPHA)
                s.fill((*colour, 100))
                overlay.blit(s, rect.topleft)

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
            if rect.size != img.get_size():
                img = pygame.transform.scale(img, rect.size)
            if not combat.unit_shadow_baked.get(key or "", False):
                combat.screen.blit(shadow_surf, rect.topleft)
            combat.screen.blit(img, rect.topleft)
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
    if combat.turn_order:
        current = combat.turn_order[combat.current_index]
        # --- HUD (panneau + barre actions) ---
        combat.action_buttons, combat.auto_button = combat.hud.draw(
            combat.screen, combat, frame
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
            if combat.selected_action in ("spell", "spellbook"):
                if action in ("back", "spellbook"):
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

