from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import time
import pygame


@dataclass
class FXEvent:
    """Transient visual effect.

    Attributes:
        sprite: Surface to draw.
        pos:   Current position in pixels.
        duration: Remaining time in seconds.
        z:     Rendering order.
        velocity: Optional pixels-per-second movement.
    """

    sprite: pygame.Surface
    pos: pygame.math.Vector2
    duration: float
    z: int = 0
    velocity: Optional[pygame.math.Vector2] = None

    def update(self, dt: float) -> None:
        if self.velocity:
            self.pos += self.velocity * dt
        self.duration -= dt

    def draw(self, surface: pygame.Surface) -> None:
        rect = self.sprite.get_rect(center=(int(self.pos.x), int(self.pos.y)))
        surface.blit(self.sprite, rect.topleft)


class FXQueue:
    """Queue managing temporary visual effects.

    This class is intentionally generic so it can be reused by other modules
    such as the world map or status indicators.
    """

    def __init__(self) -> None:
        self._events: List[FXEvent] = []
        self._last_time = time.perf_counter()

    def add(self, event: FXEvent) -> None:
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
