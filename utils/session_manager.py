# utils/session_manager.py - New utility for session management

import logging
from datetime import datetime, timedelta
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class SessionManager:
    """Utility class for managing user sessions and state"""

    @staticmethod
    def is_session_expired(session: Dict, timeout_minutes: int = 30) -> bool:
        """Check if a session has expired"""
        if not session:
            return True

        last_update = session.get('updated_at')
        if not last_update:
            return True

        try:
            last_update_time = datetime.fromisoformat(last_update.replace('Z', '+00:00'))
            time_diff = datetime.now() - last_update_time
            return time_diff.total_seconds() > (timeout_minutes * 60)
        except Exception as e:
            logger.warning(f"⚠️ Error parsing session time: {e}")
            return True

    @staticmethod
    def detect_fresh_start_intent(message: str, current_step: str) -> bool:
        """Detect if user wants to start fresh conversation"""
        message_lower = message.lower().strip()

        # Greeting words that might indicate fresh start
        greetings = ['مرحبا', 'السلام عليكم', 'أهلا', 'hello', 'hi', 'hey']

        # If user just says greeting and not at initial steps, might want fresh start
        if (any(greeting in message_lower for greeting in greetings) and
                len(message.strip()) <= 15 and
                current_step not in ['waiting_for_language', 'waiting_for_category']):
            return True

        return False

    @staticmethod
    def detect_new_order_keywords(message: str, language: str = 'arabic') -> bool:
        """Detect explicit new order keywords"""
        message_lower = message.lower().strip()

        if language == 'arabic':
            keywords = [
                'طلب جديد', 'طلبية جديدة', 'ابدأ من جديد', 'من البداية',
                'لا طلب جديد', 'اريد طلب جديد', 'بدي طلب جديد',
                'ألغي الطلب', 'ابدأ من الأول', 'بداية جديدة'
            ]
        else:
            keywords = [
                'new order', 'fresh order', 'start over', 'start fresh',
                'no new order', 'begin again', 'restart', 'cancel order',
                'fresh start'
            ]

        return any(keyword in message_lower for keyword in keywords)

    @staticmethod
    def get_session_summary(session: Dict) -> str:
        """Get a human-readable session summary"""
        if not session:
            return "No active session"

        summary = f"Step: {session.get('current_step', 'Unknown')}"

        if session.get('language_preference'):
            summary += f", Language: {session['language_preference']}"

        if session.get('selected_category'):
            summary += f", Category: {session['selected_category']}"

        if session.get('selected_item'):
            summary += f", Item: {session['selected_item']}"

        return summary


# utils/message_validator.py - Enhanced message validation

import re
from typing import Dict, List, Optional


class MessageValidator:
    """Enhanced message validation and sanitization"""

    # Spam detection patterns
    SPAM_PATTERNS = [
        r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',
        r'www\.[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
        r'(?:buy now|click here|limited time|free money|guarantee|win|prize)',
        r'(?:call|text|whatsapp)\s*[+]?[0-9\s\-()]{10,}',
    ]

    @staticmethod
    def is_valid_message(message_data: Dict) -> bool:
        """Validate incoming WhatsApp message format"""
        if not message_data:
            return False

        # Must have sender
        if 'from' not in message_data:
            return False

        # Must have text content or be a supported media type
        has_text = 'text' in message_data and 'body' in message_data.get('text', {})
        has_media = any(media_type in message_data for media_type in ['image', 'audio', 'document', 'location'])

        return has_text or has_media

    @staticmethod
    def sanitize_text(text: str) -> str:
        """Sanitize and clean user text input"""
        if not text:
            return ""

        # Remove excessive whitespace
        text = ' '.join(text.split())

        # Limit length to prevent abuse
        if len(text) > 1000:
            text = text[:1000]

        # Remove potentially harmful characters
        text = re.sub(r'[<>{}]', '', text)

        return text.strip()

    @staticmethod
    def is_spam(text: str) -> bool:
        """Simple spam detection"""
        if not text:
            return False

        text_lower = text.lower()

        # Check against spam patterns
        for pattern in MessageValidator.SPAM_PATTERNS:
            if re.search(pattern, text_lower):
                return True

        # Check for excessive repetition
        words = text_lower.split()
        if len(words) > 3:
            unique_words = set(words)
            if len(unique_words) / len(words) < 0.3:  # Less than 30% unique words
                return True

        return False

    @staticmethod
    def extract_phone_number(message_data: Dict) -> Optional[str]:
        """Extract and validate phone number from message"""
        phone = message_data.get('from', '')

        if not phone:
            return None

        # Clean phone number
        phone_cleaned = re.sub(r'[^\d+]', '', phone)

        # Validate length (should be at least 10 digits)
        if len(phone_cleaned.replace('+', '')) < 10:
            return None

        return phone_cleaned

    @staticmethod
    def extract_customer_name(message_data: Dict) -> str:
        """Extract customer name with fallback"""
        if 'contacts' in message_data:
            contacts = message_data.get('contacts', [])
            if contacts and len(contacts) > 0:
                profile = contacts[0].get('profile', {})
                name = profile.get('name', '').strip()
                if name and len(name) <= 50:  # Reasonable name length
                    return name

        # Fallback to phone number or generic name
        phone = MessageValidator.extract_phone_number(message_data)
        if phone:
            return f"Customer {phone[-4:]}"  # Last 4 digits

        return "Valued Customer"


# utils/order_formatter.py - Order formatting utilities

