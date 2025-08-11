# workflow/thread_safe_handlers.py - REFACTORED to use main handlers.py
"""
Thread-safe wrapper for main message handlers with user isolation
"""
import logging
import time
from typing import Dict, Any, Optional
from datetime import datetime

from utils.thread_safe_session import session_manager
from database.thread_safe_manager import ThreadSafeDatabaseManager
from workflow.handlers import MessageHandler
from workflow.enhanced_handlers import EnhancedMessageHandler
from speech.pipeline import VoicePipeline
from speech.providers.openai_asr import OpenAIASR
from speech.providers.openai_tts import OpenAITTS

logger = logging.getLogger(__name__)


class ThreadSafeMessageHandler:
    """Thread-safe wrapper for main message handlers with user isolation"""

    def __init__(self, database_manager: ThreadSafeDatabaseManager, ai_processor=None, action_executor=None, whatsapp_client=None):
        self.db = database_manager
        self.ai = ai_processor
        self.executor = action_executor
        self.whatsapp_client = whatsapp_client
        
        # Initialize the main message handler
        self.main_handler = MessageHandler(database_manager, ai_processor, action_executor)
        
        # Initialize enhanced handler if enhanced AI processor is available
        try:
            from ai.enhanced_processor import EnhancedAIProcessor
            if isinstance(ai_processor, EnhancedAIProcessor):
                self.enhanced_handler = EnhancedMessageHandler(database_manager, ai_processor, action_executor)
                logger.info("✅ Enhanced message handler initialized with AI integration")
            else:
                self.enhanced_handler = None
                logger.info("ℹ️ Standard message handler initialized (enhanced AI not available)")
        except ImportError:
            self.enhanced_handler = None
            logger.info("ℹ️ Standard message handler initialized (enhanced processor not available)")

        # Initialize voice pipeline if configured and OpenAI client available in AI processors
        self.voice_pipeline = None
        try:
            # Reuse OpenAI client from existing AI processor if possible
            openai_client = getattr(ai_processor, 'client', None)
            if openai_client:
                asr = OpenAIASR(openai_client, model='whisper-1')
                tts = OpenAITTS(openai_client, model='gpt-4o-mini-tts')
                from whatsapp.client import WhatsAppClient  # type: ignore
                # We already have a client instance in app/workflow; we will use self.whatsapp from workflow
                # Here, we leave pipeline prepared to be wired by the workflow that holds whatsapp client
                self.voice_pipeline = {'asr': asr, 'tts': tts}
        except Exception as e:
            logger.warning(f"Voice pipeline setup skipped: {e}")

    def handle_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Main message handling with thread safety and user isolation"""

        # Extract basic message info
        phone_number = message_data.get('from')
        message_id = message_data.get('id', f"msg_{time.time()}")
        text = message_data.get('text', {}).get('body', '').strip()

        if not phone_number:
            return self._create_error_response("Invalid phone number")

        # Check for message duplication
        if session_manager.is_message_duplicate(phone_number, message_id):
            logger.warning(f"🔄 Duplicate message detected for {phone_number}")
            return self._create_response("Message already processed")

        # Use user-specific lock for entire processing
        try:
            with session_manager.user_session_lock(phone_number):
                # If voice message, route to voice pipeline
                if message_data.get('audio') and self.voice_pipeline and hasattr(self, 'whatsapp_client'):
                    try:
                        # Prefer enhanced handler if available for natural language understanding
                        handler_for_voice = self.enhanced_handler if getattr(self, 'enhanced_handler', None) else self.main_handler
                        pipeline = VoicePipeline(self.voice_pipeline['asr'], self.voice_pipeline['tts'], self.whatsapp_client, handler_for_voice)
                        ok = pipeline.process_voice_message(phone_number, message_data)
                        if ok:
                            return { 'type': 'handled' }
                    except Exception as e:
                        logger.error(f"Voice pipeline failed: {e}")

                return self._process_user_message_safely(phone_number, text, message_data)

        except TimeoutError:
            logger.error(f"⏰ Timeout acquiring lock for user {phone_number}")
            return self._create_error_response(
                "الخدمة مشغولة حالياً. الرجاء إعادة المحاولة خلال ثواني\n"
                "Service busy. Please try again in a few seconds"
            )
        except Exception as e:
            logger.error(f"❌ Error processing message for {phone_number}: {e}")
            return self._create_error_response(
                "حدث خطأ. الرجاء إعادة المحاولة\n"
                "An error occurred. Please try again"
            )

    def _process_user_message_safely(self, phone_number: str, text: str, message_data: Dict) -> Dict:
        """Process user message within user lock using main handler"""

        # Mark user as processing
        session_manager.set_user_processing(phone_number, True)

        try:
            # Extract customer info
            customer_name = self._extract_customer_name(message_data)

            # Get current user state
            user_state = session_manager.get_user_state(phone_number)
            current_step = user_state.current_step if user_state else 'waiting_for_language'
            language = user_state.language_preference if user_state else None

            logger.info(f"👤 Processing for {phone_number}: '{text}' at step '{current_step}'")

            # Log conversation
            self.db.log_conversation(phone_number, 'user_message', text, current_step=current_step)

            # Use enhanced handler if available, otherwise fall back to main handler
            if hasattr(self, 'enhanced_handler') and self.enhanced_handler:
                logger.info(f"🧠 Using enhanced AI handler for {phone_number}")
                response = self.enhanced_handler.handle_message(message_data)
            else:
                logger.info(f"🤖 Using standard handler for {phone_number}")
                response = self.main_handler.handle_message(message_data)

            # Log response
            self.db.log_conversation(phone_number, 'bot_response', response.get('content', ''))

            return response

        finally:
            # Always clear processing flag
            session_manager.set_user_processing(phone_number, False)

    def _extract_customer_name(self, message_data: Dict) -> str:
        """Extract customer name from message data"""
        if 'contacts' in message_data:
            contacts = message_data.get('contacts', [])
            if contacts and len(contacts) > 0:
                profile = contacts[0].get('profile', {})
                name = profile.get('name', '').strip()
                if name and len(name) <= 50:
                    return name

        # Fallback to generic name
        phone = message_data.get('from', '')
        if phone:
            return f"Customer {phone[-4:]}"

        return "Valued Customer"

    def _create_response(self, content: str) -> Dict[str, Any]:
        """Create standardized response"""
        # Truncate if too long
        if len(content) > 4000:
            content = content[:3900] + "...\n(تم اختصار الرسالة)"

        return {
            'type': 'text',
            'content': content,
            'timestamp': datetime.now().isoformat()
        }

    def _create_error_response(self, message: str) -> Dict[str, Any]:
        """Create error response"""
        return self._create_response(message)