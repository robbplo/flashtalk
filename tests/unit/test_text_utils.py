from __future__ import annotations

from flashtalk_api.domain.text_utils import normalize_phrase, phrase_hash, phrase_to_filename


def test_normalize_phrase_collapses_whitespace() -> None:
    assert normalize_phrase("  Labdien   pasaule \n") == "Labdien pasaule"


def test_phrase_hash_is_stable() -> None:
    assert phrase_hash("Sveiki") == phrase_hash("Sveiki")
    assert len(phrase_hash("Sveiki")) == 12


def test_phrase_to_filename_sanitizes_invalid_characters() -> None:
    result = phrase_to_filename("Sveiki/Čau?*", max_length=120)

    assert result.filename == "Sveiki_Čau__.mp3"
    assert result.was_sanitized is True
    assert result.was_truncated is False


def test_phrase_to_filename_truncates_long_values() -> None:
    phrase = "a" * 130
    result = phrase_to_filename(phrase, max_length=10)

    assert result.filename == "aaaaaaaaaa.mp3"
    assert result.was_truncated is True

