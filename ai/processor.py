# ai/processor.py - UPDATED with Menu Awareness
"""
Enhanced AI Processing and Understanding Engine with Menu Awareness
"""

import json
import logging
import time
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
    """Enhanced AI Processing and Understanding Engine with Menu Awareness"""

    def __init__(self, api_key: str = None, config: Dict = None, database_manager=None):
        self.api_key = api_key
        self.client = None
        self.quota_exceeded_time = None
        self.database_manager = database_manager  # ADDED for menu awareness

        # Get configuration settings
        if config:
            self.quota_cache_duration = config.get('ai_quota_cache_duration', 300)
            self.disable_on_quota = config.get('ai_disable_on_quota', True)
        else:
            self.quota_cache_duration = 300  # 5 minutes default
            self.disable_on_quota = True

        if OPENAI_AVAILABLE and api_key:
            try:
                self.client = openai.OpenAI(api_key=api_key)
                logger.info("✅ Enhanced OpenAI client initialized with menu awareness")
            except Exception as e:
                logger.error(f"⚠️ OpenAI initialization failed: {e}")
                self.client = None
        else:
            logger.warning("⚠️ Running without OpenAI - AI features limited")

    def is_available(self) -> bool:
        """Check if AI processing is available with quota cache"""
        if not self.client:
            return False

        # Check quota cache first
        if self.quota_exceeded_time:
            time_since_quota_error = time.time() - self.quota_exceeded_time
            if time_since_quota_error < self.quota_cache_duration:
                logger.debug(
                    f"⚠️ AI unavailable due to recent quota error (cache: {int(self.quota_cache_duration - time_since_quota_error)}s remaining)")
                return False
            else:
                # Clear cache after duration
                self.quota_exceeded_time = None
                logger.info("🔄 Quota cache expired, retrying AI availability")

        return True

    def understand_message_with_menu_awareness(self, user_message: str, current_step: str, context: Dict) -> Optional[
        Dict]:
        """Enhanced message understanding with menu awareness"""
        if not self.client:
            logger.warning("AI client not available")
            return None

        # Check quota cache first
        if self.quota_exceeded_time:
            time_since_quota_error = time.time() - self.quota_exceeded_time
            if time_since_quota_error < self.quota_cache_duration:
                logger.debug(f"⚠️ Skipping AI call due to recent quota error")
                return None
            else:
                self.quota_exceeded_time = None
                logger.info("🔄 Quota cache expired, retrying AI processing")

        # Check if this looks like a natural menu request
        natural_indicators = [
            'i want', 'i need', 'something', 'اريد', 'بدي', 'شي', 'شيء',
            'cold', 'hot', 'sweet', 'بارد', 'حار', 'حلو', 'منعش',
            'coffee', 'tea', 'juice', 'قهوة', 'شاي', 'عصير',
            'energy', 'wake up', 'طاقة', 'صحيان', 'نشاط',
            'refresh', 'thirsty', 'عطشان', 'eat', 'food', 'hungry', 'اكل', 'طعام', 'جوعان'
        ]

        message_lower = user_message.lower().strip()
        is_natural_request = any(indicator in message_lower for indicator in natural_indicators)

        try:
            # Pre-process message for better understanding
            user_message = self._preprocess_message(user_message)

            if is_natural_request and self.database_manager:
                # Use menu-aware prompt for natural requests
                logger.info(f"🧠 Using menu-aware AI processing for: '{user_message}'")
                from ai.menu_aware_prompts import MenuAwarePrompts
                prompt = MenuAwarePrompts.get_enhanced_understanding_prompt(
                    user_message, current_step, context, self.database_manager
                )
            else:
                # Use standard prompt for regular interactions
                logger.info(f"🤖 Using standard AI processing for: '{user_message}'")
                prompt = AIPrompts.get_understanding_prompt(user_message, current_step, context)

            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system",
                     "content": "You are a helpful AI assistant for Hef Cafe with complete menu knowledge."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800,
                temperature=0.2,  # Lower temperature for more consistent responses
            )

            ai_response = response.choices[0].message.content.strip()

            # Parse and validate JSON response
            result = self._parse_and_validate_ai_response(ai_response, current_step, user_message)

            if result:
                confidence = result.get('confidence', 'medium')
                action = result.get('action', 'unknown')
                logger.info(
                    f"✅ AI Understanding: {result.get('understood_intent', 'N/A')} (confidence: {confidence}, action: {action})")
                return result
            else:
                logger.error("❌ Failed to parse or validate AI response")
                return None

        except Exception as e:
            error_msg = str(e)
            if "quota" in error_msg.lower() or "insufficient_quota" in error_msg.lower() or "429" in error_msg:
                logger.warning("⚠️ OpenAI quota exceeded, falling back to enhanced processing")
                self.quota_exceeded_time = time.time()
                return None
            elif "rate limit" in error_msg.lower():
                logger.warning("⚠️ OpenAI rate limit hit, falling back to enhanced processing")
                self.quota_exceeded_time = time.time()
                return None
            else:
                logger.error(f"❌ AI understanding error: {error_msg}")
                return None

    def understand_message(self, user_message: str, current_step: str, context: Dict) -> Optional[Dict]:
        """Standard message understanding (fallback when menu awareness not needed)"""
        if not self.client:
            return None

        # Check quota cache first
        if self.quota_exceeded_time:
            time_since_quota_error = time.time() - self.quota_exceeded_time
            if time_since_quota_error < self.quota_cache_duration:
                return None
            else:
                self.quota_exceeded_time = None

        try:
            # Pre-process message for better understanding
            user_message = self._preprocess_message(user_message)

            # Build standard prompt
            prompt = AIPrompts.get_understanding_prompt(user_message, current_step, context)

            logger.info(f"🤖 Standard AI analyzing: '{user_message}' at step '{current_step}'")

            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": AIPrompts.SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800,
                temperature=0.1,
            )

            ai_response = response.choices[0].message.content.strip()

            # Parse and validate JSON response
            result = self._parse_and_validate_ai_response(ai_response, current_step, user_message)

            if result:
                logger.info(f"✅ AI Understanding: {result['understood_intent']} (confidence: {result['confidence']})")
                return result
            else:
                logger.error("❌ Failed to parse or validate AI response")
                return None

        except Exception as e:
            error_msg = str(e)
            if "quota" in error_msg.lower() or "insufficient_quota" in error_msg.lower() or "429" in error_msg:
                logger.warning("⚠️ OpenAI quota exceeded")
                self.quota_exceeded_time = time.time()
                return None
            elif "rate limit" in error_msg.lower():
                logger.warning("⚠️ OpenAI rate limit hit")
                self.quota_exceeded_time = time.time()
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

        # Accept intelligent suggestions (new action type)
        if action == 'intelligent_suggestion':
            return True

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

        if action not in ['language_selection', 'intelligent_suggestion']:
            logger.warning(f"Invalid action for language step: {action}")
            return False

        if action == 'language_selection':
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

        if action not in ['category_selection', 'show_menu', 'help_request', 'intelligent_suggestion']:
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

        if action not in ['item_selection', 'category_selection', 'show_menu', 'intelligent_suggestion']:
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
                if key in ['category_id', 'item_id', 'quantity', 'suggested_main_category',
                           'suggested_sub_category'] and isinstance(value, str):
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

    # Keep all existing utility methods...
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