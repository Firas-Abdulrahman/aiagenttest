import logging
from typing import Dict, Any, Optional
from datetime import datetime

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

            # Get current session state
            session = self.db.get_user_session(phone_number)
            current_step = session['current_step'] if session else 'waiting_for_language'

            logger.info(f"📊 User {phone_number} at step: {current_step}")

            # Process message with AI or fallback
            response = self._process_message(phone_number, current_step, text, customer_name, session)

            # Log AI response
            self.db.log_conversation(phone_number, 'ai_response', response['content'])

            return response

        except Exception as e:
            logger.error(f"❌ Error handling message: {str(e)}")
            return self._create_error_response("حدث خطأ. الرجاء إعادة المحاولة\nAn error occurred. Please try again")

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


class SpecializedHandlers:
    """Specialized handlers for specific message types"""

    def __init__(self, database_manager):
        self.db = database_manager

    def handle_location_message(self, message_data: Dict) -> Optional[str]:
        """Handle location messages"""
        if 'location' in message_data:
            location = message_data['location']
            latitude = location.get('latitude')
            longitude = location.get('longitude')

            if latitude and longitude:
                return f"Location: {latitude}, {longitude}"

        return None

    def handle_image_message(self, message_data: Dict) -> Optional[str]:
        """Handle image messages"""
        if 'image' in message_data:
            image = message_data['image']
            caption = image.get('caption', '')

            # For now, just acknowledge the image
            return f"Image received{': ' + caption if caption else ''}"

        return None

    def handle_audio_message(self, message_data: Dict) -> Optional[str]:
        """Handle audio messages"""
        if 'audio' in message_data:
            # For now, just acknowledge the audio
            return "Audio message received. Please send text messages for ordering."

        return None

    def handle_document_message(self, message_data: Dict) -> Optional[str]:
        """Handle document messages"""
        if 'document' in message_data:
            document = message_data['document']
            filename = document.get('filename', 'document')

            return f"Document '{filename}' received. Please send text messages for ordering."

        return None


class MessageValidator:
    """Message validation utilities"""

    @staticmethod
    def is_valid_phone_number(phone_number: str) -> bool:
        """Validate phone number format"""
        if not phone_number:
            return False

        # Remove common prefixes and check length
        cleaned = phone_number.replace('+', '').replace('-', '').replace(' ', '')
        return len(cleaned) >= 10 and cleaned.isdigit()

    @staticmethod
    def is_spam_message(content: str) -> bool:
        """Simple spam detection"""
        spam_indicators = [
            'http://', 'https://', 'www.',
            'buy now', 'click here', 'limited time',
            'free money', 'guarantee', 'win', 'prize'
        ]

        content_lower = content.lower()
        return any(indicator in content_lower for indicator in spam_indicators)

    @staticmethod
    def sanitize_input(text: str) -> str:
        """Sanitize user input"""
        if not text:
            return ""

        # Remove excessive whitespace
        text = ' '.join(text.split())

        # Limit length
        if len(text) > 1000:
            text = text[:1000]

        return text.strip()