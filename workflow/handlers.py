# workflow/handlers.py - CRITICAL FIXES

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from ai.prompts import AIPrompts

logger = logging.getLogger(__name__)


class MessageHandler:
    """Main message handler for WhatsApp workflow - FIXED VERSION"""

    def __init__(self, database_manager, ai_processor, action_executor):
        self.db = database_manager
        self.ai = ai_processor
        self.executor = action_executor

    def handle_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Main message handling entry point - FIXED"""
        try:
            # Validate message format
            if not self._validate_message(message_data):
                return self._create_error_response("Invalid message format")

            # Extract message details
            text = message_data.get('text', {}).get('body', '').strip()
            phone_number = message_data.get('from')
            customer_name = self._extract_customer_name(message_data)

            logger.info(f"📨 Processing message '{text}' from {phone_number}")

            # Log incoming message
            self.db.log_conversation(phone_number, 'user_message', text)

            # Get current session state
            session = self.db.get_user_session(phone_number)

            # CRITICAL FIX: More conservative session reset logic
            should_reset = self._should_reset_session_conservative(session, text)

            if should_reset:
                logger.info(f"🔄 Resetting session for {phone_number} - Reason: {should_reset}")
                self.db.delete_session(phone_number)
                session = None

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

    def _should_reset_session_conservative(self, session: Dict, user_message: str) -> str:
        """More conservative session reset logic - FIXED"""
        if not session:
            return None  # No session to reset

        # Check session timeout (30 minutes)
        last_update = session.get('updated_at')
        if last_update:
            try:
                last_update_time = datetime.fromisoformat(last_update.replace('Z', '+00:00'))
                time_diff = datetime.now() - last_update_time
                if time_diff.total_seconds() > 1800:  # 30 minutes
                    return "Session timeout"
            except Exception as e:
                logger.warning(f"⚠️ Error parsing session time: {e}")
                return "Invalid session time"

        # ONLY reset for explicit new order commands
        user_lower = user_message.lower().strip()
        explicit_reset_commands = [
            'طلب جديد', 'طلبية جديدة', 'ابدأ من جديد', 'من البداية',
            'new order', 'start over', 'restart', 'fresh order'
        ]

        if any(cmd in user_lower for cmd in explicit_reset_commands):
            return "Explicit new order command"

        # DON'T reset for simple greetings unless at waiting_for_language
        current_step = session.get('current_step', 'waiting_for_language')
        if current_step == 'waiting_for_language':
            return None  # Stay at language selection

        return None  # Don't reset

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
        """Fallback processing when AI is unavailable - IMPROVED"""
        logger.info("🔄 Using fallback processing")

        # Convert Arabic numerals to English
        user_message = self._convert_arabic_numerals(user_message)

        # Simple language detection for initial step
        if current_step == 'waiting_for_language':
            language = self._detect_language_simple(user_message)
            if language:
                if self.db.validate_step_transition(phone_number, 'waiting_for_category'):
                    self.db.create_or_update_session(phone_number, 'waiting_for_category', language, customer_name)

                    # Show categories
                    categories = self.db.get_available_categories()
                    if language == 'arabic':
                        response = f"أهلاً وسهلاً {customer_name} في مقهى هيف!\n\n"
                        response += "القائمة الرئيسية:\n\n"
                        for i, cat in enumerate(categories, 1):
                            response += f"{i}. {cat['category_name_ar']}\n"
                        response += "\nالرجاء اختيار الفئة المطلوبة بالرد بالرقم"
                    else:
                        response = f"Welcome {customer_name} to Hef Cafe!\n\n"
                        response += "Main Menu:\n\n"
                        for i, cat in enumerate(categories, 1):
                            response += f"{i}. {cat['category_name_en']}\n"
                        response += "\nPlease select the required category by replying with the number"

                    return self._create_response(response)

        # Simple number extraction for category selection
        elif current_step == 'waiting_for_category':
            number = self._extract_number_simple(user_message)
            categories = self.db.get_available_categories()

            if number and 1 <= number <= len(categories):
                selected_category = categories[number - 1]
                language = session.get('language_preference', 'arabic')

                if self.db.validate_step_transition(phone_number, 'waiting_for_item'):
                    self.db.create_or_update_session(phone_number, 'waiting_for_item', language,
                                                     selected_category=selected_category['category_id'])

                    # Show items for selected category
                    items = self.db.get_category_items(selected_category['category_id'])
                    if language == 'arabic':
                        response = f"قائمة {selected_category['category_name_ar']}:\n\n"
                        for i, item in enumerate(items, 1):
                            response += f"{i}. {item['item_name_ar']}\n"
                            response += f"   السعر: {item['price']} دينار\n\n"
                        response += "الرجاء اختيار المنتج المطلوب"
                    else:
                        response = f"{selected_category['category_name_en']} Menu:\n\n"
                        for i, item in enumerate(items, 1):
                            response += f"{i}. {item['item_name_en']}\n"
                            response += f"   Price: {item['price']} IQD\n\n"
                        response += "Please select the required item"

                    return self._create_response(response)
            else:
                # Invalid category number - show categories again
                language = session.get('language_preference', 'arabic')
                if language == 'arabic':
                    response = "الرقم غير صحيح. الرجاء اختيار رقم من 1 إلى 13:\n\n"
                    for i, cat in enumerate(categories, 1):
                        response += f"{i}. {cat['category_name_ar']}\n"
                else:
                    response = "Invalid number. Please choose a number from 1 to 13:\n\n"
                    for i, cat in enumerate(categories, 1):
                        response += f"{i}. {cat['category_name_en']}\n"
                return self._create_response(response)

        # Simple item selection
        elif current_step == 'waiting_for_item':
            language = session.get('language_preference', 'arabic')
            selected_category_id = session.get('selected_category')

            if selected_category_id:
                items = self.db.get_category_items(selected_category_id)
                number = self._extract_number_simple(user_message)

                if number and 1 <= number <= len(items):
                    selected_item = items[number - 1]

                    if self.db.validate_step_transition(phone_number, 'waiting_for_quantity'):
                        self.db.create_or_update_session(phone_number, 'waiting_for_quantity', language,
                                                         selected_item=selected_item['id'])

                        if language == 'arabic':
                            response = f"تم اختيار: {selected_item['item_name_ar']}\n"
                            response += f"السعر: {selected_item['price']} دينار\n\n"
                            response += "كم الكمية المطلوبة؟"
                        else:
                            response = f"Selected: {selected_item['item_name_en']}\n"
                            response += f"Price: {selected_item['price']} IQD\n\n"
                            response += "How many would you like?"

                        return self._create_response(response)
                else:
                    # Show items again for invalid selection
                    categories = self.db.get_available_categories()
                    current_category = next((cat for cat in categories if cat['category_id'] == selected_category_id),
                                            None)

                    if language == 'arabic':
                        response = f"الرقم غير صحيح. الرجاء اختيار رقم من قائمة {current_category['category_name_ar'] if current_category else 'الفئة'}:\n\n"
                        for i, item in enumerate(items, 1):
                            response += f"{i}. {item['item_name_ar']} - {item['price']} دينار\n"
                    else:
                        response = f"Invalid number. Please choose from {current_category['category_name_en'] if current_category else 'category'} menu:\n\n"
                        for i, item in enumerate(items, 1):
                            response += f"{i}. {item['item_name_en']} - {item['price']} IQD\n"

                    return self._create_response(response)

        # Generic fallback response
        language = session.get('language_preference', 'arabic') if session else 'arabic'
        fallback_response = self.ai.generate_fallback_response(current_step, language)
        return self._create_response(fallback_response)

    def _convert_arabic_numerals(self, text: str) -> str:
        """Convert Arabic numerals to English numerals"""
        arabic_to_english = {
            '٠': '0', '١': '1', '٢': '2', '٣': '3', '٤': '4',
            '٥': '5', '٦': '6', '٧': '7', '٨': '8', '٩': '9'
        }

        for arabic, english in arabic_to_english.items():
            text = text.replace(arabic, english)

        return text

    def _extract_number_simple(self, text: str) -> Optional[int]:
        """Extract number from text simply"""
        import re

        # Convert Arabic numerals first
        text = self._convert_arabic_numerals(text)

        # Extract first number found
        numbers = re.findall(r'\d+', text)
        if numbers:
            return int(numbers[0])

        return None

    def _detect_language_simple(self, text: str) -> Optional[str]:
        """Simple language detection"""
        text_lower = text.lower().strip()

        # Arabic indicators
        arabic_indicators = ['عربي', 'العربية', '1', '١']

        # English indicators
        english_indicators = ['english', 'انجليزي', '2', '٢']

        if any(indicator in text_lower for indicator in arabic_indicators):
            return 'arabic'
        elif any(indicator in text_lower for indicator in english_indicators):
            return 'english'

        return None

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


# ai/processor.py - Enhanced AI processor with better Arabic numeral handling

import json
import logging
from typing import Dict, Optional, Any
from ai.prompts import AIPrompts

logger = logging.getLogger(__name__)

# Try to import OpenAI
try:
    import openai

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI not installed. AI features will be disabled.")


class AIProcessor:
    """AI Processing and Understanding Engine - ENHANCED"""

    def __init__(self, api_key: str = None):
        self.api_key = api_key
        self.client = None

        if OPENAI_AVAILABLE and api_key:
            try:
                self.client = openai.OpenAI(api_key=api_key)
                logger.info("✅ OpenAI client initialized")
            except Exception as e:
                logger.error(f"⚠️ OpenAI initialization failed: {e}")
                self.client = None
        else:
            logger.warning("⚠️ Running without OpenAI - AI features limited")

    def is_available(self) -> bool:
        """Check if AI processing is available"""
        return self.client is not None

    def extract_number_from_text(self, text: str) -> Optional[int]:
        """Extract number from text, handling Arabic and English numerals - ENHANCED"""
        import re

        # Arabic to English numeral mapping
        arabic_to_english = {
            '٠': '0', '١': '1', '٢': '2', '٣': '3', '٤': '4',
            '٥': '5', '٦': '6', '٧': '7', '٨': '8', '٩': '9'
        }

        # Replace Arabic numerals with English ones
        converted_text = text
        for arabic, english in arabic_to_english.items():
            converted_text = converted_text.replace(arabic, english)

        # Extract numbers
        numbers = re.findall(r'\d+', converted_text)

        if numbers:
            return int(numbers[0])

        # Check for word numbers (Arabic and English)
        word_numbers = {
            # English
            'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
            'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
            'first': 1, 'second': 2, 'third': 3, 'fourth': 4, 'fifth': 5,
            # Arabic
            'واحد': 1, 'اثنين': 2, 'ثلاثة': 3, 'اربعة': 4, 'خمسة': 5,
            'ستة': 6, 'سبعة': 7, 'ثمانية': 8, 'تسعة': 9, 'عشرة': 10,
            'الأول': 1, 'الثاني': 2, 'الثالث': 3, 'الرابع': 4, 'الخامس': 5,
        }

        text_lower = text.lower()
        for word, number in word_numbers.items():
            if word in text_lower:
                return number

        return None

    def fuzzy_match_item(self, text: str, items: list, language: str = 'arabic') -> Optional[Dict]:
        """Fuzzy match text to menu item - ENHANCED"""
        text_lower = text.lower().strip()

        # Direct number match
        number = self.extract_number_from_text(text)
        if number and 1 <= number <= len(items):
            return items[number - 1]

        # Enhanced name matching for Mojito case
        best_match = None
        best_score = 0

        for item in items:
            item_name_ar = item['item_name_ar'].lower()
            item_name_en = item['item_name_en'].lower()

            # Exact match
            if text_lower == item_name_ar or text_lower == item_name_en:
                return item

            # Special handling for common items
            score = 0

            # Mojito matching
            if 'موهيتو' in text_lower or 'mojito' in text_lower:
                if 'موهيتو' in item_name_ar or 'mojito' in item_name_en:
                    return item

            # Partial matching
            if text_lower in item_name_ar or item_name_ar in text_lower:
                score += 3
            if text_lower in item_name_en or item_name_en in text_lower:
                score += 3

            # Word-level matching
            text_words = text_lower.split()
            ar_words = item_name_ar.split()
            en_words = item_name_en.split()

            for word in text_words:
                if word in ar_words or word in en_words:
                    score += 1

            if score > best_score:
                best_score = score
                best_match = item

        # Return match if score is high enough
        if best_score >= 2:
            return best_match

        return None

    # Keep all other existing methods...
    def understand_message(self, user_message: str, current_step: str, context: Dict) -> Optional[Dict]:
        """Process user message and return AI understanding"""
        if not self.client:
            logger.warning("AI client not available")
            return None

        try:
            # Build AI prompt with rich context
            prompt = AIPrompts.get_understanding_prompt(user_message, current_step, context)

            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": AIPrompts.SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800,
                temperature=0.3,  # Lower temperature for consistent parsing
            )

            ai_response = response.choices[0].message.content.strip()

            # Parse JSON response
            result = self._parse_ai_response(ai_response)

            if result:
                logger.info(f"✅ AI Understanding: {result['understood_intent']} (confidence: {result['confidence']})")
                return result
            else:
                logger.error("❌ Failed to parse AI response")
                return None

        except Exception as e:
            logger.error(f"❌ AI understanding error: {str(e)}")
            return None

    def _parse_ai_response(self, ai_response: str) -> Optional[Dict]:
        """Parse AI JSON response safely"""
        try:
            # Clean the response if it has markdown formatting
            if ai_response.startswith('```json'):
                ai_response = ai_response.replace('```json', '').replace('```', '').strip()

            result = json.loads(ai_response)

            # Validate required fields
            required_fields = ['understood_intent', 'confidence', 'action', 'extracted_data']
            for field in required_fields:
                if field not in result:
                    logger.error(f"Missing required field: {field}")
                    return None

            return result

        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON parsing error: {e}")
            logger.error(f"AI Response was: {ai_response}")
            return None

    # Keep all other existing methods unchanged...