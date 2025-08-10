from abc import ABC, abstractmethod
from typing import Optional
from .types import AudioBlob


class TTSService(ABC):
    """Abstract text-to-speech service."""

    @abstractmethod
    def synthesize(self, text: str, language: Optional[str] = None, voice: Optional[str] = None,
                   mime_type: str = "audio/ogg") -> AudioBlob:
        """Generate audio for given text."""
        raise NotImplementedError


