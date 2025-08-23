try:
    import os
    import json
    import pygame
    from typing import Dict, Optional
    try:
        from .loaders.asset_manager import AssetManager
        from .loaders.core import Context, find_file, read_json
    except ImportError:  # pragma: no cover - package vs script
        from loaders.asset_manager import AssetManager  # type: ignore
        from loaders.core import Context, find_file, read_json  # type: ignore
except Exception:  # pragma: no cover - when pygame is unavailable
    pygame = None
    AssetManager = None  # type: ignore
    Context = None  # type: ignore
    find_file = None  # type: ignore
    read_json = None  # type: ignore

_sounds: Dict[str, 'pygame.mixer.Sound'] = {}
_music_enabled: bool = True
_current_music: Optional[str] = None
_music_tracks: Dict[str, str] = {}
_default_music: Optional[str] = None
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


def _load_manifests() -> None:
    """Load sound and music manifests from the assets folder."""
    if Context is None or read_json is None:
        return

    search_paths: list[str]
    if _asset_manager is not None:
        search_paths = list(_asset_manager.search_paths)
    else:
        search_paths = [os.path.join(os.path.dirname(__file__), "assets")]

    ctx = Context(repo_root="", search_paths=search_paths, asset_loader=None)

    # Load sounds
    try:
        data = read_json(ctx, os.path.join("audio", "sounds.json"))
    except Exception:  # pragma: no cover - missing manifest
        data = []
    for entry in data or []:
        key = entry.get("id")
        file = entry.get("file")
        if key and file:
            load_sound(key, file)

    # Load music tracks
    global _default_music
    try:
        music_data = read_json(ctx, os.path.join("audio", "music.json"))
    except Exception:  # pragma: no cover
        music_data = []
    for entry in music_data or []:
        key = entry.get("id")
        file = entry.get("file")
        if key and file:
            _music_tracks[key] = file
            if _default_music is None:
                _default_music = key
            if entry.get("default"):
                _default_music = key


def init(asset_manager: AssetManager | None = None) -> None:
    """Initialise mixer and load core sounds.

    ``asset_manager`` may be provided to configure additional search paths for
    audio files.  The function silently returns if pygame's mixer is
    unavailable.  Missing sound files are ignored so the rest of the game can
    run in minimal environments without the audio assets.
    """

    if asset_manager is not None:
        set_asset_manager(asset_manager)

    _load_manifests()

    if not _has_mixer():
        return
    try:  # pragma: no cover - depends on system audio
        if not pygame.mixer.get_init():
            pygame.mixer.init()
    except Exception:
        return


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
    track = data.get("music_track")
    if isinstance(track, str) and track:
        global _current_music
        _current_music = track
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


def get_music_tracks() -> list[str]:
    """Return list of available music track identifiers."""
    return list(_music_tracks.keys())


def get_current_music() -> Optional[str]:
    return _current_music


def get_default_music() -> Optional[str]:
    return _default_music


def play_sound(key: str) -> None:
    """Play a previously loaded sound identified by ``key``."""
    snd = _sounds.get(key)
    if snd is None:
        return
    try:  # pragma: no cover - actual playback
        snd.play()
    except Exception:
        pass


def play_music(track: str, loop: int = -1) -> None:
    """Start playing a music track referenced by ``track`` id or filename."""
    global _current_music
    if not _music_enabled or not _has_mixer():
        _current_music = track
        return
    filename = _music_tracks.get(track, track)
    path = _find_asset(filename)
    if path is None or not os.path.isfile(path):
        return
    try:  # pragma: no cover
        pygame.mixer.music.load(path)
        pygame.mixer.music.play(loop)
        pygame.mixer.music.set_volume(_music_volume)
        _current_music = track
    except Exception:
        _current_music = track


def stop_music() -> None:
    """Stop any currently playing music."""
    if not _has_mixer():
        return
    try:  # pragma: no cover
        pygame.mixer.music.stop()
    except Exception:
        pass


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
