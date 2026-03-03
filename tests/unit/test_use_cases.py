from __future__ import annotations

import logging
from pathlib import Path

import pytest

from flashtalk_api.domain.errors import InvalidPhraseError
from flashtalk_api.domain.use_cases import PhraseLockRegistry, get_or_generate_audio
from flashtalk_api.infrastructure.local_audio_store_service import LocalAudioStoreService


class _FakeSpeechService:
    def __init__(self, payload: bytes = b"ID3payload") -> None:
        self.payload = payload
        self.calls = 0

    async def synthesize(self, phrase: str) -> bytes:
        self.calls += 1
        return self.payload


@pytest.mark.asyncio
async def test_get_or_generate_audio_uses_cache_hit(tmp_path: Path) -> None:
    logger = logging.getLogger("test.use_case")
    store = LocalAudioStoreService(tmp_path)
    speech = _FakeSpeechService()
    lock_registry = PhraseLockRegistry()

    phrase = "Sveiki"
    path = store.path_for_phrase(phrase)
    store.write_atomic(path, b"ID3cached")

    resolved = await get_or_generate_audio(phrase, speech, store, lock_registry, logger)

    assert resolved == path
    assert speech.calls == 0


@pytest.mark.asyncio
async def test_get_or_generate_audio_miss_generates_and_writes(tmp_path: Path) -> None:
    logger = logging.getLogger("test.use_case")
    store = LocalAudioStoreService(tmp_path)
    speech = _FakeSpeechService(payload=b"ID3new")
    lock_registry = PhraseLockRegistry()

    resolved = await get_or_generate_audio("Labdien", speech, store, lock_registry, logger)

    assert speech.calls == 1
    assert resolved.read_bytes() == b"ID3new"


@pytest.mark.asyncio
async def test_get_or_generate_audio_rejects_empty_phrase(tmp_path: Path) -> None:
    logger = logging.getLogger("test.use_case")
    store = LocalAudioStoreService(tmp_path)
    speech = _FakeSpeechService()
    lock_registry = PhraseLockRegistry()

    with pytest.raises(InvalidPhraseError):
        await get_or_generate_audio("   ", speech, store, lock_registry, logger)

