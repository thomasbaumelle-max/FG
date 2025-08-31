import types
import audio


def test_queue_music_resumes_previous_track(monkeypatch, tmp_path):
    queued = []

    class DummyMusic:
        @staticmethod
        def load(path):
            pass

        @staticmethod
        def play(loop):
            pass

        @staticmethod
        def queue(path):
            queued.append(path)

        @staticmethod
        def set_volume(vol):
            pass

    dummy_mixer = types.SimpleNamespace(music=DummyMusic)
    dummy_pygame = types.SimpleNamespace(mixer=dummy_mixer)
    monkeypatch.setattr(audio, "pygame", dummy_pygame)
    monkeypatch.setattr(audio, "_has_mixer", lambda: True)

    files = {}
    for name in ["theme.ogg", "jingle.ogg"]:
        p = tmp_path / name
        p.write_bytes(b"0")
        files[name] = str(p)

    monkeypatch.setattr(audio, "_find_asset", lambda filename: files.get(filename))

    audio._music_tracks.clear()
    audio._music_tracks.update({"theme": "theme.ogg", "jingle": "jingle.ogg"})
    audio._current_music = None

    audio.play_music("theme")
    prev = audio.get_current_music()
    audio.play_music("jingle", loop=0)
    audio.queue_music(prev)

    assert queued == [files["theme.ogg"]]
    assert audio._queued_music == "theme"

    # Simulate jingle ending
    audio.play_music(audio._queued_music)
    assert audio.get_current_music() == "theme"
