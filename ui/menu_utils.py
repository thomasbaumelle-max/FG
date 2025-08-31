"""Utility functions shared by various menu screens."""

from __future__ import annotations

import os
from typing import Iterable, List, Optional, Tuple

import pygame

try:  # pragma: no cover - allow package and script use
    from .. import constants, audio
except ImportError:  # pragma: no cover
    import constants, audio  # type: ignore


def _load_background() -> Optional[pygame.Surface]:
    """Search for an optional background image for menus."""

    filenames = ["menu_background.png", "menu_backround.png"]
    base_dir = os.path.dirname(__file__)
    env_paths = os.environ.get("FG_ASSETS_DIR")
    search_dirs: List[str] = []
    if env_paths:
        search_dirs.extend(p for p in env_paths.split(os.pathsep) if p)
    search_dirs.append(os.path.join(base_dir, "assets"))
    search_dirs.append(os.path.join(os.path.dirname(base_dir), "assets"))
    for directory in search_dirs:
        for root, _dirs, files in os.walk(directory):
            for name in filenames:
                if name in files:
                    path = os.path.join(root, name)
                    try:  # pragma: no cover - depends on asset presence
                        return pygame.image.load(path)
                    except Exception:
                        return None
    return None


_BG_IMAGE: Optional[pygame.Surface] = _load_background()


def simple_menu(
    screen: pygame.Surface, options: Iterable[str], title: str | None = None
) -> Tuple[Optional[int], pygame.Surface]:
    """Display a list of ``options`` and return ``(choice, screen)``.

    The user navigates with arrow keys or *W/S*. Pressing Enter selects the
    current option. Pressing F11 toggles fullscreen. The function returns the
    possibly updated display surface alongside the chosen index (or ``None`` if
    the window was closed).
    """

    opts: List[str] = list(options)
    if not opts:
        return None, screen

    if not pygame.font.get_init():
        pygame.font.init()

    font = pygame.font.SysFont(None, 36)
    title_font = pygame.font.SysFont(None, 48)
    selected = 0
    clock = pygame.time.Clock()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None, screen
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_UP, pygame.K_w):
                    selected = (selected - 1) % len(opts)
                    audio.play_sound("list_scroll")
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    selected = (selected + 1) % len(opts)
                    audio.play_sound("list_scroll")
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    audio.play_sound("ui_confirm")
                    return selected, screen
                elif event.key == pygame.K_ESCAPE:
                    audio.play_sound("ui_cancel")
                    return None, screen
                elif event.key == pygame.K_F11:
                    pygame.display.toggle_fullscreen()
                    screen = pygame.display.get_surface()

        if _BG_IMAGE:
            bg = pygame.transform.scale(_BG_IMAGE, screen.get_size())
            screen.blit(bg, (0, 0))
        else:
            screen.fill(constants.BLACK)
        if title:
            text = title_font.render(title, True, constants.WHITE)
            rect = text.get_rect(
                center=(screen.get_width() // 2, screen.get_height() // 4)
            )
            screen.blit(text, rect)

        for i, option in enumerate(opts):
            colour = constants.YELLOW if i == selected else constants.WHITE
            text = font.render(option, True, colour)
            rect = text.get_rect(
                center=(screen.get_width() // 2, screen.get_height() // 2 + i * 40)
            )
            screen.blit(text, rect)

        pygame.display.flip()
        clock.tick(constants.FPS)


__all__ = ["simple_menu"]

