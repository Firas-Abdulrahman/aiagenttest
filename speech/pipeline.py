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

            # Determine session language to guide ASR and TTS
            session_lang = None
            try:
                if hasattr(self.handler, 'db') and self.handler.db:
                    session = self.handler.db.get_user_session(phone_number)
                    if session:
                        session_lang = (session.get('language') or '').lower() or None
            except Exception as e:
                logger.warning(f"Could not fetch session for language preference: {e}")

            # Map session language to ASR hint code
            lang_hint = None
            if session_lang in ('english', 'en'):
                lang_hint = 'en'
            elif session_lang in ('arabic', 'ar'):
                lang_hint = 'ar'

            # ASR with language hint (if available)
            transcript: Transcript = self.asr.transcribe(media_bytes, mime_type, language_hint=lang_hint)
            if not transcript or not transcript.text:
                # Handle as "processed" to avoid normal text flow sending another message
                if session_lang in ('english', 'en'):
                    fallback_text = "Sorry, I couldn't understand the voice note. Please send a shorter or clearer voice message."
                else:
                    fallback_text = "لم أتمكن من فهم الرسالة الصوتية. الرجاء إعادة إرسال ملاحظة صوتية أقصر أو أوضح."
                self.whatsapp.send_text_message(phone_number, fallback_text)
                return True

            # Build a synthetic text message for downstream handler (use transcript)
            synthetic_message = {
                'from': phone_number,
                'text': {'body': transcript.text},
                'id': message.get('id'),
                'type': 'text',
                'contacts': message.get('contacts', [])
            }

            response = self.handler.handle_message(synthetic_message)

            reply_text = response.get('content', '')
            if not reply_text:
                return False

            # TTS
            # Decide output format: prefer OGG voice notes; fallback to MP3 if configured
            preferred_mime = "audio/ogg"
            # Choose TTS language: prefer session language; fallback to transcript language
            tts_lang = session_lang or getattr(transcript, 'language', None) or 'arabic'
            audio_blob: AudioBlob = self.tts.synthesize(
                reply_text,
                language=tts_lang,
                mime_type=preferred_mime
            )
            if not audio_blob or not audio_blob.data:
                # fallback: text-only, but mark handled to avoid duplicate sends
                self.whatsapp.send_text_message(phone_number, reply_text)
                return True

            # Upload and send voice message
            media_id_out = self.whatsapp.upload_media(audio_blob.data, audio_blob.mime_type)
            if not media_id_out:
                self.whatsapp.send_text_message(phone_number, reply_text)
                return True

            # If we produced ogg, send as voice note; if mp3/mpeg, send as regular audio
            is_voice_note = 'ogg' in audio_blob.mime_type
            voice_ok = self.whatsapp.send_voice_message(phone_number, media_id_out, voice=is_voice_note)
            if not voice_ok:
                self.whatsapp.send_text_message(phone_number, reply_text)
                return True

            # Voice-only behavior: do not also send text when original message was voice
            return True

        except Exception as e:
            logger.error(f"Voice pipeline error: {e}")
            return False


