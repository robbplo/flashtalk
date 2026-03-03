class InvalidPhraseError(ValueError):
    """Raised when an invalid phrase is provided by the caller."""


class SpeechGenerationError(RuntimeError):
    """Raised when audio generation fails."""


class AudioStoreError(RuntimeError):
    """Raised when reading/writing audio files fails."""

