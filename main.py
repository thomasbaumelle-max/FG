"""Entry point for the graphical Heroes‑like game.

Initialises Pygame, sets up the display window and launches the interactive
main menu.  The menu is responsible for starting new games, loading saved
ones or exiting the application."""

import os
import pygame

try:  # pragma: no cover - package vs script execution
    from . import constants, audio
    from .ui.menu import main_menu
    from .loaders.asset_manager import AssetManager
    from .ui.loading_screen import LoadingScreen
except ImportError:  # pragma: no cover - fallback when run as a script
    import constants, audio  # type: ignore
    from ui.menu import main_menu  # type: ignore
    from loaders.asset_manager import AssetManager  # type: ignore
    from ui.loading_screen import LoadingScreen  # type: ignore

def _compute_window_size() -> tuple[int, int]:
    """Determine an appropriate window size based on the default map."""

    map_path = os.path.join(os.path.dirname(__file__), "maps", "example_map.txt")
    window_width = constants.WINDOW_WIDTH
    window_height = constants.WINDOW_HEIGHT
    max_cols = rows = None
    map_width = map_height = None
    if os.path.isfile(map_path):
        with open(map_path, "r", encoding="utf-8") as f:
            lines = [line.rstrip("\n") for line in f]
        if lines:
            max_cols = max(len(line) for line in lines)
            rows = len(lines)
            map_width = max_cols * constants.TILE_SIZE
            map_height = rows * constants.TILE_SIZE + constants.UI_HEIGHT
            window_width = max(window_width, map_width)
            window_height = max(window_height, map_height)
    display_info = pygame.display.Info()
    screen_w, screen_h = display_info.current_w, display_info.current_h
    if window_width > screen_w or window_height > screen_h:
        scale = min(screen_w / window_width, screen_h / window_height)
        constants.TILE_SIZE = max(1, int(constants.TILE_SIZE * scale))
        constants.COMBAT_TILE_SIZE = max(1, int(constants.COMBAT_TILE_SIZE * scale))
        constants.UI_HEIGHT = int(constants.UI_HEIGHT * scale)
        width_from_default = not map_width or map_width <= constants.WINDOW_WIDTH
        height_from_default = not map_height or map_height <= constants.WINDOW_HEIGHT
        if width_from_default:
            window_width = int(constants.WINDOW_WIDTH * scale)
        else:
            window_width = min(screen_w, max_cols * constants.TILE_SIZE)
        if height_from_default:
            window_height = int(constants.WINDOW_HEIGHT * scale)
        else:
            window_height = min(screen_h, rows * constants.TILE_SIZE + constants.UI_HEIGHT)
    else:
        window_width = min(window_width, screen_w)
        window_height = min(window_height, screen_h)
    return window_width, window_height
    
def main() -> None:
    pygame.init()
    settings = audio.load_settings()
    constants.AI_DIFFICULTY = settings.get("ai_difficulty", constants.AI_DIFFICULTY)
    window_size = _compute_window_size()
    flags = pygame.FULLSCREEN if settings.get("fullscreen") else 0
    screen = pygame.display.set_mode(window_size, flags)
    pygame.display.set_caption("Fantasy Strategy Game")

    LoadingScreen(screen)
    repo_root = os.path.dirname(__file__)
    assets = AssetManager(repo_root)
    audio.init(assets)

    screen = main_menu(screen)
    pygame.quit()


if __name__ == "__main__":
    main()
