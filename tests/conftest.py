from __future__ import annotations

import logging

import pytest

from flashtalk_api.core.config import Settings


@pytest.fixture
def test_settings(tmp_path) -> Settings:
    return Settings(
        elevenlabs_api_key="test-key",
        elevenlabs_voice_id="test-voice",
        elevenlabs_model_id="eleven_v3",
        audio_dir=str(tmp_path),
        log_level="DEBUG",
    )


@pytest.fixture(autouse=True)
def configure_test_logging() -> None:
    logging.getLogger().setLevel(logging.DEBUG)

