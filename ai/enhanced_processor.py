# ai/enhanced_processor.py
"""
Enhanced AI Processor with Deep Workflow Integration
Provides natural language understanding while maintaining structured flow
"""

import json
import logging
import time
from typing import Dict, Optional, Any, List
from .prompts import AIPrompts
from .menu_aware_prompts import MenuAwarePrompts

logger = logging.getLogger(__name__)

# Try to import OpenAI
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI not installed. AI features will be disabled.")


class EnhancedAIProcessor:
    """Enhanced AI Processor with Deep Workflow Integration"""

    def __init__(self, api_key: str = None, config: Dict = None, database_manager=None):
        self.api_key = api_key
        self.client = None
        self.database_manager = database_manager
        
        # Enhanced error tracking
        self.consecutive_failures = 0
        self.max_consecutive_failures = 5
        self.failure_window_start = None
        self.failure_window_duration = 300  # 5 minutes

        # Configuration
        if config:
            self.quota_cache_duration = config.get('ai_quota_cache_duration', 300)
            self.disable_on_quota = config.get('ai_disable_on_quota', True)
            self.fallback_enabled = config.get('ai_fallback_enabled', True)
        else:
            self.quota_cache_duration = 300
            self.disable_on_quota = True
            self.fallback_enabled = True

        if OPENAI_AVAILABLE and api_key:
            try:
                self.client = openai.OpenAI(api_key=api_key)
                logger.info("✅ Enhanced AI Processor initialized with deep workflow integration")
            except Exception as e:
                logger.error(f"⚠️ OpenAI initialization failed: {e}")
                self.client = None
        else:
            logger.warning("⚠️ Running without OpenAI - Enhanced AI features limited")

    def is_available(self) -> bool:
        """Check if enhanced AI processing is available"""
        if not self.client:
            return False

        # Check consecutive failures
        if self.consecutive_failures >= self.max_consecutive_failures:
            if self.failure_window_start:
                time_since_failures = time.time() - self.failure_window_start
                if time_since_failures < self.failure_window_duration:
                    logger.warning(f"⚠️ AI temporarily disabled due to {self.consecutive_failures} consecutive failures")
                    return False
                else:
                    self.consecutive_failures = 0
                    self.failure_window_start = None
                    logger.info("🔄 Failure window expired, re-enabling AI")

        return True

    def understand_natural_language(self, user_message: str, current_step: str, 
                                  user_context: Dict, language: str = 'arabic') -> Dict:
        """
        Primary method for natural language understanding with deep workflow integration
        """
        if not self.is_available():
            logger.warning("Enhanced AI unavailable, using fallback")
            return self._generate_enhanced_fallback(user_message, current_step, user_context, language)

        try:
            # Pre-process message
            processed_message = self._preprocess_message(user_message)
            
            # Build comprehensive context
            enhanced_context = self._build_enhanced_context(current_step, user_context, language)
            
            # Generate enhanced prompt
            prompt = self._generate_enhanced_prompt(processed_message, current_step, enhanced_context)
            
            logger.info(f"🧠 Enhanced AI analyzing: '{processed_message}' at step '{current_step}'")

            # Call OpenAI with enhanced parameters
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": self._get_enhanced_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.3,  # Slightly higher for more creative understanding
                timeout=30,
            )

            ai_response = response.choices[0].message.content.strip()
            
            # Parse and validate response
            result = self._parse_enhanced_response(ai_response, current_step, processed_message)
            
            if result:
                logger.info(f"✅ Enhanced AI Understanding: {result.get('understood_intent', 'N/A')} "
                           f"(confidence: {result.get('confidence', 'N/A')}, action: {result.get('action', 'N/A')})")
                self._reset_failure_counter()
                return result
            else:
                logger.error("❌ Failed to parse enhanced AI response")
                self._handle_ai_failure(Exception("Invalid enhanced AI response format"))
                return self._generate_enhanced_fallback(user_message, current_step, user_context, language)

        except Exception as e:
            self._handle_ai_failure(e)
            return self._generate_enhanced_fallback(user_message, current_step, user_context, language)

    def _get_enhanced_system_prompt(self) -> str:
        """Get enhanced system prompt for natural language understanding"""
        return """You are an intelligent AI assistant for Hef Cafe's WhatsApp ordering bot with deep workflow integration.

Your capabilities:
1. NATURAL LANGUAGE UNDERSTANDING: Understand user requests in Arabic and English
2. CONTEXT AWARENESS: Know the current conversation step and user's order history
3. INTELLIGENT SUGGESTIONS: Suggest appropriate menu items based on user preferences
4. CROSS-STEP ITEM SELECTION: Handle item requests at any step by finding them across the menu
5. WORKFLOW GUIDANCE: Guide users through the ordering process naturally
6. FALLBACK HANDLING: Provide helpful responses when understanding is unclear

Key principles:
- Always respond in the user's preferred language
- Provide context-aware suggestions
- Maintain conversation flow naturally
- Handle both structured (numbers) and unstructured (natural language) inputs
- Be helpful and friendly while being efficient
- When user mentions a specific item (e.g., "موهيتو", "coffee"), use "item_selection" action regardless of current step
- When user mentions preferences (e.g., "cold", "sweet"), use "intelligent_suggestion" action

Respond with clean JSON that includes:
- understood_intent: Clear description of what user wants
- confidence: high/medium/low
- action: The specific action to take
- extracted_data: Relevant data for the action
- response_message: Natural response to user
- clarification_needed: Whether you need more information
- clarification_question: Question to ask if clarification needed"""

    def _build_enhanced_context(self, current_step: str, user_context: Dict, language: str) -> Dict:
        """Build comprehensive context for AI understanding"""
        context = {
            'current_step': current_step,
            'language': language,
            'step_description': self._get_step_description(current_step),
            'user_order_history': user_context.get('order_history', []),
            'current_order_items': user_context.get('current_order_items', []),
            'available_categories': user_context.get('available_categories', []),
            'current_category_items': user_context.get('current_category_items', []),
            'selected_main_category': user_context.get('selected_main_category'),
            'selected_sub_category': user_context.get('selected_sub_category'),
            'selected_item': user_context.get('selected_item'),
            'conversation_history': user_context.get('conversation_history', [])
        }

        # Add menu context if database manager is available
        if self.database_manager:
            try:
                context['menu_context'] = MenuAwarePrompts.get_menu_context(self.database_manager)
            except Exception as e:
                logger.warning(f"Could not get menu context: {e}")
                context['menu_context'] = "Menu context unavailable"

        return context

    def _get_step_description(self, step: str) -> str:
        """Get human-readable description of current step"""
        descriptions = {
            'waiting_for_language': 'User needs to select language preference',
            'waiting_for_main_category': 'User needs to select main menu category',
            'waiting_for_sub_category': 'User needs to select sub-category',
            'waiting_for_item': 'User needs to select specific item',
            'waiting_for_quantity': 'User needs to specify quantity',
            'waiting_for_additional': 'User needs to decide if they want more items',
            'waiting_for_service': 'User needs to choose service type (dine-in/delivery)',
            'waiting_for_location': 'User needs to provide location/table number',
            'waiting_for_confirmation': 'User needs to confirm their order'
        }
        return descriptions.get(step, f'Unknown step: {step}')

    def _generate_enhanced_prompt(self, user_message: str, current_step: str, context: Dict) -> str:
        """Generate enhanced prompt for natural language understanding"""
        
        # Get menu context
        menu_context = context.get('menu_context', 'Menu context unavailable')
        
        # Build conversation context
        conversation_context = self._format_conversation_context(context)
        
        # Get step-specific guidance
        step_guidance = self._get_step_guidance(current_step, context)
        
        return f"""ENHANCED NATURAL LANGUAGE UNDERSTANDING REQUEST
==================================================

MENU KNOWLEDGE:
{menu_context}

CURRENT CONVERSATION STATE:
==========================
- Step: {current_step} ({context['step_description']})
- Language: {context['language']}
- User Message: "{user_message}"

CONVERSATION CONTEXT:
{conversation_context}

STEP-SPECIFIC GUIDANCE:
{step_guidance}

TASK: Analyze the user's message and provide intelligent understanding with appropriate action.

RESPOND WITH CLEAN JSON:
{{
    "understood_intent": "Clear description of what user wants",
    "confidence": "high/medium/low",
    "action": "intelligent_suggestion/language_selection/category_selection/item_selection/quantity_selection/yes_no/service_selection/location_input/confirmation/show_menu/help_request",
    "extracted_data": {{
        "language": "arabic/english/null",
        "suggested_main_category": "number or null",
        "suggested_sub_category": "number or null", 
        "category_id": "number or null",
        "category_name": "string or null",
        "item_id": "number or null",
        "item_name": "string or null",
        "quantity": "number or null",
        "yes_no": "yes/no/null",
        "service_type": "dine-in/delivery/null",
        "location": "string or null"
    }},
    "clarification_needed": false,
    "clarification_question": "question if clarification needed",
    "response_message": "Natural, helpful response in user's language with context and suggestions"
}}

EXAMPLES:
========
User: "اريد شي بارد"
Response: {{
    "understood_intent": "User wants something cold to drink",
    "confidence": "high",
    "action": "intelligent_suggestion",
    "extracted_data": {{
        "suggested_main_category": 1,
        "suggested_sub_category": null
    }},
    "response_message": "فهمت أنك تريد مشروب بارد! ممتاز لإنعاش يومك. هذه خياراتنا للمشروبات الباردة:\\n\\n1. المشروبات الباردة\\n2. المشروبات الحارة\\n3. الحلويات والمعجنات\\n\\nاختر رقم 1 للمشروبات الباردة أو قل لي ما تفضل!"
}}

User: "I want something sweet"
Response: {{
    "understood_intent": "User wants something sweet to eat or drink",
    "confidence": "medium",
    "action": "intelligent_suggestion", 
    "extracted_data": {{
        "suggested_main_category": 1,
        "suggested_sub_category": 2
    }},
    "response_message": "I understand you want something sweet! Great choice. I recommend our Frappuccinos - they're deliciously sweet and refreshing:\\n\\n1. Cold Drinks (includes Frappuccinos)\\n2. Hot Drinks\\n3. Pastries & Sweets\\n\\nChoose option 1 for cold sweet drinks or 3 for sweet pastries!"
}}

User: "موهيتو" (at sub-category step)
Response: {{
    "understood_intent": "User wants a mojito drink",
    "confidence": "high",
    "action": "item_selection",
    "extracted_data": {{
        "item_name": "موهيتو",
        "item_id": null
    }},
    "response_message": "ممتاز! سأجد لك موهيتو في قائمتنا وأحضره لك مباشرة."
}}

User: "coffee" (at sub-category step)
Response: {{
    "understood_intent": "User wants coffee",
    "confidence": "high", 
    "action": "item_selection",
    "extracted_data": {{
        "item_name": "coffee",
        "item_id": null
    }},
    "response_message": "Great! I'll find coffee in our menu and get it ready for you right away."
}}"""

    def _format_conversation_context(self, context: Dict) -> str:
        """Format conversation context for AI prompt"""
        parts = []
        
        # Current order
        if context.get('current_order_items'):
            parts.append(f"Current Order: {len(context['current_order_items'])} items")
            for item in context['current_order_items'][-3:]:  # Last 3 items
                parts.append(f"  - {item.get('name', 'Unknown')} × {item.get('quantity', 1)}")
        
        # Selected categories
        if context.get('selected_main_category'):
            parts.append(f"Selected Main Category: {context['selected_main_category']}")
        if context.get('selected_sub_category'):
            parts.append(f"Selected Sub-Category: {context['selected_sub_category']}")
            
        # Available options
        if context.get('available_categories'):
            parts.append(f"Available Categories: {len(context['available_categories'])} options")
        if context.get('current_category_items'):
            parts.append(f"Current Category Items: {len(context['current_category_items'])} options")
            
        return "\n".join(parts) if parts else "No specific context available"

    def _get_step_guidance(self, current_step: str, context: Dict) -> str:
        """Get step-specific guidance for AI understanding"""
        guidance = {
            'waiting_for_language': """
                - Detect language preference from user input
                - Accept: Arabic words, English words, numbers 1-2
                - Default to Arabic if unclear
                - Response: Welcome message in detected language
            """,
            
            'waiting_for_main_category': """
                - Accept: numbers 1-3, category names, natural language preferences
                - Natural language examples: "cold drinks", "something hot", "food", "sweets"
                - Intelligent suggestions based on preferences
                - Response: Show appropriate categories or sub-categories
            """,
            
            'waiting_for_sub_category': """
                - Accept: numbers, sub-category names, specific item requests
                - If user asks for specific item (e.g., "موهيتو", "coffee"), use action "item_selection"
                - If user asks for sub-category type (e.g., "عصائر", "hot drinks"), use action "intelligent_suggestion"
                - Response: For items, directly show quantity selection; for categories, show sub-category items
            """,
            
            'waiting_for_item': """
                - Accept: numbers, item names, descriptions
                - Support partial matching and synonyms
                - Response: Confirm selection and ask for quantity
            """,
            
            'waiting_for_quantity': """
                - Accept: numbers 1-50, word numbers, Arabic numerals
                - Numbers are ALWAYS quantities in this step
                - Response: Confirm quantity and ask if they want more
            """,
            
            'waiting_for_additional': """
                - Accept: yes/no responses in any form
                - Arabic: نعم, لا, ايوه, لا هاهية
                - English: yes, no, yeah, nope
                - Numbers: 1=yes, 2=no
                - Response: Show main menu again or proceed to service
            """,
            
            'waiting_for_service': """
                - Accept: service type preferences
                - Dine-in: "dine in", "في المقهى", "table", "طاولة"
                - Delivery: "delivery", "توصيل", "home", "بيت"
                - Response: Ask for location details
            """,
            
            'waiting_for_location': """
                - Accept: table numbers (1-7), addresses, location descriptions
                - Support Arabic numerals for table numbers
                - Response: Show order summary and ask for confirmation
            """,
            
            'waiting_for_confirmation': """
                - Accept: yes/no responses for order confirmation
                - Response: Complete order or cancel based on choice
            """
        }
        
        return guidance.get(current_step, "No specific guidance for this step")

    def _parse_enhanced_response(self, ai_response: str, current_step: str, user_message: str) -> Optional[Dict]:
        """Parse and validate enhanced AI response"""
        try:
            # Debug: Log the raw AI response
            logger.info(f"🔍 Raw AI Response: {ai_response}")
            
            # Clean the response
            if ai_response.startswith('```json'):
                ai_response = ai_response.replace('```json', '').replace('```', '').strip()
            
            # Remove common prefixes
            prefixes_to_remove = ['RESPOND WITH JSON:', 'JSON:', 'RESPONSE:']
            for prefix in prefixes_to_remove:
                if ai_response.startswith(prefix):
                    ai_response = ai_response[len(prefix):].strip()
            
            # Extract JSON if not clean
            if not ai_response.strip().startswith('{'):
                import re
                json_pattern = r'\{[\s\S]*\}'
                json_match = re.search(json_pattern, ai_response)
                if json_match:
                    ai_response = json_match.group(0)
            
            # Fix common JSON issues
            ai_response = self._fix_json_format(ai_response)
            
            logger.info(f"🔧 Fixed JSON: {ai_response}")
            
            result = json.loads(ai_response)
            
            # Validate required fields
            required_fields = ['understood_intent', 'confidence', 'action', 'extracted_data']
            for field in required_fields:
                if field not in result:
                    logger.error(f"Missing required field: {field}")
                    return None
            
            # Validate for current step
            if not self._validate_enhanced_result(result, current_step, user_message):
                return None
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON parsing error: {e}")
            logger.error(f"AI Response was: {ai_response}")
            return None

    def _fix_json_format(self, json_str: str) -> str:
        """Fix common JSON formatting issues"""
        try:
            import re
            
            # Remove trailing commas before closing braces/brackets
            json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
            
            # Fix empty values (key with no value)
            json_str = re.sub(r':\s*,', ': null,', json_str)
            json_str = re.sub(r':\s*([}\]])', r': null\1', json_str)
            
            # Fix multiple commas
            json_str = re.sub(r',+', ',', json_str)
            
            # Fix missing commas between properties - improved pattern
            json_str = re.sub(r'}(\s*)"', r'},\1"', json_str)
            json_str = re.sub(r'(\d+)(\s*)"', r'\1,\2"', json_str)
            json_str = re.sub(r'("[\w\s]+")(\s*)"', r'\1,\2"', json_str)
            json_str = re.sub(r'(true|false|null)(\s*)"', r'\1,\2"', json_str)
            
            # Fix missing quotes around property names
            json_str = re.sub(r'([{,])\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1 "\2":', json_str)
            
            # Fix trailing commas in arrays and objects
            json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
            
            # Fix missing closing braces/brackets
            if json_str.count('{') > json_str.count('}'):
                json_str += '}'
            if json_str.count('[') > json_str.count(']'):
                json_str += ']'
            
            return json_str
            
        except Exception as e:
            logger.warning(f"⚠️ Error fixing JSON format: {e}")
            return json_str

    def _validate_enhanced_result(self, result: Dict, current_step: str, user_message: str) -> bool:
        """Validate enhanced AI result for current step"""
        action = result.get('action')
        extracted_data = result.get('extracted_data', {})
        
        # Accept intelligent suggestions
        if action == 'intelligent_suggestion':
            return True
        
        # Step-specific validation
        validators = {
            'waiting_for_language': self._validate_language_step,
            'waiting_for_main_category': self._validate_category_step,
            'waiting_for_sub_category': self._validate_sub_category_step,
            'waiting_for_item': self._validate_item_step,
            'waiting_for_quantity': self._validate_quantity_step,
            'waiting_for_additional': self._validate_additional_step,
            'waiting_for_service': self._validate_service_step,
            'waiting_for_location': self._validate_location_step,
            'waiting_for_confirmation': self._validate_confirmation_step
        }
        
        validator = validators.get(current_step)
        if validator:
            return validator(result, extracted_data, user_message)
        
        return True

    def _validate_language_step(self, result: Dict, extracted_data: Dict, user_message: str) -> bool:
        """Validate language selection step"""
        action = result.get('action')
        if action not in ['language_selection', 'intelligent_suggestion']:
            return False
        
        if action == 'language_selection':
            language = extracted_data.get('language')
            if language not in ['arabic', 'english']:
                return False
        
        return True

    def _validate_category_step(self, result: Dict, extracted_data: Dict, user_message: str) -> bool:
        """Validate category selection step"""
        action = result.get('action')
        valid_actions = ['category_selection', 'intelligent_suggestion', 'show_menu', 'help_request']
        
        if action not in valid_actions:
            return False
        
        if action == 'category_selection':
            category_id = extracted_data.get('category_id')
            if category_id and (category_id < 1 or category_id > 3):
                return False
        
        return True

    def _validate_sub_category_step(self, result: Dict, extracted_data: Dict, user_message: str) -> bool:
        """Validate sub-category selection step"""
        action = result.get('action')
        valid_actions = ['category_selection', 'item_selection', 'intelligent_suggestion']
        
        if action not in valid_actions:
            return False
        
        return True

    def _validate_item_step(self, result: Dict, extracted_data: Dict, user_message: str) -> bool:
        """Validate item selection step"""
        action = result.get('action')
        valid_actions = ['item_selection', 'category_selection', 'intelligent_suggestion']
        
        if action not in valid_actions:
            return False
        
        return True

    def _validate_quantity_step(self, result: Dict, extracted_data: Dict, user_message: str) -> bool:
        """Validate quantity selection step"""
        action = result.get('action')
        
        if action != 'quantity_selection':
            return False
        
        quantity = extracted_data.get('quantity')
        if not isinstance(quantity, int) or quantity <= 0 or quantity > 50:
            return False
        
        return True

    def _validate_additional_step(self, result: Dict, extracted_data: Dict, user_message: str) -> bool:
        """Validate additional items step"""
        action = result.get('action')
        
        if action != 'yes_no':
            return False
        
        yes_no = extracted_data.get('yes_no')
        if yes_no not in ['yes', 'no']:
            return False
        
        return True

    def _validate_service_step(self, result: Dict, extracted_data: Dict, user_message: str) -> bool:
        """Validate service selection step"""
        action = result.get('action')
        
        if action != 'service_selection':
            return False
        
        service_type = extracted_data.get('service_type')
        if service_type not in ['dine-in', 'delivery']:
            return False
        
        return True

    def _validate_location_step(self, result: Dict, extracted_data: Dict, user_message: str) -> bool:
        """Validate location input step"""
        action = result.get('action')
        
        if action != 'location_input':
            return False
        
        location = extracted_data.get('location')
        if not location or len(location.strip()) < 1:
            return False
        
        return True

    def _validate_confirmation_step(self, result: Dict, extracted_data: Dict, user_message: str) -> bool:
        """Validate confirmation step"""
        action = result.get('action')
        
        if action not in ['yes_no', 'confirmation']:
            return False
        
        if action == 'yes_no':
            yes_no = extracted_data.get('yes_no')
            if yes_no not in ['yes', 'no']:
                return False
        
        return True

    def _generate_enhanced_fallback(self, user_message: str, current_step: str, 
                                  user_context: Dict, language: str) -> Dict:
        """Generate enhanced fallback response when AI is unavailable"""
        logger.info(f"🔄 Generating enhanced fallback for step: {current_step}")
        
        # Enhanced fallback with better understanding
        fallback_result = {
            'understood_intent': 'fallback_processing',
            'confidence': 'low',
            'action': 'fallback',
            'extracted_data': {},
            'fallback_used': True,
            'response_message': self._get_fallback_message(current_step, language)
        }
        
        # Step-specific fallback processing
        if current_step == 'waiting_for_language':
            language_detected = self._detect_language_fallback(user_message)
            if language_detected:
                fallback_result.update({
                    'action': 'language_selection',
                    'extracted_data': {'language': language_detected},
                    'confidence': 'medium'
                })
        
        elif current_step == 'waiting_for_quantity':
            quantity = self._extract_number_fallback(user_message)
            if quantity and 1 <= quantity <= 50:
                fallback_result.update({
                    'action': 'quantity_selection',
                    'extracted_data': {'quantity': quantity},
                    'confidence': 'medium'
                })
        
        elif current_step in ['waiting_for_additional', 'waiting_for_confirmation']:
            yes_no = self._detect_yes_no_fallback(user_message, language)
            if yes_no:
                fallback_result.update({
                    'action': 'yes_no',
                    'extracted_data': {'yes_no': yes_no},
                    'confidence': 'medium'
                })
        
        return fallback_result

    def _detect_language_fallback(self, user_message: str) -> Optional[str]:
        """Detect language preference in fallback mode"""
        message_lower = user_message.lower().strip()
        
        arabic_indicators = ['عربي', 'العربية', 'مرحبا', 'أهلا', 'اريد', 'بدي']
        english_indicators = ['english', 'hello', 'hi', 'hey', 'want', 'need']
        
        if any(indicator in message_lower for indicator in arabic_indicators):
            return 'arabic'
        
        if any(indicator in message_lower for indicator in english_indicators):
            return 'english'
        
        if message_lower.strip() == '1':
            return 'arabic'
        elif message_lower.strip() == '2':
            return 'english'
        
        return None

    def _extract_number_fallback(self, text: str) -> Optional[int]:
        """Extract number in fallback mode"""
        import re
        
        # Convert Arabic numerals
        arabic_to_english = {
            '٠': '0', '١': '1', '٢': '2', '٣': '3', '٤': '4',
            '٥': '5', '٦': '6', '٧': '7', '٨': '8', '٩': '9'
        }
        
        processed_text = text
        for arabic, english in arabic_to_english.items():
            processed_text = processed_text.replace(arabic, english)
        
        # Extract numbers
        numbers = re.findall(r'\d+', processed_text)
        if numbers:
            return int(numbers[0])
        
        return None

    def _detect_yes_no_fallback(self, text: str, language: str) -> Optional[str]:
        """Detect yes/no in fallback mode"""
        text_lower = text.lower().strip()
        
        if language == 'arabic':
            yes_indicators = ['نعم', 'ايوه', 'اه', 'صح', 'تمام', 'yes', '1']
            no_indicators = ['لا', 'كلا', 'مش', 'مو', 'no', '2']
        else:
            yes_indicators = ['yes', 'yeah', 'yep', 'sure', 'ok', 'okay', '1']
            no_indicators = ['no', 'nope', 'cancel', 'stop', '2']
        
        for indicator in no_indicators:
            if indicator in text_lower:
                return 'no'
        
        for indicator in yes_indicators:
            if indicator in text_lower:
                return 'yes'
        
        return None

    def _get_fallback_message(self, current_step: str, language: str) -> str:
        """Get appropriate fallback message"""
        if language == 'arabic':
            messages = {
                'waiting_for_language': 'الرجاء اختيار لغتك المفضلة:\n1. العربية\n2. English',
                'waiting_for_main_category': 'الرجاء اختيار من القائمة:\n1. المشروبات الباردة\n2. المشروبات الحارة\n3. الحلويات والمعجنات',
                'waiting_for_sub_category': 'الرجاء اختيار الفئة الفرعية المطلوبة',
                'waiting_for_item': 'الرجاء اختيار المنتج المطلوب',
                'waiting_for_quantity': 'كم الكمية المطلوبة؟',
                'waiting_for_additional': 'هل تريد إضافة المزيد من الأصناف؟\n1. نعم\n2. لا',
                'waiting_for_service': 'هل تريد طلبك للتناول في المقهى أم للتوصيل؟\n1. تناول في المقهى\n2. توصيل',
                'waiting_for_location': 'الرجاء تحديد رقم الطاولة (1-7) أو العنوان',
                'waiting_for_confirmation': 'هل تريد تأكيد هذا الطلب؟\n1. نعم\n2. لا'
            }
        else:
            messages = {
                'waiting_for_language': 'Please select your preferred language:\n1. العربية (Arabic)\n2. English',
                'waiting_for_main_category': 'Please select from the menu:\n1. Cold Drinks\n2. Hot Drinks\n3. Pastries & Sweets',
                'waiting_for_sub_category': 'Please select the required sub-category',
                'waiting_for_item': 'Please select the required item',
                'waiting_for_quantity': 'How many would you like?',
                'waiting_for_additional': 'Would you like to add more items?\n1. Yes\n2. No',
                'waiting_for_service': 'Do you want your order for dine-in or delivery?\n1. Dine-in\n2. Delivery',
                'waiting_for_location': 'Please provide your table number (1-7) or address',
                'waiting_for_confirmation': 'Would you like to confirm this order?\n1. Yes\n2. No'
            }
        
        return messages.get(current_step, 'Please provide a valid response.')

    def _preprocess_message(self, message: str) -> str:
        """Preprocess message for better AI understanding"""
        if not message:
            return ""
        
        # Convert Arabic numerals to English
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

    def _handle_ai_failure(self, error: Exception) -> None:
        """Handle AI processing failures"""
        self.consecutive_failures += 1
        
        if self.failure_window_start is None:
            self.failure_window_start = time.time()
        
        error_msg = str(error).lower()
        
        if "quota" in error_msg or "insufficient_quota" in error_msg or "429" in error_msg:
            logger.warning("⚠️ OpenAI quota exceeded, using fallback")
        elif "rate limit" in error_msg:
            logger.warning("⚠️ OpenAI rate limit hit, using fallback")
        elif "timeout" in error_msg:
            logger.warning("⚠️ OpenAI request timeout, using fallback")
        else:
            logger.error(f"❌ Enhanced AI processing error: {error}")
        
        logger.warning(f"⚠️ Consecutive failures: {self.consecutive_failures}/{self.max_consecutive_failures}")

    def _reset_failure_counter(self) -> None:
        """Reset failure counter on successful AI processing"""
        if self.consecutive_failures > 0:
            logger.info(f"✅ Enhanced AI processing successful, resetting failure counter from {self.consecutive_failures}")
            self.consecutive_failures = 0
            self.failure_window_start = None 