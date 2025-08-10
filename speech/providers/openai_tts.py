import logging
from typing import Optional

from ..tts_service import TTSService
from ..types import AudioBlob

logger = logging.getLogger(__name__)


class OpenAITTS(TTSService):
    """OpenAI TTS wrapper (e.g., gpt-4o-mini-tts)."""

    def __init__(self, client, model: str = "gpt-4o-mini-tts"):
        self.client = client
        self.model = model

    def synthesize(self, text: str, language: Optional[str] = None, voice: Optional[str] = None,
                   mime_type: str = "audio/ogg") -> AudioBlob:
        logger.info("TTS request prepared (OpenAI)")
        # Return a dummy blob to be replaced by real integration
        return AudioBlob(data=b"", mime_type=mime_type)


