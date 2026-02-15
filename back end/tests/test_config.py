from __future__ import annotations

import pytest

from app.config import get_settings


def test_settings_load_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.5-flash-native-audio-preview-12-2025")
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.gemini_api_key == "test-key"
    assert settings.gemini_model == "gemini-2.5-flash-native-audio-preview-12-2025"


def test_deprecated_model_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.0-flash-live-001")
    get_settings.cache_clear()

    with pytest.raises(Exception):
        get_settings()
