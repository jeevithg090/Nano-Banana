import pytest

from nano_banana.config import DEFAULT_MODEL, Settings


def test_defaults(monkeypatch):
    for name in ("GEMINI_API_KEY", "GEMINI_MODEL", "FLASK_SECRET_KEY", "MAX_IMAGES"):
        monkeypatch.delenv(name, raising=False)
    s = Settings.from_env()
    assert s.gemini_api_key is None
    assert s.gemini_model == DEFAULT_MODEL
    assert len(s.secret_key) == 64
    assert s.max_images == 5
    assert s.max_content_length == 16 * 1024 * 1024


def test_reads_environment(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "abc")
    monkeypatch.setenv("GEMINI_MODEL", "custom")
    monkeypatch.setenv("MAX_IMAGES", "2")
    s = Settings.from_env()
    assert (s.gemini_api_key, s.gemini_model, s.max_images) == ("abc", "custom", 2)


@pytest.mark.parametrize("value", ["abc", "0", "-1"])
def test_rejects_bad_integers(monkeypatch, value):
    monkeypatch.setenv("MAX_IMAGES", value)
    with pytest.raises(ValueError, match="MAX_IMAGES"):
        Settings.from_env()
