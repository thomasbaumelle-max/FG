
from __future__ import annotations

"""Reusable particle effect helpers and animation classes.

Centralises simple sprite based effects so they can be shared between the
combat system and other parts of the game.  Assets are loaded via
:class:`~loaders.asset_manager.AssetManager` which provides a dictionary like
interface and fallback images when files are missing.
"""

from dataclasses import dataclass, field
from typing import List, Optional

import pygame
import time

from loaders.asset_manager import AssetManager
import constants


@dataclass
class FXEvent:
    """Effect displaying a single static sprite."""

    sprite: pygame.Surface = field(repr=False)
    pos: pygame.math.Vector2
    duration: float
    z: int = 0
    velocity: Optional[pygame.math.Vector2] = None

    def update(self, dt: float) -> None:  # pragma: no cover - trivial
        if self.velocity:
            self.pos += self.velocity * dt
        self.duration -= dt

    def draw(self, surface: pygame.Surface) -> None:
        rect = self.sprite.get_rect(center=(int(self.pos.x), int(self.pos.y)))
        surface.blit(self.sprite, rect.topleft)


@dataclass
class AnimatedFX:
    """Effect cycling through a list of sprite frames."""

    frames: List[pygame.Surface] = field(repr=False, default_factory=list)
    pos: pygame.math.Vector2 = field(default_factory=lambda: pygame.math.Vector2(0, 0))
    duration: float = 0.0
    z: int = 0
    velocity: Optional[pygame.math.Vector2] = None
    frame_time: float = field(default=1 / constants.FPS)
    _timer: float = field(default=0, init=False, repr=False)
    _index: int = field(default=0, init=False, repr=False)

    def draw(self, surface: pygame.Surface) -> None:
        if not self.frames:
            return
        frame = self.frames[min(self._index, len(self.frames) - 1)]
        rect = frame.get_rect(center=(int(self.pos.x), int(self.pos.y)))
        surface.blit(frame, rect.topleft)

    def update(self, dt: float) -> None:
        if self.velocity:
            self.pos += self.velocity * dt
        self.duration -= dt
        if self.duration <= 0 or not self.frames:
            return
        self._timer += dt
        while self._timer >= self.frame_time and self.duration > 0:
            self._timer -= self.frame_time
            self._index += 1
            if self._index >= len(self.frames):
                self.duration = 0
                break


class FXQueue:
    """Queue managing temporary visual effects."""

    def __init__(self) -> None:
        self._events: List[FXEvent | AnimatedFX] = []
        self._last_time = time.perf_counter()

    def add(self, event: FXEvent | AnimatedFX) -> None:
        self._events.append(event)

    def update_and_draw(self, surface: pygame.Surface) -> None:
        now = time.perf_counter()
        dt = now - self._last_time
        self._last_time = now

        for ev in list(self._events):
            ev.update(dt)
        self._events = [e for e in self._events if e.duration > 0]

        for ev in sorted(self._events, key=lambda e: e.z):
            ev.draw(surface)


def load_animation(
    assets: AssetManager,
    key: str,
    frame_width: int,
    frame_height: int,
) -> List[pygame.Surface]:
    """Load ``key`` from ``assets`` and slice into equally sized frames."""

    sheet = assets.get(key)
    if sheet is None:
        return []
    rect = sheet.get_rect()
    frames: List[pygame.Surface] = []
    for y in range(0, rect.height, frame_height):
        for x in range(0, rect.width, frame_width):
            frame_surface = pygame.Surface((frame_width, frame_height), pygame.SRCALPHA)
            frame_surface.blit(sheet, (0, 0), pygame.Rect(x, y, frame_width, frame_height))
            frames.append(frame_surface)
    return frames
