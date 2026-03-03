from __future__ import annotations

from pathlib import Path
from typing import Protocol


class SpeechGeneratorPort(Protocol):
    async def synthesize(self, phrase: str) -> bytes:
        ...


class AudioStorePort(Protocol):
    def path_for_phrase(self, phrase: str) -> Path:
        ...

    def exists(self, path: Path) -> bool:
        ...

    def write_atomic(self, path: Path, data: bytes) -> None:
        ...

