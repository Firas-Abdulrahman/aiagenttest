import logging
from typing import Optional

from ..asr_service import ASRService
from ..types import Transcript

logger = logging.getLogger(__name__)


class OpenAIASR(ASRService):
    """OpenAI Whisper/4o-based ASR wrapper.

    This is a thin facade; actual API calls are implemented where configured.
    """

    def __init__(self, client, model: str = "whisper-1"):
        self.client = client
        self.model = model

    def transcribe(self, media_bytes: bytes, mime_type: str, language_hint: Optional[str] = None) -> Transcript:
        # Placeholder structure; the actual HTTP call will be implemented with the provided client
        # keeping the code minimal here as requested (no full implementation now).
        logger.info("ASR request prepared (OpenAI)")
        # Return a dummy transcript to be replaced by real integration
        return Transcript(text="", language=language_hint, confidence=None, duration_s=None)


