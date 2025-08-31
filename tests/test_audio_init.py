import types
import audio


def test_init_initializes_mixer_before_loading(monkeypatch, tmp_path):
    init_states: list[bool] = []

    class DummySound:
        def __init__(self, path):
            init_states.append(DummyMixer.initialized)
        def set_volume(self, vol):
            pass

    class DummyMixer:
        initialized = False
        @staticmethod
        def get_init():
            return DummyMixer.initialized
        @staticmethod
        def init():
            DummyMixer.initialized = True
        Sound = DummySound
        class music:
            @staticmethod
            def set_volume(vol):
                pass
            @staticmethod
            def load(path):
                pass
            @staticmethod
            def play(loop):
                pass

    dummy_pygame = types.SimpleNamespace(mixer=DummyMixer)
    monkeypatch.setattr(audio, "pygame", dummy_pygame)
    monkeypatch.setattr(audio, "_has_mixer", lambda: True)

    dummy_file = tmp_path / "foo.wav"
    dummy_file.write_bytes(b"\0")
    monkeypatch.setattr(audio, "_find_asset", lambda filename: str(dummy_file))
    monkeypatch.setattr(audio, "_load_manifests", lambda: audio.load_sound("beep", "foo.wav"))

    audio._sounds.clear()
    audio.init()

    assert init_states and init_states[0]
    assert "beep" in audio._sounds
