from __future__ import annotations

import os
import pygame

from typing import Dict, List, Tuple

import theme
import constants
from loaders.boat_loader import BoatDef
from core.entities import Hero, Boat
from core.buildings import Shipyard


SLOT_COUNT = 7
SLOT_SIZE = 80
SLOT_GAP = 10
PANEL_PAD = 20
BUTTON_H = 28
FONT_NAME = None


def _can_afford(hero: Hero, cost: Dict[str, int]) -> bool:
    """Return ``True`` if hero has enough resources for ``cost``."""
    for res, amt in cost.items():
        if hero.resources.get(res, 0) < amt:
            return False
    return True


def _buy_boat(game, shipyard: Shipyard, bdef: BoatDef) -> None:
    """Deduct cost and spawn a boat next to ``shipyard``."""
    hero: Hero = game.hero
    for res, amt in bdef.cost.items():
        hero.resources[res] = hero.resources.get(res, 0) - int(amt)
    sx, sy = shipyard.origin
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            tx, ty = sx + dx, sy + dy
            if not game.world.in_bounds(tx, ty):
                continue
            tile = game.world.grid[ty][tx]
            if tile.biome in constants.WATER_BIOMES and tile.boat is None:
                boat = Boat(
                    id=bdef.id,
                    x=tx,
                    y=ty,
                    movement=bdef.movement,
                    capacity=bdef.capacity,
                    owner=0,
                )
                tile.boat = boat
                return


def open(
    screen: pygame.Surface,
    game,
    shipyard: Shipyard,
    clock: pygame.time.Clock | None = None,
) -> None:
    """Open the shipyard overlay allowing boat purchases."""
    if not pygame.display.get_init() or pygame.display.get_surface() is None:
        return

    clock = clock or pygame.time.Clock()
    font = theme.get_font(16) or pygame.font.SysFont(FONT_NAME, 16)
    font_small = theme.get_font(14) or pygame.font.SysFont(FONT_NAME, 14)

    panel_w = SLOT_COUNT * SLOT_SIZE + (SLOT_COUNT - 1) * SLOT_GAP + PANEL_PAD * 2
    panel_h = SLOT_SIZE + 80
    panel_rect = pygame.Rect(0, 0, panel_w, panel_h)
    panel_rect.center = screen.get_rect().center

    slot_rects: List[Tuple[pygame.Rect, pygame.Rect]] = []
    start_x = panel_rect.x + PANEL_PAD
    y = panel_rect.y + PANEL_PAD
    for i in range(SLOT_COUNT):
        rect = pygame.Rect(start_x + i * (SLOT_SIZE + SLOT_GAP), y, SLOT_SIZE, SLOT_SIZE)
        btn_rect = pygame.Rect(rect.x, rect.bottom + 32, SLOT_SIZE, BUTTON_H)
        slot_rects.append((rect, btn_rect))

    background = screen.copy()
    running = True
    hero = game.hero

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                boats = list(game.boat_defs.values())
                for idx, (_, btn) in enumerate(slot_rects):
                    if idx >= len(boats):
                        continue
                    if btn.collidepoint(event.pos) and _can_afford(hero, boats[idx].cost):
                        _buy_boat(game, shipyard, boats[idx])
                        running = False
                        break

        screen.blit(background, (0, 0))
        dim = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        dim.fill((*theme.PALETTE["background"], 200))
        screen.blit(dim, (0, 0))
        pygame.draw.rect(screen, theme.PALETTE["panel"], panel_rect)
        pygame.draw.rect(screen, theme.PALETTE["accent"], panel_rect, theme.FRAME_WIDTH)

        boats = list(game.boat_defs.values())
        asset_loader = getattr(game.ctx, "asset_loader", None)

        for idx, (slot, btn) in enumerate(slot_rects):
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
                    screen.blit(surf, surf.get_rect(center=slot.center))
                pygame.draw.rect(screen, theme.PALETTE["accent"], slot, theme.FRAME_WIDTH)
                y_text = slot.bottom + 4
                move_txt = font_small.render(
                    f"Move: {bdef.movement}", True, theme.PALETTE["text"]
                )
                screen.blit(move_txt, (slot.x, y_text))
                y_text += 16
                cap_txt = font_small.render(
                    f"Cap: {bdef.capacity}", True, theme.PALETTE["text"]
                )
                screen.blit(cap_txt, (slot.x, y_text))
                cost_line = ", ".join(f"{r}: {v}" for r, v in bdef.cost.items())
                cost_txt = font_small.render(cost_line, True, theme.PALETTE["text"])
                screen.blit(cost_txt, (btn.x, btn.y - 20))
                pygame.draw.rect(screen, theme.PALETTE["accent"], btn)
                pygame.draw.rect(screen, theme.PALETTE["text"], btn, theme.FRAME_WIDTH)
                label = font_small.render("Buy", True, theme.PALETTE["text"])
                screen.blit(label, label.get_rect(center=btn.center))
            else:
                pygame.draw.rect(screen, theme.PALETTE["accent"], slot, theme.FRAME_WIDTH)

        pygame.display.flip()
        if "PYTEST_CURRENT_TEST" in os.environ:
            break
        clock.tick(getattr(constants, "FPS", 30))


__all__ = ["open", "_buy_boat"]

