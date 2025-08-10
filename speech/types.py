from dataclasses import dataclass
from typing import Optional


@dataclass
class Transcript:
    """Result of ASR transcription."""
    text: str
    language: Optional[str] = None
    confidence: Optional[float] = None
    duration_s: Optional[float] = None


@dataclass
class AudioBlob:
    """Binary audio payload for TTS output."""
    data: bytes
    mime_type: str  # e.g., "audio/ogg" or "audio/ogg;codecs=opus"