class OrderFormatter:
    """Utilities for formatting orders and menu items"""

    @staticmethod
    def format_menu_categories(categories: List[Dict], language: str = 'arabic') -> str:
        """Format menu categories for display"""
        if not categories:
            return "لا توجد فئات متاحة\nNo categories available"

        if language == 'arabic':
            formatted = "القائمة الرئيسية:\n\n"
            for i, cat in enumerate(categories, 1):
                formatted += f"{i}. {cat['category_name_ar']}\n"
            formatted += "\nالرجاء اختيار الفئة المطلوبة بالرد بالرقم"
        else:
            formatted = "Main Menu:\n\n"
            for i, cat in enumerate(categories, 1):
                formatted += f"{i}. {cat['category_name_en']}\n"
            formatted += "\nPlease select the required category by replying with the number"

        return formatted

    @staticmethod
    def format_menu_items(items: List[Dict], category_name: str, language: str = 'arabic') -> str:
        """Format menu items for display"""
        if not items:
            return "لا توجد عناصر متاحة\nNo items available"

        if language == 'arabic':
            formatted = f"قائمة {category_name}:\n\n"
            for i, item in enumerate(items, 1):
                formatted += f"{i}. {item['item_name_ar']}\n"
                formatted += f"   السعر: {item['price']} دينار\n\n"
            formatted += "الرجاء اختيار المنتج المطلوب"
        else:
            formatted = f"{category_name} Menu:\n\n"
            for i, item in enumerate(items, 1):
                formatted += f"{i}. {item['item_name_en']}\n"
                formatted += f"   Price: {item['price']} IQD\n\n"
            formatted += "Please select the required item"

        return formatted

    @staticmethod
    def format_order_summary(order: Dict, language: str = 'arabic') -> str:
        """Format complete order summary"""
        if not order or not order.get('items'):
            if language == 'arabic':
                return "لا توجد عناصر في طلبك"
            else:
                return "No items in your order"

        if language == 'arabic':
            summary = "ملخص طلبك:\n\n"
            summary += "الأصناف:\n"
            for item in order['items']:
                summary += f"• {item['item_name_ar']} × {item['quantity']} - {item['subtotal']} دينار\n"

            details = order.get('details', {})
            if details.get('service_type'):
                service_ar = 'تناول في المقهى' if details['service_type'] == 'dine-in' else 'توصيل'
                summary += f"\nنوع الخدمة: {service_ar}"

            if details.get('location'):
                summary += f"\nالمكان: {details['location']}"

            summary += f"\n\nالمجموع الكلي: {order.get('total', 0)} دينار"
        else:
            summary = "Your Order Summary:\n\n"
            summary += "Items:\n"
            for item in order['items']:
                summary += f"• {item['item_name_en']} × {item['quantity']} - {item['subtotal']} IQD\n"

            details = order.get('details', {})
            if details.get('service_type'):
                summary += f"\nService Type: {details['service_type'].title()}"

            if details.get('location'):
                summary += f"\nLocation: {details['location']}"

            summary += f"\n\nTotal: {order.get('total', 0)} IQD"

        return summary

    @staticmethod
    def format_order_confirmation(order_id: str, total_amount: int, language: str = 'arabic') -> str:
        """Format order confirmation message"""
        if language == 'arabic':
            message = f"🎉 تم تأكيد طلبك بنجاح!\n\n"
            message += f"📋 رقم الطلب: {order_id}\n"
            message += f"💰 المبلغ الإجمالي: {total_amount} دينار\n\n"
            message += f"⏰ سنقوم بإشعارك عندما يصبح طلبك جاهزاً\n"
            message += f"💳 الرجاء دفع المبلغ للكاشير عند المنضدة\n\n"
            message += f"شكراً لك لاختيار مقهى هيف! ☕"
        else:
            message = f"🎉 Your order has been confirmed successfully!\n\n"
            message += f"📋 Order ID: {order_id}\n"
            message += f"💰 Total Amount: {total_amount} IQD\n\n"
            message += f"⏰ We'll notify you when your order is ready\n"
            message += f"💳 Please pay the amount to the cashier at the counter\n\n"
            message += f"Thank you for choosing Hef Cafe! ☕"

        return message


# workflow/main.py - Enhanced main workflow with new utilities

import logging
from typing import Dict, Any
from config.settings import WhatsAppConfig
from database.manager import DatabaseManager
from ai.processor import AIProcessor
from workflow.handlers import MessageHandler
from workflow.actions import ActionExecutor
from whatsapp.client import WhatsAppClient
from utils.session_manager import SessionManager
from utils.message_validator import MessageValidator

logger = logging.getLogger(__name__)


