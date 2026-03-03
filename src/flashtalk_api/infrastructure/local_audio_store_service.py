from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path

from flashtalk_api.domain.errors import AudioStoreError
from flashtalk_api.domain.protocols import AudioStorePort
from flashtalk_api.domain.text_utils import phrase_to_filename, phrase_hash


class LocalAudioStoreService(AudioStorePort):
    def __init__(self, base_dir: Path, logger: logging.Logger | None = None) -> None:
        self._base_dir = base_dir
        self._logger = logger if logger is not None else logging.getLogger(__name__)

    def path_for_phrase(self, phrase: str) -> Path:
        name_result = phrase_to_filename(phrase)
        path = self._base_dir / name_result.filename

        if name_result.was_sanitized or name_result.was_truncated:
            self._logger.warning(
                "phrase_sanitized_for_filename",
                extra={
                    "phrase_hash": phrase_hash(phrase),
                    "cache_filename": name_result.filename,
                    "truncated": name_result.was_truncated,
                },
            )
        else:
            self._logger.debug(
                "filename_resolved",
                extra={"phrase_hash": phrase_hash(phrase), "cache_filename": name_result.filename},
            )

        return path

    def exists(self, path: Path) -> bool:
        exists = path.is_file()
        self._logger.debug("cache_exists_check", extra={"cache_path": str(path), "exists": exists})
        return exists

    def write_atomic(self, path: Path, data: bytes) -> None:
        tmp_path = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")

        self._logger.debug("cache_write_start", extra={"cache_path": str(path), "tmp_path": str(tmp_path)})

        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with tmp_path.open("wb") as file_obj:
                file_obj.write(data)
            os.replace(tmp_path, path)
        except OSError as exc:
            self._logger.error(
                "cache_write_failed",
                exc_info=exc,
                extra={"cache_path": str(path), "tmp_path": str(tmp_path)},
            )
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)
            raise AudioStoreError(f"failed writing audio file at {path}") from exc

        self._logger.info("cache_write_success", extra={"cache_path": str(path), "bytes": len(data)})
