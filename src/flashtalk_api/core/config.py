from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    elevenlabs_api_key: str = Field(validation_alias="ELEVENLABS_API_KEY")
    elevenlabs_voice_id: str = Field(validation_alias="ELEVENLABS_VOICE_ID")
    elevenlabs_model_id: str = Field(default="eleven_v3", validation_alias="ELEVENLABS_MODEL_ID")
    audio_dir: str = Field(default="./data", validation_alias="AUDIO_DIR")
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")