class WhatsAppWorkflow:
    """Enhanced main workflow orchestrator for WhatsApp bot"""

    def __init__(self, config: Dict[str, str]):
        """Initialize the complete workflow system"""
        self.config = config
        self.session_manager = SessionManager()
        self.message_validator = MessageValidator()

        # Initialize core components
        self._init_components()

        logger.info("✅ Enhanced WhatsApp workflow initialized successfully")

    def _init_components(self):
        """Initialize all workflow components"""
        try:
            # Database manager
            self.db = DatabaseManager(self.config.get('db_path', 'hef_cafe.db'))
            logger.info("✅ Database manager initialized")

            # AI processor
            self.ai = AIProcessor(self.config.get('openai_api_key'))
            logger.info("✅ AI processor initialized")

            # WhatsApp client
            self.whatsapp = WhatsAppClient(self.config)
            logger.info("✅ WhatsApp client initialized")

            # Action executor
            self.executor = ActionExecutor(self.db)
            logger.info("✅ Action executor initialized")

            # Message handler
            self.handler = MessageHandler(self.db, self.ai, self.executor)
            logger.info("✅ Message handler initialized")

            # Start background cleanup task
            self._schedule_cleanup()

        except Exception as e:
            logger.error(f"❌ Error initializing components: {str(e)}")
            raise

    def _schedule_cleanup(self):
        """Schedule periodic cleanup of expired sessions"""
        import threading
        import time

        def cleanup_worker():
            while True:
                try:
                    time.sleep(1800)  # Run every 30 minutes
                    cleaned = self.db.cleanup_expired_sessions()
                    if cleaned > 0:
                        logger.info(f"🧹 Background cleanup: removed {cleaned} expired sessions")
                except Exception as e:
                    logger.error(f"❌ Background cleanup error: {e}")

        cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        cleanup_thread.start()
        logger.info("🔄 Background session cleanup scheduled")

    def handle_whatsapp_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced message handling with validation and spam protection"""
        try:
            logger.info("📨 Processing incoming WhatsApp message")

            # Validate message format
            if not self.message_validator.is_valid_message(message_data):
                logger.warning("⚠️ Invalid message format received")
                return self._create_error_response("Invalid message format")

            # Extract and validate content
            text = message_data.get('text', {}).get('body', '').strip()
            phone_number = self.message_validator.extract_phone_number(message_data)

            if not phone_number:
                logger.warning("⚠️ Invalid phone number in message")
                return self._create_error_response("Invalid phone number")

            # Spam detection
            if self.message_validator.is_spam(text):
                logger.warning(f"🚨 Spam detected from {phone_number}: {text[:50]}")
                return self._create_error_response("Message flagged as spam")

            # Sanitize input
            text = self.message_validator.sanitize_text(text)
            customer_name = self.message_validator.extract_customer_name(message_data)

            # Process through enhanced handler
            response = self.handler.handle_message({
                'from': phone_number,
                'text': {'body': text},
                'contacts': [{'profile': {'name': customer_name}}]
            })

            logger.info("✅ Message processed successfully")
            return response

        except Exception as e:
            logger.error(f"❌ Error handling WhatsApp message: {str(e)}")
            return self._create_error_response("حدث خطأ. الرجاء إعادة المحاولة\nAn error occurred. Please try again")

    def _create_error_response(self, message: str) -> Dict[str, Any]:
        """Create standardized error response"""
        return {
            'type': 'text',
            'content': message,
            'timestamp': __import__('datetime').datetime.now().isoformat()
        }

    # Enhanced health check with session monitoring
    def health_check(self) -> Dict:
        """Enhanced health check with session monitoring"""
        health_status = {
            'status': 'healthy',
            'components': {},
            'session_info': {},
            'timestamp': __import__('datetime').datetime.now().isoformat()
        }

        # Database health
        try:
            stats = self.db.get_database_stats()

            # Get session statistics
            active_sessions = stats.get('user_sessions_count', 0)
            expired_cleaned = self.db.cleanup_expired_sessions()

            health_status['components']['database'] = {
                'status': 'healthy',
                'stats': stats
            }

            health_status['session_info'] = {
                'active_sessions': active_sessions,
                'expired_cleaned': expired_cleaned,
                'session_timeout_minutes': 30
            }

        except Exception as e:
            health_status['components']['database'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
            health_status['status'] = 'degraded'

        # AI health
        ai_test = self.test_ai_connection()
        health_status['components']['ai'] = ai_test
        if ai_test['status'] == 'error':
            health_status['status'] = 'degraded'

        # WhatsApp API health
        try:
            phone_numbers = self.get_phone_numbers()
            health_status['components']['whatsapp'] = {
                'status': 'healthy',
                'phone_numbers_count': len(phone_numbers) if phone_numbers else 0
            }
        except Exception as e:
            health_status['components']['whatsapp'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
            health_status['status'] = 'degraded'

        return health_status

    # Rest of the existing methods remain the same...
    def send_whatsapp_message(self, phone_number: str, response_data: Dict[str, Any]) -> bool:
        """Send response back to WhatsApp"""
        try:
            logger.info(f"📤 Sending response to {phone_number}")
            return self.whatsapp.send_response(phone_number, response_data)
        except Exception as e:
            logger.error(f"❌ Error sending WhatsApp message: {str(e)}")
            return False

    def verify_webhook(self, mode: str, token: str, challenge: str) -> str:
        """Verify webhook for WhatsApp"""
        return self.whatsapp.verify_webhook(mode, token, challenge)

    def validate_webhook_payload(self, payload: Dict) -> bool:
        """Validate incoming webhook payload"""
        return self.whatsapp.validate_webhook_payload(payload)

    def extract_messages_from_webhook(self, payload: Dict) -> list:
        """Extract messages from webhook payload"""
        return self.whatsapp.get_webhook_data(payload)

    def is_ai_available(self) -> bool:
        """Check if AI processing is available"""
        return self.ai.is_available()

    def test_ai_connection(self) -> Dict:
        """Test AI connection and capabilities"""
        if not self.ai.is_available():
            return {'status': 'unavailable', 'message': 'AI not configured'}

        try:
            test_result = self.ai.understand_message(
                "Hello",
                "waiting_for_language",
                {'current_step': 'waiting_for_language'}
            )

            if test_result:
                return {'status': 'available', 'message': 'AI working correctly'}
            else:
                return {'status': 'error', 'message': 'AI not responding properly'}

        except Exception as e:
            return {'status': 'error', 'message': f'AI test failed: {str(e)}'}

    def get_phone_numbers(self) -> list:
        """Get all phone numbers associated with the account"""
        return self.whatsapp.get_phone_numbers() or []


# For backward compatibility
TrueAIWorkflow = WhatsAppWorkflow  # workflow/handlers.py - Updated MessageHandler with session timeout and new order detection

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class MessageHandler:
    """Main message handler for WhatsApp workflow"""

    def __init__(self, database_manager, ai_processor, action_executor):
        self.db = database_manager
        self.ai = ai_processor
        self.executor = action_executor

    def handle_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Main message handling entry point"""
        try:
            # Validate message format
            if not self._validate_message(message_data):
                return self._create_error_response("Invalid message format")

            # Extract message details
            text = message_data.get('text', {}).get('body', '').strip()
            phone_number = message_data.get('from')
            customer_name = self._extract_customer_name(message_data)

            # Log incoming message
            self.db.log_conversation(phone_number, 'user_message', text)

            # Get current session state with timeout check
            session = self.db.get_user_session(phone_number)

            # Check for session timeout or new order intent
            should_reset = self._should_reset_session(session, text)

            if should_reset:
                logger.info(f"🔄 Resetting session for {phone_number}")
                self.db.delete_session(phone_number)
                session = None

            current_step = session['current_step'] if session else 'waiting_for_language'

            # Check for new order intent specifically
            if session and self._detect_new_order_intent(text, session.get('language_preference', 'arabic')):
                logger.info(f"🆕 New order intent detected for {phone_number}")
                self.db.delete_session(phone_number)
                current_step = 'waiting_for_language'
                session = None

            logger.info(f"📊 User {phone_number} at step: {current_step}")

            # Process message with AI or fallback
            response = self._process_message(phone_number, current_step, text, customer_name, session)

            # Log AI response
            self.db.log_conversation(phone_number, 'ai_response', response['content'])

            return response

        except Exception as e:
            logger.error(f"❌ Error handling message: {str(e)}")
            return self._create_error_response("حدث خطأ. الرجاء إعادة المحاولة\nAn error occurred. Please try again")

    def _should_reset_session(self, session: Dict, user_message: str) -> bool:
        """Check if session should be reset due to timeout or greeting"""
        if not session:
            return False

        # Check session timeout (30 minutes)
        last_update = session.get('updated_at')
        if last_update:
            try:
                last_update_time = datetime.fromisoformat(last_update.replace('Z', '+00:00'))
                time_diff = datetime.now() - last_update_time
                if time_diff.total_seconds() > 1800:  # 30 minutes
                    logger.info(f"⏰ Session timeout detected: {time_diff.total_seconds()} seconds")
                    return True
            except Exception as e:
                logger.warning(f"⚠️ Error parsing session time: {e}")
                return True

        # Check for greeting words that might indicate a fresh start
        greeting_words = ['مرحبا', 'السلام عليكم', 'أهلا', 'hello', 'hi', 'hey']
        user_lower = user_message.lower().strip()

        # If user just says a greeting and is not at language selection step, might want fresh start
        if (any(greeting in user_lower for greeting in greeting_words) and
                len(user_message.strip()) <= 10 and
                session.get('current_step') not in ['waiting_for_language', 'waiting_for_category']):
            return True

        return False

    def _detect_new_order_intent(self, text: str, language: str) -> bool:
        """Detect when user explicitly wants to start a new order"""
        text_lower = text.lower().strip()

        if language == 'arabic':
            new_order_keywords = [
                'طلب جديد', 'طلبية جديدة', 'ابدأ من جديد', 'من البداية',
                'لا طلب جديد', 'اريد طلب جديد', 'بدي طلب جديد',
                'ألغي الطلب', 'ابدأ من الأول', 'جديد'
            ]
        else:
            new_order_keywords = [
                'new order', 'fresh order', 'start over', 'start fresh',
                'no new order', 'begin again', 'restart', 'cancel order'
            ]

        return any(keyword in text_lower for keyword in new_order_keywords)

    def _validate_message(self, message_data: Dict) -> bool:
        """Validate incoming message format"""
        if not message_data:
            return False

        # Check for required fields
        if 'from' not in message_data:
            return False

        # Check for text content
        if 'text' not in message_data or 'body' not in message_data.get('text', {}):
            return False

        return True

    def _extract_customer_name(self, message_data: Dict) -> str:
        """Extract customer name from WhatsApp message data"""
        if 'contacts' in message_data:
            contacts = message_data.get('contacts', [])
            if contacts and len(contacts) > 0:
                profile = contacts[0].get('profile', {})
                return profile.get('name', 'Customer')
        return 'Customer'

    def _process_message(self, phone_number: str, current_step: str, user_message: str,
                         customer_name: str, session: Dict) -> Dict:
        """Process user message with AI understanding or fallback"""

        # Build context for AI
        context = self._build_conversation_context(session, current_step)

        # Try AI processing first
        if self.ai.is_available():
            ai_result = self.ai.understand_message(user_message, current_step, context)

            if ai_result:
                return self.executor.execute_action(phone_number, ai_result, session, customer_name)

        # Fallback to simple processing
        return self._fallback_processing(phone_number, current_step, user_message, customer_name, session)

    def _build_conversation_context(self, session: Dict, current_step: str) -> Dict:
        """Build rich context for AI understanding"""
        context = {
            'current_step': current_step,
            'step_description': self._get_step_description(current_step),
            'available_categories': [],
            'current_category_items': [],
            'current_order': {},
            'language': session.get('language_preference') if session else None
        }

        # Add categories if relevant
        if current_step in ['waiting_for_language', 'waiting_for_category']:
            context['available_categories'] = self.db.get_available_categories()

        # Add items if in item selection
        if current_step == 'waiting_for_item' and session and session.get('selected_category'):
            context['current_category_items'] = self.db.get_category_items(session['selected_category'])

        # Add current order if exists
        if session:
            context['current_order'] = self.db.get_user_order(session['phone_number']) if 'phone_number' in str(
                session) else {}

        return context

    def _get_step_description(self, step: str) -> str:
        """Get human-readable step description"""
        descriptions = {
            'waiting_for_language': 'Choose language preference (Arabic or English)',
            'waiting_for_category': 'Select menu category',
            'waiting_for_item': 'Choose specific item from category',
            'waiting_for_quantity': 'Specify quantity needed',
            'waiting_for_additional': 'Decide if more items needed',
            'waiting_for_service': 'Choose service type (dine-in or delivery)',
            'waiting_for_location': 'Provide location/table number',
            'waiting_for_confirmation': 'Confirm the complete order'
        }
        return descriptions.get(step, 'Unknown step')

    def _fallback_processing(self, phone_number: str, current_step: str, user_message: str,
                             customer_name: str, session: Dict) -> Dict:
        """Fallback processing when AI is unavailable"""
        logger.info("🔄 Using fallback processing")

        # Simple language detection for initial step
        if current_step == 'waiting_for_language':
            language = self.ai.extract_language_preference(user_message)
            if language:
                if self.db.validate_step_transition(phone_number, 'waiting_for_category'):
                    self.db.create_or_update_session(phone_number, 'waiting_for_category', language, customer_name)

                    # Show categories
                    categories = self.db.get_available_categories()
                    if language == 'arabic':
                        response = f"أهلاً {customer_name}!\n\nاختر الفئة:\n"
                        for i, cat in enumerate(categories, 1):
                            response += f"{i}. {cat['category_name_ar']}\n"
                    else:
                        response = f"Welcome {customer_name}!\n\nChoose category:\n"
                        for i, cat in enumerate(categories, 1):
                            response += f"{i}. {cat['category_name_en']}\n"

                    return self._create_response(response)

        # Simple number extraction for other steps
        if current_step == 'waiting_for_category':
            number = self.ai.extract_number_from_text(user_message)
            categories = self.db.get_available_categories()

            if number and 1 <= number <= len(categories):
                selected_category = categories[number - 1]
                language = session.get('language_preference', 'arabic')

                if self.db.validate_step_transition(phone_number, 'waiting_for_item'):
                    self.db.create_or_update_session(phone_number, 'waiting_for_item', language,
                                                     selected_category=selected_category['category_id'])

                    # Show items
                    items = self.db.get_category_items(selected_category['category_id'])
                    if language == 'arabic':
                        response = f"قائمة {selected_category['category_name_ar']}:\n\n"
                        for i, item in enumerate(items, 1):
                            response += f"{i}. {item['item_name_ar']} - {item['price']} دينار\n"
                    else:
                        response = f"{selected_category['category_name_en']} Menu:\n\n"
                        for i, item in enumerate(items, 1):
                            response += f"{i}. {item['item_name_en']} - {item['price']} IQD\n"

                    return self._create_response(response)

        # Generic fallback response
        language = session.get('language_preference', 'arabic') if session else 'arabic'
        fallback_response = self.ai.generate_fallback_response(current_step, language)
        return self._create_response(fallback_response)

    def _create_response(self, content: str) -> Dict[str, Any]:
        """Create standardized response format"""
        # Ensure message doesn't exceed WhatsApp limits
        if len(content) > 4000:
            content = content[:3900] + "... (تم اختصار الرسالة)"

        return {
            'type': 'text',
            'content': content,
            'timestamp': datetime.now().isoformat()
        }

    def _create_error_response(self, message: str) -> Dict[str, Any]:
        """Create error response"""
        return self._create_response(message)


