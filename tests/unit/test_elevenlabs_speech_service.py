from __future__ import annotations

from collections.abc import Iterator

import pytest

from flashtalk_api.domain.errors import SpeechGenerationError
from flashtalk_api.infrastructure.elevenlabs_speech_service import ElevenLabsSpeechService


class _FakeTextToSpeech:
    def __init__(self, payload, should_fail: bool = False) -> None:
        self.payload = payload
        self.should_fail = should_fail
        self.calls: list[dict[str, str]] = []

    def convert(self, **kwargs):
        self.calls.append(kwargs)
        if self.should_fail:
            raise RuntimeError("upstream failed")
        return self.payload


class _FakeClient:
    def __init__(self, payload, should_fail: bool = False) -> None:
        self.text_to_speech = _FakeTextToSpeech(payload=payload, should_fail=should_fail)


@pytest.mark.asyncio
async def test_synthesize_collects_iterable_chunks() -> None:
    payload = [b"ID3", b"audio"]
    client = _FakeClient(payload=payload)
    service = ElevenLabsSpeechService(
        api_key="x",
        voice_id="voice",
        model_id="eleven_v3",
        output_format="mp3_44100_128",
        client=client,
    )

    result = await service.synthesize("Labdien")

    assert result == b"ID3audio"
    assert client.text_to_speech.calls[0]["model_id"] == "eleven_v3"
    assert client.text_to_speech.calls[0]["output_format"] == "mp3_44100_128"


@pytest.mark.asyncio
async def test_synthesize_accepts_bytes_payload() -> None:
    client = _FakeClient(payload=b"ID3bytes")
    service = ElevenLabsSpeechService(api_key="x", voice_id="voice", client=client)

    result = await service.synthesize("Sveiki")

    assert result == b"ID3bytes"


@pytest.mark.asyncio
async def test_synthesize_raises_on_upstream_error() -> None:
    client = _FakeClient(payload=b"", should_fail=True)
    service = ElevenLabsSpeechService(api_key="x", voice_id="voice", client=client)

    with pytest.raises(SpeechGenerationError):
        await service.synthesize("Sveiki")


@pytest.mark.asyncio
async def test_synthesize_raises_on_unsupported_payload_chunk_type() -> None:
    def _iter_values() -> Iterator[str]:
        yield "not-bytes"

    client = _FakeClient(payload=_iter_values())
    service = ElevenLabsSpeechService(api_key="x", voice_id="voice", client=client)

    with pytest.raises(SpeechGenerationError):
        await service.synthesize("Sveiki")

