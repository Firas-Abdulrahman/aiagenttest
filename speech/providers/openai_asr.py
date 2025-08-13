import logging
import io
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
        """Transcribe audio using OpenAI Whisper (whisper-1)."""
        try:
            buf = io.BytesIO(media_bytes)
            buf.name = "audio.ogg"  # some SDKs expect a filename

            # Log the transcription request with language hint
            if language_hint:
                logger.info(f"🎤 Transcribing with language hint: {language_hint}")
            else:
                logger.info(f"🎤 Transcribing with auto-language detection")

            result = self.client.audio.transcriptions.create(
                model=self.model,
                file=buf,
                language=language_hint if language_hint else None,
                response_format="json"
            )

            text = getattr(result, 'text', None)
            if not text and isinstance(result, dict):
                text = result.get('text')

            if text:
                logger.info(f"✅ ASR completed (OpenAI whisper-1) - Language hint: {language_hint}, Text: '{text[:50]}{'...' if len(text) > 50 else ''}'")
                return Transcript(text=text, language=language_hint, confidence=None, duration_s=None)

            logger.warning("ASR returned no text")
            return Transcript(text="", language=language_hint, confidence=None, duration_s=None)

        except Exception as e:
            logger.error(f"❌ ASR error: {e}")
            return Transcript(text="", language=language_hint, confidence=None, duration_s=None)


