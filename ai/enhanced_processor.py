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

        # NEW: Enhanced context management
        self.conversation_memory = {}  # Store conversation history per user
        self.user_preferences = {}     # Store user preferences and patterns
        self.error_patterns = {}       # Track common error patterns
        self.success_strategies = {}   # Store successful resolution strategies

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
            # NEW: Enhanced pre-processing with context
            processed_message = self._preprocess_message(user_message)
            
            # NEW: Build comprehensive context with conversation memory
            enhanced_context = self._build_enhanced_context(current_step, user_context, language)
            
            # NEW: Generate enhanced prompt with conversation history
            prompt = self._generate_enhanced_prompt(processed_message, current_step, enhanced_context)
            
            logger.info(f"🧠 Enhanced AI analyzing: '{processed_message}' at step '{current_step}'")

            # Call OpenAI with enhanced parameters
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": self._get_enhanced_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=800,
                response_format={"type": "json_object"}
            )

            # NEW: Enhanced response parsing with fallback strategies
            ai_response = response.choices[0].message.content
            result = self._parse_enhanced_response(ai_response, current_step, user_message)
            
            if result:
                # NEW: Validate and monitor the response
                result = self._validate_and_monitor_response(result, user_message, current_step, enhanced_context)
                
                # NEW: Update conversation memory and learn from success
                self._update_conversation_memory(user_context.get('phone_number'), user_message, result, True)
                self._reset_failure_counter()
                return result
            else:
                # NEW: Try alternative parsing strategies
                logger.warning("🔄 Primary parsing failed, trying alternative strategies")
                fallback_result = self._try_alternative_parsing(ai_response, current_step, user_message, user_context)
                
                if fallback_result:
                    # NEW: Validate and monitor the fallback result
                    fallback_result = self._validate_and_monitor_response(fallback_result, user_message, current_step, enhanced_context)
                    
                    # NEW: Update conversation memory with fallback result
                    self._update_conversation_memory(user_context.get('phone_number'), user_message, fallback_result, False)
                    return fallback_result
                else:
                    # NEW: Generate enhanced fallback with validation
                    enhanced_fallback = self._generate_enhanced_fallback(user_message, current_step, user_context, language)
                    enhanced_fallback = self._validate_and_monitor_response(enhanced_fallback, user_message, current_step, enhanced_context)
                    
                    # NEW: Update conversation memory with enhanced fallback
                    self._update_conversation_memory(user_context.get('phone_number'), user_message, enhanced_fallback, False)
                    return enhanced_fallback

        except Exception as e:
            logger.error(f"❌ Enhanced AI processing error: {str(e)}")
            self._handle_ai_failure(e)
            return self._generate_enhanced_fallback(user_message, current_step, user_context, language)

    # NEW: Enhanced conversation memory management
    def _update_conversation_memory(self, phone_number: str, user_message: str, ai_result: Dict, success: bool):
        """Update conversation memory and learn from interactions"""
        if not phone_number:
            return
            
        if phone_number not in self.conversation_memory:
            self.conversation_memory[phone_number] = {
                'history': [],
                'preferences': {},
                'error_patterns': [],
                'success_patterns': []
            }
        
        # Add to conversation history (keep last 10 exchanges)
        memory = self.conversation_memory[phone_number]
        memory['history'].append({
            'user_message': user_message,
            'ai_result': ai_result,
            'timestamp': time.time(),
            'success': success
        })
        
        # Keep only last 10 exchanges
        if len(memory['history']) > 10:
            memory['history'] = memory['history'][-10:]
        
        # Learn from success/failure
        if success:
            memory['success_patterns'].append({
                'message_type': user_message[:50],  # First 50 chars
                'step': ai_result.get('current_step', 'unknown'),
                'action': ai_result.get('action', 'unknown')
            })
        else:
            memory['error_patterns'].append({
                'message_type': user_message[:50],
                'step': ai_result.get('current_step', 'unknown'),
                'error': str(ai_result.get('error', 'unknown'))
            })

    # NEW: Alternative parsing strategies
    def _try_alternative_parsing(self, ai_response: str, current_step: str, user_message: str, user_context: Dict) -> Optional[Dict]:
        """Try alternative parsing strategies when primary parsing fails"""
        strategies = [
            self._try_regex_parsing,
            self._try_keyword_parsing,
            self._try_contextual_parsing,
            self._try_fallback_parsing
        ]
        
        for strategy in strategies:
            try:
                result = strategy(ai_response, current_step, user_message, user_context)
                if result:
                    logger.info(f"✅ Alternative parsing strategy succeeded: {strategy.__name__}")
                    return result
            except Exception as e:
                logger.warning(f"⚠️ Alternative parsing strategy failed: {strategy.__name__} - {e}")
                continue
        
        return None

    # NEW: Regex-based parsing fallback
    def _try_regex_parsing(self, ai_response: str, current_step: str, user_message: str, user_context: Dict) -> Optional[Dict]:
        """Try to parse response using regex patterns"""
        import re
        
        # Extract key information using regex
        patterns = {
            'action': r'"action":\s*"([^"]+)"',
            'confidence': r'"confidence":\s*"([^"]+)"',
            'language': r'"language":\s*"([^"]+)"',
            'quantity': r'"quantity":\s*(\d+)',
            'yes_no': r'"yes_no":\s*"([^"]+)"'
        }
        
        extracted_data = {}
        for key, pattern in patterns.items():
            match = re.search(pattern, ai_response)
            if match:
                extracted_data[key] = match.group(1) if key != 'quantity' else int(match.group(1))
        
        if extracted_data:
            return self._build_fallback_result(extracted_data, current_step, user_message, user_context)
        
        return None

    # NEW: Keyword-based parsing fallback
    def _try_keyword_parsing(self, ai_response: str, current_step: str, user_message: str, user_context: Dict) -> Optional[Dict]:
        """Try to parse response using keyword analysis"""
        keywords = {
            'language_selection': ['arabic', 'english', 'عربي', 'انجليزي'],
            'category_selection': ['category', 'category_id', 'category_name'],
            'item_selection': ['item', 'item_id', 'item_name'],
            'quantity_selection': ['quantity', 'number', 'amount'],
            'service_selection': ['service', 'dine-in', 'delivery'],
            'confirmation': ['confirm', 'yes', 'no']
        }
        
        # Analyze response content for keywords
        response_lower = ai_response.lower()
        detected_actions = []
        
        for action, action_keywords in keywords.items():
            if any(keyword in response_lower for keyword in action_keywords):
                detected_actions.append(action)
        
        if detected_actions:
            # Use the most relevant action
            action = detected_actions[0]
            return self._build_fallback_result({'action': action}, current_step, user_message, user_context)
        
        return None

    # NEW: Contextual parsing fallback
    def _try_contextual_parsing(self, ai_response: str, current_step: str, user_message: str, user_context: Dict) -> Optional[Dict]:
        """Try to parse response using contextual information"""
        # Use current step to infer likely action
        step_action_mapping = {
            'waiting_for_language': 'language_selection',
            'waiting_for_main_category': 'category_selection',
            'waiting_for_sub_category': 'category_selection',
            'waiting_for_item': 'item_selection',
            'waiting_for_quantity': 'quantity_selection',
            'waiting_for_additional': 'yes_no',
            'waiting_for_service': 'service_selection',
            'waiting_for_location': 'location_input',
            'waiting_for_confirmation': 'confirmation'
        }
        
        if current_step in step_action_mapping:
            action = step_action_mapping[current_step]
            return self._build_fallback_result({'action': action}, current_step, user_message, user_context)
        
        return None

    # NEW: Build fallback result from extracted data
    def _build_fallback_result(self, extracted_data: Dict, current_step: str, user_message: str, user_context: Dict) -> Dict:
        """Build a structured result from extracted data"""
        return {
            "understood_intent": f"Parsed from fallback strategy: {extracted_data.get('action', 'unknown')}",
            "confidence": "medium",  # Lower confidence for fallback results
            "action": extracted_data.get('action', 'stay_current_step'),
            "extracted_data": {
                "language": extracted_data.get('language', user_context.get('language_preference', 'arabic')),
                "category_id": extracted_data.get('category_id'),
                "category_name": extracted_data.get('category_name'),
                "item_id": extracted_data.get('item_id'),
                "item_name": extracted_data.get('item_name'),
                "quantity": extracted_data.get('quantity'),
                "yes_no": extracted_data.get('yes_no'),
                "service_type": extracted_data.get('service_type'),
                "location": extracted_data.get('location')
            },
            "clarification_needed": True,  # Always ask for clarification with fallback
            "clarification_question": "Could you please clarify your request?",
            "response_message": "أفهم طلبك. هل يمكنك التوضيح أكثر؟\nI understand your request. Could you please clarify?",
            "fallback_used": True,  # Flag that this is a fallback result
            "parsing_method": "fallback_strategy"
        }

    # NEW: Enhanced context building with conversation memory
    def _build_enhanced_context(self, current_step: str, user_context: Dict, language: str) -> Dict:
        """Build enhanced context with conversation memory and user preferences"""
        enhanced_context = user_context.copy()
        
        # Add conversation history if available
        phone_number = user_context.get('phone_number')
        if phone_number and phone_number in self.conversation_memory:
            memory = self.conversation_memory[phone_number]
            enhanced_context['conversation_history'] = memory['history'][-5:]  # Last 5 exchanges
            enhanced_context['user_preferences'] = memory['preferences']
            enhanced_context['common_errors'] = memory['error_patterns'][-3:]  # Last 3 errors
            enhanced_context['success_patterns'] = memory['success_patterns'][-3:]  # Last 3 successes
        
        # Add step-specific guidance
        enhanced_context['step_guidance'] = self._get_step_guidance()
        enhanced_context['available_actions'] = self._get_available_actions_for_step(current_step)
        
        # Add menu context if database manager is available
        if self.database_manager:
            try:
                enhanced_context['menu_context'] = MenuAwarePrompts.get_menu_context(self.database_manager)
            except Exception as e:
                logger.warning(f"⚠️ Could not load menu context: {e}")
                enhanced_context['menu_context'] = "Menu context unavailable"
        
        return enhanced_context

    # NEW: Enhanced prompt generation with conversation history
    def _generate_enhanced_prompt(self, user_message: str, current_step: str, context: Dict) -> str:
        """Generate enhanced prompt with conversation history and context"""
        prompt = f"""
ENHANCED AI UNDERSTANDING PROMPT
================================

CURRENT SITUATION:
- User is at step: {current_step} ({self._get_step_description(current_step)})
- User said: "{user_message}"
- Language preference: {context.get('language_preference', 'arabic')}

CONVERSATION CONTEXT:
{self._format_conversation_context(context)}

STEP-SPECIFIC GUIDANCE:
{self._get_step_specific_guidance(current_step)}

AVAILABLE ACTIONS FOR THIS STEP:
{self._get_available_actions_for_step(current_step)}

MENU CONTEXT:
{context.get('menu_context', 'Menu context not available')}

USER PREFERENCES & PATTERNS:
{self._format_user_preferences(context)}

PREVIOUS INTERACTIONS (Last 5):
{self._format_conversation_history(context)}

RESPOND WITH ENHANCED JSON:
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
    "response_message": "natural response to user in their preferred language",
    "context_used": "list of context elements that helped understanding",
    "suggested_next_steps": "suggested actions for user"
}}

IMPORTANT: Use conversation history and user preferences to provide more accurate responses.
"""
        return prompt

    # NEW: Format conversation context with history
    def _format_conversation_context(self, context: Dict) -> str:
        """Format conversation context for AI understanding"""
        formatted = []
        
        # Basic context
        if context.get('customer_name'):
            formatted.append(f"- Customer: {context['customer_name']}")
        if context.get('selected_main_category'):
            formatted.append(f"- Selected main category: {context['selected_main_category']}")
        if context.get('selected_sub_category'):
            formatted.append(f"- Selected sub-category: {context['selected_sub_category']}")
        if context.get('selected_item'):
            formatted.append(f"- Selected item: {context['selected_item']}")
        
        # Conversation history
        history = context.get('conversation_history', [])
        if history:
            formatted.append("\nRECENT CONVERSATION:")
            for i, exchange in enumerate(history[-3:], 1):  # Last 3 exchanges
                formatted.append(f"  {i}. User: {exchange['user_message'][:100]}...")
                formatted.append(f"     AI: {exchange['ai_result'].get('action', 'unknown')} (confidence: {exchange['ai_result'].get('confidence', 'unknown')})")
        
        return "\n".join(formatted) if formatted else "No additional context available"

    # NEW: Format user preferences and patterns
    def _format_user_preferences(self, context: Dict) -> str:
        """Format user preferences and patterns for AI understanding"""
        preferences = context.get('user_preferences', {})
        patterns = context.get('success_patterns', [])
        
        formatted = []
        
        if preferences:
            formatted.append("USER PREFERENCES:")
            for key, value in preferences.items():
                formatted.append(f"  - {key}: {value}")
        
        if patterns:
            formatted.append("\nSUCCESS PATTERNS:")
            for pattern in patterns[-3:]:  # Last 3 patterns
                formatted.append(f"  - {pattern['action']} at {pattern['step']}")
        
        return "\n".join(formatted) if formatted else "No user preferences available"

    # NEW: Format conversation history
    def _format_conversation_history(self, context: Dict) -> str:
        """Format conversation history for AI understanding"""
        history = context.get('conversation_history', [])
        
        if not history:
            return "No previous conversation history"
        
        formatted = []
        for i, exchange in enumerate(history[-5:], 1):  # Last 5 exchanges
            formatted.append(f"{i}. User: {exchange['user_message'][:80]}...")
            formatted.append(f"   Result: {exchange['ai_result'].get('action', 'unknown')} (success: {exchange['success']})")
        
        return "\n".join(formatted)

    # NEW: Get step-specific guidance
    def _get_step_specific_guidance(self, step: str) -> str:
        """Get step-specific guidance for AI understanding"""
        guidance = {
            'waiting_for_language': """
                - Look for language indicators in user's message
                - Consider previous language preferences if available
                - Default to Arabic if unclear
                - Provide bilingual response options
            """,
            'waiting_for_main_category': """
                - Accept numbers 1-3 for main categories
                - Accept category names in both languages
                - Look for temperature, mood, or preference indicators
                - Consider user's previous category choices
            """,
            'waiting_for_sub_category': """
                - Accept numbers for sub-categories
                - Accept sub-category names
                - Consider main category context
                - Look for specific drink/food preferences
            """,
            'waiting_for_item': """
                - Accept numbers for items
                - Accept item names (partial matching)
                - Consider user's taste preferences
                - Look for specific flavor indicators
            """,
            'waiting_for_quantity': """
                - Numbers are always quantities
                - Support Arabic and English numerals
                - Look for word-based numbers
                - Validate reasonable quantities (1-50)
            """,
            'waiting_for_additional': """
                - Look for yes/no indicators
                - Consider user's order patterns
                - Suggest common additions
            """,
            'waiting_for_service': """
                - Accept dine-in/delivery preferences
                - Consider user's previous service choices
                - Look for location indicators
            """,
            'waiting_for_location': """
                - Accept any location description
                - Consider user's previous locations
                - Look for address components
            """,
            'waiting_for_confirmation': """
                - Look for confirmation/denial
                - Consider user's order history
                - Provide clear confirmation options
            """
        }
        
        return guidance.get(step, "Use general understanding rules for this step")

    def _get_enhanced_system_prompt(self) -> str:
        """Get enhanced system prompt for OpenAI"""
        return """You are an intelligent WhatsApp bot for a café ordering system. Your role is to understand natural language requests and guide users through the ordering process.

CORE PRINCIPLES:
1. **Natural Language Understanding (NLU)**: Understand user intent regardless of how they express it
2. **Context Awareness**: Always consider the current conversation step and user's previous choices
3. **Intelligent Suggestions**: Provide helpful suggestions based on user preferences and menu knowledge
4. **Workflow Guidance**: Guide users through the ordering process step by step
5. **Cross-Step Item Selection**: Allow users to mention specific items at any step and intelligently route them
6. **Fresh Start Flow**: Handle post-order greetings with options to start new or keep previous order

DETAILED MENU STRUCTURE:
Main Category 1 - Cold Drinks (المشروبات الباردة):
  1. Iced Coffee (ايس كوفي) - Contains: Americano, Iced Coffee, Mocha, Latte variants
  2. Frappuccino (فرابتشينو) - Contains: Various frappuccino flavors
  3. Milkshake (ميلك شيك) - Contains: Various milkshake flavors
  4. Iced Tea (شاي مثلج) - Contains: Various iced tea types
  5. Fresh Juices (عصائر طازجة) - Contains: Orange, Apple, Mixed juices
  6. Mojito (موهيتو) - Contains: Classic mojito variants
  7. Energy Drinks (مشروبات الطاقة) - Contains: Red Bull, Monster, etc.

Main Category 2 - Hot Drinks (المشروبات الحارة):
  1. Coffee & Espresso (قهوة واسبرسو) - Contains: Espresso, Turkish coffee, etc.
  2. Latte & Special Drinks (لاتيه ومشروبات خاصة) - Contains: Various latte types
  3. Other Hot Drinks (مشروبات ساخنة أخرى) - Contains: Tea, hot chocolate, etc.

Main Category 3 - Pastries & Sweets (الحلويات والمعجنات):
  1. Toast (توست) - Contains: Various toast types
  2. Sandwiches (سندويشات) - Contains: Various sandwich types
  3. Croissants (كرواسان) - Contains: Various croissant types
  4. Pastries (فطائر) - Contains: Various pastry types
  5. Cake Pieces (قطع كيك) - Contains: Various cake pieces

ENHANCED ARABIC TERM MAPPING (CRITICAL):
- "طاقة" or "مشروب طاقة" or "مشروبات الطاقة" = Energy Drinks (Sub-category 7 of Cold Drinks)
- "كوفي" or "قهوة" or "كوفي بارد" or "قهوة باردة" = Coffee-related items (Multiple sub-categories)
- "بارد" or "مشروب بارد" or "مشروبات باردة" = Cold drinks (Main category 1)
- "ساخن" or "حار" or "مشروب ساخن" or "مشروبات ساخنة" = Hot drinks (Main category 2)
- "حلو" or "حلويات" or "حلو" or "معجنات" = Pastries & Sweets (Main category 3)
- "حلاوة" or "حلاوة طيبة" or "حلويات" = Pastries & Sweets (Main category 3)
- "فطائر" or "فطاير" or "فطيرة" = Pastries (Sub-category 4 of Pastries & Sweets)
- "سندويشات" or "سندويشة" or "سندويش" = Sandwiches (Sub-category 2 of Pastries & Sweets)
- "توست" = Toast (Sub-category 1 of Pastries & Sweets)
- "كرواسان" or "كرواسون" = Croissants (Sub-category 3 of Pastries & Sweets)
- "قطع كيك" or "كيك" or "قطع" = Cake Pieces (Sub-category 5 of Pastries & Sweets)
- "موهيتو" or "mojito" = Mojito (Sub-category 6 of Cold Drinks) - Contains: Blue Mojito, Passion Fruit Mojito, Blueberry Mojito, etc.
- "فرابتشينو" or "فراب" = Frappuccino (Sub-category 2 of Cold Drinks)
- "ميلك شيك" or "شيك" = Milkshake (Sub-category 3 of Cold Drinks)
- "عصير" or "عصائر" = Fresh Juices (Sub-category 5 of Cold Drinks)
- "شاي" or "شاي مثلج" = Iced Tea (Sub-category 4 of Cold Drinks)
- "عصير برتقال" or "عصير تفاح" = Fresh Juices (Sub-category 5 of Cold Drinks)
- "لاتيه" or "كابتشينو" = Latte & Special Drinks (Sub-category 2 of Hot Drinks)
- "اسبرسو" or "تركي" = Coffee & Espresso (Sub-category 1 of Hot Drinks)

SERVICE TYPE MAPPING (CRITICAL):
- "بالكهوة" or "في الكهوة" or "في المقهى" or "تناول" = Dine-in service
- "توصيل" or "للبيت" or "للمنزل" = Delivery service
- "في المقهى" or "في الكافيه" = Dine-in service
- "عندكم" or "عندك" = Dine-in service (colloquial)

CONFIRMATION MAPPING (CRITICAL):
- "هاهية" or "اي" or "ايوا" or "نعم" = Yes/Confirm
- "لا" or "مش" or "لا شكرا" = No/Decline
- "اوك" or "تمام" or "حسنا" = Yes/OK/Confirm

ARABIC QUANTITY MAPPING (CRITICAL):
- "واحد" or "واحدة" = 1
- "اثنين" or "اثنتين" = 2  
- "ثلاثة" or "ثلاث" = 3
- "أربعة" or "أربع" = 4
- "خمسة" or "خمس" = 5
- "ستة" or "ست" = 6
- "سبعة" or "سبع" = 7
- "ثمانية" or "ثماني" = 8
- "تسعة" or "تسع" = 9
- "عشرة" or "عشر" = 10
- "كوب" or "كوب واحد" = 1
- "كوبين" = 2
- "ثلاثة أكواب" = 3
- "قطعة" or "قطعة واحدة" = 1
- "قطعتين" = 2
- "ثلاث قطع" = 3

CONVERSATION FLOW:
1. Language Selection → 2. Main Category → 3. Sub-Category → 4. Item Selection → 5. Quantity → 6. Additional Items → 7. Service Type → 8. Location → 9. Confirmation

AI RESPONSE FORMAT:
Always respond with valid JSON in this exact format:
{
    "understood_intent": "Brief description of what user wants",
    "confidence": "high/medium/low",
    "action": "action_type",
    "extracted_data": {
        "language": "arabic/english/null",
        "suggested_main_category": "number or null",
        "suggested_sub_category": "number or null", 
        "category_id": "number or null",
        "category_name": "string or null",
        "sub_category_id": "number or null",
        "sub_category_name": "string or null",
        "item_id": "number or null",
        "item_name": "string or null",
        "quantity": "number or null",
        "yes_no": "yes/no/null",
        "service_type": "dine-in/delivery/null",
        "location": "string or null"
    },
    "response_message": "Brief response to user"
}

AVAILABLE ACTIONS:
- language_selection: User is choosing language
- category_selection: User is selecting main category
- sub_category_selection: User is selecting sub-category (e.g., "موهيتو" for mojito sub-category)
- intelligent_suggestion: AI suggests category/sub-category based on preferences
- item_selection: User is selecting specific item (e.g., "موهيتو ازرق" for specific mojito)
- quantity_selection: User is specifying quantity
- yes_no: User is answering yes/no question
- service_selection: User is choosing service type
- location_input: User is providing location
- confirmation: User is confirming order
- show_menu: User wants to see menu
- back_navigation: User wants to go back to previous step (CRITICAL: Detect "رجوع", "back", "السابق", "previous", "قبل", "عودة")
- conversational_response: User makes conversational comment that needs acknowledgment

IMPORTANT RULES:
- When user mentions a specific item (e.g., "موهيتو", "coffee"), use "item_selection" action regardless of current step
- When user mentions preferences (e.g., "cold", "sweet"), use "intelligent_suggestion" action
- IMPORTANT: For mixed input like "4 iced tea" at sub-category step, extract the number (4) for sub-category selection, not item selection
- Numbers in sub-category step should be treated as sub-category selection, not item selection
- Numbers in item step should be treated as item ID selection
- Always maintain conversation flow and provide helpful guidance
- If confidence is low, extract basic information and let the system handle the rest
- BACK NAVIGATION: Detect back requests ("رجوع", "back", "السابق", "previous") and use "back_navigation" action
- SERVICE TYPE: When user says "بالكهوة" or similar, interpret as dine-in service, not coffee selection
- CONFIRMATION: When user says "هاهية" or "اوك", interpret as yes/confirm

EXAMPLES:
User: "اريد موهيتو" (at any step)
Response: {
    "understood_intent": "User wants to order a mojito",
    "confidence": "high",
    "action": "item_selection",
    "extracted_data": {
        "item_name": "موهيتو",
        "category_id": 1,
        "sub_category_id": 6
    },
    "response_message": "تم اختيار موهيتو. كم الكمية المطلوبة؟"
}

User: "حلاوة طيبة" (at category step)
Response: {
    "understood_intent": "User wants pastries/sweets",
    "confidence": "high",
    "action": "category_selection",
    "extracted_data": {
        "category_id": 3,
        "category_name": "الحلويات والمعجنات"
    },
    "response_message": "ممتاز! اختر من قائمة الحلويات والمعجنات"
}

User: "بالكهوة" (at service step)
Response: {
    "understood_intent": "User wants dine-in service",
    "confidence": "high",
    "action": "service_selection",
    "extracted_data": {
        "service_type": "dine-in"
    },
    "response_message": "ممتاز! تناول في المقهى. الرجاء تحديد رقم الطاولة"
}

User: "هاهية" (at confirmation step)
Response: {
    "understood_intent": "User confirms the order",
    "confidence": "high",
    "action": "confirmation",
    "extracted_data": {
        "yes_no": "yes"
    },
    "response_message": "تم تأكيد طلبك بنجاح!"
}

User: "اوك" (at any yes/no step)
Response: {
    "understood_intent": "User confirms/agrees",
    "confidence": "high",
    "action": "yes_no",
    "extracted_data": {
        "yes_no": "yes"
    },
    "response_message": "ممتاز! المتابعة..."
}"""

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

    def _get_available_actions_for_step(self, step: str) -> str:
        """Get available actions for the current step"""
        actions = {
            'waiting_for_language': 'language_selection, back_navigation',
            'waiting_for_main_category': 'category_selection, intelligent_suggestion, back_navigation',
            'waiting_for_sub_category': 'sub_category_selection, intelligent_suggestion, back_navigation',
            'waiting_for_item': 'item_selection, sub_category_selection, back_navigation',
            'waiting_for_quantity': 'quantity_selection, back_navigation',
            'waiting_for_additional': 'yes_no, back_navigation',
            'waiting_for_service': 'service_selection, back_navigation',
            'waiting_for_location': 'location_input, back_navigation',
            'waiting_for_confirmation': 'confirmation, back_navigation'
        }
        return actions.get(step, 'unknown')

    def _generate_enhanced_prompt(self, user_message: str, current_step: str, context: Dict) -> str:
        """Generate enhanced prompt for natural language understanding"""
        
        # Use menu-aware prompts for specific steps that need special handling
        if current_step in ['waiting_for_additional', 'waiting_for_sub_category', 'waiting_for_item']:
            from .menu_aware_prompts import MenuAwarePrompts
            return MenuAwarePrompts.get_enhanced_understanding_prompt(
                user_message, current_step, context, self.database_manager
            )
        
        # Get menu context
        menu_context = context.get('menu_context', 'Menu context unavailable')
        
        # Build conversation context
        conversation_context = self._format_conversation_context(context)
        
        # Get step-specific guidance
        step_guidance = self._get_step_guidance()
        
        return f"""ENHANCED NATURAL LANGUAGE UNDERSTANDING REQUEST
==================================================

MENU KNOWLEDGE:
{menu_context}

CURRENT CONVERSATION STATE:
==========================
- Step: {current_step} ({context['step_description']})
- Language: {context['language']}
- User Message: "{user_message}"

STEP-SPECIFIC CONTEXT:
- Current Step: {current_step}
- Available Actions: {self._get_available_actions_for_step(current_step)}

CONVERSATION CONTEXT:
{conversation_context}

STEP-SPECIFIC GUIDANCE:
{step_guidance.get(current_step, "No specific guidance for this step")}

TASK: Analyze the user's message and provide intelligent understanding with appropriate action.

RESPOND WITH CLEAN JSON:
{{
    "understood_intent": "Clear description of what user wants",
    "confidence": "high/medium/low",
    "action": "intelligent_suggestion/language_selection/category_selection/item_selection/quantity_selection/yes_no/service_selection/location_input/confirmation/show_menu/help_request/back_navigation/conversational_response",
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
    "response_message": "Perfect! I'll find coffee in our menu and get it for you directly."
}}

User: "4 iced tea" (at sub-category step)
Response: {{
    "understood_intent": "User wants to select sub-category number 4 (Iced Tea)",
    "confidence": "high",
    "action": "intelligent_suggestion",
    "extracted_data": {{
        "suggested_sub_category": 4
    }},
    "response_message": "Perfect! I'll show you the Iced Tea options."
}}

User: "1" (at category step)
Response: {{
    "understood_intent": "User wants to select main category number 1 (Cold Drinks)",
    "confidence": "high",
    "action": "intelligent_suggestion",
    "extracted_data": {{
        "suggested_main_category": 1
    }},
    "response_message": "ممتاز! لقد اخترت المشروبات الباردة. الآن، إليك الخيارات المتاحة:\\n\\n1. ايس كوفي\\n2. فرابتشينو\\n3. ميلك شيك\\n4. شاي مثلج\\n5. عصائر طازجة\\n6. موهيتو\\n7. مشروبات الطاقة\\n\\nاختر رقم الفئة التي تفضلها!"
}}

User: "١" (Arabic numeral 1 at category step)
Response: {{
    "understood_intent": "User wants to select main category number 1 (Cold Drinks)",
    "confidence": "high",
    "action": "intelligent_suggestion",
    "extracted_data": {{
        "suggested_main_category": 1
    }},
    "response_message": "ممتاز! لقد اخترت المشروبات الباردة. الآن، إليك الخيارات المتاحة:\\n\\n1. ايس كوفي\\n2. فرابتشينو\\n3. ميلك شيك\\n4. شاي مثلج\\n5. عصائر طازجة\\n6. موهيتو\\n7. مشروبات الطاقة\\n\\nاختر رقم الفئة التي تفضلها!"
}}

User: "طاقة" (at sub-category step)
Response: {{
    "understood_intent": "User wants energy drinks",
    "confidence": "high",
    "action": "intelligent_suggestion",
    "extracted_data": {{
        "suggested_sub_category": 7
    }},
    "response_message": "فهمت أنك تريد مشروبات الطاقة! سأعرض لك خياراتنا من مشروبات الطاقة المتاحة"
}}

User: "مشروب طاقة" (at item step)
Response: {{
    "understood_intent": "User wants an energy drink",
    "confidence": "high",
    "action": "item_selection",
    "extracted_data": {{
        "item_name": "مشروب طاقة"
    }},
    "response_message": "ممتاز! سأجد لك مشروب الطاقة في قائمتنا"
}}

User: "1" (at service step)
Response: {{
    "understood_intent": "User wants dine-in service",
    "confidence": "high",
    "action": "service_selection",
    "extracted_data": {{
        "service_type": "dine-in"
    }},
    "response_message": "ممتاز! لقد اخترت التناول في المقهى. الرجاء تحديد رقم الطاولة (1-7):"
}}

User: "2" (at service step)
Response: {{
    "understood_intent": "User wants delivery service",
    "confidence": "high",
    "action": "service_selection",
    "extracted_data": {{
        "service_type": "delivery"
    }},
    "response_message": "ممتاز! لقد اخترت خدمة التوصيل. الرجاء مشاركة موقعك وأي تعليمات خاصة:"
}}

User: "رجوع" (at any step)
Response: {{
    "understood_intent": "User wants to go back to previous step",
    "confidence": "high",
    "action": "back_navigation",
    "extracted_data": {{}},
    "response_message": "سأعيدك إلى الخطوة السابقة"
}}

User: "كيف الحال" (at confirmation step)
Response: {{
    "understood_intent": "User is making conversational comment",
    "confidence": "high",
    "action": "conversational_response",
    "extracted_data": {{}},
    "response_message": "الحمد لله، بخير! شكراً لسؤالك. الآن، هل تريد تأكيد طلبك؟\\n\\n1. نعم\\n2. لا"
}}

User: "اريد شراب جوكلت بارد" (at sub-category step)
Response: {{
    "understood_intent": "User wants cold chocolate drink",
    "confidence": "high",
    "action": "intelligent_suggestion",
    "extracted_data": {{
        "suggested_sub_category": 2
    }},
    "response_message": "فهمت أنك تريد شراب شوكولاتة بارد! سأعرض لك خياراتنا من فرابتشينو:"
}}

User: "اين هي" (at any step)
Response: {{
    "understood_intent": "User is asking where something is",
    "confidence": "high",
    "action": "conversational_response",
    "extracted_data": {{}},
    "response_message": "عذراً على عدم الوضوح. دعني أعرض لك الخيارات المتاحة مرة أخرى."
}}"""

    def _format_conversation_context(self, context: Dict) -> str:
        """Format conversation context for AI understanding"""
        parts = []
        
        # Current order
        if context.get('current_order_items'):
            parts.append(f"Current Order: {len(context['current_order_items'])} items")
            for item in context['current_order_items'][-3:]:  # Last 3 items
                parts.append(f"  - {item.get('name', 'Unknown')} × {item.get('quantity', 1)}")
        
        # Selected categories with detailed context
        selected_main = context.get('selected_main_category')
        if selected_main:
            main_category_names = {
                1: "Cold Drinks (المشروبات الباردة)",
                2: "Hot Drinks (المشروبات الحارة)", 
                3: "Pastries & Sweets (الحلويات والمعجنات)"
            }
            main_name = main_category_names.get(selected_main, f"Unknown Category {selected_main}")
            parts.append(f"CURRENT MAIN CATEGORY: {selected_main} - {main_name}")
            
            # Add sub-category context based on main category
            if selected_main == 1:  # Cold Drinks
                parts.append("Available Sub-Categories: 1=Iced Coffee, 2=Frappuccino, 3=Milkshake, 4=Iced Tea, 5=Fresh Juices, 6=Mojito, 7=Energy Drinks")
            elif selected_main == 2:  # Hot Drinks
                parts.append("Available Sub-Categories: 1=Coffee & Espresso, 2=Latte & Special Drinks, 3=Other Hot Drinks")
            elif selected_main == 3:  # Pastries & Sweets
                parts.append("Available Sub-Categories: 1=Toast, 2=Sandwiches, 3=Croissants, 4=Pastries, 5=Cake Pieces")
                
        if context.get('selected_sub_category'):
            parts.append(f"CURRENT SUB-CATEGORY: {context['selected_sub_category']}")
            
        # Available options
        if context.get('available_categories'):
            parts.append(f"Available Main Categories: {len(context['available_categories'])} options")
        if context.get('current_category_items'):
            parts.append(f"Current Sub-Category Items: {len(context['current_category_items'])} options")
            
        return "\n".join(parts) if parts else "No specific context available"

    def _get_step_guidance(self) -> Dict[str, str]:
        """Get step-specific guidance for AI"""
        return {
            'waiting_for_language': """
                - Accept: language keywords, numbers (1-2)
                - Arabic indicators: "مرحبا", "السلام عليكم", "أهلا", "عربي", "1"
                - English indicators: "hello", "hi", "english", "2"
                - Response: Confirm language and show main categories
            """,
            
            'waiting_for_category': """
                - Accept: numbers (1-3), category names, preferences
                - Numbers: 1=Cold Drinks, 2=Hot Drinks, 3=Pastries & Sweets
                - Natural language: "cold", "hot", "sweet", "drink", "pastry"
                - Response: Show sub-categories for selected main category
            """,
            
            'waiting_for_sub_category': """
                - CRITICAL: Use CURRENT MAIN CATEGORY from conversation context to determine valid sub-categories
                - If CURRENT MAIN CATEGORY = 1 (Cold Drinks): Accept numbers 1-7 only
                  1=Iced Coffee, 2=Frappuccino, 3=Milkshake, 4=Iced Tea, 5=Fresh Juices, 6=Mojito, 7=Energy Drinks
                - If CURRENT MAIN CATEGORY = 2 (Hot Drinks): Accept numbers 1-3 only
                  1=Coffee & Espresso, 2=Latte & Special Drinks, 3=Other Hot Drinks
                - If CURRENT MAIN CATEGORY = 3 (Pastries & Sweets): Accept numbers 1-5 only
                  1=Toast, 2=Sandwiches, 3=Croissants, 4=Pastries, 5=Cake Pieces
                - NEVER suggest sub-categories outside the current main category context
                - IMPORTANT: If user provides mixed input like "4 iced tea", extract the number (4) for sub-category selection
                - If user asks for specific item (e.g., "موهيتو", "coffee", "iced tea"), use action "item_selection"
                - If user asks for sub-category type (e.g., "عصائر", "hot drinks"), use action "intelligent_suggestion"
                - If user provides just a number, use action "intelligent_suggestion" with suggested_sub_category
                - NEVER suggest sub-category numbers higher than 7 for Cold Drinks or 3 for Hot Drinks
                - Response: For items, directly show quantity selection; for categories, show sub-category items
            """,
            
            'waiting_for_item': """
                - Accept: numbers (which are item IDs), item names, descriptions.
                - IMPORTANT: If user provides a number, it is ALWAYS an item ID for selection.
                - Support partial matching and synonyms for item names.
                - Response: Confirm selection and ask for quantity.
            """,
            
            'waiting_for_quantity': """
                - Accept: numbers (1-50), Arabic numerals, Arabic number words
                - Convert Arabic numerals (٠-٩) and Arabic words (خمسة, عشرة) to English digits
                - Response: Confirm quantity and ask if user wants to add more items
            """,
            
            'waiting_for_additional': """
                - Accept: yes/no responses, numbers (1-2)
                - Yes indicators: "نعم", "اي", "yes", "1", "add", "more"
                - No indicators: "لا", "no", "2", "finish", "done"
                - Response: If yes, show main categories; if no, proceed to service selection
            """,
            
            'waiting_for_service': """
                - Accept: service type preferences, numbers (1-2 ONLY)
                - Dine-in: "في المقهى", "داخل", "dine", "1"
                - Delivery: "توصيل", "delivery", "2"
                - CRITICAL: ONLY accept numbers 1 or 2. Reject 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, etc.
                - If user enters number > 2, return validation error
                - IMPORTANT: Numbers like "12", "21", "123", etc. are INVALID - they contain digits > 2
                - ONLY accept "1" or "2" as valid numeric inputs
                - Response: Ask for location (table number or address)
            """,
            
            'waiting_for_location': """
                - Accept: table numbers (1-7), addresses, location descriptions
                - For dine-in: expect table number (ONLY 1-7, reject 8, 9, 10, etc.)
                - For delivery: expect address or location
                - CRITICAL: If user enters table number > 7 for dine-in, reject it
                - Response: Show order summary and ask for confirmation
            """,
            
            'waiting_for_confirmation': """
                - Accept: yes/no responses, numbers (1-2), conversational interruptions
                - Yes indicators: "نعم", "اي", "yes", "1", "confirm"
                - No indicators: "لا", "no", "2", "cancel"
                - Conversational: "كيف الحال", "مرحبا", "شكرا", "hello", "how are you", "thanks"
                - IMPORTANT: If user makes conversational comment, acknowledge it briefly then redirect to confirmation
                - Response: If yes, confirm order; if no, cancel; if conversational, acknowledge and redirect
            """,
            
            'waiting_for_fresh_start_choice': """
                - Accept: numbers (1-2), fresh start preferences
                - 1: Start new order (cancel previous)
                - 2: Keep previous order
                - Response: Execute the chosen action
            """
        }

    def _parse_enhanced_response(self, ai_response: str, current_step: str, user_message: str) -> Optional[Dict]:
        """Parse enhanced AI response with improved error handling"""
        try:
            # Try to parse as JSON first
            if isinstance(ai_response, str):
                # Clean up the response
                cleaned_response = self._fix_json_format(ai_response)
                
                try:
                    result = json.loads(cleaned_response)
                except json.JSONDecodeError:
                    # Try to fix common JSON issues
                    fixed_response = self._fix_json_format(ai_response)
                    try:
                        result = json.loads(fixed_response)
                    except json.JSONDecodeError:
                        logger.warning("🔄 JSON parsing failed, response may be malformed")
                        return None
            else:
                result = ai_response

            # Validate the result structure
            if not isinstance(result, dict):
                logger.warning("🔄 AI response is not a dictionary")
                return None

            # Enhanced validation with fallback handling
            if self._validate_enhanced_result(result, current_step, user_message):
                # Add metadata to the result
                result['parsing_method'] = 'enhanced_ai'
                result['current_step'] = current_step
                result['original_message'] = user_message
                result['timestamp'] = time.time()
                
                return result
            else:
                logger.warning("🔄 Enhanced AI response validation failed")
                return None

        except Exception as e:
            logger.error(f"❌ Error parsing enhanced AI response: {str(e)}")
            return None

    def _validate_enhanced_result(self, result: Dict, current_step: str, user_message: str) -> bool:
        """Enhanced validation with better error handling"""
        try:
            # Check required fields
            required_fields = ['understood_intent', 'confidence', 'action', 'extracted_data']
            for field in required_fields:
                if field not in result:
                    logger.warning(f"🔄 Missing required field: {field}")
                    return False

            # Validate action field
            valid_actions = [
                'language_selection', 'category_selection', 'item_selection', 
                'quantity_selection', 'yes_no', 'service_selection', 
                'location_input', 'confirmation', 'show_menu', 'help_request', 
                'stay_current_step'
            ]
            
            if result['action'] not in valid_actions:
                logger.warning(f"🔄 Invalid action: {result['action']}")
                # Try to map to valid action
                mapped_action = self._map_action_to_valid(result['action'])
                if mapped_action:
                    result['action'] = mapped_action
                    result['action_mapped'] = True
                    logger.info(f"✅ Mapped action {result['action']} to {mapped_action}")
                else:
                    return False

            # Validate extracted_data structure
            extracted_data = result.get('extracted_data', {})
            if not isinstance(extracted_data, dict):
                logger.warning("🔄 extracted_data is not a dictionary")
                return False

            # Enhanced step-specific validation
            validation_method = f"_validate_{current_step}_step"
            if hasattr(self, validation_method):
                try:
                    if not getattr(self, validation_method)(result, extracted_data, user_message):
                        logger.warning(f"🔄 Step-specific validation failed for {current_step}")
                        # Don't fail completely, just mark as needing clarification
                        result['clarification_needed'] = True
                        result['validation_warnings'] = [f"Step {current_step} validation had issues"]
                except Exception as e:
                    logger.warning(f"🔄 Step validation error: {e}")
                    result['clarification_needed'] = True

            return True

        except Exception as e:
            logger.error(f"❌ Validation error: {str(e)}")
            return False

    # NEW: Action mapping for invalid actions
    def _map_action_to_valid(self, invalid_action: str) -> Optional[str]:
        """Map invalid actions to valid ones"""
        action_mapping = {
            'language': 'language_selection',
            'category': 'category_selection',
            'item': 'item_selection',
            'quantity': 'quantity_selection',
            'service': 'service_selection',
            'location': 'location_input',
            'confirm': 'confirmation',
            'menu': 'show_menu',
            'help': 'help_request',
            'stay': 'stay_current_step'
        }
        
        # Try exact match first
        if invalid_action in action_mapping:
            return action_mapping[invalid_action]
        
        # Try partial matching
        for key, value in action_mapping.items():
            if key in invalid_action.lower():
                return value
        
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
            
            # Fix missing commas between properties - more specific patterns
            # Only add comma after closing brace if followed by a quoted key (but not if already has comma)
            json_str = re.sub(r'}(\s*)"([^"]+)"\s*:', r'},\1"\2":', json_str)
            # Fix cases where there's no comma between object properties
            json_str = re.sub(r'"([^"]+)"\s*"([^"]+)"\s*:', r'"\1", "\2":', json_str)
            
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

    def _validate_language_step(self, result: Dict, extracted_data: Dict, user_message: str) -> bool:
        """Validate language selection step"""
        action = result.get('action')
        logger.debug(f"DEBUG: _validate_language_step - action: {action}, extracted_data: {extracted_data}")
        
        if action not in ['language_selection', 'intelligent_suggestion']:
            logger.debug(f"DEBUG: _validate_language_step - Invalid action: {action}")
            return False
        
        if action == 'language_selection':
            language = extracted_data.get('language')
            logger.debug(f"DEBUG: _validate_language_step - language: {language}")
            if language not in ['arabic', 'english']:
                logger.debug(f"DEBUG: _validate_language_step - Invalid language: {language}")
                return False
        
        logger.debug(f"DEBUG: _validate_language_step - Validation passed")
        return True

    def _validate_category_step(self, result: Dict, extracted_data: Dict, user_message: str) -> bool:
        """Validate category selection step"""
        action = result.get('action')
        valid_actions = ['category_selection', 'intelligent_suggestion', 'show_menu', 'help_request', 'conversational_response']
        
        if action not in valid_actions:
            return False
        
        if action == 'category_selection':
            category_id = extracted_data.get('category_id')
            if category_id and (category_id < 1 or category_id > 3):
                return False
        
        # Extra validation for numeric inputs at category step
        user_message_lower = user_message.lower().strip()
        if user_message_lower in ['1', '2', '3', '4', '5', '6', '7', '١', '٢', '٣', '٤', '٥', '٦', '٧']:
            # Force correct interpretation for category step
            if user_message_lower in ['1', '١']:
                forced_category_id = 1
            elif user_message_lower in ['2', '٢']:
                forced_category_id = 2
            elif user_message_lower in ['3', '٣']:
                forced_category_id = 3
            else:
                # Numbers 4-7 should map to main category 1 (Cold Drinks)
                forced_category_id = 1

            extracted_data['category_id'] = forced_category_id  # Set category_id directly
            extracted_data['suggested_main_category'] = None  # Clear suggested_main_category if it was set by AI
            result['extracted_data'] = extracted_data
            result['action'] = 'category_selection'
            result['understood_intent'] = f"User wants to select main category number {forced_category_id}"
            logger.info(f"🔧 Fixed category selection: {user_message} -> main_category={forced_category_id}")
        
        return True

    def _validate_sub_category_step(self, result: Dict, extracted_data: Dict, user_message: str) -> bool:
        """Validate sub-category selection step"""
        action = result.get('action')
        # Accept explicit sub_category_selection in addition to others
        valid_actions = ['sub_category_selection', 'category_selection', 'item_selection', 'intelligent_suggestion', 'conversational_response']

        if action not in valid_actions:
            return False

        return True

    def _validate_item_step(self, result: Dict, extracted_data: Dict, user_message: str) -> bool:
        """Validate item selection step"""
        action = result.get('action')
        valid_actions = ['item_selection', 'category_selection', 'intelligent_suggestion', 'conversational_response']
        
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
        
        # Extra validation for Arabic words and numerals
        user_message_lower = user_message.lower().strip()
        if user_message_lower in ['نعم', 'اي', 'yes', '1'] and yes_no != 'yes':
            logger.warning(f"⚠️ AI incorrectly interpreted '{user_message}' as '{yes_no}' instead of 'yes'")
            # Force correct interpretation
            extracted_data['yes_no'] = 'yes'
            result['extracted_data'] = extracted_data
            result['understood_intent'] = "User wants to add more items to their order"
            result['response_message'] = "ممتاز! سأعرض لك قائمة الأصناف مرة أخرى:\n\n1. مشروبات باردة\n2. مشروبات ساخنة\n3. معجنات وحلويات\n\nاختر رقم الصنف الذي تريده:"
        
        elif user_message_lower in ['لا', 'لأ', 'no', '2'] and yes_no != 'no':
            logger.warning(f"⚠️ AI incorrectly interpreted '{user_message}' as '{yes_no}' instead of 'no'")
            # Force correct interpretation
            extracted_data['yes_no'] = 'no'
            result['extracted_data'] = extracted_data
            result['understood_intent'] = "User wants to finish their order and not add more items"
            result['response_message'] = "ممتاز! لننتقل إلى اختيار نوع الخدمة. هل تفضل تناول الطعام في المقهى أم التوصيل للمنزل؟"
        
        return True

    def _validate_service_step(self, result: Dict, extracted_data: Dict, user_message: str) -> bool:
        """Validate service selection step"""
        action = result.get('action')
        
        if action != 'service_selection':
            return False
        
        service_type = extracted_data.get('service_type')
        if service_type not in ['dine-in', 'delivery']:
            return False
        
        # Additional validation: Check if user entered a number above 2
        import re
        # Convert Arabic numerals to English
        arabic_to_english = {
            '٠': '0', '١': '1', '٢': '2', '٣': '3', '٤': '4',
            '٥': '5', '٦': '6', '٧': '7', '٨': '8', '٩': '9'
        }
        
        processed_message = user_message
        for arabic, english in arabic_to_english.items():
            processed_message = processed_message.replace(arabic, english)
        
        # Check if it's a pure number
        if re.match(r'^\d+$', processed_message.strip()):
            number = int(processed_message.strip())
            if number > 2:
                logger.warning(f"⚠️ Invalid service selection number: {number} (must be 1 or 2)")
                # Add validation flag for the handler
                extracted_data['service_validation'] = 'invalid'
                extracted_data['invalid_service_number'] = number
                result['extracted_data'] = extracted_data
                return False
        
        return True

    def _validate_location_step(self, result: Dict, extracted_data: Dict, user_message: str) -> bool:
        """Validate location input step with enhanced table number validation"""
        action = result.get('action')
        
        if action != 'location_input':
            return False
        
        location = extracted_data.get('location')
        if not location or len(location.strip()) < 1:
            return False
        
        # Enhanced validation for dine-in table numbers
        # Check if this is a numeric input that could be a table number
        import re
        
        # Convert Arabic numerals to English
        arabic_to_english = {
            '٠': '0', '١': '1', '٢': '2', '٣': '3', '٤': '4',
            '٥': '5', '٦': '6', '٧': '7', '٨': '8', '٩': '9'
        }
        
        processed_location = location
        for arabic, english in arabic_to_english.items():
            processed_location = processed_location.replace(arabic, english)
        
        # Check if it's a pure number (could be table number)
        if re.match(r'^\d+$', processed_location.strip()):
            table_num = int(processed_location.strip())
            
            # For dine-in service, table numbers must be 1-7
            # We need to check the current order's service type
            # Since we don't have direct access to the database here,
            # we'll add a note in the extracted_data for the handler to validate
            if table_num < 1 or table_num > 7:
                logger.warning(f"⚠️ Invalid table number detected: {table_num} (must be 1-7)")
                # Add validation flag for the handler
                extracted_data['table_number_validation'] = 'invalid'
                extracted_data['invalid_table_number'] = table_num
                result['extracted_data'] = extracted_data
                return False
            else:
                # Valid table number
                extracted_data['table_number_validation'] = 'valid'
                extracted_data['table_number'] = table_num
                result['extracted_data'] = extracted_data
                logger.info(f"✅ Valid table number detected: {table_num}")
        
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

    def _validate_fresh_start_choice_step(self, result: Dict, extracted_data: Dict, user_message: str) -> bool:
        """Validate fresh start choice step"""
        action = result.get('action')
        
        if action != 'yes_no':
            return False
        
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
        """Preprocess message for better AI understanding with enhanced Arabic quantity recognition"""
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
        
        # Enhanced Arabic quantity word recognition
        arabic_quantity_mapping = {
            'واحد': '1', 'واحدة': '1',
            'اثنين': '2', 'اثنتين': '2',
            'ثلاثة': '3', 'ثلاث': '3',
            'أربعة': '4', 'أربع': '4',
            'خمسة': '5', 'خمس': '5',
            'ستة': '6', 'ست': '6',
            'سبعة': '7', 'سبع': '7',
            'ثمانية': '8', 'ثماني': '8',
            'تسعة': '9', 'تسع': '9',
            'عشرة': '10', 'عشر': '10',
            'كوب واحد': '1 كوب', 'كوب': '1 كوب',
            'كوبين': '2 كوب',
            'ثلاثة أكواب': '3 كوب',
            'قطعة واحدة': '1 قطعة', 'قطعة': '1 قطعة',
            'قطعتين': '2 قطعة',
            'ثلاث قطع': '3 قطعة'
        }
        
        # Replace Arabic quantity words with numbers
        for arabic_word, replacement in arabic_quantity_mapping.items():
            processed_message = processed_message.replace(arabic_word, replacement)
        
        # Clean whitespace
        processed_message = ' '.join(processed_message.split())
        
        return processed_message.strip()

    def _handle_ai_failure(self, error: Exception) -> None:
        """Enhanced AI failure handling with recovery strategies"""
        try:
            # Log the error with context
            logger.error(f"❌ AI processing failure: {str(error)}")
            logger.error(f"❌ Error type: {type(error).__name__}")
            
            # Update failure tracking
            self.consecutive_failures += 1
            if not self.failure_window_start:
                self.failure_window_start = time.time()
            
            # Log failure pattern
            error_type = type(error).__name__
            if error_type not in self.error_patterns:
                self.error_patterns[error_type] = 0
            self.error_patterns[error_type] += 1
            
            # Determine recovery strategy
            recovery_strategy = self._determine_recovery_strategy(error)
            logger.info(f"🔄 Using recovery strategy: {recovery_strategy}")
            
            # Execute recovery strategy
            self._execute_recovery_strategy(recovery_strategy, error)
            
        except Exception as recovery_error:
            logger.error(f"❌ Error in failure recovery: {str(recovery_error)}")

    # NEW: Determine recovery strategy based on error type
    def _determine_recovery_strategy(self, error: Exception) -> str:
        """Determine the best recovery strategy for the given error"""
        error_type = type(error).__name__
        
        if 'quota' in str(error).lower() or 'rate' in str(error).lower():
            return 'quota_exceeded'
        elif 'timeout' in str(error).lower() or 'timed' in str(error).lower():
            return 'timeout_retry'
        elif 'json' in str(error).lower() or 'parse' in str(error).lower():
            return 'parsing_fallback'
        elif 'network' in str(error).lower() or 'connection' in str(error).lower():
            return 'network_retry'
        elif 'authentication' in str(error).lower() or 'unauthorized' in str(error).lower():
            return 'auth_error'
        else:
            return 'general_fallback'

    # NEW: Execute recovery strategy
    def _execute_recovery_strategy(self, strategy: str, error: Exception) -> None:
        """Execute the determined recovery strategy"""
        try:
            if strategy == 'quota_exceeded':
                self._handle_quota_exceeded()
            elif strategy == 'timeout_retry':
                self._handle_timeout_retry()
            elif strategy == 'parsing_fallback':
                self._handle_parsing_fallback()
            elif strategy == 'network_retry':
                self._handle_network_retry()
            elif strategy == 'auth_error':
                self._handle_auth_error()
            elif strategy == 'general_fallback':
                self._handle_general_fallback()
            
        except Exception as recovery_error:
            logger.error(f"❌ Recovery strategy execution failed: {str(recovery_error)}")

    # NEW: Handle quota exceeded errors
    def _handle_quota_exceeded(self) -> None:
        """Handle API quota exceeded errors"""
        logger.warning("⚠️ API quota exceeded, implementing quota management")
        
        # Extend failure window for quota issues
        self.failure_window_duration = 600  # 10 minutes for quota issues
        
        # Update configuration if possible
        if hasattr(self, 'disable_on_quota') and self.disable_on_quota:
            logger.info("🔄 Disabling AI processing due to quota exceeded")
            # The is_available() method will handle this

    # NEW: Handle timeout errors
    def _handle_timeout_retry(self) -> None:
        """Handle timeout errors with retry logic"""
        logger.warning("⚠️ Timeout error detected, implementing retry logic")
        
        # Reduce failure window for timeout issues
        self.failure_window_duration = 180  # 3 minutes for timeout issues
        
        # Log timeout pattern for optimization
        if 'timeout' not in self.error_patterns:
            self.error_patterns['timeout'] = 0
        self.error_patterns['timeout'] += 1

    # NEW: Handle parsing fallback
    def _handle_parsing_fallback(self) -> None:
        """Handle parsing errors with fallback strategies"""
        logger.warning("⚠️ Parsing error detected, enabling fallback strategies")
        
        # Enable all fallback strategies
        self.fallback_enabled = True
        
        # Log parsing error pattern
        if 'parsing' not in self.error_patterns:
            self.error_patterns['parsing'] = 0
        self.error_patterns['parsing'] += 1

    # NEW: Handle network retry
    def _handle_network_retry(self) -> None:
        """Handle network errors with retry logic"""
        logger.warning("⚠️ Network error detected, implementing retry logic")
        
        # Short failure window for network issues
        self.failure_window_duration = 120  # 2 minutes for network issues
        
        # Log network error pattern
        if 'network' not in self.error_patterns:
            self.error_patterns['network'] = 0
        self.error_patterns['network'] += 1

    # NEW: Handle authentication errors
    def _handle_auth_error(self) -> None:
        """Handle authentication errors"""
        logger.error("❌ Authentication error detected")
        
        # Long failure window for auth issues
        self.failure_window_duration = 1800  # 30 minutes for auth issues
        
        # Log auth error pattern
        if 'authentication' not in self.error_patterns:
            self.error_patterns['authentication'] = 0
        self.error_patterns['authentication'] += 1

    # NEW: Handle general fallback
    def _handle_general_fallback(self) -> None:
        """Handle general errors with fallback strategies"""
        logger.warning("⚠️ General error detected, enabling all fallback strategies")
        
        # Enable all fallback strategies
        self.fallback_enabled = True
        
        # Standard failure window
        self.failure_window_duration = 300  # 5 minutes for general issues

    # NEW: Extract basic information from user message
    def _extract_basic_info(self, user_message: str, current_step: str, language: str) -> Dict:
        """Extract basic information from user message using fallback strategies"""
        extracted_data = {}
        
        try:
            # Language detection
            if self._detect_language_fallback(user_message):
                extracted_data['language'] = self._detect_language_fallback(user_message)
            
            # Number extraction for quantities
            if 'waiting_for_quantity' in current_step:
                quantity = self._extract_number_fallback(user_message)
                if quantity:
                    extracted_data['quantity'] = quantity
            
            # Yes/No detection
            if 'waiting_for_additional' in current_step or 'waiting_for_confirmation' in current_step:
                yes_no = self._detect_yes_no_fallback(user_message, language)
                if yes_no:
                    extracted_data['yes_no'] = yes_no
            
            # Action mapping based on current step
            action = self._map_step_to_action(current_step)
            if action:
                extracted_data['action'] = action
            
        except Exception as e:
            logger.warning(f"⚠️ Error in basic info extraction: {e}")
        
        return extracted_data

    # NEW: Map current step to likely action
    def _map_step_to_action(self, current_step: str) -> Optional[str]:
        """Map current step to likely user action"""
        step_action_mapping = {
            'waiting_for_language': 'language_selection',
            'waiting_for_main_category': 'category_selection',
            'waiting_for_sub_category': 'category_selection',
            'waiting_for_item': 'item_selection',
            'waiting_for_quantity': 'quantity_selection',
            'waiting_for_additional': 'yes_no',
            'waiting_for_service': 'service_selection',
            'waiting_for_location': 'location_input',
            'waiting_for_confirmation': 'confirmation'
        }
        
        return step_action_mapping.get(current_step)

    # NEW: Get fallback clarification question
    def _get_fallback_clarification_question(self, current_step: str, language: str) -> str:
        """Get appropriate clarification question for fallback responses"""
        questions = {
            'waiting_for_language': {
                'arabic': 'أي لغة تفضل؟ العربية أم الإنجليزية؟',
                'english': 'Which language do you prefer? Arabic or English?'
            },
            'waiting_for_main_category': {
                'arabic': 'أي فئة تريد؟ المشروبات الباردة، المشروبات الحارة، أم الحلويات؟',
                'english': 'Which category would you like? Cold Drinks, Hot Drinks, or Food?'
            },
            'waiting_for_quantity': {
                'arabic': 'كم عدد تريد؟',
                'english': 'How many would you like?'
            },
            'waiting_for_additional': {
                'arabic': 'هل تريد إضافة شيء آخر؟',
                'english': 'Would you like to add anything else?'
            }
        }
        
        step_questions = questions.get(current_step, {
            'arabic': 'هل يمكنك التوضيح أكثر؟',
            'english': 'Could you please clarify?'
        })
        
        return step_questions.get(language, step_questions['arabic'])

    # NEW: Get basic fallback response
    def _get_basic_fallback_response(self, current_step: str, language: str) -> Dict:
        """Get basic fallback response when enhanced fallback fails"""
        return {
            "understood_intent": "Basic fallback processing",
            "confidence": "low",
            "action": "stay_current_step",
            "extracted_data": {},
            "clarification_needed": True,
            "clarification_question": "Could you please clarify your request?",
            "response_message": "أفهم طلبك. هل يمكنك التوضيح أكثر؟\nI understand your request. Could you please clarify?",
            "fallback_used": True,
            "parsing_method": "basic_fallback",
            "error_context": "Fallback processing failed, using basic response"
        }

    def _reset_failure_counter(self) -> None:
        """Reset failure counter on successful AI processing"""
        if self.consecutive_failures > 0:
            logger.info(f"✅ Enhanced AI processing successful, resetting failure counter from {self.consecutive_failures}")
            self.consecutive_failures = 0
            self.failure_window_start = None 

    # NEW: Fallback parsing method
    def _try_fallback_parsing(self, ai_response: str, current_step: str, user_message: str, user_context: Dict) -> Optional[Dict]:
        """Try to parse response using general fallback strategies"""
        # Try to extract any meaningful information from the response
        extracted_data = {}
        
        # Look for any JSON-like structure
        if '{' in ai_response and '}' in ai_response:
            try:
                # Try to extract JSON content
                start = ai_response.find('{')
                end = ai_response.rfind('}') + 1
                json_content = ai_response[start:end]
                
                # Try to parse as JSON
                parsed = json.loads(json_content)
                if isinstance(parsed, dict):
                    # Extract any valid fields
                    for key in ['action', 'confidence', 'language', 'quantity', 'yes_no']:
                        if key in parsed:
                            extracted_data[key] = parsed[key]
            except:
                pass
        
        # If we found some data, build a result
        if extracted_data:
            return self._build_fallback_result(extracted_data, current_step, user_message, user_context)
        
        # Last resort: use contextual inference
        return self._try_contextual_parsing(ai_response, current_step, user_message, user_context)

    # NEW: Enhanced response validation and monitoring system
    def _validate_and_monitor_response(self, ai_response: Dict, user_message: str, current_step: str, user_context: Dict) -> Dict:
        """Validate AI response and monitor performance metrics"""
        try:
            # Initialize monitoring data
            monitoring_data = {
                'timestamp': time.time(),
                'user_message': user_message,
                'current_step': current_step,
                'response_quality': 'unknown',
                'validation_issues': [],
                'performance_metrics': {}
            }
            
            # Validate response structure
            structure_validation = self._validate_response_structure(ai_response)
            if not structure_validation['valid']:
                monitoring_data['validation_issues'].extend(structure_validation['issues'])
                monitoring_data['response_quality'] = 'poor'
            
            # Validate response content
            content_validation = self._validate_response_content(ai_response, current_step, user_context)
            if not content_validation['valid']:
                monitoring_data['validation_issues'].extend(content_validation['issues'])
                monitoring_data['response_quality'] = 'poor'
            
            # Validate response logic
            logic_validation = self._validate_response_logic(ai_response, current_step, user_context)
            if not logic_validation['valid']:
                monitoring_data['validation_issues'].extend(logic_validation['issues'])
                monitoring_data['response_quality'] = 'poor'
            
            # Calculate response quality score
            quality_score = self._calculate_response_quality(ai_response, monitoring_data)
            monitoring_data['response_quality'] = quality_score['level']
            monitoring_data['quality_score'] = quality_score['score']
            
            # Update performance metrics
            self._update_performance_metrics(monitoring_data)
            
            # Log validation results
            if monitoring_data['validation_issues']:
                logger.warning(f"🔄 Response validation issues: {monitoring_data['validation_issues']}")
            else:
                logger.info(f"✅ Response validation passed with quality: {quality_score['level']}")
            
            # Add monitoring data to response
            ai_response['monitoring_data'] = monitoring_data
            
            return ai_response
            
        except Exception as e:
            logger.error(f"❌ Error in response validation and monitoring: {str(e)}")
            # Return response with basic monitoring data
            ai_response['monitoring_data'] = {
                'timestamp': time.time(),
                'response_quality': 'unknown',
                'validation_error': str(e)
            }
            return ai_response

    # NEW: Validate response structure
    def _validate_response_structure(self, ai_response: Dict) -> Dict:
        """Validate the structure of AI response"""
        validation_result = {
            'valid': True,
            'issues': []
        }
        
        # Check required fields
        required_fields = ['understood_intent', 'confidence', 'action', 'extracted_data']
        for field in required_fields:
            if field not in ai_response:
                validation_result['valid'] = False
                validation_result['issues'].append(f"Missing required field: {field}")
        
        # Check field types
        if 'extracted_data' in ai_response and not isinstance(ai_response['extracted_data'], dict):
            validation_result['valid'] = False
            validation_result['issues'].append("extracted_data must be a dictionary")
        
        if 'confidence' in ai_response and ai_response['confidence'] not in ['high', 'medium', 'low']:
            validation_result['valid'] = False
            validation_result['issues'].append("confidence must be 'high', 'medium', or 'low'")
        
        return validation_result

    # NEW: Validate response content
    def _validate_response_content(self, ai_response: Dict, current_step: str, user_context: Dict) -> Dict:
        """Validate the content of AI response"""
        validation_result = {
            'valid': True,
            'issues': []
        }
        
        # Validate action appropriateness for current step
        action = ai_response.get('action')
        if action:
            step_actions = self._get_valid_actions_for_step(current_step)
            if action not in step_actions:
                validation_result['valid'] = False
                validation_result['issues'].append(f"Action '{action}' not valid for step '{current_step}'")
        
        # Validate extracted data consistency
        extracted_data = ai_response.get('extracted_data', {})
        if extracted_data:
            data_validation = self._validate_extracted_data(extracted_data, current_step)
            if not data_validation['valid']:
                validation_result['valid'] = False
                validation_result['issues'].extend(data_validation['issues'])
        
        return validation_result

    # NEW: Validate response logic
    def _validate_response_logic(self, ai_response: Dict, current_step: str, user_context: Dict) -> Dict:
        """Validate the logic of AI response"""
        validation_result = {
            'valid': True,
            'issues': []
        }
        
        # Check for logical inconsistencies
        action = ai_response.get('action')
        extracted_data = ai_response.get('extracted_data', {})
        
        # Language selection logic
        if action == 'language_selection' and current_step != 'waiting_for_language':
            validation_result['valid'] = False
            validation_result['issues'].append("Language selection action not appropriate for current step")
        
        # Category selection logic
        if action == 'category_selection':
            if current_step == 'waiting_for_language':
                validation_result['valid'] = False
                validation_result['issues'].append("Category selection before language selection")
            elif 'category_id' in extracted_data and not extracted_data['category_id']:
                validation_result['valid'] = False
                validation_result['issues'].append("Category selection action without category_id")
        
        # Item selection logic
        if action == 'item_selection':
            if not user_context.get('selected_sub_category'):
                validation_result['valid'] = False
                validation_result['issues'].append("Item selection without sub-category selection")
            elif 'item_id' in extracted_data and not extracted_data['item_id']:
                validation_result['valid'] = False
                validation_result['issues'].append("Item selection action without item_id")
        
        return validation_result

    # NEW: Get valid actions for current step
    def _get_valid_actions_for_step(self, current_step: str) -> List[str]:
        """Get valid actions for the current step"""
        step_actions = {
            'waiting_for_language': ['language_selection', 'help_request'],
            'waiting_for_main_category': ['category_selection', 'show_menu', 'help_request', 'back_navigation'],
            'waiting_for_sub_category': ['category_selection', 'show_menu', 'help_request', 'back_navigation'],
            'waiting_for_item': ['item_selection', 'show_menu', 'help_request', 'back_navigation'],
            'waiting_for_quantity': ['quantity_selection', 'help_request', 'back_navigation'],
            'waiting_for_additional': ['yes_no', 'item_selection', 'help_request', 'back_navigation'],
            'waiting_for_service': ['service_selection', 'help_request', 'back_navigation'],
            'waiting_for_location': ['location_input', 'help_request', 'back_navigation'],
            'waiting_for_confirmation': ['confirmation', 'help_request', 'back_navigation']
        }
        
        return step_actions.get(current_step, ['help_request'])

    # NEW: Validate extracted data
    def _validate_extracted_data(self, extracted_data: Dict, current_step: str) -> Dict:
        """Validate extracted data for current step"""
        validation_result = {
            'valid': True,
            'issues': []
        }
        
        # Step-specific data validation
        if current_step == 'waiting_for_language':
            if 'language' in extracted_data and extracted_data['language'] not in ['arabic', 'english', None]:
                validation_result['valid'] = False
                validation_result['issues'].append("Invalid language value")
        
        elif current_step == 'waiting_for_quantity':
            if 'quantity' in extracted_data and extracted_data['quantity']:
                try:
                    quantity = int(extracted_data['quantity'])
                    if quantity <= 0 or quantity > 50:
                        validation_result['valid'] = False
                        validation_result['issues'].append("Quantity must be between 1 and 50")
                except (ValueError, TypeError):
                    validation_result['valid'] = False
                    validation_result['issues'].append("Quantity must be a valid number")
        
        elif current_step == 'waiting_for_additional':
            if 'yes_no' in extracted_data and extracted_data['yes_no'] not in ['yes', 'no', None]:
                validation_result['valid'] = False
                validation_result['issues'].append("yes_no must be 'yes', 'no', or null")
        
        return validation_result

    # NEW: Calculate response quality score
    def _calculate_response_quality(self, ai_response: Dict, monitoring_data: Dict) -> Dict:
        """Calculate quality score for AI response"""
        score = 100
        deductions = []
        
        # Deduct points for validation issues
        validation_issues = len(monitoring_data.get('validation_issues', []))
        score -= validation_issues * 10
        
        # Deduct points for low confidence
        confidence = ai_response.get('confidence', 'medium')
        if confidence == 'low':
            score -= 20
        elif confidence == 'medium':
            score -= 10
        
        # Deduct points for clarification needed
        if ai_response.get('clarification_needed', False):
            score -= 15
        
        # Deduct points for fallback usage
        if ai_response.get('fallback_used', False):
            score -= 25
        
        # Ensure score doesn't go below 0
        score = max(0, score)
        
        # Determine quality level
        if score >= 80:
            level = 'excellent'
        elif score >= 60:
            level = 'good'
        elif score >= 40:
            level = 'fair'
        elif score >= 20:
            level = 'poor'
        else:
            level = 'very_poor'
        
        return {
            'score': score,
            'level': level,
            'deductions': deductions
        }

    # NEW: Update performance metrics
    def _update_performance_metrics(self, monitoring_data: Dict) -> None:
        """Update performance metrics for AI processing"""
        try:
            # Initialize metrics if not exists
            if not hasattr(self, 'performance_metrics'):
                self.performance_metrics = {
                    'total_responses': 0,
                    'quality_scores': [],
                    'validation_issues': [],
                    'step_performance': {},
                    'error_patterns': {}
                }
            
            # Update basic metrics
            self.performance_metrics['total_responses'] += 1
            self.performance_metrics['quality_scores'].append(monitoring_data.get('quality_score', 0))
            
            # Keep only last 100 scores for rolling average
            if len(self.performance_metrics['quality_scores']) > 100:
                self.performance_metrics['quality_scores'] = self.performance_metrics['quality_scores'][-100:]
            
            # Update step performance
            current_step = monitoring_data.get('current_step', 'unknown')
            if current_step not in self.performance_metrics['step_performance']:
                self.performance_metrics['step_performance'][current_step] = {
                    'total_responses': 0,
                    'quality_scores': [],
                    'validation_issues': []
                }
            
            step_metrics = self.performance_metrics['step_performance'][current_step]
            step_metrics['total_responses'] += 1
            step_metrics['quality_scores'].append(monitoring_data.get('quality_score', 0))
            
            # Keep only last 50 scores per step
            if len(step_metrics['quality_scores']) > 50:
                step_metrics['quality_scores'] = step_metrics['quality_scores'][-50:]
            
            # Update validation issues
            if monitoring_data.get('validation_issues'):
                self.performance_metrics['validation_issues'].extend(monitoring_data['validation_issues'])
                step_metrics['validation_issues'].extend(monitoring_data['validation_issues'])
                
                # Keep only last 100 issues
                if len(self.performance_metrics['validation_issues']) > 100:
                    self.performance_metrics['validation_issues'] = self.performance_metrics['validation_issues'][-100:]
                if len(step_metrics['validation_issues']) > 50:
                    step_metrics['validation_issues'] = step_metrics['validation_issues'][-50:]
            
        except Exception as e:
            logger.error(f"❌ Error updating performance metrics: {str(e)}")

    # NEW: Get performance summary
    def get_performance_summary(self) -> Dict:
        """Get summary of AI performance metrics"""
        try:
            if not hasattr(self, 'performance_metrics'):
                return {'error': 'No performance data available'}
            
            metrics = self.performance_metrics
            
            # Calculate averages
            avg_quality = sum(metrics['quality_scores']) / len(metrics['quality_scores']) if metrics['quality_scores'] else 0
            
            # Step performance summary
            step_summary = {}
            for step, step_metrics in metrics['step_performance'].items():
                step_avg = sum(step_metrics['quality_scores']) / len(step_metrics['quality_scores']) if step_metrics['quality_scores'] else 0
                step_summary[step] = {
                    'total_responses': step_metrics['total_responses'],
                    'average_quality': round(step_avg, 2),
                    'validation_issues': len(step_metrics['validation_issues'])
                }
            
            return {
                'total_responses': metrics['total_responses'],
                'average_quality_score': round(avg_quality, 2),
                'step_performance': step_summary,
                'total_validation_issues': len(metrics['validation_issues']),
                'error_patterns': self.error_patterns,
                'conversation_memory_size': len(self.conversation_memory)
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting performance summary: {str(e)}")
            return {'error': str(e)}