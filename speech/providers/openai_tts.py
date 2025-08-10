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
        """Generate audio using OpenAI TTS (gpt-4o-mini-tts)."""
        try:
            # OpenAI v1 TTS: audio.speech.create
            # Choose voice; default to 'alloy' if not provided
            voice_name = voice or 'alloy'
            # Choose output format from mime
            if 'mp3' in mime_type or 'mpeg' in mime_type:
                format_hint = 'mp3'
            elif 'wav' in mime_type:
                format_hint = 'wav'
            else:
                format_hint = 'ogg'

            result = self.client.audio.speech.create(
                model=self.model,
                voice=voice_name,
                input=text,
                response_format=format_hint,
            )

            # openai v1 returns bytes in .read() or .content; handle both
            audio_bytes = None
            if hasattr(result, 'content'):
                audio_bytes = result.content
            elif hasattr(result, 'read'):
                audio_bytes = result.read()

            if not audio_bytes:
                logger.warning("TTS produced no audio")
                return AudioBlob(data=b"", mime_type=mime_type)

            logger.info("TTS completed (OpenAI)")
            return AudioBlob(data=audio_bytes, mime_type=mime_type)

        except Exception as e:
            logger.error(f"TTS error: {e}")
            return AudioBlob(data=b"", mime_type=mime_type)


