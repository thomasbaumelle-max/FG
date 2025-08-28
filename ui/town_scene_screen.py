from __future__ import annotations

"""Minimal screen to render a town scene using :class:`TownSceneRenderer`."""

import os
from typing import Any

import pygame
import constants

from loaders.town_scene_loader import TownScene, TownBuilding
from render.town_scene_renderer import TownSceneRenderer


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

    def __init__(self, screen: pygame.Surface, scene: TownScene, assets: Any, clock: pygame.time.Clock | None = None) -> None:
        self.screen = screen
        self.clock = clock or pygame.time.Clock()
        self.renderer = TownSceneRenderer(scene, assets)

    def on_building_click(self, building: TownBuilding) -> bool:
        """Hook executed when a building hotspot is clicked.

        Subclasses may override this to open panels or trigger other actions.
        Return ``True`` to close the screen after handling the click.
        """

        # Placeholder action: override in subclass for real behaviour
        return False

    def run(self, debug: bool = False) -> None:
        if not (self.renderer.scene.layers or self.renderer.scene.buildings):
            return
        running = True
        fast_tests = os.environ.get("FG_FAST_TESTS") == "1"
        while running:
            events = pygame.event.get()
            if not events and fast_tests:
                break
            for event in events:
                if event.type == pygame.KEYDOWN and getattr(event, "key", None) == pygame.K_ESCAPE:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    for building in self.renderer.scene.buildings:
                        hotspot = getattr(building, "hotspot", None)
                        if not hotspot or len(hotspot) < 4:
                            continue
                        x1, y1, x2, y2 = hotspot[0], hotspot[1], hotspot[2], hotspot[3]
                        x, y = event.pos
                        if x1 <= x <= x2 and y1 <= y <= y2:
                            if self.on_building_click(building):
                                running = False
                            break
            self.renderer.draw(self.screen, {}, debug=debug)
            pygame.display.flip()
            self.clock.tick(getattr(constants, "FPS", 60))


__all__ = ["TownSceneScreen"]
