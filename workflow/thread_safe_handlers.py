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

logger = logging.getLogger(__name__)


class ThreadSafeMessageHandler:
    """Thread-safe wrapper for main message handlers with user isolation"""

    def __init__(self, database_manager: ThreadSafeDatabaseManager, ai_processor=None, action_executor=None):
        self.db = database_manager
        self.ai = ai_processor
        self.executor = action_executor
        
        # Initialize the main message handler
        self.main_handler = MessageHandler(database_manager, ai_processor, action_executor)

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

            # Use the main handler to process the message
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