# workflow/actions.py - Updated ActionExecutor with better flow management

class ActionExecutor:
    """Execute actions determined by AI understanding"""

    def __init__(self, database_manager):
        self.db = database_manager

    def execute_action(self, phone_number: str, ai_result: Dict, session: Dict, customer_name: str) -> Dict:
        """Execute the action determined by AI with flexible workflow support"""
        action = ai_result.get('action')
        extracted_data = ai_result.get('extracted_data', {})
        response_message = ai_result.get('response_message', '')
        clarification_needed = ai_result.get('clarification_needed', False)
        current_step = session.get('current_step') if session else 'waiting_for_language'

        logger.info(f"🎯 Executing action: {action}")

        # If AI needs clarification, return clarification question
        if clarification_needed:
            clarification_question = ai_result.get('clarification_question', 'Could you please clarify?')
            return self._create_response(clarification_question)

        try:
            # Handle staying at current step for clarification/help
            if action == 'stay_current_step':
                return self._create_response(response_message)

            # Handle specific actions based on AI understanding
            if action == 'language_selection':
                return self._execute_language_selection(phone_number, extracted_data, customer_name, response_message)

            elif action == 'category_selection':
                return self._execute_category_selection(phone_number, extracted_data, response_message, session)

            elif action == 'item_selection':
                return self._execute_item_selection(phone_number, extracted_data, response_message, session)

            elif action == 'quantity_selection':
                return self._execute_quantity_selection(phone_number, extracted_data, response_message, session)

            elif action == 'yes_no':
                return self._execute_yes_no_action(phone_number, extracted_data, response_message, session)

            elif action == 'service_selection':
                return self._execute_service_selection(phone_number, extracted_data, response_message, session)

            elif action == 'location_input':
                return self._execute_location_input(phone_number, extracted_data, response_message, session)

            elif action == 'confirmation':
                return self._execute_confirmation(phone_number, extracted_data, response_message, session)

            elif action == 'show_menu':
                return self._execute_show_menu(phone_number, current_step, response_message, session)

            elif action == 'help_request':
                return self._execute_help_request(phone_number, current_step, response_message, session)

            else:
                # AI provided a natural response without specific action
                return self._create_response(response_message)

        except Exception as e:
            logger.error(f"❌ Error executing action {action}: {e}")
            return self._create_response(
                "عذراً، حدث خطأ. هل يمكنك المحاولة مرة أخرى؟\nSorry, something went wrong. Can you try again?")

    def _execute_language_selection(self, phone_number: str, extracted_data: Dict, customer_name: str,
                                    response_message: str) -> Dict:
        """Execute language selection with AI understanding"""
        language = extracted_data.get('language')

        if language and self.db.validate_step_transition(phone_number, 'waiting_for_category'):
            success = self.db.create_or_update_session(phone_number, 'waiting_for_category', language, customer_name)

            if success:
                categories = self.db.get_available_categories()

                # Always show the menu after language selection
                if language == 'arabic':
                    response_message = f"أهلاً وسهلاً {customer_name} في مقهى هيف!\n\n"
                    response_message += "القائمة الرئيسية:\n\n"
                    for i, cat in enumerate(categories, 1):
                        response_message += f"{i}. {cat['category_name_ar']}\n"
                    response_message += "\nالرجاء اختيار الفئة المطلوبة بالرد بالرقم"
                else:
                    response_message = f"Welcome {customer_name} to Hef Cafe!\n\n"
                    response_message += "Main Menu:\n\n"
                    for i, cat in enumerate(categories, 1):
                        response_message += f"{i}. {cat['category_name_en']}\n"
                    response_message += "\nPlease select the category by replying with the number"

                return self._create_response(response_message)

        # Language not detected, ask properly
        return self._create_response(
            f"مرحباً بك في مقهى هيف\n\n"
            f"الرجاء اختيار لغتك المفضلة:\n"
            f"1. العربية\n"
            f"2. English\n\n"
            f"Welcome to Hef Cafe\n\n"
            f"Please select your preferred language:\n"
            f"1. العربية (Arabic)\n"
            f"2. English"
        )

    def _execute_yes_no_action(self, phone_number: str, extracted_data: Dict, response_message: str,
                               session: Dict) -> Dict:
        """Execute yes/no actions based on current step - FIXED VERSION"""
        language = session['language_preference'] if session else 'arabic'
        current_step = session['current_step'] if session else 'waiting_for_language'
        yes_no = extracted_data.get('yes_no')

        logger.info(f"🔄 Yes/No action: {yes_no} at step {current_step}")

        if current_step == 'waiting_for_additional':
            if yes_no == 'yes':
                # User wants to add more items - go back to category selection
                if self.db.validate_step_transition(phone_number, 'waiting_for_category'):
                    self.db.create_or_update_session(phone_number, 'waiting_for_category', language)
                    categories = self.db.get_available_categories()

                    # ACTUALLY SHOW THE MENU
                    if language == 'arabic':
                        response_message = "ممتاز! إليك القائمة الرئيسية:\n\n"
                        for i, cat in enumerate(categories, 1):
                            response_message += f"{i}. {cat['category_name_ar']}\n"
                        response_message += "\nالرجاء اختيار الفئة المطلوبة"
                    else:
                        response_message = "Great! Here's the main menu:\n\n"
                        for i, cat in enumerate(categories, 1):
                            response_message += f"{i}. {cat['category_name_en']}\n"
                        response_message += "\nPlease select the required category"

                    return self._create_response(response_message)

            elif yes_no == 'no':
                # User doesn't want more items - go to service selection
                if self.db.validate_step_transition(phone_number, 'waiting_for_service'):
                    self.db.create_or_update_session(phone_number, 'waiting_for_service', language)

                    if language == 'arabic':
                        response_message = "ممتاز! الآن دعنا نحدد نوع الخدمة:\n\n"
                        response_message += "1. تناول في المقهى\n"
                        response_message += "2. توصيل\n\n"
                        response_message += "الرجاء اختيار نوع الخدمة"
                    else:
                        response_message = "Great! Now let's determine the service type:\n\n"
                        response_message += "1. Dine-in\n"
                        response_message += "2. Delivery\n\n"
                        response_message += "Please select the service type"

                    return self._create_response(response_message)

        elif current_step == 'waiting_for_confirmation':
            if yes_no == 'yes':
                # Complete order with proper final confirmation
                order_id = self.db.complete_order(phone_number)
                if order_id:
                    # Get order details before deletion
                    order = self.db.get_user_order(phone_number)
                    total_amount = order.get('total', 0)

                    if language == 'arabic':
                        response_message = f"شكراً لك! تم تأكيد طلبك بنجاح.\n\n"
                        response_message += f"رقم الطلب: {order_id}\n"
                        response_message += f"المبلغ الإجمالي: {total_amount} دينار\n\n"
                        response_message += f"سنقوم بإشعارك بمجرد أن يصبح طلبك جاهزاً.\n"
                        response_message += f"الرجاء دفع المبلغ للكاشير عند المنضدة."
                    else:
                        response_message = f"Thank you! Your order has been confirmed successfully.\n\n"
                        response_message += f"Order ID: {order_id}\n"
                        response_message += f"Total Amount: {total_amount} IQD\n\n"
                        response_message += f"We'll notify you once your order is ready.\n"
                        response_message += f"Please pay the amount to the cashier at the counter."

                    return self._create_response(response_message)

            elif yes_no == 'no':
                # Get customer name before deleting session
                customer_name = session.get('customer_name', 'Customer')
                
                # Cancel order and restart
                self.db.delete_session(phone_number)

                if language == 'arabic':
                    response_message = f"تم إلغاء الطلب. شكراً لك {customer_name} لزيارة مقهى هيف.\n\n"
                    response_message += "يمكنك البدء بطلب جديد في أي وقت بإرسال 'مرحبا'"
                else:
                    response_message = f"Order cancelled. Thank you {customer_name} for visiting Hef Cafe.\n\n"
                    response_message += "You can start a new order anytime by sending 'hello'"

                return self._create_response(response_message)

        # Default response if unclear
        if language == 'arabic':
            return self._create_response("لم أفهم إجابتك. الرجاء الرد بـ 'نعم' أو 'لا'")
        else:
            return self._create_response("I didn't understand your answer. Please reply with 'yes' or 'no'")

    def _execute_show_menu(self, phone_number: str, current_step: str, response_message: str,
                           session: Dict) -> Dict:
        """Show menu based on current step - IMPROVED VERSION"""
        language = session['language_preference'] if session else 'arabic'

        if current_step == 'waiting_for_category':
            # Stay at category step, show categories
            categories = self.db.get_available_categories()

            if language == 'arabic':
                response_message = "القائمة الرئيسية:\n\n"
                for i, cat in enumerate(categories, 1):
                    response_message += f"{i}. {cat['category_name_ar']}\n"
                response_message += "\nالرجاء اختيار الفئة المطلوبة بالرد بالرقم"
            else:
                response_message = "Main Menu:\n\n"
                for i, cat in enumerate(categories, 1):
                    response_message += f"{i}. {cat['category_name_en']}\n"
                response_message += "\nPlease select the required category by replying with the number"

            return self._create_response(response_message)

        elif current_step == 'waiting_for_item' and session and session.get('selected_category'):
            # Stay at item step, show items for current category
            items = self.db.get_category_items(session['selected_category'])
            categories = self.db.get_available_categories()
            current_category = next(
                (cat for cat in categories if cat['category_id'] == session['selected_category']), None)

            if current_category and items:
                if language == 'arabic':
                    response_message = f"قائمة {current_category['category_name_ar']}:\n\n"
                    for i, item in enumerate(items, 1):
                        response_message += f"{i}. {item['item_name_ar']}\n"
                        response_message += f"   السعر: {item['price']} دينار\n\n"
                    response_message += "الرجاء اختيار المنتج المطلوب بالرد بالرقم"
                else:
                    response_message = f"{current_category['category_name_en']} Menu:\n\n"
                    for i, item in enumerate(items, 1):
                        response_message += f"{i}. {item['item_name_en']}\n"
                        response_message += f"   Price: {item['price']} IQD\n\n"
                    response_message += "Please select the required item by replying with the number"

                return self._create_response(response_message)

        # Default menu response for other cases
        if language == 'arabic':
            return self._create_response("لعرض القائمة، الرجاء تحديد الخطوة المناسبة أولاً")
        else:
            return self._create_response("To show the menu, please specify the appropriate step first")

    def _execute_category_selection(self, phone_number: str, extracted_data: Dict, response_message: str,
                                    session: Dict) -> Dict:
        """Execute category selection with AI understanding"""
        language = session['language_preference'] if session else 'arabic'

        # Get category by ID or name
        category_id = extracted_data.get('category_id')
        category_name = extracted_data.get('category_name')

        categories = self.db.get_available_categories()
        selected_category = None

        # Find category by ID
        if category_id:
            selected_category = next((cat for cat in categories if cat['category_id'] == category_id), None)

        # Find category by name if not found by ID
        if not selected_category and category_name:
            name_lower = category_name.lower().strip()
            for cat in categories:
                if (name_lower in cat['category_name_ar'].lower() or
                        name_lower in cat['category_name_en'].lower() or
                        cat['category_name_ar'].lower() in name_lower or
                        cat['category_name_en'].lower() in name_lower):
                    selected_category = cat
                    break

        if selected_category and self.db.validate_step_transition(phone_number, 'waiting_for_item'):
            # Store selected category
            self.db.create_or_update_session(phone_number, 'waiting_for_item', language,
                                             selected_category=selected_category['category_id'])

            # Get items for category
            items = self.db.get_category_items(selected_category['category_id'])

            # Always show the items menu
            if language == 'arabic':
                response_message = f"قائمة {selected_category['category_name_ar']}:\n\n"
                for i, item in enumerate(items, 1):
                    response_message += f"{i}. {item['item_name_ar']}\n"
                    response_message += f"   السعر: {item['price']} دينار\n\n"
                response_message += "الرجاء اختيار المنتج المطلوب"
            else:
                response_message = f"{selected_category['category_name_en']} Menu:\n\n"
                for i, item in enumerate(items, 1):
                    response_message += f"{i}. {item['item_name_en']}\n"
                    response_message += f"   Price: {item['price']} IQD\n\n"
                response_message += "Please select the required item"

            return self._create_response(response_message)

        # Category not found, ask again professionally
        if language == 'arabic':
            response_message = "الفئة غير محددة. الرجاء اختيار رقم صحيح من القائمة:\n\n"
            for i, cat in enumerate(categories, 1):
                response_message += f"{i}. {cat['category_name_ar']}\n"
        else:
            response_message = "Category not specified. Please choose a valid number from the menu:\n\n"
            for i, cat in enumerate(categories, 1):
                response_message += f"{i}. {cat['category_name_en']}\n"

        return self._create_response(response_message)

    def _execute_item_selection(self, phone_number: str, extracted_data: Dict, response_message: str,
                                session: Dict) -> Dict:
        """Execute item selection with AI understanding"""
        language = session['language_preference'] if session else 'arabic'
        selected_category_id = session.get('selected_category') if session else None

        if not selected_category_id:
            return self._create_response(
                "خطأ في النظام. الرجاء إعادة البدء\nSystem error. Please restart")

        # Get items for current category
        items = self.db.get_category_items(selected_category_id)

        # Find item by ID, name, or position
        item_id = extracted_data.get('item_id')
        item_name = extracted_data.get('item_name')
        selected_item = None

        # Find by position (if item_id represents position like 1, 2, 3)
        if item_id and 1 <= item_id <= len(items):
            selected_item = items[item_id - 1]

        # Find by direct item ID from database
        if not selected_item and item_id:
            selected_item = next((item for item in items if item['id'] == item_id), None)

        # Find by name with fuzzy matching
        if not selected_item and item_name:
            name_lower = item_name.lower().strip()
            for item in items:
                if (name_lower in item['item_name_ar'].lower() or
                        name_lower in item['item_name_en'].lower() or
                        item['item_name_ar'].lower() in name_lower or
                        item['item_name_en'].lower() in name_lower):
                    selected_item = item
                    break

        if selected_item and self.db.validate_step_transition(phone_number, 'waiting_for_quantity'):
            # Store selected item
            self.db.create_or_update_session(phone_number, 'waiting_for_quantity', language,
                                             selected_item=selected_item['id'])

            # Ask for quantity professionally
            if language == 'arabic':
                response_message = f"تم اختيار: {selected_item['item_name_ar']}\n"
                response_message += f"السعر: {selected_item['price']} دينار\n\n"
                response_message += "كم الكمية المطلوبة؟"
            else:
                response_message = f"Selected: {selected_item['item_name_en']}\n"
                response_message += f"Price: {selected_item['price']} IQD\n\n"
                response_message += "How many would you like?"

            return self._create_response(response_message)

        # Item not found, show menu again
        categories = self.db.get_available_categories()
        current_category = next(
            (cat for cat in categories if cat['category_id'] == selected_category_id), None)

        if language == 'arabic':
            response_message = f"المنتج غير محدد. الرجاء اختيار رقم صحيح من قائمة {current_category['category_name_ar'] if current_category else 'الفئة'}:\n\n"
            for i, item in enumerate(items, 1):
                response_message += f"{i}. {item['item_name_ar']} - {item['price']} دينار\n"
        else:
            response_message = f"Item not specified. Please choose a valid number from {current_category['category_name_en'] if current_category else 'category'} menu:\n\n"
            for i, item in enumerate(items, 1):
                response_message += f"{i}. {item['item_name_en']} - {item['price']} IQD\n"

        return self._create_response(response_message)

    def _execute_quantity_selection(self, phone_number: str, extracted_data: Dict, response_message: str,
                                    session: Dict) -> Dict:
        """Execute quantity selection with AI understanding"""
        language = session['language_preference'] if session else 'arabic'
        selected_item_id = session.get('selected_item') if session else None
        quantity = extracted_data.get('quantity')

        if not selected_item_id:
            return self._create_response(
                "خطأ في النظام. الرجاء إعادة البدء\nSystem error. Please restart")

        if quantity and quantity > 0 and self.db.validate_step_transition(phone_number, 'waiting_for_additional'):
            # Add item to order
            success = self.db.add_item_to_order(phone_number, selected_item_id, quantity)

            if success:
                item = self.db.get_item_by_id(selected_item_id)
                self.db.create_or_update_session(phone_number, 'waiting_for_additional', language)

                # Professional additional items question
                if language == 'arabic':
                    response_message = f"تم إضافة {item['item_name_ar']} × {quantity} إلى طلبك\n\n"
                    response_message += "هل تريد إضافة المزيد من الأصناف؟\n\n"
                    response_message += "1. نعم\n"
                    response_message += "2. لا"
                else:
                    response_message = f"Added {item['item_name_en']} × {quantity} to your order\n\n"
                    response_message += "Would you like to add more items?\n\n"
                    response_message += "1. Yes\n"
                    response_message += "2. No"

                return self._create_response(response_message)

        # Invalid quantity
        if language == 'arabic':
            response_message = "الكمية غير صحيحة. الرجاء إدخال رقم صحيح (1، 2، 3...)"
        else:
            response_message = "Invalid quantity. Please enter a valid number (1, 2, 3...)"

        return self._create_response(response_message)

    def _execute_service_selection(self, phone_number: str, extracted_data: Dict, response_message: str,
                                   session: Dict) -> Dict:
        """Execute service type selection with AI understanding"""
        language = session['language_preference'] if session else 'arabic'
        service_type = extracted_data.get('service_type')

        if service_type and self.db.validate_step_transition(phone_number, 'waiting_for_location'):
            # Update service type
            self.db.update_order_details(phone_number, service_type=service_type)
            self.db.create_or_update_session(phone_number, 'waiting_for_location', language)

            # Ask for location details after service selection
            if language == 'arabic':
                if service_type == 'dine-in':
                    response_message = "ممتاز! الرجاء تحديد رقم الطاولة (1-7):"
                else:  # delivery
                    response_message = "ممتاز! الرجاء مشاركة موقعك أو عنوانك:"
            else:
                if service_type == 'dine-in':
                    response_message = "Great! Please specify your table number (1-7):"
                else:  # delivery
                    response_message = "Great! Please share your location or address:"

            return self._create_response(response_message)

        # Service type not clear
        if language == 'arabic':
            response_message = "نوع الخدمة غير محدد. الرجاء الاختيار:\n\n"
            response_message += "1. تناول في المقهى\n"
            response_message += "2. توصيل"
        else:
            response_message = "Service type not specified. Please choose:\n\n"
            response_message += "1. Dine-in\n"
            response_message += "2. Delivery"

        return self._create_response(response_message)

    def _execute_location_input(self, phone_number: str, extracted_data: Dict, response_message: str,
                                session: Dict) -> Dict:
        """Execute location input with AI understanding"""
        language = session['language_preference'] if session else 'arabic'
        location = extracted_data.get('location')

        if location:
            # Store location and move to confirmation
            self.db.update_order_details(phone_number, location=location)

            if self.db.validate_step_transition(phone_number, 'waiting_for_confirmation'):
                self.db.create_or_update_session(phone_number, 'waiting_for_confirmation', language)

                # Get order summary
                order = self.db.get_user_order(phone_number)

                if language == 'arabic':
                    response_message = "إليك ملخص طلبك:\n\n"
                    response_message += "الأصناف:\n"
                    for item in order['items']:
                        response_message += f"• {item['item_name_ar']} × {item['quantity']} - {item['subtotal']} دينار\n"

                    service_type = order['details'].get('service_type', 'غير محدد')
                    service_type_ar = 'تناول في المقهى' if service_type == 'dine-in' else 'توصيل'

                    response_message += f"\nنوع الخدمة: {service_type_ar}\n"
                    response_message += f"المكان: {location}\n"
                    response_message += f"السعر الإجمالي: {order['total']} دينار\n\n"
                    response_message += "هل تريد تأكيد هذا الطلب؟\n\n1. نعم\n2. لا"
                else:
                    response_message = "Here is your order summary:\n\n"
                    response_message += "Items:\n"
                    for item in order['items']:
                        response_message += f"• {item['item_name_en']} × {item['quantity']} - {item['subtotal']} IQD\n"

                    response_message += f"\nService: {order['details'].get('service_type', 'Not specified')}\n"
                    response_message += f"Location: {location}\n"
                    response_message += f"Total Price: {order['total']} IQD\n\n"
                    response_message += "Would you like to confirm this order?\n\n1. Yes\n2. No"

                return self._create_response(response_message)

        # Location not clear
        if language == 'arabic':
            response_message = "الرجاء تحديد المكان بوضوح (رقم الطاولة أو العنوان)"
        else:
            response_message = "Please specify the location clearly (table number or address)"

        return self._create_response(response_message)

    def _execute_confirmation(self, phone_number: str, extracted_data: Dict, response_message: str,
                              session: Dict) -> Dict:
        """Execute order confirmation"""
        # This is handled by yes_no_action, so just return the AI response
        return self._create_response(response_message or "تأكد الطلب؟\nConfirm the order?")

    def _execute_help_request(self, phone_number: str, current_step: str, response_message: str,
                              session: Dict) -> Dict:
        """Handle help requests based on current step"""
        language = session['language_preference'] if session else 'arabic'

        if current_step == 'waiting_for_category':
            if language == 'arabic':
                response_message = "المساعدة - اختيار الفئة:\n\n"
                response_message += "• اختر رقم الفئة من القائمة (1، 2، 3...)\n"
                response_message += "• أو اكتب اسم الفئة\n"
                response_message += "• اكتب 'منيو' لرؤية القائمة الكاملة"
            else:
                response_message = "Help - Category selection:\n\n"
                response_message += "• Choose category number from menu (1, 2, 3...)\n"
                response_message += "• Or type the category name\n"
                response_message += "• Type 'menu' to see the full menu"

        elif current_step == 'waiting_for_item':
            if language == 'arabic':
                response_message = "المساعدة - اختيار المنتج:\n\n"
                response_message += "• اختر رقم المنتج من القائمة أعلاه\n"
                response_message += "• أو اكتب اسم المنتج بدقة\n"
                response_message += "• اكتب 'القائمة' لإعادة عرض المنتجات"
            else:
                response_message = "Help - Item selection:\n\n"
                response_message += "• Choose item number from menu above\n"
                response_message += "• Or type the item name accurately\n"
                response_message += "• Type 'menu' to show items again"

        elif current_step == 'waiting_for_quantity':
            if language == 'arabic':
                response_message = "المساعدة - الكمية:\n\n"
                response_message += "• اكتب رقم الكمية المطلوبة (1، 2، 3...)\n"
                response_message += "• يمكنك كتابة الرقم بالعربية أو الإنجليزية"
            else:
                response_message = "Help - Quantity:\n\n"
                response_message += "• Type the quantity number you want (1, 2, 3...)\n"
                response_message += "• You can write the number in Arabic or English"

        else:
            if language == 'arabic':
                response_message = "مرحباً! أنا هنا لمساعدتك في الطلب من مقهى هيف.\n\n"
                response_message += "يمكنك:\n"
                response_message += "• كتابة 'منيو' لرؤية القائمة\n"
                response_message += "• كتابة 'طلب جديد' للبدء من جديد\n"
                response_message += "• اتباع التعليمات المعروضة"
            else:
                response_message = "Hello! I'm here to help you order from Hef Cafe.\n\n"
                response_message += "You can:\n"
                response_message += "• Type 'menu' to see the menu\n"
                response_message += "• Type 'new order' to start fresh\n"
                response_message += "• Follow the displayed instructions"

        return self._create_response(response_message)

    def _create_response(self, content: str) -> Dict[str, Any]:
        """Create standardized response format"""
        # Ensure message doesn't exceed WhatsApp limits
        if len(content) > 4000:
            content = content[:3900] + "... (تم اختصار الرسالة)"

        return {
            'type': 'text',
            'content': content,
            'timestamp': datetime.now().isoformat()
        }


