from __future__ import annotations

"""Minimal screen to render a town scene using :class:`TownSceneRenderer`."""

import os
from typing import Any, Mapping

import pygame
import constants

from loaders.town_scene_loader import TownScene, TownBuilding
from render.town_scene_renderer import TownSceneRenderer
from core import economy
from state.game_state import PlayerResources
from . import (
    market_screen,
    castle_overlay,
    tavern_overlay,
    bounty_overlay,
    recruit_overlay,
    spellbook_overlay,
    build_structure_overlay,
)
from .town_common import (
    draw_army_row,
    draw_label,
    ROW_H,
    RESBAR_H,
    TOPBAR_H,
    GAP,
)
from .town_screen import TownScreen, FONT_NAME, COLOR_PANEL
from .widgets.resources_bar import ResourcesBar


def _point_in_poly(pt: tuple[int, int], poly: list[tuple[int, int]]) -> bool:
    x, y = pt
    inside = False
    j = len(poly) - 1
    for i in range(len(poly)):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


class TownSceneScreen:
    """Display a static town scene.

    Parameters
    ----------
    screen:
        Target surface to draw onto.
    scene:
        Parsed scene definition.
    assets:
        Asset manager providing access to loaded images.
    clock:
        Optional pygame clock for regulating the loop.
    """

    def __init__(
        self,
        screen: pygame.Surface,
        scene: TownScene,
        assets: Any,
        clock: pygame.time.Clock | None = None,
        building_states: Mapping[str, str] | None = None,
        game: Any | None = None,
        town: Any | None = None,
    ) -> None:
        self.screen = screen
        self.clock = clock or pygame.time.Clock()
        self.renderer = TownSceneRenderer(scene, assets)
        self.building_states = dict(building_states) if building_states else {}
        self.game = game
        self.town = town
        self.hero = getattr(game, "hero", None) if game else None
        self.army_units = getattr(self.hero, "army", []) if self.hero else []

        self.font = pygame.font.SysFont(FONT_NAME, 18)
        self.font_small = pygame.font.SysFont(FONT_NAME, 14)
        self.font_big = pygame.font.SysFont(FONT_NAME, 20, bold=True)

        self.res_bar = ResourcesBar()
        if self.hero is not None:
            pr = PlayerResources(
                gold=getattr(self.hero, "gold", 0),
                wood=self.hero.resources.get("wood", 0),
                stone=self.hero.resources.get("stone", 0),
                crystal=self.hero.resources.get("crystal", 0),
            )
            self.res_bar.set_resources(pr)

    def on_building_click(self, building: TownBuilding) -> bool:
        """Hook executed when a building hotspot is clicked.

        Subclasses may override this to open panels or trigger other actions.
        Return ``True`` to close the screen after handling the click.
        """
        if not (self.game and self.town):
            return False

        sid = getattr(building, "id", "")
        hero = getattr(self.game, "hero", None)
        if not sid or hero is None:
            return False

        # Build structure if not yet built
        if not self.town.is_structure_built(sid):
            if self.town.built_today:
                return False
            confirmed = build_structure_overlay.open(
                self.screen, self.town, hero, sid, self.clock
            )
            if confirmed:
                player = economy.PlayerEconomy()
                player.resources.update(getattr(hero, "resources", {}))
                player.resources["gold"] = getattr(hero, "gold", 0)
                if self.town.build_structure(sid, hero, player):
                    if hasattr(self.game, "_publish_resources"):
                        self.game._publish_resources()
                    self.building_states[sid] = "built"
            return False

        # Already built -> open corresponding panel
        if sid == "market":
            market_screen.open(self.screen, self.game, self.town, hero, self.clock)
        elif sid == "castle":
            castle_overlay.open(self.screen, self.game, self.town, hero, self.clock)
        elif sid == "tavern":
            tavern_overlay.open(self.screen, self.game, self.town, hero, self.clock)
        elif sid == "bounty_board":
            bounty_overlay.open(self.screen, self.game, self.town, hero, self.clock)
        elif sid == "magic_school":
            spellbook_overlay.open(self.screen, self.game, self.town, hero, self.clock)
        else:
            units = self.town.recruitable_units(sid)
            if units:
                recruit_overlay.open(
                    self.screen,
                    self.game,
                    self.town,
                    hero,
                    self.clock,
                    sid,
                    units[0],
                )
        return True

    def run(self, debug: bool = False) -> bool | None:
        if not (self.renderer.scene.layers or self.renderer.scene.buildings):
            return False
        running = True
        result: bool | None = None
        fast_tests = os.environ.get("FG_FAST_TESTS") == "1"
        while running:
            dt = self.clock.tick(getattr(constants, "FPS", 60)) / 1000.0
            layout = self._compute_layout()
            events = pygame.event.get()
            if not events and fast_tests:
                break
            for event in events:
                if event.type == pygame.KEYDOWN:
                    key = getattr(event, "key", None)
                    if key == pygame.K_ESCAPE:
                        running = False
                        result = None
                    elif key == pygame.K_F1:
                        debug = not debug
                    elif key == pygame.K_F2:
                        running = False
                        result = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if any(rect.collidepoint(event.pos) for rect in layout.values()):
                        continue
                    for building in self.renderer.scene.buildings:
                        hotspot = getattr(building, "hotspot", [])
                        if hotspot and _point_in_poly(event.pos, hotspot):
                            if self.on_building_click(building):
                                running = False
                                result = True
                            break
            self.renderer.draw(self.screen, self.building_states, debug=debug)
            if self.town is not None:
                pygame.draw.rect(self.screen, COLOR_PANEL, layout["top_bar"])
                pygame.draw.rect(self.screen, COLOR_PANEL, layout["garrison_row"])
                pygame.draw.rect(self.screen, COLOR_PANEL, layout["hero_row"])
                pygame.draw.rect(self.screen, COLOR_PANEL, layout["resbar"])
                draw_label(
                    self.screen,
                    self.font_big,
                    self.town.name,
                    pygame.Rect(
                        layout["top_bar"].x + 20, layout["top_bar"].y + 8, 0, 0
                    ),
                )
                draw_label(
                    self.screen,
                    self.font_big,
                    "Garrison",
                    layout["garrison_row"].inflate(-8, -ROW_H + 24).move(8, 4),
                )
                draw_label(
                    self.screen,
                    self.font_big,
                    "Visiting Hero",
                    layout["hero_row"].inflate(-8, -ROW_H + 24).move(8, 4),
                )
                draw_army_row(
                    self.screen,
                    self.font,
                    self.font_small,
                    getattr(self.town, "garrison", []),
                    layout["garrison_row"],
                )
                draw_army_row(
                    self.screen,
                    self.font,
                    self.font_small,
                    self.army_units,
                    layout["hero_row"],
                )
                self.res_bar.update(dt)
                self.res_bar.draw(self.screen, layout["resbar"])
            pygame.display.flip()
        return result

    def _compute_layout(self) -> dict[str, pygame.Rect]:
        """Compute rectangles for UI elements."""
        W, H = self.screen.get_size()
        rects: dict[str, pygame.Rect] = {}
        rects["top_bar"] = pygame.Rect(0, 0, W, TOPBAR_H)
        rects["resbar"] = pygame.Rect(0, H - RESBAR_H, W, RESBAR_H)
        rects["hero_row"] = pygame.Rect(20, H - RESBAR_H - GAP - ROW_H, W - 40, ROW_H)
        rects["garrison_row"] = pygame.Rect(
            20, rects["hero_row"].y - GAP - ROW_H, W - 40, ROW_H
        )
        return rects


__all__ = ["TownSceneScreen"]
