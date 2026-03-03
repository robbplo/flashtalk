from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from flashtalk_api.app import create_app
from flashtalk_api.core.config import Settings
from flashtalk_api.domain.errors import SpeechGenerationError
from flashtalk_api.infrastructure.local_audio_store_service import LocalAudioStoreService


class _FakeSpeechService:
    def __init__(self, payload: bytes = b"ID3payload", delay_seconds: float = 0.0) -> None:
        self.payload = payload
        self.delay_seconds = delay_seconds
        self.calls = 0

    async def synthesize(self, phrase: str) -> bytes:
        self.calls += 1
        if self.delay_seconds > 0:
            await asyncio.sleep(self.delay_seconds)
        return self.payload


class _FailingSpeechService:
    async def synthesize(self, phrase: str) -> bytes:
        raise SpeechGenerationError("upstream unavailable")


def _build_settings(tmp_path: Path) -> Settings:
    return Settings(
        elevenlabs_api_key="test-key",
        elevenlabs_voice_id="test-voice",
        elevenlabs_model_id="eleven_v3",
        audio_dir=str(tmp_path),
        log_level="DEBUG",
    )


@pytest.mark.asyncio
async def test_say_serves_cached_audio(tmp_path: Path) -> None:
    speech = _FakeSpeechService(payload=b"ID3new")
    store = LocalAudioStoreService(tmp_path)
    phrase = "Sveiki"
    path = store.path_for_phrase(phrase)
    store.write_atomic(path, b"ID3cached")

    app = create_app(settings=_build_settings(tmp_path), speech_generator=speech, audio_store=store)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/say", params={"phrase": phrase})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("audio/mpeg")
    assert response.content == b"ID3cached"
    assert speech.calls == 0


@pytest.mark.asyncio
async def test_say_generates_audio_on_cache_miss(tmp_path: Path) -> None:
    speech = _FakeSpeechService(payload=b"ID3generated")
    store = LocalAudioStoreService(tmp_path)
    phrase = "Labdien"

    app = create_app(settings=_build_settings(tmp_path), speech_generator=speech, audio_store=store)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/say", params={"phrase": phrase})

    assert response.status_code == 200
    assert response.content == b"ID3generated"
    assert speech.calls == 1
    assert store.path_for_phrase(phrase).exists()


@pytest.mark.asyncio
async def test_say_single_flight_for_concurrent_requests(tmp_path: Path) -> None:
    speech = _FakeSpeechService(payload=b"ID3concurrent", delay_seconds=0.1)
    store = LocalAudioStoreService(tmp_path)
    app = create_app(settings=_build_settings(tmp_path), speech_generator=speech, audio_store=store)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        first, second = await asyncio.gather(
            client.get("/say", params={"phrase": "Viena frāze"}),
            client.get("/say", params={"phrase": "Viena frāze"}),
        )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.content == b"ID3concurrent"
    assert second.content == b"ID3concurrent"
    assert speech.calls == 1


@pytest.mark.asyncio
async def test_say_rejects_blank_phrase(tmp_path: Path) -> None:
    speech = _FakeSpeechService()
    store = LocalAudioStoreService(tmp_path)
    app = create_app(settings=_build_settings(tmp_path), speech_generator=speech, audio_store=store)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/say", params={"phrase": "   "})

    assert response.status_code == 400
    assert response.json()["error"] == "invalid_phrase"


@pytest.mark.asyncio
async def test_say_returns_502_on_generation_failure(tmp_path: Path) -> None:
    store = LocalAudioStoreService(tmp_path)
    app = create_app(
        settings=_build_settings(tmp_path),
        speech_generator=_FailingSpeechService(),
        audio_store=store,
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/say", params={"phrase": "Neizdodas"})

    assert response.status_code == 502
    assert response.json()["error"] == "speech_generation_failed"


@pytest.mark.asyncio
async def test_say_logs_across_levels(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    store = LocalAudioStoreService(tmp_path)
    app = create_app(
        settings=_build_settings(tmp_path),
        speech_generator=_FailingSpeechService(),
        audio_store=store,
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.get("/say", params={"phrase": "Nederīga/frasē"})

    levels = {record.levelname for record in caplog.records}
    assert "DEBUG" in levels
    assert "INFO" in levels
    assert "WARNING" in levels
    assert "ERROR" in levels

