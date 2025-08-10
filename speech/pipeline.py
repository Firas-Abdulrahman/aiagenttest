import logging
from typing import Dict, Any, Optional

from .types import Transcript, AudioBlob
from .asr_service import ASRService
from .tts_service import TTSService

logger = logging.getLogger(__name__)


class VoicePipeline:
    """Coordinates ASR → NLP handler → TTS for WhatsApp voice messages."""

    def __init__(self, asr: ASRService, tts: TTSService, whatsapp_client, handler):
        self.asr = asr
        self.tts = tts
        self.whatsapp = whatsapp_client
        self.handler = handler

    def process_voice_message(self, phone_number: str, message: Dict[str, Any]) -> bool:
        try:
            audio = message.get('audio') or {}
            media_id = audio.get('id')
            if not media_id:
                logger.warning("No media id in audio message")
                return False

            # Resolve media info and download bytes
            media_info = self.whatsapp.get_media(media_id)
            if not media_info or 'url' not in media_info:
                logger.error("Failed to get media info for audio")
                return False

            media_url = media_info['url']
            media_bytes = self.whatsapp.download_media(media_url)
            if not media_bytes:
                logger.error("Failed to download media bytes")
                return False

            mime_type = media_info.get('mime_type', 'audio/ogg')

            # ASR
            transcript: Transcript = self.asr.transcribe(media_bytes, mime_type)
            if not transcript or not transcript.text:
                self.whatsapp.send_text_message(phone_number, "لم أتمكن من فهم الرسالة الصوتية. الرجاء المحاولة بصوت أوضح.")
                return False

            # Build a synthetic text message for downstream handler
            synthetic_message = {
                'from': phone_number,
                'text': {'body': transcript.text},
                'id': message.get('id')
            }

            response = self.handler.handle_message(synthetic_message)

            reply_text = response.get('content', '')
            if not reply_text:
                return False

            # TTS
            audio_blob: AudioBlob = self.tts.synthesize(
                reply_text,
                language=transcript.language,
                mime_type="audio/ogg"
            )
            if not audio_blob or not audio_blob.data:
                # fallback: text-only
                return self.whatsapp.send_text_message(phone_number, reply_text)

            # Upload and send voice message
            media_id_out = self.whatsapp.upload_media(audio_blob.data, audio_blob.mime_type)
            if not media_id_out:
                return self.whatsapp.send_text_message(phone_number, reply_text)

            voice_ok = self.whatsapp.send_voice_message(phone_number, media_id_out)
            if not voice_ok:
                return self.whatsapp.send_text_message(phone_number, reply_text)

            # Optionally send text too (can be toggled later)
            self.whatsapp.send_text_message(phone_number, reply_text)

            return True

        except Exception as e:
            logger.error(f"Voice pipeline error: {e}")
            return False


