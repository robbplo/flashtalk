from __future__ import annotations

import os
from pathlib import Path

import pytest

from flashtalk_api.domain.errors import AudioStoreError
from flashtalk_api.infrastructure.local_audio_store_service import LocalAudioStoreService


def test_path_for_phrase_is_deterministic(tmp_path: Path) -> None:
    service = LocalAudioStoreService(tmp_path)

    path_one = service.path_for_phrase("Labdien")
    path_two = service.path_for_phrase("Labdien")

    assert path_one == path_two
    assert path_one.suffix == ".mp3"


def test_write_atomic_and_exists(tmp_path: Path) -> None:
    service = LocalAudioStoreService(tmp_path)
    path = service.path_for_phrase("Sveiki")

    assert service.exists(path) is False

    service.write_atomic(path, b"ID3audio")

    assert service.exists(path) is True
    assert path.read_bytes() == b"ID3audio"


def test_write_atomic_raises_audio_store_error_on_replace_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = LocalAudioStoreService(tmp_path)
    path = service.path_for_phrase("Nedrīkst")

    def _replace_fail(src: os.PathLike[str], dst: os.PathLike[str]) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(
        "flashtalk_api.infrastructure.local_audio_store_service.os.replace",
        _replace_fail,
    )

    with pytest.raises(AudioStoreError):
        service.write_atomic(path, b"abc")

