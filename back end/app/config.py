from __future__ import annotations

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


DEPRECATED_MODELS = {
    "gemini-2.0-flash-live-001",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "raksha"
    gemini_api_key: str
    gemini_model: str = "gemini-2.5-flash-native-audio-preview-12-2025"
    host: str = "0.0.0.0"
    port: int = 8000
    frontend_origin: str = "http://localhost:5173"
    log_level: str = "info"

    @field_validator("gemini_model")
    @classmethod
    def validate_model_not_deprecated(cls, model: str) -> str:
        if model in DEPRECATED_MODELS:
            raise ValueError(
                f"Model '{model}' is deprecated. Use a current Live model, for example "
                "'gemini-2.5-flash-native-audio-preview-12-2025'."
            )
        return model


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
