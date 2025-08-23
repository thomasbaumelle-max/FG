try:
    import os
    import json
    import pygame
    from typing import Dict, Optional
    try:
        from . import constants
        from .loaders.asset_manager import AssetManager
        from .loaders.core import Context, find_file
    except ImportError:  # pragma: no cover - package vs script
        import constants  # type: ignore
        from loaders.asset_manager import AssetManager  # type: ignore
        from loaders.core import Context, find_file  # type: ignore
except Exception:  # pragma: no cover - when pygame is unavailable
    pygame = None
    constants = None
    AssetManager = None  # type: ignore
    Context = None  # type: ignore
    find_file = None  # type: ignore

_sounds: Dict[str, 'pygame.mixer.Sound'] = {}
_music_enabled: bool = True
_current_music: Optional[str] = None
_music_volume: float = 1.0
_sfx_volume: float = 1.0
_SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "settings.json")

# Optional ``AssetManager`` used to locate audio assets.  When ``None`` the
# module falls back to searching the built-in ``assets`` directory only.
_asset_manager: AssetManager | None = None


def set_asset_manager(manager: AssetManager) -> None:
    """Provide an :class:`~loaders.asset_manager.AssetManager` for lookups."""

    global _asset_manager
    _asset_manager = manager


def _find_asset(filename: str) -> Optional[str]:
    """Search the configured asset paths for ``filename``."""

    search_paths: list[str]
    if _asset_manager is not None:
        search_paths = list(_asset_manager.search_paths)
    else:
        search_paths = [os.path.join(os.path.dirname(__file__), "assets")]

    if Context is None or find_file is None:  # pragma: no cover - defensive
        for base in search_paths:
            candidate = os.path.join(base, filename)
            if os.path.isfile(candidate):
                return candidate
        return None

    ctx = Context(repo_root="", search_paths=search_paths, asset_loader=None)
    try:
        return find_file(ctx, filename)
    except FileNotFoundError:
        return None


def _has_mixer() -> bool:
    return pygame is not None and hasattr(pygame, 'mixer')


def init(asset_manager: AssetManager | None = None) -> None:
    """Initialise mixer and load core sounds.

    ``asset_manager`` may be provided to configure additional search paths for
    audio files.  The function silently returns if pygame's mixer is
    unavailable.  Missing sound files are ignored so the rest of the game can
    run in minimal environments without the audio assets.
    """

    if asset_manager is not None:
        set_asset_manager(asset_manager)

    if not _has_mixer():
        return
    try:  # pragma: no cover - depends on system audio
        if not pygame.mixer.get_init():
            pygame.mixer.init()
    except Exception:
        return
    # Load predefined sounds
    if constants is None:
        return
    load_sound('move', constants.SOUND_MOVE)
    load_sound('attack', constants.SOUND_ATTACK)
    load_sound('victory', constants.SOUND_VICTORY)
    # UI interactions
    load_sound('hover', constants.SOUND_HOVER)
    load_sound('click', constants.SOUND_CLICK)
    load_sound('end_turn', constants.SOUND_END_TURN)


def load_sound(key: str, filename: str) -> None:
    """Load a sound from the assets directory under the given key."""
    if not _has_mixer():
        return
    path = _find_asset(filename)
    if path is None or not os.path.isfile(path):
        return
    try:  # pragma: no cover - loading depends on external files
        snd = pygame.mixer.Sound(path)
        snd.set_volume(_sfx_volume)
        _sounds[key] = snd
    except Exception:
        pass


def _save_settings(extra: Optional[dict] | None = None) -> None:
    data = {}
    if os.path.isfile(_SETTINGS_FILE):
        try:
            with open(_SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}
    data["music_volume"] = _music_volume
    data["sfx_volume"] = _sfx_volume
    if extra:
        data.update(extra)
    with open(_SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f)


def load_settings() -> dict:
    """Load persisted settings and apply volumes."""
    data: dict = {}
    if os.path.isfile(_SETTINGS_FILE):
        try:
            with open(_SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}
    set_music_volume(float(data.get("music_volume", _music_volume)), save=False)
    set_sfx_volume(float(data.get("sfx_volume", _sfx_volume)), save=False)
    return data


def save_settings(**extra: float | int | str | bool) -> None:
    """Persist current settings to ``settings.json``."""
    _save_settings(extra)


def set_music_volume(value: float, save: bool = True) -> None:
    """Set music volume (0.0-1.0) and optionally persist it."""
    global _music_volume
    _music_volume = max(0.0, min(value, 1.0))
    if _has_mixer():
        try:
            pygame.mixer.music.set_volume(_music_volume)
        except Exception:
            pass
    if save:
        _save_settings(None)


def get_music_volume() -> float:
    return _music_volume


def set_sfx_volume(value: float, save: bool = True) -> None:
    """Set sound effects volume (0.0-1.0)."""
    global _sfx_volume
    _sfx_volume = max(0.0, min(value, 1.0))
    if _has_mixer():
        for snd in _sounds.values():
            try:
                snd.set_volume(_sfx_volume)
            except Exception:
                pass
    if save:
        _save_settings(None)


def get_sfx_volume() -> float:
    return _sfx_volume


def play_sound(key: str) -> None:
    """Play a previously loaded sound identified by ``key``."""
    snd = _sounds.get(key)
    if snd is None:
        return
    try:  # pragma: no cover - actual playback
        snd.play()
    except Exception:
        pass


def play_music(filename: str, loop: int = -1) -> None:
    """Start playing a music track from the assets folder."""
    global _current_music
    if not _music_enabled or not _has_mixer():
        return
    path = _find_asset(filename)
    if path is None or not os.path.isfile(path):
        return
    try:  # pragma: no cover
        pygame.mixer.music.load(path)
        pygame.mixer.music.play(loop)
        pygame.mixer.music.set_volume(_music_volume)
        _current_music = filename
    except Exception:
        _current_music = None


def stop_music() -> None:
    """Stop any currently playing music."""
    global _current_music
    if not _has_mixer():
        return
    try:  # pragma: no cover
        pygame.mixer.music.stop()
    except Exception:
        pass
    _current_music = None


def set_music_enabled(value: bool) -> None:
    """Enable or disable music playback."""
    global _music_enabled
    _music_enabled = value
    if not value:
        stop_music()
    elif _current_music:
        play_music(_current_music)


def is_music_enabled() -> bool:
    return _music_enabled
