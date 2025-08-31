"""Utility helpers for simple modal dialogs."""

from __future__ import annotations

from typing import Callable, Iterable, Tuple, Any

import pygame

import constants
import audio


def run_dialog(
    screen: pygame.Surface,
    clock: pygame.time.Clock,
    draw_fn: Callable[[], None],
    buttons: Iterable[Tuple[pygame.Rect, Any]],
    escape_result: Any,
    on_escape: Callable[[], None] | None = None,
):
    """Handle a basic dialog event loop.

    ``draw_fn`` is called every frame to draw the dialog. ``buttons`` is an
    iterable of ``(rect, result)`` pairs where ``rect`` is checked for mouse
    clicks and ``result`` is returned when it is clicked. Pressing *Escape*
    triggers ``on_escape`` if provided and returns ``escape_result``.
    """
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                audio.play_sound("ui_cancel")
                if on_escape:
                    on_escape()
                return escape_result
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for rect, result in buttons:
                    if rect.collidepoint(event.pos):
                        audio.play_sound("ui_confirm")
                        return result
        draw_fn()
        pygame.display.flip()
        clock.tick(constants.FPS)
