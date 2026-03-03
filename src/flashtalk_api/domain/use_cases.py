from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from flashtalk_api.domain.errors import AudioStoreError, InvalidPhraseError, SpeechGenerationError
from flashtalk_api.domain.protocols import AudioStorePort, SpeechGeneratorPort
from flashtalk_api.domain.text_utils import normalize_phrase, phrase_hash


class PhraseLockRegistry:
    def __init__(self) -> None:
        self._locks: dict[str, asyncio.Lock] = {}
        self._registry_lock = asyncio.Lock()

    async def get_lock(self, key: str) -> asyncio.Lock:
        async with self._registry_lock:
            lock = self._locks.get(key)
            if lock is None:
                lock = asyncio.Lock()
                self._locks[key] = lock
            return lock


async def get_or_generate_audio(
    raw_phrase: str,
    speech_generator: SpeechGeneratorPort,
    audio_store: AudioStorePort,
    lock_registry: PhraseLockRegistry,
    logger: logging.Logger,
) -> Path:
    phrase = normalize_phrase(raw_phrase)
    hashed_phrase = phrase_hash(phrase or raw_phrase)

    logger.debug("phrase_normalized", extra={"phrase_hash": hashed_phrase})

    if not phrase:
        logger.warning("invalid_phrase", extra={"phrase_hash": hashed_phrase})
        raise InvalidPhraseError("phrase must be a non-empty string")

    target_path = audio_store.path_for_phrase(phrase)
    logger.debug("cache_path_resolved", extra={"cache_path": str(target_path), "phrase_hash": hashed_phrase})

    if audio_store.exists(target_path):
        logger.info("cache_hit", extra={"cache_path": str(target_path), "phrase_hash": hashed_phrase})
        return target_path

    lock = await lock_registry.get_lock(phrase)
    logger.debug("waiting_for_phrase_lock", extra={"phrase_hash": hashed_phrase})

    async with lock:
        if audio_store.exists(target_path):
            logger.info(
                "cache_hit_after_lock",
                extra={"cache_path": str(target_path), "phrase_hash": hashed_phrase},
            )
            return target_path

        logger.info(
            "cache_miss_generating_audio",
            extra={"cache_path": str(target_path), "phrase_hash": hashed_phrase},
        )

        try:
            audio_bytes = await speech_generator.synthesize(phrase)
        except SpeechGenerationError:
            raise
        except Exception as exc:  # pragma: no cover - guardrail
            raise SpeechGenerationError("unexpected speech generation failure") from exc

        if not audio_bytes:
            logger.error("empty_audio_response", extra={"phrase_hash": hashed_phrase})
            raise SpeechGenerationError("speech generator returned empty audio")

        try:
            audio_store.write_atomic(target_path, audio_bytes)
        except AudioStoreError:
            raise

        logger.info(
            "audio_generated",
            extra={"cache_path": str(target_path), "phrase_hash": hashed_phrase, "bytes": len(audio_bytes)},
        )

    return target_path

