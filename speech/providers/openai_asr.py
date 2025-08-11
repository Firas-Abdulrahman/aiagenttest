import logging
import io
from typing import Optional

from ..asr_service import ASRService
from ..types import Transcript

logger = logging.getLogger(__name__)


class OpenAIASR(ASRService):
    """OpenAI Whisper/4o-based ASR wrapper with enhanced Arabic support."""

    def __init__(self, client, model: str = "whisper-1"):
        self.client = client
        self.model = model

    def transcribe(self, media_bytes: bytes, mime_type: str, language_hint: Optional[str] = None) -> Transcript:
        """Transcribe audio using OpenAI Whisper with forced Arabic language for better accuracy."""
        try:
            buf = io.BytesIO(media_bytes)
            buf.name = "audio.ogg"  # some SDKs expect a filename

            # Force Arabic language for better transcription of Arabic speech
            forced_language = 'ar' if language_hint in ['ar', 'arabic'] else language_hint
            
            logger.info(f"🎙️ Starting ASR transcription with model {self.model}, language: {forced_language}")
            
            result = self.client.audio.transcriptions.create(
                model=self.model,
                file=buf,
                language=forced_language,
                response_format="json",
                # Add prompt to improve Arabic transcription
                prompt="This is Arabic speech. Please transcribe accurately with proper Arabic text."
            )

            text = getattr(result, 'text', None)
            if not text and isinstance(result, dict):
                text = result.get('text')

            if text:
                # Clean up the transcribed text
                cleaned_text = text.strip()
                logger.info(f"✅ ASR completed (OpenAI {self.model}): '{cleaned_text}'")
                return Transcript(text=cleaned_text, language=forced_language, confidence=None, duration_s=None)

            logger.warning("⚠️ ASR returned no text")
            return Transcript(text="", language=forced_language, confidence=None, duration_s=None)

        except Exception as e:
            logger.error(f"❌ ASR error: {e}")
            return Transcript(text="", language=language_hint, confidence=None, duration_s=None)


