import json
import logging
from typing import Dict, Optional, Any
from .prompts import AIPrompts

logger = logging.getLogger(__name__)

# Try to import OpenAI
try:
    import openai

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI not installed. AI features will be disabled.")


class AIProcessor:
    """AI Processing and Understanding Engine"""

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

    def extract_language_preference(self, user_message: str) -> Optional[str]:
        """Extract language preference from user message"""
        message_lower = user_message.lower().strip()

        # Arabic language indicators
        arabic_indicators = [
            'عربي', 'العربية', 'مرحبا', 'أهلا', 'اريد', 'بدي',
            'شو', 'ايش', 'كيف', 'وين', '1', '١'
        ]

        # English language indicators
        english_indicators = [
            'english', 'hello', 'hi', 'hey', 'want', 'need',
            'order', 'menu', 'what', 'how', '2', '٢'
        ]

        # Check for Arabic
        if any(indicator in message_lower for indicator in arabic_indicators):
            return 'arabic'

        # Check for English
        if any(indicator in message_lower for indicator in english_indicators):
            return 'english'

        return None

    def extract_number_from_text(self, text: str) -> Optional[int]:
        """Extract number from text, handling Arabic and English numerals"""
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

        # Check for word numbers
        word_numbers = {
            'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
            'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
            'واحد': 1, 'اثنين': 2, 'ثلاثة': 3, 'اربعة': 4, 'خمسة': 5,
            'ستة': 6, 'سبعة': 7, 'ثمانية': 8, 'تسعة': 9, 'عشرة': 10,
            'first': 1, 'second': 2, 'third': 3, 'fourth': 4, 'fifth': 5
        }

        text_lower = text.lower()
        for word, number in word_numbers.items():
            if word in text_lower:
                return number

        return None

    def detect_yes_no(self, text: str, language: str = 'arabic') -> Optional[str]:
        """Detect yes/no intent from text"""
        text_lower = text.lower().strip()

        if language == 'arabic':
            yes_indicators = ['نعم', 'ايوه', 'اه', 'صح', 'تمام', 'موافق', 'اكيد', 'yes', '1', '١']
            no_indicators = ['لا', 'كلا', 'مش', 'مو', 'لأ', 'رفض', 'no', '2', '٢']
        else:
            yes_indicators = ['yes', 'yeah', 'yep', 'sure', 'ok', 'okay', 'confirm', '1']
            no_indicators = ['no', 'nope', 'cancel', 'stop', 'abort', '2']

        if any(indicator in text_lower for indicator in yes_indicators):
            return 'yes'

        if any(indicator in text_lower for indicator in no_indicators):
            return 'no'

        return None

    def detect_service_type(self, text: str, language: str = 'arabic') -> Optional[str]:
        """Detect service type (dine-in or delivery) from text"""
        text_lower = text.lower().strip()

        if language == 'arabic':
            dine_in_indicators = [
                'مقهى', 'داخل', 'هنا', 'جوا', 'في المكان', 'في الكافيه',
                'طاولة', 'جلسة', '1', '١'
            ]
            delivery_indicators = [
                'توصيل', 'بيت', 'منزل', 'خارج', 'ديليفري', 'عنوان',
                'موقع', 'مكان', '2', '٢'
            ]
        else:
            dine_in_indicators = [
                'dine', 'in', 'here', 'cafe', 'restaurant', 'table',
                'inside', 'sit', '1'
            ]
            delivery_indicators = [
                'delivery', 'home', 'address', 'location', 'deliver',
                'outside', 'takeaway', '2'
            ]

        if any(indicator in text_lower for indicator in dine_in_indicators):
            return 'dine-in'

        if any(indicator in text_lower for indicator in delivery_indicators):
            return 'delivery'

        return None

    def fuzzy_match_category(self, text: str, categories: list, language: str = 'arabic') -> Optional[Dict]:
        """Fuzzy match text to menu category"""
        text_lower = text.lower().strip()

        # Direct number match
        number = self.extract_number_from_text(text)
        if number and 1 <= number <= len(categories):
            return categories[number - 1]

        # Name matching
        for category in categories:
            category_name_ar = category['category_name_ar'].lower()
            category_name_en = category['category_name_en'].lower()

            # Exact match
            if text_lower == category_name_ar or text_lower == category_name_en:
                return category

            # Partial match
            if (text_lower in category_name_ar or category_name_ar in text_lower or
                    text_lower in category_name_en or category_name_en in text_lower):
                return category

        # Keyword matching for common terms
        keyword_mapping = {
            'arabic': {
                'حار': 1, 'ساخن': 1, 'قهوة': 1, 'شاي': 1,
                'بارد': 2, 'مثلج': 2, 'ايس': 2,
                'حلو': 3, 'كيك': 3, 'حلويات': 3,
                'عصير': 6, 'فريش': 6,
                'توست': 9, 'خبز': 9,
                'سندويش': 10,
                'كرواسان': 12,
                'فطيرة': 13, 'مالح': 13
            },
            'english': {
                'hot': 1, 'warm': 1, 'coffee': 1, 'tea': 1,
                'cold': 2, 'iced': 2, 'ice': 2,
                'sweet': 3, 'cake': 3, 'dessert': 3,
                'juice': 6, 'fresh': 6,
                'toast': 9, 'bread': 9,
                'sandwich': 10,
                'croissant': 12,
                'pie': 13, 'savory': 13
            }
        }

        keywords = keyword_mapping.get(language, keyword_mapping['arabic'])
        for keyword, category_id in keywords.items():
            if keyword in text_lower:
                return next((cat for cat in categories if cat['category_id'] == category_id), None)

        return None

    def fuzzy_match_item(self, text: str, items: list, language: str = 'arabic') -> Optional[Dict]:
        """Fuzzy match text to menu item"""
        text_lower = text.lower().strip()

        # Direct number match
        number = self.extract_number_from_text(text)
        if number and 1 <= number <= len(items):
            return items[number - 1]

        # Name matching
        best_match = None
        best_score = 0

        for item in items:
            item_name_ar = item['item_name_ar'].lower()
            item_name_en = item['item_name_en'].lower()

            # Exact match
            if text_lower == item_name_ar or text_lower == item_name_en:
                return item

            # Calculate similarity score
            score = 0
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

    def generate_fallback_response(self, current_step: str, language: str = 'arabic') -> str:
        """Generate fallback response when AI is not available"""
        templates = AIPrompts.get_response_templates(language)

        step_mapping = {
            'waiting_for_language': templates['welcome'],
            'waiting_for_category': templates['categories'],
            'waiting_for_item': templates['items'],
            'waiting_for_quantity': templates['quantity'],
            'waiting_for_additional': templates['additional'],
            'waiting_for_service': templates['service'],
            'waiting_for_location': templates['location_dine'],
            'waiting_for_confirmation': templates['confirmation']
        }

        return step_mapping.get(current_step, templates['error'])

    def build_context(self, session: Dict, current_step: str, database_manager) -> Dict:
        """Build conversation context for AI understanding"""
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
            context['available_categories'] = database_manager.get_available_categories()

        # Add items if in item selection
        if current_step == 'waiting_for_item' and session and session.get('selected_category'):
            context['current_category_items'] = database_manager.get_category_items(session['selected_category'])

        # Add current order if exists
        if session:
            phone_number = session.get('phone_number')
            if phone_number:
                context['current_order'] = database_manager.get_user_order(phone_number)

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

    def validate_extracted_data(self, extracted_data: Dict, current_step: str) -> bool:
        """Validate extracted data based on current step"""
        if not extracted_data:
            return False

        validation_rules = {
            'waiting_for_language': lambda d: d.get('language') in ['arabic', 'english'],
            'waiting_for_category': lambda d: d.get('category_id') or d.get('category_name'),
            'waiting_for_item': lambda d: d.get('item_id') or d.get('item_name'),
            'waiting_for_quantity': lambda d: isinstance(d.get('quantity'), int) and d.get('quantity') > 0,
            'waiting_for_additional': lambda d: d.get('yes_no') in ['yes', 'no'],
            'waiting_for_service': lambda d: d.get('service_type') in ['dine-in', 'delivery'],
            'waiting_for_location': lambda d: bool(d.get('location')),
            'waiting_for_confirmation': lambda d: d.get('yes_no') in ['yes', 'no']
        }

        validator = validation_rules.get(current_step)
        if validator:
            return validator(extracted_data)

        return True  # Default to valid for unknown steps