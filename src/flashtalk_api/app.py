from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from fastapi import FastAPI, Request
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response

from flashtalk_api.api.routes import router
from flashtalk_api.core.config import Settings
from flashtalk_api.core.logging import configure_logging, reset_request_id, set_request_id
from flashtalk_api.domain.protocols import AudioStorePort, SpeechGeneratorPort
from flashtalk_api.domain.use_cases import PhraseLockRegistry
from flashtalk_api.infrastructure.elevenlabs_speech_service import ElevenLabsSpeechService
from flashtalk_api.infrastructure.local_audio_store_service import LocalAudioStoreService


@dataclass(slots=True)
class AppServices:
    speech_generator: SpeechGeneratorPort
    audio_store: AudioStorePort
    lock_registry: PhraseLockRegistry


def create_app(
    settings: Settings | None = None,
    speech_generator: SpeechGeneratorPort | None = None,
    audio_store: AudioStorePort | None = None,
) -> FastAPI:
    app_settings = settings if settings is not None else Settings()  # type: ignore[call-arg]
    configure_logging(app_settings.log_level)

    app = FastAPI(title="FlashTalk API", version="0.1.0")
    logger = logging.getLogger("flashtalk.request")

    resolved_audio_store = (
        audio_store
        if audio_store is not None
        else LocalAudioStoreService(base_dir=Path(app_settings.audio_dir))
    )
    resolved_speech_generator = (
        speech_generator
        if speech_generator is not None
        else ElevenLabsSpeechService(
            api_key=app_settings.elevenlabs_api_key,
            voice_id=app_settings.elevenlabs_voice_id,
            model_id=app_settings.elevenlabs_model_id,
            output_format="mp3_44100_128",
        )
    )

    app.state.services = AppServices(
        speech_generator=resolved_speech_generator,
        audio_store=resolved_audio_store,
        lock_registry=PhraseLockRegistry(),
    )

    @app.middleware("http")
    async def request_context_middleware(
        request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        token = set_request_id(request_id)
        start = time.perf_counter()

        logger.info(
            "request_started",
            extra={"method": request.method, "path": request.url.path, "query": str(request.url.query)},
        )

        try:
            response = await call_next(request)
        except Exception:
            logger.error("request_unhandled_error", exc_info=True)
            reset_request_id(token)
            raise

        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        response.headers["X-Request-ID"] = request_id

        logger.info(
            "request_finished",
            extra={"status_code": response.status_code, "duration_ms": duration_ms},
        )

        reset_request_id(token)
        return response

    app.include_router(router)
    return app
