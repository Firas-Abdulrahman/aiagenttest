# ai/processor.py - ENHANCED with better understanding and integration

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
    """Enhanced AI Processing and Understanding Engine"""

    def __init__(self, api_key: str = None):
        self.api_key = api_key
        self.client = None

        if OPENAI_AVAILABLE and api_key:
            try:
                self.client = openai.OpenAI(api_key=api_key)
                logger.info("✅ Enhanced OpenAI client initialized")
            except Exception as e:
                logger.error(f"⚠️ OpenAI initialization failed: {e}")
                self.client = None
        else:
            logger.warning("⚠️ Running without OpenAI - AI features limited")

    def is_available(self) -> bool:
        """Check if AI processing is available"""
        if not self.client:
            return False
        
        # Additional check for quota/rate limit issues
        try:
            # Simple test call to check if API is working
            test_response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5,
                temperature=0
            )
            return True
        except Exception as e:
            error_msg = str(e)
            if "quota" in error_msg.lower() or "insufficient_quota" in error_msg.lower() or "429" in error_msg:
                logger.warning("⚠️ OpenAI quota exceeded, AI unavailable")
                return False
            elif "rate limit" in error_msg.lower():
                logger.warning("⚠️ OpenAI rate limit hit, AI unavailable")
                return False
            else:
                logger.warning(f"⚠️ OpenAI API error: {error_msg}")
                return False

    def understand_message(self, user_message: str, current_step: str, context: Dict) -> Optional[Dict]:
        """Enhanced message understanding with better context processing"""
        if not self.client:
            logger.warning("AI client not available")
            return None

        try:
            # Pre-process message for better understanding
            user_message = self._preprocess_message(user_message)

            # Build enhanced prompt with better context
            prompt = AIPrompts.get_understanding_prompt(user_message, current_step, context)

            logger.info(f"🤖 AI analyzing: '{user_message}' at step '{current_step}'")

            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": AIPrompts.SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800,
                temperature=0.1,  # Lower temperature for more consistent parsing
            )

            ai_response = response.choices[0].message.content.strip()

            # Parse and validate JSON response
            result = self._parse_and_validate_ai_response(ai_response, current_step, user_message)

            if result:
                logger.info(f"✅ AI Understanding: {result['understood_intent']} (confidence: {result['confidence']})")
                logger.info(f"🎯 Action: {result['action']}")
                return result
            else:
                logger.error("❌ Failed to parse or validate AI response")
                return None

        except Exception as e:
            error_msg = str(e)
            if "quota" in error_msg.lower() or "insufficient_quota" in error_msg.lower() or "429" in error_msg:
                logger.warning("⚠️ OpenAI quota exceeded, falling back to enhanced processing")
                return None
            elif "rate limit" in error_msg.lower():
                logger.warning("⚠️ OpenAI rate limit hit, falling back to enhanced processing")
                return None
            else:
                logger.error(f"❌ AI understanding error: {error_msg}")
                return None

    def _preprocess_message(self, message: str) -> str:
        """Preprocess message for better AI understanding"""
        if not message:
            return ""

        # Convert Arabic numerals to English for consistent processing
        arabic_to_english = {
            '٠': '0', '١': '1', '٢': '2', '٣': '3', '٤': '4',
            '٥': '5', '٦': '6', '٧': '7', '٨': '8', '٩': '9'
        }

        processed_message = message
        for arabic, english in arabic_to_english.items():
            processed_message = processed_message.replace(arabic, english)

        # Clean whitespace
        processed_message = ' '.join(processed_message.split())

        return processed_message.strip()

    def _parse_and_validate_ai_response(self, ai_response: str, current_step: str, user_message: str) -> Optional[Dict]:
        """Parse and validate AI JSON response with enhanced validation"""
        try:
            # Clean the response if it has markdown formatting or prefixes
            if ai_response.startswith('```json'):
                ai_response = ai_response.replace('```json', '').replace('```', '').strip()
            
            # Remove common prefixes that might cause JSON parsing issues
            prefixes_to_remove = ['RESPOND WITH JSON:', 'JSON:', 'RESPONSE:']
            for prefix in prefixes_to_remove:
                if ai_response.startswith(prefix):
                    ai_response = ai_response[len(prefix):].strip()

            # Try to find JSON object in the response if it's not a clean JSON
            if not ai_response.strip().startswith('{'):
                import re
                json_pattern = r'\{[\s\S]*\}'
                json_match = re.search(json_pattern, ai_response)
                if json_match:
                    ai_response = json_match.group(0)
                    logger.info("Extracted JSON object from response")
            
            # Log the cleaned response for debugging
            logger.debug(f"Cleaned AI response for parsing: {ai_response}")
            
            result = json.loads(ai_response)

            # Validate required fields
            required_fields = ['understood_intent', 'confidence', 'action', 'extracted_data']
            for field in required_fields:
                if field not in result:
                    logger.error(f"Missing required field: {field}")
                    return None

            # Enhanced validation based on current step
            if not self._validate_result_for_step(result, current_step, user_message):
                return None

            return self._validate_and_postprocess_result(result, current_step, user_message)

        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON parsing error: {e}")
            logger.error(f"AI Response was: {ai_response}")
            
            # Additional debugging information
            logger.error(f"Response type: {type(ai_response)}")
            logger.error(f"Response length: {len(ai_response)}")
            
            # Try to salvage the response if possible
            try:
                # Sometimes the response might have extra characters at the beginning or end
                # Try to find a valid JSON object within the response
                import re
                json_pattern = r'\{[\s\S]*?\}'
                matches = re.findall(json_pattern, ai_response)
                
                if matches:
                    for potential_json in matches:
                        try:
                            result = json.loads(potential_json)
                            logger.info(f"✅ Successfully salvaged JSON from response")
                            return self._validate_and_postprocess_result(result, current_step, user_message)
                        except:
                            continue
            except Exception as salvage_error:
                logger.error(f"Failed to salvage JSON: {salvage_error}")
            
            return None

    def _validate_and_postprocess_result(self, result: Dict, current_step: str, user_message: str) -> Optional[Dict]:
        """Validate and post-process the parsed result"""
        # Validate required fields
        required_fields = ['understood_intent', 'confidence', 'action', 'extracted_data']
        for field in required_fields:
            if field not in result:
                logger.error(f"Missing required field: {field}")
                return None

        # Enhanced validation based on current step
        if not self._validate_result_for_step(result, current_step, user_message):
            return None

        # Post-process extracted data
        result['extracted_data'] = self._postprocess_extracted_data(result['extracted_data'], current_step)

        return result

    def _validate_result_for_step(self, result: Dict, current_step: str, user_message: str) -> bool:
        """Enhanced validation for AI results based on current step"""
        action = result.get('action')
        extracted_data = result.get('extracted_data', {})
        confidence = result.get('confidence', 'low')

        # Step-specific validation
        step_validations = {
            'waiting_for_language': self._validate_language_step,
            'waiting_for_category': self._validate_category_step,
            'waiting_for_item': self._validate_item_step,
            'waiting_for_quantity': self._validate_quantity_step,
            'waiting_for_additional': self._validate_additional_step,
            'waiting_for_service': self._validate_service_step,
            'waiting_for_location': self._validate_location_step,
            'waiting_for_confirmation': self._validate_confirmation_step
        }

        validator = step_validations.get(current_step)
        if validator:
            return validator(result, extracted_data, user_message)

        return True

    def _validate_language_step(self, result: Dict, extracted_data: Dict, user_message: str) -> bool:
        """Validate language selection step"""
        action = result.get('action')

        if action != 'language_selection':
            logger.warning(f"Invalid action for language step: {action}")
            return False

        language = extracted_data.get('language')
        if language not in ['arabic', 'english']:
            logger.warning(f"Invalid language detected: {language}")
            return False

        return True

    def _validate_quantity_step(self, result: Dict, extracted_data: Dict, user_message: str) -> bool:
        """CRITICAL: Validate quantity step - prevent language selection confusion"""
        action = result.get('action')

        # For quantity step, ONLY accept quantity_selection action
        if action != 'quantity_selection':
            logger.warning(f"❌ Invalid action for quantity step: {action} (should be quantity_selection)")
            return False

        quantity = extracted_data.get('quantity')
        if not isinstance(quantity, int) or quantity <= 0 or quantity > 50:
            logger.warning(f"❌ Invalid quantity: {quantity}")
            return False

        # CRITICAL: Ensure no language data is present in quantity step
        if extracted_data.get('language'):
            logger.warning(f"❌ Language detected in quantity step - rejecting")
            return False

        logger.info(f"✅ Valid quantity detected: {quantity}")
        return True

    def _validate_category_step(self, result: Dict, extracted_data: Dict, user_message: str) -> bool:
        """Validate category selection step"""
        action = result.get('action')

        if action not in ['category_selection', 'show_menu', 'help_request']:
            logger.warning(f"Invalid action for category step: {action}")
            return False

        if action == 'category_selection':
            category_id = extracted_data.get('category_id')
            category_name = extracted_data.get('category_name')

            if not category_id and not category_name:
                logger.warning("No category identifier provided")
                return False

            if category_id and (category_id < 1 or category_id > 13):
                logger.warning(f"Invalid category ID: {category_id}")
                return False

        return True

    def _validate_item_step(self, result: Dict, extracted_data: Dict, user_message: str) -> bool:
        """Validate item selection step"""
        action = result.get('action')

        if action not in ['item_selection', 'category_selection', 'show_menu']:
            logger.warning(f"Invalid action for item step: {action}")
            return False

        if action == 'item_selection':
            item_id = extracted_data.get('item_id')
            item_name = extracted_data.get('item_name')

            if not item_id and not item_name:
                logger.warning("No item identifier provided")
                return False

        return True

    def _validate_additional_step(self, result: Dict, extracted_data: Dict, user_message: str) -> bool:
        """Validate additional items step"""
        action = result.get('action')

        if action != 'yes_no':
            logger.warning(f"Invalid action for additional step: {action}")
            return False

        yes_no = extracted_data.get('yes_no')
        if yes_no not in ['yes', 'no']:
            logger.warning(f"Invalid yes/no response: {yes_no}")
            return False

        return True

    def _validate_service_step(self, result: Dict, extracted_data: Dict, user_message: str) -> bool:
        """Validate service selection step"""
        action = result.get('action')

        if action != 'service_selection':
            logger.warning(f"Invalid action for service step: {action}")
            return False

        service_type = extracted_data.get('service_type')
        if service_type not in ['dine-in', 'delivery']:
            logger.warning(f"Invalid service type: {service_type}")
            return False

        return True

    def _validate_location_step(self, result: Dict, extracted_data: Dict, user_message: str) -> bool:
        """Validate location input step"""
        action = result.get('action')

        if action != 'location_input':
            logger.warning(f"Invalid action for location step: {action}")
            return False

        location = extracted_data.get('location')
        if not location or len(location.strip()) < 1:
            logger.warning("No valid location provided")
            return False

        return True

    def _validate_confirmation_step(self, result: Dict, extracted_data: Dict, user_message: str) -> bool:
        """Validate confirmation step"""
        action = result.get('action')

        if action not in ['yes_no', 'confirmation']:
            logger.warning(f"Invalid action for confirmation step: {action}")
            return False

        if action == 'yes_no':
            yes_no = extracted_data.get('yes_no')
            if yes_no not in ['yes', 'no']:
                logger.warning(f"Invalid yes/no response: {yes_no}")
                return False

        return True

    def _postprocess_extracted_data(self, extracted_data: Dict, current_step: str) -> Dict:
        """Post-process extracted data for consistency"""
        # Clean up extracted data
        cleaned_data = {}

        for key, value in extracted_data.items():
            if value is not None and value != "null":
                if key in ['category_id', 'item_id', 'quantity'] and isinstance(value, str):
                    try:
                        cleaned_data[key] = int(value)
                    except ValueError:
                        cleaned_data[key] = value
                else:
                    cleaned_data[key] = value

        # Step-specific cleaning
        if current_step == 'waiting_for_quantity':
            # Ensure only quantity-related data is present
            quantity = cleaned_data.get('quantity')
            if quantity:
                cleaned_data = {'quantity': quantity}

        return cleaned_data

    def extract_language_preference(self, user_message: str) -> Optional[str]:
        """Extract language preference from user message"""
        message_lower = user_message.lower().strip()

        # Convert Arabic numerals first
        message_lower = self._preprocess_message(message_lower)

        # Arabic language indicators (strong)
        arabic_indicators = [
            'عربي', 'العربية', 'مرحبا', 'أهلا', 'اريد', 'بدي',
            'شو', 'ايش', 'كيف', 'وين', 'هلا', 'هلا والله'
        ]

        # English language indicators (strong)
        english_indicators = [
            'english', 'hello', 'hi', 'hey', 'want', 'need',
            'order', 'menu', 'what', 'how'
        ]

        # Check for strong indicators first
        if any(indicator in message_lower for indicator in arabic_indicators):
            return 'arabic'

        if any(indicator in message_lower for indicator in english_indicators):
            return 'english'

        # Check for numbers ONLY if they are 1 or 2
        if message_lower.strip() == '1':
            return 'arabic'
        elif message_lower.strip() == '2':
            return 'english'

        return None

    def extract_number_from_text(self, text: str) -> Optional[int]:
        """Extract number from text, handling Arabic and English numerals"""
        import re

        # Preprocess to convert Arabic numerals
        text = self._preprocess_message(text)

        # Extract numbers
        numbers = re.findall(r'\d+', text)

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
        """Detect yes/no intent from text with Iraqi dialect support"""
        text_lower = text.lower().strip()

        if language == 'arabic':
            yes_indicators = ['نعم', 'ايوه', 'اه', 'صح', 'تمام', 'موافق', 'اكيد', 'yes', '1', 'هيه', 'هاهية']
            no_indicators = ['لا', 'كلا', 'مش', 'مو', 'لأ', 'رفض', 'no', '2', 'هاهية لا', 'لا هاهية']
        else:
            yes_indicators = ['yes', 'yeah', 'yep', 'sure', 'ok', 'okay', 'confirm', '1']
            no_indicators = ['no', 'nope', 'cancel', 'stop', 'abort', '2']

        # Check for no first (more specific patterns)
        for indicator in no_indicators:
            if indicator in text_lower:
                return 'no'

        # Then check for yes
        for indicator in yes_indicators:
            if indicator in text_lower:
                return 'yes'

        return None

    def detect_service_type(self, text: str, language: str = 'arabic') -> Optional[str]:
        """Detect service type (dine-in or delivery) from text"""
        text_lower = text.lower().strip()

        if language == 'arabic':
            dine_in_indicators = [
                'مقهى', 'داخل', 'هنا', 'جوا', 'في المكان', 'في الكافيه',
                'طاولة', 'جلسة', '1'
            ]
            delivery_indicators = [
                'توصيل', 'بيت', 'منزل', 'خارج', 'ديليفري', 'عنوان',
                'موقع', 'مكان', '2'
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
        """Fuzzy match text to menu category with enhanced matching"""
        text_lower = text.lower().strip()

        # Convert Arabic numerals
        text_lower = self._preprocess_message(text_lower)

        # Direct number match
        number = self.extract_number_from_text(text)
        if number and 1 <= number <= len(categories):
            return categories[number - 1]

        # Name matching with scoring
        best_match = None
        best_score = 0

        for category in categories:
            category_name_ar = category['category_name_ar'].lower()
            category_name_en = category['category_name_en'].lower()

            score = 0

            # Exact match gets highest score
            if text_lower == category_name_ar or text_lower == category_name_en:
                return category

            # Partial match scoring
            if text_lower in category_name_ar or category_name_ar in text_lower:
                score += 3
            if text_lower in category_name_en or category_name_en in text_lower:
                score += 3

            # Word-level matching
            text_words = text_lower.split()
            ar_words = category_name_ar.split()
            en_words = category_name_en.split()

            for word in text_words:
                if word in ar_words or word in en_words:
                    score += 1

            if score > best_score:
                best_score = score
                best_match = category

        # Return match if score is high enough
        if best_score >= 2:
            return best_match

        # Enhanced keyword matching
        keyword_mapping = {
            'موهيتو': 7, 'mojito': 7,
            'فرابتشينو': 5, 'frappuccino': 5,
            'ميلك شيك': 8, 'milkshake': 8,
            'توست': 9, 'toast': 9,
            'سندويش': 10, 'sandwich': 10,
            'كرواسان': 12, 'croissant': 12,
            'كيك': 11, 'cake': 11,
            'عصير': 6, 'juice': 6,
            'شاي': 4, 'tea': 4,
            'حار': 1, 'hot': 1,
            'بارد': 2, 'cold': 2,
            'حلو': 3, 'sweet': 3
        }

        for keyword, category_id in keyword_mapping.items():
            if keyword in text_lower:
                return next((cat for cat in categories if cat['category_id'] == category_id), None)

        return None

    def fuzzy_match_item(self, text: str, items: list, language: str = 'arabic') -> Optional[Dict]:
        """Fuzzy match text to menu item with enhanced matching"""
        text_lower = text.lower().strip()

        # Convert Arabic numerals
        text_lower = self._preprocess_message(text_lower)

        # Direct number match
        number = self.extract_number_from_text(text)
        if number and 1 <= number <= len(items):
            return items[number - 1]

        # Name matching with enhanced scoring
        best_match = None
        best_score = 0

        for item in items:
            item_name_ar = item['item_name_ar'].lower()
            item_name_en = item['item_name_en'].lower()

            score = 0

            # Exact match
            if text_lower == item_name_ar or text_lower == item_name_en:
                return item

            # Calculate similarity score
            if text_lower in item_name_ar or item_name_ar in text_lower:
                score += 4
            if text_lower in item_name_en or item_name_en in text_lower:
                score += 4

            # Word-level matching
            text_words = text_lower.split()
            ar_words = item_name_ar.split()
            en_words = item_name_en.split()

            for word in text_words:
                if word in ar_words or word in en_words:
                    score += 2

            if score > best_score:
                best_score = score
                best_match = item

        # Return match if score is high enough
        if best_score >= 3:
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
            'language': session.get('language_preference') if session else None,
            'session_data': session or {}
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