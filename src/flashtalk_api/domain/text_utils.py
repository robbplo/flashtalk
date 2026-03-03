from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

_INVALID_FILENAME_CHARS = re.compile(r"[\\/:*?\"<>|\x00-\x1F]")
_WHITESPACE = re.compile(r"\s+")


@dataclass(frozen=True)
class FilenameResult:
    filename: str
    was_sanitized: bool
    was_truncated: bool


def normalize_phrase(raw_phrase: str) -> str:
    collapsed = _WHITESPACE.sub(" ", raw_phrase.strip())
    return collapsed


def phrase_hash(phrase: str) -> str:
    return hashlib.sha256(phrase.encode("utf-8")).hexdigest()[:12]


def phrase_to_filename(phrase: str, max_length: int = 120) -> FilenameResult:
    sanitized = _INVALID_FILENAME_CHARS.sub("_", phrase)
    sanitized = _WHITESPACE.sub(" ", sanitized).strip()

    if not sanitized:
        return FilenameResult(filename="phrase.mp3", was_sanitized=True, was_truncated=False)

    was_sanitized = sanitized != phrase
    was_truncated = False

    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length].rstrip()
        was_truncated = True

    return FilenameResult(
        filename=f"{sanitized}.mp3",
        was_sanitized=was_sanitized,
        was_truncated=was_truncated,
    )

