from abc import ABC, abstractmethod
from typing import Optional
from .types import Transcript


class ASRService(ABC):
    """Abstract speech-to-text service."""

    @abstractmethod
    def transcribe(self, media_bytes: bytes, mime_type: str, language_hint: Optional[str] = None) -> Transcript:
        """Transcribe audio bytes to text."""
        raise NotImplementedError


