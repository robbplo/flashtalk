from __future__ import annotations

import logging
import time
from collections.abc import Iterable
from typing import Any

from elevenlabs.client import ElevenLabs
from starlette.concurrency import run_in_threadpool

from flashtalk_api.domain.errors import SpeechGenerationError
from flashtalk_api.domain.protocols import SpeechGeneratorPort
from flashtalk_api.domain.text_utils import phrase_hash


class ElevenLabsSpeechService(SpeechGeneratorPort):
    def __init__(
        self,
        api_key: str,
        voice_id: str,
        model_id: str = "eleven_v3",
        output_format: str = "mp3_44100_128",
        client: Any | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self._voice_id = voice_id
        self._model_id = model_id
        self._output_format = output_format
        self._client = client if client is not None else ElevenLabs(api_key=api_key)
        self._logger = logger if logger is not None else logging.getLogger(__name__)

    async def synthesize(self, phrase: str) -> bytes:
        start = time.perf_counter()
        hashed_phrase = phrase_hash(phrase)

        self._logger.debug(
            "elevenlabs_request_start",
            extra={
                "phrase_hash": hashed_phrase,
                "voice_id": self._voice_id,
                "model_id": self._model_id,
                "output_format": self._output_format,
            },
        )

        try:
            payload = await run_in_threadpool(self._convert, phrase)
            audio_bytes = self._to_bytes(payload)
        except Exception as exc:
            self._logger.error(
                "elevenlabs_request_failed",
                exc_info=exc,
                extra={"phrase_hash": hashed_phrase},
            )
            raise SpeechGenerationError("failed to generate speech with ElevenLabs") from exc

        if not audio_bytes:
            self._logger.error("elevenlabs_empty_audio", extra={"phrase_hash": hashed_phrase})
            raise SpeechGenerationError("ElevenLabs returned empty audio")

        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        self._logger.info(
            "elevenlabs_request_success",
            extra={"phrase_hash": hashed_phrase, "duration_ms": duration_ms, "bytes": len(audio_bytes)},
        )

        return audio_bytes

    def _convert(self, phrase: str) -> Any:
        return self._client.text_to_speech.convert(
            text=phrase,
            voice_id=self._voice_id,
            model_id=self._model_id,
            output_format=self._output_format,
        )

    @staticmethod
    def _to_bytes(payload: Any) -> bytes:
        if isinstance(payload, bytes):
            return payload
        if isinstance(payload, bytearray):
            return bytes(payload)
        if isinstance(payload, Iterable):
            chunks: list[bytes] = []
            for item in payload:
                if isinstance(item, bytes):
                    chunks.append(item)
                elif isinstance(item, bytearray):
                    chunks.append(bytes(item))
                else:
                    raise SpeechGenerationError("unsupported chunk type from ElevenLabs response")
            return b"".join(chunks)

        raise SpeechGenerationError("unsupported payload type from ElevenLabs response")

