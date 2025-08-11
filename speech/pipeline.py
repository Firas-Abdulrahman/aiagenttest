import logging
from typing import Dict, Any, Optional
from datetime import datetime

from .asr_service import ASRService
from .tts_service import TTSService
from ..whatsapp.client import WhatsAppClient
from ..database.thread_safe_manager import ThreadSafeDatabaseManager
from ..workflow.thread_safe_handlers import ThreadSafeMessageHandler
from .types import Transcript, AudioBlob

logger = logging.getLogger(__name__)


class VoiceMessagePipeline:
    def __init__(self, asr_service: ASRService, tts_service: TTSService,
                 whatsapp_client: WhatsAppClient, db_manager: ThreadSafeDatabaseManager,
                 message_handler: ThreadSafeMessageHandler, config: Dict):
        self.asr = asr_service
        self.tts = tts_service
        self.whatsapp = whatsapp_client
        self.db = db_manager
        self.message_handler = message_handler
        self.config = config

        self.asr_enabled = config.get('asr_enabled', False)
        self.tts_enabled = config.get('tts_enabled', False)
        self.tts_mime_type = config.get('tts_mime', 'audio/ogg')
        self.tts_voice_ar = config.get('tts_voice_ar', 'shimmer')
        self.tts_voice_en = config.get('tts_voice_en', 'alloy')
        self.voice_reply_text_fallback = config.get('voice_reply_text_fallback', True)

        logger.info(f"✅ Voice pipeline initialized: ASR={self.asr_enabled}, TTS={self.tts_enabled}")

    async def process_voice_message(self, message_data: Dict[str, Any]) -> bool:
        phone_number = message_data.get('from')
        audio_id = message_data.get('audio', {}).get('id')
        message_id = message_data.get('id')

        if not phone_number or not audio_id:
            logger.error("❌ Missing phone number or audio ID in voice message data.")
            return False

        logger.info(f"🎙️ Processing voice message from {phone_number} (ID: {audio_id})")

        media_info = self.whatsapp.get_media(audio_id)
        if not media_info or not media_info.get('url'):
            logger.error(f"❌ Could not get media info for audio ID: {audio_id}")
            self._send_text_fallback(phone_number, "عذراً، لم أتمكن من معالجة رسالتك الصوتية. الرجاء المحاولة مرة أخرى أو إرسال رسالة نصية.\nSorry, I couldn't process your voice message. Please try again or send a text message.", language='arabic')
            return True

        audio_bytes = self.whatsapp.download_media(media_info['url'])
        if not audio_bytes:
            logger.error(f"❌ Could not download audio for ID: {audio_id}")
            self._send_text_fallback(phone_number, "عذراً، لم أتمكن من تحميل رسالتك الصوتية. الرجاء المحاولة مرة أخرى أو إرسال رسالة نصية.\nSorry, I couldn't download your voice message. Please try again or send a text message.", language='arabic')
            return True

        mime_type = media_info.get('mime_type', 'audio/ogg')
        
        transcript = Transcript(text="", language=None, confidence=None, duration_s=None)
        if self.asr_enabled:
            # Force Arabic language hint for better transcription
            transcript = self.asr.transcribe(audio_bytes, mime_type, language_hint='ar')
            if not transcript.text:
                logger.warning(f"⚠️ ASR failed or returned empty transcript for {phone_number}. Sending fallback.")
                self._send_text_fallback(phone_number, "عذراً، لم أتمكن من فهم رسالتك الصوتية. الرجاء المحاولة مرة أخرى أو إرسال رسالة نصية.\nSorry, I couldn't understand your voice message. Please try again or send a text message.", language='arabic')
                return True

        logger.info(f"🗣️ Transcribed: '{transcript.text}' (Lang: {transcript.language})")
        self.db.log_conversation(phone_number, 'user_voice_message', transcript.text)

        synthetic_message_data = {
            'from': phone_number,
            'id': message_id,
            'type': 'text', # CRITICAL: Ensure it's treated as a text message by the handler
            'text': {'body': transcript.text},
            'contacts': message_data.get('contacts', []) # CRITICAL: Preserve contact info
        }
        
        text_response_data = self.message_handler.handle_message(synthetic_message_data)
        response_text = text_response_data.get('content', '')
        response_language = text_response_data.get('language', 'arabic')

        if not response_text:
            logger.warning(f"⚠️ Handler returned empty text response for {phone_number}.")
            self._send_text_fallback(phone_number, "عذراً، لم أتمكن من توليد رد. الرجاء المحاولة مرة أخرى.\nSorry, I couldn't generate a response. Please try again.", language=response_language)
            return True

        self.db.log_conversation(phone_number, 'bot_voice_response_text', response_text)

        audio_response = AudioBlob(data=b"", mime_type=self.tts_mime_type)
        if self.tts_enabled:
            tts_voice = self.tts_voice_ar if response_language == 'arabic' else self.tts_voice_en
            audio_response = self.tts.synthesize(response_text, response_language, tts_voice, self.tts_mime_type)
            
            if not audio_response.data:
                logger.warning(f"⚠️ TTS failed or returned empty audio for {phone_number}. Sending text fallback.")
                self._send_text_fallback(phone_number, response_text, language=response_language)
                return True

        if audio_response.data:
            media_upload_mime = audio_response.mime_type
            file_extension = 'ogg' if 'ogg' in media_upload_mime else ('mp3' if 'mp3' in media_upload_mime else 'audio')
            uploaded_media_id = self.whatsapp.upload_media(audio_response.data, media_upload_mime, filename=f"response.{file_extension}")

            if uploaded_media_id:
                is_voice_note = 'ogg' in media_upload_mime or 'opus' in media_upload_mime
                success = self.whatsapp.send_voice_message(phone_number, uploaded_media_id, voice=is_voice_note)
                if success:
                    logger.info(f"✅ Voice message sent successfully to {phone_number}.")
                    return True
                else:
                    logger.error(f"❌ Failed to send voice message to {phone_number}. Sending text fallback.")
                    self._send_text_fallback(phone_number, response_text, language=response_language)
                    return True
            else:
                logger.error(f"❌ Failed to upload audio for {phone_number}. Sending text fallback.")
                self._send_text_fallback(phone_number, response_text, language=response_language)
                return True
        else:
            logger.info(f"ℹ️ No audio generated/enabled for {phone_number}. Sending text response.")
            self._send_text_fallback(phone_number, response_text, language=response_language)
            return True

    def _send_text_fallback(self, phone_number: str, text: str, language: str = 'arabic'):
        if self.voice_reply_text_fallback:
            logger.info(f"Fallback: Sending text message to {phone_number}: {text[:50]}...")
            self.whatsapp.send_text_message(phone_number, text)
        else:
            logger.info(f"Fallback: Text fallback disabled. Not sending text to {phone_number}.")


# Keep the old simple pipeline for backward compatibility
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
                # Handle as "processed" to avoid normal text flow sending another message
                self.whatsapp.send_text_message(phone_number, "لم أتمكن من فهم الرسالة الصوتية. الرجاء إعادة إرسال ملاحظة صوتية أقصر أو أوضح.")
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
            audio_blob: AudioBlob = self.tts.synthesize(
                reply_text,
                language=transcript.language,
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


