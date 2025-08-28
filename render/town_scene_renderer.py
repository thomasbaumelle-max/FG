from __future__ import annotations

"""Renderer for :class:`loaders.town_scene_loader.TownScene` instances."""

from typing import Dict, Mapping, Any

import pygame
import constants

from loaders.town_scene_loader import TownScene


class TownSceneRenderer:
    """Draw a :class:`TownScene` onto a surface.

    Parameters
    ----------
    scene:
        Parsed town scene definition.
    assets:
        Asset manager providing a ``get`` method returning ``pygame.Surface``
        objects.
    """

    def __init__(self, scene: TownScene, assets: Any) -> None:
        self.scene = scene
        self.assets = assets
        # Preload layer and building images for quick rendering.
        self._layer_imgs: Dict[str, pygame.Surface] = {}
        for layer in scene.layers:
            img = assets.get(layer.image) if layer.image else None
            if img is not None:
                self._layer_imgs[layer.id] = img
        self._building_imgs: Dict[str, Dict[str, pygame.Surface]] = {}
        for building in scene.buildings:
            states: Dict[str, pygame.Surface] = {}
            for state, img_path in building.states.items():
                img = assets.get(img_path)
                if img is not None:
                    states[state] = img
            self._building_imgs[building.id] = states

    def draw(self, surface: pygame.Surface, states: Mapping[str, str], debug: bool = False) -> None:
        """Render the scene to ``surface``.

        Parameters
        ----------
        surface:
            Destination surface to draw onto.
        states:
            Mapping of building id to state name (e.g. ``"built"`` or
            ``"unbuilt"``).  Missing entries default to ``"unbuilt"``.
        """

        # Draw static layers in their defined order
        for layer in self.scene.layers:
            img = self._layer_imgs.get(layer.id)
            if img is not None:
                surface.blit(img, (0, 0))

        # Draw buildings according to their current state
        for building in sorted(self.scene.buildings, key=lambda b: b.z_index):
            state = states.get(building.id, "unbuilt")
            building_states = self._building_imgs.get(building.id, {})
            img = building_states.get(state)

            if img is None:
                img = next(iter(building_states.values()), None)

            if img is not None:
                surface.blit(img, building.pos)
                if debug and getattr(building, "hotspot", None):
                    hs = building.hotspot
                    if len(hs) >= 3:
                        pygame.draw.polygon(surface, constants.MAGENTA, hs, 1)


__all__ = ["TownSceneRenderer"]
