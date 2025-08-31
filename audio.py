import os
import json
import sys
import logging
from typing import Dict, Optional

try:
    import pygame
    try:
        from .loaders.asset_manager import AssetManager
        from .loaders import audio_loader
    except ImportError:  # pragma: no cover - package vs script
        from loaders.asset_manager import AssetManager  # type: ignore
        from loaders import audio_loader  # type: ignore
except Exception:  # pragma: no cover - when pygame is unavailable
    pygame = None
    AssetManager = None  # type: ignore
    audio_loader = None  # type: ignore


_logger = logging.getLogger(__name__)


_logger = logging.getLogger(__name__)

import settings

_sounds: Dict[str, 'pygame.mixer.Sound'] = {}
_music_enabled: bool = True
_current_music: Optional[str] = None
_queued_music: Optional[str] = None
_music_tracks: Dict[str, str] = {}
_default_music: Optional[str] = None
_music_volume: float = 1.0
_sfx_volume: float = 1.0
# Settings are persisted via :mod:`settings`
_SETTINGS_FILE = str(settings.SETTINGS_FILE)

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
        search_paths = ["assets"]

    if audio_loader is not None:
        return audio_loader.find_audio_file(filename, search_paths)
    for base in search_paths:
        candidate = os.path.join(base, filename)
        if os.path.isfile(candidate):
            return candidate
    return None


def _has_mixer() -> bool:
    return pygame is not None and hasattr(pygame, 'mixer')


def _load_manifests() -> None:
    """Load sound and music manifests from the assets folder."""
    if audio_loader is None:
        return

    search_paths: list[str]
    if _asset_manager is not None:
        search_paths = list(_asset_manager.search_paths)
    else:
        search_paths = ["assets"]

    # Load sounds
    data = audio_loader.load_manifest("sounds.json", search_paths)
    for entry in data or []:
        key = entry.get("id")
        file = entry.get("file")
        if key and file:
            load_sound(key, file)

    # Load music tracks
    global _default_music
    music_data = audio_loader.load_manifest("music.json", search_paths)
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

    if _has_mixer():
        if "SDL_AUDIODRIVER" not in os.environ:
            if sys.platform.startswith("win"):
                os.environ["SDL_AUDIODRIVER"] = "directsound"
            else:
                os.environ["SDL_AUDIODRIVER"] = "pulseaudio"
        try:  # pragma: no cover - depends on system audio
            if not pygame.mixer.get_init():
                pygame.mixer.init()
        except Exception as exc:
            _logger.error("Failed to initialise audio mixer: %s", exc)
        if pygame.mixer.get_init() is None:
            _logger.warning("Audio device not available; sound will be disabled.")

    _load_manifests()


def load_sound(key: str, filename: str) -> None:
    """Load a sound from the assets directory under the given key."""
    if not _has_mixer():
        return
    path = _find_asset(filename)
    if path is None or not os.path.isfile(path):
        _logger.warning("Missing audio file %s", filename)
        return
    try:  # pragma: no cover - loading depends on external files
        snd = pygame.mixer.Sound(path)
        snd.set_volume(_sfx_volume)
        _sounds[key] = snd
    except Exception:
        pass


def _save_settings(extra: Optional[dict] | None = None) -> None:
    data = {"music_volume": _music_volume, "sfx_volume": _sfx_volume}
    if extra:
        data.update(extra)
    settings.save_settings(**data)


def load_settings() -> dict:
    """Load persisted settings and apply volumes."""
    data: dict = {}
    if os.path.isfile(_SETTINGS_FILE):
        try:
            with open(_SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}
    vol = data.get("volume")
    if vol is not None:
        try:
            volume_val = float(vol)
            set_music_volume(volume_val, save=False)
            set_sfx_volume(volume_val, save=False)
            settings.VOLUME = volume_val
        except Exception:
            set_music_volume(float(data.get("music_volume", _music_volume)), save=False)
            set_sfx_volume(float(data.get("sfx_volume", _sfx_volume)), save=False)
            settings.VOLUME = _music_volume
    else:
        set_music_volume(float(data.get("music_volume", _music_volume)), save=False)
        set_sfx_volume(float(data.get("sfx_volume", _sfx_volume)), save=False)
        settings.VOLUME = _music_volume
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
    global _current_music, _queued_music
    _queued_music = None
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


def queue_music(track: str) -> None:
    """Queue a music track to play after the current one ends."""
    global _queued_music
    if not track:
        return
    filename = _music_tracks.get(track, track)
    path = _find_asset(filename)
    if path is None or not os.path.isfile(path):
        return
    _queued_music = track if _has_mixer() else path
    if not _music_enabled or not _has_mixer():
        return
    try:  # pragma: no cover
        pygame.mixer.music.queue(path)
    except Exception:
        pass


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
