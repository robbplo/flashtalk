from __future__ import annotations

import logging

from fastapi import APIRouter, Query, Request
from fastapi.responses import FileResponse, JSONResponse, Response

from flashtalk_api.core.logging import get_request_id
from flashtalk_api.domain.errors import AudioStoreError, InvalidPhraseError, SpeechGenerationError
from flashtalk_api.domain.use_cases import get_or_generate_audio

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/say")
async def say(request: Request, phrase: str = Query(..., description="Latvian phrase to speak")) -> Response:
    services = request.app.state.services

    try:
        path = await get_or_generate_audio(
            raw_phrase=phrase,
            speech_generator=services.speech_generator,
            audio_store=services.audio_store,
            lock_registry=services.lock_registry,
            logger=logger,
        )
    except InvalidPhraseError as exc:
        logger.warning("invalid_phrase_request", extra={"request_id": get_request_id()})
        return JSONResponse(
            status_code=400,
            content={
                "error": "invalid_phrase",
                "message": str(exc),
                "request_id": get_request_id(),
            },
        )
    except SpeechGenerationError as exc:
        logger.error("speech_generation_failed", exc_info=exc)
        return JSONResponse(
            status_code=502,
            content={
                "error": "speech_generation_failed",
                "message": "failed to generate audio",
                "request_id": get_request_id(),
            },
        )
    except AudioStoreError as exc:
        logger.error("audio_store_failure", exc_info=exc)
        return JSONResponse(
            status_code=500,
            content={
                "error": "audio_store_failure",
                "message": "failed to persist audio",
                "request_id": get_request_id(),
            },
        )

    return FileResponse(path=path, media_type="audio/mpeg", filename=path.name)
