from __future__ import annotations

"""Minimal screen to render a town scene using :class:`TownSceneRenderer`."""

import os
from typing import Any, Mapping

import pygame
import constants

from loaders.town_scene_loader import TownScene, TownBuilding
from render.town_scene_renderer import TownSceneRenderer
from core import economy
from . import market_screen
from .town_screen import TownScreen


def _point_in_poly(pt: tuple[int, int], poly: list[tuple[int, int]]) -> bool:
    x, y = pt
    inside = False
    j = len(poly) - 1
    for i in range(len(poly)):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if ((yi > y) != (yj > y)) and (
            x < (xj - xi) * (y - yi) / (yj - yi) + xi
        ):
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
            cost = self.town.structure_cost(sid)
            if TownScreen._can_afford(hero, cost):
                player = economy.PlayerEconomy()
                player.resources.update(getattr(hero, "resources", {}))
                player.resources["gold"] = getattr(hero, "gold", 0)
                if self.town.build_structure(sid, hero, player):
                    if hasattr(self.game, "_publish_resources"):
                        self.game._publish_resources()
                    self.building_states[sid] = "built"
            return False

        # Already built -> open corresponding panel
        ts = TownScreen(self.screen, self.game, self.town, clock=self.clock)
        if sid == "market":
            market_screen.open(self.screen, self.game, self.town, hero, self.clock)
        elif sid == "castle":
            ts._open_castle_overlay()
            ts.run()
        elif sid == "tavern":
            ts._open_tavern_overlay()
            ts.run()
        elif sid == "bounty_board":
            ts._open_bounty_overlay()
        elif sid == "magic_school":
            ts._open_spellbook_overlay()
        else:
            units = self.town.recruitable_units(sid)
            if units:
                ts._open_recruit_overlay(sid, units[0])
                ts.run()
        return True

    def run(self, debug: bool = False) -> bool:
        if not (self.renderer.scene.layers or self.renderer.scene.buildings):
            return False
        running = True
        handled = False
        fast_tests = os.environ.get("FG_FAST_TESTS") == "1"
        while running:
            events = pygame.event.get()
            if not events and fast_tests:
                break
            for event in events:
                if event.type == pygame.KEYDOWN:
                    key = getattr(event, "key", None)
                    if key == pygame.K_ESCAPE:
                        running = False
                    elif key == pygame.K_F1:
                        debug = not debug
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    for building in self.renderer.scene.buildings:
                        hotspot = getattr(building, "hotspot", [])
                        if hotspot and _point_in_poly(event.pos, hotspot):
                            if self.on_building_click(building):
                                running = False
                                handled = True
                            break
            self.renderer.draw(self.screen, self.building_states, debug=debug)
            pygame.display.flip()
            self.clock.tick(getattr(constants, "FPS", 60))
        return handled


__all__ = ["TownSceneScreen"]