# ai/prompts.py - Updated prompts for better understanding

class AIPrompts:
    # ... existing code ...

    @staticmethod
    def get_understanding_prompt(user_message: str, current_step: str, context: dict) -> str:
        """Generate AI understanding prompt with context - ENHANCED VERSION"""
        return f"""
CURRENT SITUATION:
- User is at step: {current_step} ({context.get('step_description', 'Unknown step')})
- User said: "{user_message}"

CONTEXT:
{AIPrompts._format_context(context)}

SPECIAL RULES:
1. If user says greetings like "مرحبا" and they're NOT at language step, they might want to start fresh
2. If user says "طلب جديد" or "new order" at ANY step, treat as language_selection action
3. If user says "لا طلب جديد" it means "No, I want a NEW order" - treat as language_selection
4. When user says "نعم" to add more items, ALWAYS show the menu categories
5. When showing menu, ALWAYS provide the actual list, not just a promise to show it
6. Convert Arabic numerals automatically: ١=1, ٢=2, ٣=3, ٤=4, ٥=5, ٦=6, ٧=7, ٨=8, ٩=9

CRITICAL ACTIONS:
- Use "language_selection" for fresh starts, new order requests, or greetings when not at language step
- Use "show_menu" when user asks for منيو, قائمة, menu
- Use "category_selection" when user selects a category 
- Use "yes_no" for نعم/لا responses
- ALWAYS include actual menu content in response_message when promising to show menu

RESPOND WITH JSON:
{{
    "understood_intent": "clear description of what user wants",
    "confidence": "high/medium/low",
    "action": "language_selection/category_selection/item_selection/quantity_selection/yes_no/service_selection/location_input/confirmation/show_menu/help_request/stay_current_step",
    "extracted_data": {{
        "language": "arabic/english/null",
        "category_id": "number or null",
        "category_name": "string or null",
        "item_id": "number or null",
        "item_name": "string or null",
        "quantity": "number or null",
        "yes_no": "yes/no/null",
        "service_type": "dine-in/delivery/null",
        "location": "string or null"
    }},
    "clarification_needed": "true/false",
    "clarification_question": "question to ask if clarification needed",
    "response_message": "natural response to user in their preferred language WITH ACTUAL MENU CONTENT if showing menu"
}}

EXAMPLES:
- "مرحبا" at waiting_for_additional → language_selection (user wants fresh start)
- "لا طلب جديد" → language_selection action (user wants NEW order)
- "نعم" at waiting_for_additional → yes_no with yes, and response_message should include full category menu
- "منيو" → show_menu with actual categories listed in response_message
- "6" or "٦" → category_selection with category_id: 6
"""