from __future__ import annotations

"""Minimal screen to render a town scene using :class:`TownSceneRenderer`."""

import os
from typing import Any

import pygame
import constants

from loaders.town_scene_loader import TownScene
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

    def run(self) -> None:
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
                    running = False
            self.renderer.draw(self.screen, {})
            pygame.display.flip()
            self.clock.tick(getattr(constants, "FPS", 60))


__all__ = ["TownSceneScreen"]
