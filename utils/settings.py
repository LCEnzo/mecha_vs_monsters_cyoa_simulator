from __future__ import annotations

import enum

from pydantic_settings import BaseSettings, SettingsConfigDict


class Modes(enum.Enum):
    PROD = "PROD"
    DEBUG = "DEBUG"


class Settings(BaseSettings):
    mode: Modes = Modes.PROD

    model_config = SettingsConfigDict(env_file=".env")

    _instance: Settings | None = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls, *args, **kwargs)
        return cls._instance

    @classmethod
    def reset(cls):
        """Reset the singleton instance to allow reloading environment variables."""
        cls._instance = None

    def is_debug(self) -> bool:
        return self.mode == Modes.DEBUG

    def is_prod(self) -> bool:
        return self.mode == Modes.PROD


settings = Settings()
assert settings is not None
