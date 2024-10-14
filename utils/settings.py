from __future__ import annotations

import enum

from pydantic_settings import BaseSettings, SettingsConfigDict


class Modes(enum.Enum):
    PROD = "PROD"
    DEBUG = "DEBUG"


class Settings(BaseSettings):
    mode: Modes = Modes.PROD

    model_config = SettingsConfigDict(env_file=".env")

    def is_debug(self) -> bool:
        return self.mode == Modes.DEBUG

    def is_prod(self) -> bool:
        return self.mode == Modes.PROD


settings = Settings()
