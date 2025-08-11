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
    """Enhanced AI Processor with Deep Workflow Integration and Advanced Context Awareness"""

    def __init__(self, api_key: str = None, config: Dict = None, database_manager=None):
        self.api_key = api_key
        self.client = None
        self.database_manager = database_manager
        
        # Enhanced error tracking
        self.consecutive_failures = 0
        self.max_consecutive_failures = 5
        self.failure_window_start = None
        self.failure_window_duration = 300  # 5 minutes

        # Advanced context tracking
        self.user_preferences = {}  # Store user preferences across sessions
        self.conversation_memory = {}  # Enhanced conversation memory
        self.menu_insights = {}  # Menu popularity and combination insights

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
                logger.info("✅ Enhanced AI Processor initialized with advanced context awareness")
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
        Primary method for natural language understanding with advanced context awareness
        """
        if not self.is_available():
            logger.warning("Enhanced AI unavailable, using fallback")
            return self._generate_enhanced_fallback(user_message, current_step, user_context, language)

        try:
            # Pre-process message with advanced understanding
            processed_message = self._preprocess_message_advanced(user_message)
            
            # Build comprehensive enhanced context
            enhanced_context = self._build_enhanced_context_advanced(current_step, user_context, language)
            
            # Generate enhanced prompt with advanced features
            prompt = self._generate_enhanced_prompt_advanced(processed_message, current_step, enhanced_context)
            
            logger.info(f"🧠 Advanced AI analyzing: '{processed_message}' at step '{current_step}'")

            # Call OpenAI with enhanced parameters
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": self._get_enhanced_system_prompt_advanced()},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1500,  # Increased for more detailed responses
                temperature=0.4,  # Slightly higher for more creative understanding
                timeout=45,  # Increased timeout for complex processing
            )

            ai_response = response.choices[0].message.content.strip()
            
            # Parse and validate response with advanced validation
            result = self._parse_enhanced_response_advanced(ai_response, current_step, processed_message)
            
            if result:
                # Update user preferences and insights
                self._update_user_insights(user_context.get('phone_number'), result, user_message)
                
                # Enhance response with context and personalization
                result = self._enhance_response_with_context(result, user_context)
                
                # Check if steps can be skipped
                if self._should_skip_steps(result, current_step, user_context):
                    skip_suggestions = self._get_skip_suggestions(result, current_step)
                    if skip_suggestions:
                        result['skip_suggestions'] = skip_suggestions
                        result['can_skip_steps'] = True
                
                logger.info(f"✅ Advanced AI Understanding: {result.get('understood_intent', 'N/A')} "
                           f"(confidence: {result.get('confidence', 'N/A')}, action: {result.get('action', 'N/A')})")
                self._reset_failure_counter()
                return result
            else:
                logger.error("❌ Failed to parse advanced AI response")
                self._handle_ai_failure(Exception("Invalid advanced AI response format"))
                return self._generate_enhanced_fallback(user_message, current_step, user_context, language)

        except Exception as e:
            self._handle_ai_failure(e)
            return self._generate_enhanced_fallback(user_message, current_step, user_context, language)

    def _get_enhanced_system_prompt_advanced(self) -> str:
        """Get advanced system prompt for OpenAI with enhanced capabilities"""
        return """You are an intelligent WhatsApp bot for a café ordering system with ADVANCED CONTEXT AWARENESS and INTELLIGENT MENU UNDERSTANDING. Your role is to understand natural language requests and guide users through the ordering process with personalized recommendations.

ADVANCED CAPABILITIES:
1. **Intelligent Context Awareness**: Understand user preferences, order history, and conversation context
2. **Smart Menu Navigation**: Suggest optimal paths through the menu based on user needs
3. **Personalized Recommendations**: Learn from user behavior and provide tailored suggestions
4. **Multi-Intent Understanding**: Handle complex requests with multiple items or preferences
5. **Proactive Assistance**: Anticipate user needs and provide helpful shortcuts
6. **Seasonal & Time-Based Suggestions**: Consider time of day, weather, and seasonal preferences

CORE PRINCIPLES:
1. **Natural Language Understanding (NLU)**: Understand user intent regardless of how they express it
2. **Context Awareness**: Always consider the current conversation step, user's previous choices, and preferences
3. **Intelligent Suggestions**: Provide helpful suggestions based on user preferences, menu knowledge, and context
4. **Workflow Guidance**: Guide users through the ordering process step by step with smart shortcuts
5. **Cross-Step Item Selection**: Allow users to mention specific items at any step and intelligently route them
6. **Fresh Start Flow**: Handle post-order greetings with options to start new or keep previous order
7. **Personalization**: Remember user preferences and provide tailored experiences

DETAILED MENU STRUCTURE WITH INTELLIGENT INSIGHTS:
Main Category 1 - Cold Drinks (المشروبات الباردة):
  1. Iced Coffee (ايس كوفي) - Contains: Americano, Iced Coffee, Mocha, Latte variants
     * Popular combinations: Iced Coffee + Pastries, Iced Latte + Croissants
     * Best for: Morning energy, afternoon refreshment
  2. Frappuccino (فرابتشينو) - Contains: Various frappuccino flavors
     * Popular combinations: Frappuccino + Cake Slices, Frappuccino + Toast
     * Best for: Sweet cravings, social occasions
  3. Milkshake (ميلك شيك) - Contains: Various milkshake flavors
     * Popular combinations: Milkshake + Sandwiches, Milkshake + Croissants
     * Best for: Dessert replacement, comfort food
  4. Iced Tea (شاي مثلج) - Contains: Various iced tea types
     * Popular combinations: Iced Tea + Light Pastries, Iced Tea + Toast
     * Best for: Refreshing breaks, afternoon relaxation
  5. Fresh Juices (عصائر طازجة) - Contains: Orange, Apple, Mixed juices
     * Popular combinations: Juice + Healthy Pastries, Juice + Sandwiches
     * Best for: Health-conscious choices, morning nutrition
  6. Mojito (موهيتو) - Contains: Classic mojito variants
     * Popular combinations: Mojito + Appetizers, Mojito + Light Food
     * Best for: Social gatherings, evening refreshment
  7. Energy Drinks (مشروبات الطاقة) - Contains: Red Bull, Monster, etc.
     * Popular combinations: Energy Drinks + Quick Bites, Energy Drinks + Sandwiches
     * Best for: Work sessions, study breaks

Main Category 2 - Hot Drinks (المشروبات الحارة):
  1. Coffee & Espresso (قهوة واسبرسو) - Contains: Espresso, Turkish coffee, etc.
     * Popular combinations: Coffee + Pastries, Espresso + Croissants
     * Best for: Morning routine, work productivity
  2. Latte & Special Drinks (لاتيه ومشروبات خاصة) - Contains: Various latte types
     * Popular combinations: Latte + Sweet Pastries, Latte + Cake
     * Best for: Comfort moments, afternoon breaks
  3. Other Hot Drinks (مشروبات ساخنة أخرى) - Contains: Tea, hot chocolate, etc.
     * Popular combinations: Tea + Light Food, Hot Chocolate + Sweet Pastries
     * Best for: Relaxation, evening comfort

Main Category 3 - Pastries & Sweets (الحلويات والمعجنات):
  1. Toast (توست) - Contains: Various toast types
     * Popular combinations: Toast + Coffee, Toast + Juice
     * Best for: Breakfast, light meals
  2. Sandwiches (سندويشات) - Contains: Various sandwich types
     * Popular combinations: Sandwiches + Cold Drinks, Sandwiches + Hot Drinks
     * Best for: Lunch, substantial meals
  3. Croissants (كرواسان) - Contains: Various croissant types
     * Popular combinations: Croissants + Coffee, Croissants + Latte
     * Best for: Breakfast, morning treats
  4. Pastries (فطائر) - Contains: Various pastry types
     * Popular combinations: Pastries + Tea, Pastries + Hot Drinks
     * Best for: Afternoon tea, dessert
  5. Cake Pieces (قطع كيك) - Contains: Various cake pieces
     * Popular combinations: Cake + Coffee, Cake + Milkshakes
     * Best for: Dessert, celebrations

INTELLIGENT UNDERSTANDING FEATURES:
==================================

1. **User Preference Learning**:
   - Remember user's favorite categories and items
   - Learn from order patterns and combinations
   - Suggest based on previous successful orders

2. **Contextual Recommendations**:
   - Time of day suggestions (morning coffee, afternoon tea)
   - Weather-based recommendations (cold drinks on hot days)
   - Occasion-based suggestions (celebration cakes, comfort food)

3. **Smart Combinations**:
   - Suggest complementary items (coffee + pastry)
   - Recommend balanced meals (drink + food)
   - Avoid conflicting combinations

4. **Proactive Assistance**:
   - Suggest popular items for new users
   - Recommend seasonal specialties
   - Provide shortcuts for returning customers

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
    "response_message": "Brief response to user",
    "personalized_suggestions": ["suggestion1", "suggestion2"],
    "context_insights": "Brief insight about user's choice or preference"
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
- multi_item_selection: User wants multiple items in one request
- preference_learning: AI learns from user's choice for future recommendations

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
- PERSONALIZATION: Always provide personalized suggestions based on user context and preferences
- CONTEXT INSIGHTS: Include brief insights about why certain suggestions are made

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
    "response_message": "تم اختيار موهيتو. كم الكمية المطلوبة؟",
    "personalized_suggestions": ["موهيتو ازرق", "موهيتو فراولة", "موهيتو توت ازرق"],
    "context_insights": "Mojito is perfect for refreshing moments. Popular choice for social gatherings!"
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
    "response_message": "ممتاز! اختر من قائمة الحلويات والمعجنات",
    "personalized_suggestions": ["قطع كيك", "كرواسان", "فطائر"],
    "context_insights": "Sweet pastries are perfect for afternoon tea or dessert. Great choice for comfort food!"
}

User: "بالكهوة" (at service step)
Response: {
    "understood_intent": "User wants dine-in service",
    "confidence": "high",
    "action": "service_selection",
    "extracted_data": {
        "service_type": "dine-in"
    },
    "response_message": "ممتاز! تناول في المقهى. الرجاء تحديد رقم الطاولة",
    "personalized_suggestions": ["Table 1 (Window)", "Table 3 (Quiet corner)", "Table 5 (Central)"],
    "context_insights": "Dine-in service allows you to enjoy the café atmosphere and immediate service!"
}

User: "هاهية" (at confirmation step)
Response: {
    "understood_intent": "User confirms the order",
    "confidence": "high",
    "action": "confirmation",
    "extracted_data": {
        "yes_no": "yes"
    },
    "response_message": "تم تأكيد طلبك بنجاح!",
    "personalized_suggestions": ["Track your order", "Save favorites for next time"],
    "context_insights": "Great choice! Your order is being prepared with care."
}

User: "اوك" (at any yes/no step)
Response: {
    "understood_intent": "User confirms/agrees",
    "confidence": "high",
    "action": "yes_no",
    "extracted_data": {
        "yes_no": "yes"
    },
    "response_message": "ممتاز! المتابعة...",
    "personalized_suggestions": ["Next step", "Additional options"],
    "context_insights": "User is ready to proceed. Great engagement!"
}

User: "اريد شي بارد وحلو" (at category step)
Response: {
    "understood_intent": "User wants something cold and sweet",
    "confidence": "high",
    "action": "intelligent_suggestion",
    "extracted_data": {
        "suggested_main_category": 1,
        "suggested_sub_category": 2
    },
    "response_message": "فهمت أنك تريد شي بارد وحلو! ممتاز لإنعاش يومك. أنصحك بالفرابتشينو - بارد وحلو تماماً!",
    "personalized_suggestions": ["فرابتشينو كراميل", "فرابتشينو فانيلا", "ميلك شيك"],
    "context_insights": "Cold and sweet combination is perfect for hot days and sweet cravings. Frappuccinos are our most popular choice!"
}"""

    def _build_enhanced_context_advanced(self, current_step: str, user_context: Dict, language: str) -> Dict:
        """Build comprehensive enhanced context for AI understanding with advanced features"""
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
            'conversation_history': user_context.get('conversation_history', []),
            'phone_number': user_context.get('phone_number'),
            'customer_name': user_context.get('customer_name'),
            'time_of_day': self._get_time_of_day(),
            'user_preferences': self._get_user_preferences(user_context.get('phone_number')),
            'popular_combinations': self._get_popular_combinations(),
            'seasonal_suggestions': self._get_seasonal_suggestions()
        }

        # Add menu context if database manager is available
        if self.database_manager:
            try:
                context['menu_context'] = MenuAwarePrompts.get_menu_context(self.database_manager)
                context['menu_insights'] = self._get_menu_insights()
            except Exception as e:
                logger.warning(f"Could not get menu context: {e}")
                context['menu_context'] = "Menu context unavailable"
                context['menu_insights'] = {}

        return context

    def _get_time_of_day(self) -> str:
        """Get current time of day for contextual suggestions"""
        import datetime
        hour = datetime.datetime.now().hour
        
        if 5 <= hour < 12:
            return "morning"
        elif 12 <= hour < 17:
            return "afternoon"
        elif 17 <= hour < 21:
            return "evening"
        else:
            return "night"

    def _get_user_preferences(self, phone_number: str) -> Dict:
        """Get user preferences based on order history and behavior"""
        if not phone_number or phone_number not in self.user_preferences:
            return {}
        
        return self.user_preferences.get(phone_number, {})

    def _get_popular_combinations(self) -> List[Dict]:
        """Get popular item combinations for suggestions"""
        return [
            {"drink": "Coffee", "food": "Croissant", "popularity": "high"},
            {"drink": "Iced Tea", "food": "Toast", "popularity": "medium"},
            {"drink": "Frappuccino", "food": "Cake", "popularity": "high"},
            {"drink": "Milkshake", "food": "Sandwich", "popularity": "medium"}
        ]

    def _get_seasonal_suggestions(self) -> Dict:
        """Get seasonal suggestions based on current time"""
        import datetime
        month = datetime.datetime.now().month
        
        if month in [12, 1, 2]:  # Winter
            return {"hot_drinks": "high", "comfort_food": "high", "cold_drinks": "low"}
        elif month in [3, 4, 5]:  # Spring
            return {"fresh_juices": "high", "light_food": "high", "hot_drinks": "medium"}
        elif month in [6, 7, 8]:  # Summer
            return {"cold_drinks": "high", "refreshing_food": "high", "hot_drinks": "low"}
        else:  # Fall
            return {"warm_drinks": "high", "comfort_food": "medium", "cold_drinks": "medium"}

    def _get_menu_insights(self) -> Dict:
        """Get insights about menu popularity and trends"""
        return {
            "most_popular_categories": [1, 3, 2],  # Cold Drinks, Pastries, Hot Drinks
            "trending_items": ["موهيتو ازرق", "فرابتشينو كراميل", "كرواسان"],
            "best_combinations": ["Coffee + Croissant", "Iced Tea + Toast", "Frappuccino + Cake"]
        }

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

    def _generate_enhanced_prompt_advanced(self, user_message: str, current_step: str, context: Dict) -> str:
        """Generate enhanced prompt for natural language understanding with advanced features"""
        
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
        
        # Add advanced context features
        advanced_features = self._get_advanced_context_features(context)
        
        return f"""ENHANCED NATURAL LANGUAGE UNDERSTANDING REQUEST WITH ADVANCED CONTEXT AWARENESS
==================================================================================

MENU KNOWLEDGE:
{menu_context}

ADVANCED CONTEXT FEATURES:
{advanced_features}

CURRENT CONVERSATION STATE:
==========================
- Step: {current_step} ({context['step_description']})
- Language: {context['language']}
- User Message: "{user_message}"
- Time of Day: {context.get('time_of_day', 'unknown')}
- User Preferences: {self._format_user_preferences(context.get('phone_number'))}

STEP-SPECIFIC CONTEXT:
- Current Step: {current_step}
- Available Actions: {self._get_available_actions_for_step(current_step)}

CONVERSATION CONTEXT:
{conversation_context}

STEP-SPECIFIC GUIDANCE:
{step_guidance.get(current_step, "No specific guidance for this step")}

TASK: Analyze the user's message with advanced context awareness and provide intelligent understanding with appropriate action.

RESPOND WITH CLEAN JSON:
{{
    "understood_intent": "Clear description of what user wants",
    "confidence": "high/medium/low",
    "action": "intelligent_suggestion/language_selection/category_selection/item_selection/quantity_selection/yes_no/service_selection/location_input/confirmation/show_menu/help_request/back_navigation/conversational_response/multi_item_selection/preference_learning",
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
    "response_message": "Natural, helpful response in user's language with context and suggestions",
    "personalized_suggestions": ["suggestion1", "suggestion2"],
    "context_insights": "Brief insight about user's choice or preference",
    "can_skip_steps": false,
    "skip_suggestions": []
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
    "response_message": "فهمت أنك تريد مشروب بارد! ممتاز لإنعاش يومك. هذه خياراتنا للمشروبات الباردة:\\n\\n1. المشروبات الباردة\\n2. المشروبات الحارة\\n3. الحلويات والمعجنات\\n\\nاختر رقم 1 للمشروبات الباردة أو قل لي ما تفضل!",
    "personalized_suggestions": ["موهيتو", "ايس كوفي", "عصائر طازجة"],
    "context_insights": "Cold drinks are perfect for refreshing moments! Great choice for energy and refreshment."
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
    "response_message": "I understand you want something sweet! Great choice. I recommend our Frappuccinos - they're deliciously sweet and refreshing:\\n\\n1. Cold Drinks (includes Frappuccinos)\\n2. Hot Drinks\\n3. Pastries & Sweets\\n\\nChoose option 1 for cold sweet drinks or 3 for sweet pastries!",
    "personalized_suggestions": ["Frappuccino", "Milkshake", "Cake Slices"],
    "context_insights": "Sweet treats are perfect for satisfying cravings! Frappuccinos are our most popular sweet choice."
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
    "response_message": "ممتاز! سأجد لك موهيتو في قائمتنا وأحضره لك مباشرة.",
    "personalized_suggestions": ["موهيتو ازرق", "موهيتو فراولة", "موهيتو توت ازرق"],
    "context_insights": "Mojito is our most popular refreshing drink! Perfect for social gatherings and refreshing moments."
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
    "response_message": "Perfect! I'll find coffee in our menu and get it for you directly.",
    "personalized_suggestions": ["Iced Coffee", "Hot Coffee", "Latte"],
    "context_insights": "Coffee is perfect for energy and focus! Great choice for productivity and comfort."
}}

User: "4 iced tea" (at sub-category step)
Response: {{
    "understood_intent": "User wants to select sub-category number 4 (Iced Tea)",
    "confidence": "high",
    "action": "intelligent_suggestion",
    "extracted_data": {{
        "suggested_sub_category": 4
    }},
    "response_message": "Perfect! I'll show you the Iced Tea options.",
    "personalized_suggestions": ["Peach Iced Tea", "Passion Fruit Iced Tea"],
    "context_insights": "Iced Tea is perfect for refreshing breaks! Great choice for afternoon relaxation."
}}

User: "1" (at category step)
Response: {{
    "understood_intent": "User wants to select main category number 1 (Cold Drinks)",
    "confidence": "high",
    "action": "intelligent_suggestion",
    "extracted_data": {{
        "suggested_main_category": 1
    }},
    "response_message": "ممتاز! لقد اخترت المشروبات الباردة. الآن، إليك الخيارات المتاحة:\\n\\n1. ايس كوفي\\n2. فرابتشينو\\n3. ميلك شيك\\n4. شاي مثلج\\n5. عصائر طازجة\\n6. موهيتو\\n7. مشروبات الطاقة\\n\\nاختر رقم الفئة التي تفضلها!",
    "personalized_suggestions": ["موهيتو", "فرابتشينو", "ايس كوفي"],
    "context_insights": "Cold Drinks are perfect for refreshing moments! Great choice for energy and refreshment."
}}

User: "١" (Arabic numeral 1 at category step)
Response: {{
    "understood_intent": "User wants to select main category number 1 (Cold Drinks)",
    "confidence": "high",
    "action": "intelligent_suggestion",
    "extracted_data": {{
        "suggested_main_category": 1
    }},
    "response_message": "ممتاز! لقد اخترت المشروبات الباردة. الآن، إليك الخيارات المتاحة:\\n\\n1. ايس كوفي\\n2. فرابتشينو\\n3. ميلك شيك\\n4. شاي مثلج\\n5. عصائر طازجة\\n6. موهيتو\\n7. مشروبات الطاقة\\n\\nاختر رقم الفئة التي تفضلها!",
    "personalized_suggestions": ["موهيتو", "فرابتشينو", "ايس كوفي"],
    "context_insights": "Cold Drinks are perfect for refreshing moments! Great choice for energy and refreshment."
}}

User: "طاقة" (at sub-category step)
Response: {{
    "understood_intent": "User wants energy drinks",
    "confidence": "high",
    "action": "intelligent_suggestion",
    "extracted_data": {{
        "suggested_sub_category": 7
    }},
    "response_message": "فهمت أنك تريد مشروبات الطاقة! سأعرض لك خياراتنا من مشروبات الطاقة المتاحة",
    "personalized_suggestions": ["Red Bull", "Energy Mix", "Monster"],
    "context_insights": "Energy drinks are perfect for work sessions and study breaks! Great choice for productivity."
}}

User: "مشروب طاقة" (at item step)
Response: {{
    "understood_intent": "User wants an energy drink",
    "confidence": "high",
    "action": "item_selection",
    "extracted_data": {{
        "item_name": "مشروب طاقة"
    }},
    "response_message": "ممتاز! سأجد لك مشروب الطاقة في قائمتنا",
    "personalized_suggestions": ["Red Bull", "Energy Mix", "Monster"],
    "context_insights": "Energy drinks are perfect for work sessions and study breaks! Great choice for productivity."
}}

User: "1" (at service step)
Response: {{
    "understood_intent": "User wants dine-in service",
    "confidence": "high",
    "action": "service_selection",
    "extracted_data": {{
        "service_type": "dine-in"
    }},
    "response_message": "ممتاز! لقد اخترت التناول في المقهى. الرجاء تحديد رقم الطاولة (1-7):",
    "personalized_suggestions": ["Table 1 (Window)", "Table 3 (Quiet corner)", "Table 5 (Central)"],
    "context_insights": "Dine-in service allows you to enjoy the café atmosphere and immediate service! Great choice for social experience."
}}

User: "2" (at service step)
Response: {{
    "understood_intent": "User wants delivery service",
    "confidence": "high",
    "action": "service_selection",
    "extracted_data": {{
        "service_type": "delivery"
    }},
    "response_message": "ممتاز! لقد اخترت خدمة التوصيل. الرجاء مشاركة موقعك وأي تعليمات خاصة:",
    "personalized_suggestions": ["Home delivery", "Office delivery", "Special instructions"],
    "context_insights": "Delivery service brings our delicious items right to your location! Great choice for convenience."
}}

User: "رجوع" (at any step)
Response: {{
    "understood_intent": "User wants to go back to previous step",
    "confidence": "high",
    "action": "back_navigation",
    "extracted_data": {{}},
    "response_message": "سأعيدك إلى الخطوة السابقة",
    "personalized_suggestions": ["Previous step", "Alternative options"],
    "context_insights": "Going back helps you make the right choice! Great for exploring all options."
}}

User: "كيف الحال" (at confirmation step)
Response: {{
    "understood_intent": "User is making conversational comment",
    "confidence": "high",
    "action": "conversational_response",
    "extracted_data": {{}},
    "response_message": "الحمد لله، بخير! شكراً لسؤالك. الآن، هل تريد تأكيد طلبك؟\\n\\n1. نعم\\n2. لا",
    "personalized_suggestions": ["Confirm order", "Modify order"],
    "context_insights": "Great to hear you're doing well! Let's get your order confirmed and ready."
}}

User: "اريد شراب جوكلت بارد" (at sub-category step)
Response: {{
    "understood_intent": "User wants cold chocolate drink",
    "confidence": "high",
    "action": "intelligent_suggestion",
    "extracted_data": {{
        "suggested_sub_category": 2
    }},
    "response_message": "فهمت أنك تريد شراب شوكولاتة بارد! سأعرض لك خياراتنا من فرابتشينو:",
    "personalized_suggestions": ["Chocolate Frappuccino", "Iced Mocha", "Chocolate Milkshake"],
    "context_insights": "Cold chocolate drinks are perfect for sweet cravings! Great choice for indulgence and refreshment."
}}

User: "اين هي" (at any step)
Response: {{
    "understood_intent": "User is asking where something is",
    "confidence": "high",
    "action": "conversational_response",
    "extracted_data": {{}},
    "response_message": "عذراً على عدم الوضوح. دعني أعرض لك الخيارات المتاحة مرة أخرى.",
    "personalized_suggestions": ["Show menu", "Help options", "Popular items"],
    "context_insights": "Let me help you find exactly what you're looking for! Great to ask for clarification."
}}"""

    def _get_advanced_context_features(self, context: Dict) -> str:
        """Get advanced context features for enhanced understanding"""
        features = []
        
        # Time-based features
        time_of_day = context.get('time_of_day', '')
        if time_of_day:
            features.append(f"⏰ Time of Day: {time_of_day}")
        
        # User preferences
        user_prefs = context.get('user_preferences', {})
        if user_prefs:
            if user_prefs.get('favorite_categories'):
                features.append(f"❤️ Favorite Categories: {', '.join(map(str, user_prefs['favorite_categories']))}")
            if user_prefs.get('favorite_items'):
                features.append(f"⭐ Favorite Items: {', '.join(user_prefs['favorite_items'][:3])}")
        
        # Seasonal suggestions
        seasonal = context.get('seasonal_suggestions', {})
        if seasonal:
            features.append(f"🌤️ Seasonal Preferences: {', '.join([f'{k}={v}' for k, v in seasonal.items()])}")
        
        # Popular combinations
        popular = context.get('popular_combinations', [])
        if popular:
            combo_strings = []
            for item in popular[:3]:
                combo_strings.append(f"{item.get('drink', 'Unknown')}+{item.get('food', 'Unknown')}")
            features.append(f"🔥 Popular Combinations: {', '.join(combo_strings)}")
        
        return "\n".join(features) if features else "No advanced context features available"

    def _format_user_preferences(self, phone_number: str) -> str:
        """Format user preferences for display"""
        if not phone_number or phone_number not in self.user_preferences:
            return "No preferences available"
        
        prefs = self.user_preferences[phone_number]
        formatted = []
        
        if prefs.get('favorite_categories'):
            category_names = {1: "Cold Drinks", 2: "Hot Drinks", 3: "Pastries"}
            categories = [category_names.get(cat, f"Category {cat}") for cat in prefs['favorite_categories']]
            formatted.append(f"Favorite Categories: {', '.join(categories)}")
        
        if prefs.get('favorite_items'):
            formatted.append(f"Favorite Items: {', '.join(prefs['favorite_items'][:3])}")
        
        return "; ".join(formatted) if formatted else "No preferences available"

    def _format_conversation_context(self, context: Dict) -> str:
        """Format conversation context for AI prompt"""
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

    def _parse_enhanced_response_advanced(self, ai_response: str, current_step: str, user_message: str) -> Optional[Dict]:
        """Parse and validate enhanced AI response with advanced validation"""
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
            
            # Try to parse the JSON first without fixing
            try:
                result = json.loads(ai_response)
                logger.info(f"✅ JSON parsed successfully without fixing")
                logger.info(f"✨ Parsed result before validation: {result}")
                
                # Fix malformed structure where action is inside extracted_data
                if 'extracted_data' in result and isinstance(result['extracted_data'], dict):
                    extracted_data = result['extracted_data']
                    if 'action' in extracted_data and 'action' not in result:
                        # Move action from extracted_data to top level
                        result['action'] = extracted_data.pop('action')
                        logger.info(f"🔧 Fixed malformed structure: moved action to top level")
                    
                    if 'confidence' in extracted_data and 'confidence' not in result:
                        # Move confidence from extracted_data to top level
                        result['confidence'] = extracted_data.pop('confidence')
                        logger.info(f"🔧 Fixed malformed structure: moved confidence to top level")
                    
                    if 'understood_intent' in extracted_data and 'understood_intent' not in result:
                        # Move understood_intent from extracted_data to top level
                        result['understood_intent'] = extracted_data.pop('understood_intent')
                        logger.info(f"🔧 Fixed malformed structure: moved understood_intent to top level")
                
                # Validate required fields
                required_fields = ['understood_intent', 'confidence', 'action', 'extracted_data']
                for field in required_fields:
                    if field not in result:
                        logger.error(f"Missing required field: {field}")
                        return None
                
                # Validate for current step
                if not self._validate_enhanced_result(result, current_step, user_message):
                    logger.error(f"❌ Validation failed for step: {current_step}")
                    return None
                
                return result
            except json.JSONDecodeError:
                # Only fix JSON if it's actually invalid
                logger.info(f"⚠️ JSON parsing failed, attempting to fix...")
                ai_response = self._fix_json_format(ai_response)
                logger.info(f"🔧 Fixed JSON: {ai_response}")
                
                result = json.loads(ai_response)
                logger.info(f"✨ Parsed result after fixing and before validation: {result}")
                
                # Apply the same structure fixes after JSON fixing
                if 'extracted_data' in result and isinstance(result['extracted_data'], dict):
                    extracted_data = result['extracted_data']
                    if 'action' in extracted_data and 'action' not in result:
                        result['action'] = extracted_data.pop('action')
                        logger.info(f"🔧 Fixed malformed structure: moved action to top level")
                    
                    if 'confidence' in extracted_data and 'confidence' not in result:
                        result['confidence'] = extracted_data.pop('confidence')
                        logger.info(f"🔧 Fixed malformed structure: moved confidence to top level")
                    
                    if 'understood_intent' in extracted_data and 'understood_intent' not in result:
                        result['understood_intent'] = extracted_data.pop('understood_intent')
                        logger.info(f"🔧 Fixed malformed structure: moved understood_intent to top level")
            
            # Validate required fields
            required_fields = ['understood_intent', 'confidence', 'action', 'extracted_data']
            for field in required_fields:
                if field not in result:
                    logger.error(f"Missing required field: {field}")
                    return None
            
            # Validate for current step
            if not self._validate_enhanced_result(result, current_step, user_message):
                logger.error(f"❌ Validation failed for step: {current_step}")
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

    def _validate_enhanced_result(self, result: Dict, current_step: str, user_message: str) -> bool:
        """Validate enhanced AI result for current step"""
        action = result.get('action')
        extracted_data = result.get('extracted_data', {})
        
        # Step-specific validation
        validators = {
            'waiting_for_language': self._validate_language_step,
            'waiting_for_category': self._validate_category_step,
            'waiting_for_main_category': self._validate_category_step,
            'waiting_for_sub_category': self._validate_sub_category_step,
            'waiting_for_item': self._validate_item_step,
            'waiting_for_quantity': self._validate_quantity_step,
            'waiting_for_additional': self._validate_additional_step,
            'waiting_for_service': self._validate_service_step,
            'waiting_for_location': self._validate_location_step,
            'waiting_for_confirmation': self._validate_confirmation_step,
            'waiting_for_fresh_start_choice': self._validate_fresh_start_choice_step
        }
        
        validator = validators.get(current_step)
        if validator:
            # Always run step-specific validation, even for intelligent_suggestion
            return validator(result, extracted_data, user_message)
        
        # Accept intelligent suggestions and navigation actions if no step-specific validation
        if action in ['intelligent_suggestion', 'back_navigation', 'conversational_response']:
            return True
        
        return True

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
        """Generate enhanced fallback response when AI is unavailable with context awareness"""
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
        
        # Enhance fallback with context-aware suggestions
        fallback_result = self._enhance_fallback_with_context(fallback_result, user_context)
        
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

    def _preprocess_message_advanced(self, message: str) -> str:
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

    def _update_user_insights(self, phone_number: str, ai_result: Dict, user_message: str) -> None:
        """Update user preferences and insights based on AI result"""
        if not phone_number:
            return
        
        # Initialize user preferences if not exists
        if phone_number not in self.user_preferences:
            self.user_preferences[phone_number] = {
                'favorite_categories': [],
                'favorite_items': [],
                'preferred_combinations': [],
                'order_patterns': [],
                'last_interaction': time.time()
            }
        
        user_prefs = self.user_preferences[phone_number]
        
        # Update last interaction
        user_prefs['last_interaction'] = time.time()
        
        # Learn from category selection
        if ai_result.get('action') == 'category_selection':
            category_id = ai_result.get('extracted_data', {}).get('category_id')
            if category_id:
                if category_id not in user_prefs['favorite_categories']:
                    user_prefs['favorite_categories'].append(category_id)
                logger.info(f"📚 Learned user {phone_number} prefers category {category_id}")
        
        # Learn from item selection
        if ai_result.get('action') == 'item_selection':
            item_name = ai_result.get('extracted_data', {}).get('item_name')
            if item_name:
                if item_name not in user_prefs['favorite_items']:
                    user_prefs['favorite_items'].append(item_name)
                logger.info(f"📚 Learned user {phone_number} likes item: {item_name}")
        
        # Learn from intelligent suggestions
        if ai_result.get('action') == 'intelligent_suggestion':
            suggested_category = ai_result.get('extracted_data', {}).get('suggested_main_category')
            if suggested_category:
                if suggested_category not in user_prefs['favorite_categories']:
                    user_prefs['favorite_categories'].append(suggested_category)
                logger.info(f"📚 Learned user {phone_number} interested in category {suggested_category}")
        
        # Store order patterns
        if ai_result.get('action') in ['item_selection', 'category_selection']:
            pattern = {
                'action': ai_result.get('action'),
                'data': ai_result.get('extracted_data'),
                'timestamp': time.time()
            }
            user_prefs['order_patterns'].append(pattern)
            
            # Keep only last 10 patterns
            if len(user_prefs['order_patterns']) > 10:
                user_prefs['order_patterns'] = user_prefs['order_patterns'][-10:]

    def _get_personalized_suggestions(self, phone_number: str, current_step: str, context: Dict) -> List[str]:
        """Get personalized suggestions based on user preferences and context"""
        if not phone_number or phone_number not in self.user_preferences:
            return []
        
        user_prefs = self.user_preferences[phone_number]
        suggestions = []
        
        # Time-based suggestions
        time_of_day = context.get('time_of_day', '')
        if time_of_day == 'morning':
            suggestions.extend(['Coffee + Croissant', 'Fresh Juice + Toast', 'Iced Coffee'])
        elif time_of_day == 'afternoon':
            suggestions.extend(['Iced Tea + Light Pastry', 'Frappuccino + Cake', 'Mojito'])
        elif time_of_day == 'evening':
            suggestions.extend(['Hot Chocolate + Pastry', 'Tea + Cake', 'Warm Drinks'])
        
        # Preference-based suggestions
        if user_prefs.get('favorite_categories'):
            for category_id in user_prefs['favorite_categories'][:2]:  # Top 2 categories
                if category_id == 1:  # Cold Drinks
                    suggestions.extend(['Frappuccino', 'Iced Coffee', 'Mojito'])
                elif category_id == 2:  # Hot Drinks
                    suggestions.extend(['Coffee', 'Latte', 'Tea'])
                elif category_id == 3:  # Pastries
                    suggestions.extend(['Croissant', 'Cake', 'Toast'])
        
        # Popular combinations
        suggestions.extend(['Coffee + Pastry', 'Iced Tea + Light Food', 'Frappuccino + Cake'])
        
        # Remove duplicates and limit
        unique_suggestions = list(dict.fromkeys(suggestions))  # Preserve order
        return unique_suggestions[:5]  # Return top 5

    def _generate_context_insights(self, ai_result: Dict, user_context: Dict) -> str:
        """Generate contextual insights about user's choice"""
        action = ai_result.get('action')
        extracted_data = ai_result.get('extracted_data', {})
        
        insights = []
        
        # Category insights
        if action == 'category_selection':
            category_id = extracted_data.get('category_id')
            if category_id == 1:  # Cold Drinks
                insights.append("Cold drinks are perfect for refreshing moments!")
            elif category_id == 2:  # Hot Drinks
                insights.append("Hot drinks provide comfort and warmth!")
            elif category_id == 3:  # Pastries
                insights.append("Pastries are great for satisfying cravings!")
        
        # Item insights
        elif action == 'item_selection':
            item_name = extracted_data.get('item_name', '')
            if 'موهيتو' in item_name:
                insights.append("Mojito is our most popular refreshing drink!")
            elif 'فرابتشينو' in item_name:
                insights.append("Frappuccino is perfect for sweet cravings!")
            elif 'كرواسان' in item_name:
                insights.append("Croissants are ideal for breakfast or coffee pairing!")
        
        # Time-based insights
        time_of_day = user_context.get('time_of_day', '')
        if time_of_day == 'morning':
            insights.append("Great morning choice for energy and focus!")
        elif time_of_day == 'afternoon':
            insights.append("Perfect afternoon pick-me-up!")
        elif time_of_day == 'evening':
            insights.append("Excellent evening comfort choice!")
        
        # Combination insights
        if user_context.get('current_order_items'):
            insights.append("This pairs well with your current order!")
        
        return " ".join(insights) if insights else "Great choice! This is one of our favorites."

    def _enhance_response_with_context(self, ai_result: Dict, user_context: Dict) -> Dict:
        """Enhance AI response with personalized suggestions and context insights"""
        phone_number = user_context.get('phone_number')
        
        # Add personalized suggestions
        if phone_number:
            personalized_suggestions = self._get_personalized_suggestions(phone_number, ai_result.get('current_step', ''), user_context)
            ai_result['personalized_suggestions'] = personalized_suggestions
        
        # Add context insights
        context_insights = self._generate_context_insights(ai_result, user_context)
        ai_result['context_insights'] = context_insights
        
        # Enhance response message with insights
        if context_insights and ai_result.get('response_message'):
            enhanced_message = f"{ai_result['response_message']}\n\n💡 {context_insights}"
            ai_result['response_message'] = enhanced_message
        
        return ai_result

    def _detect_multi_intent(self, user_message: str) -> bool:
        """Detect if user message contains multiple intents"""
        multi_intent_indicators = [
            'و', 'and', 'مع', 'with', 'كمان', 'also', 'بالإضافة', 'in addition',
            'أريد', 'بدي', 'i want', 'need', 'احتاج', 'require'
        ]
        
        message_lower = user_message.lower()
        intent_count = 0
        
        for indicator in multi_intent_indicators:
            if indicator in message_lower:
                intent_count += 1
        
        return intent_count >= 2

    def _extract_multiple_items(self, user_message: str) -> List[Dict]:
        """Extract multiple items from a single user message"""
        items = []
        
        # Simple pattern matching for multiple items
        # This can be enhanced with more sophisticated NLP
        if 'و' in user_message or 'and' in user_message.lower():
            # Split by common conjunctions
            parts = user_message.replace('و', '|').replace('and', '|').split('|')
            
            for part in parts:
                part = part.strip()
                if part:
                    # Try to identify item type
                    item_info = self._identify_item_from_text(part)
                    if item_info:
                        items.append(item_info)
        
        return items

    def _identify_item_from_text(self, text: str) -> Optional[Dict]:
        """Identify item information from text"""
        text_lower = text.lower().strip()
        
        # Simple keyword matching - can be enhanced with AI
        if 'موهيتو' in text_lower:
            return {'type': 'drink', 'category': 'mojito', 'name': text.strip()}
        elif 'قهوة' in text_lower or 'coffee' in text_lower:
            return {'type': 'drink', 'category': 'coffee', 'name': text.strip()}
        elif 'كرواسان' in text_lower or 'croissant' in text_lower:
            return {'type': 'food', 'category': 'pastry', 'name': text.strip()}
        elif 'كيك' in text_lower or 'cake' in text_lower:
            return {'type': 'food', 'category': 'dessert', 'name': text.strip()}
        
        return None

    def _should_skip_steps(self, ai_result: Dict, current_step: str, user_context: Dict) -> bool:
        """Determine if steps can be skipped based on user input"""
        action = ai_result.get('action')
        
        # Skip to item selection if user mentions specific item
        if action == 'item_selection' and current_step in ['waiting_for_main_category', 'waiting_for_sub_category']:
            return True
        
        # Skip to quantity if user mentions both item and quantity
        if action == 'item_selection' and ai_result.get('extracted_data', {}).get('quantity'):
            return True
        
        # Skip to service type if user mentions service preference
        if action == 'service_selection' and current_step in ['waiting_for_main_category', 'waiting_for_sub_category', 'waiting_for_item', 'waiting_for_quantity', 'waiting_for_additional']:
            return True
        
        return False

    def _get_skip_suggestions(self, ai_result: Dict, current_step: str) -> List[str]:
        """Get suggestions for steps that can be skipped"""
        suggestions = []
        action = ai_result.get('action')
        
        if action == 'item_selection':
            if current_step == 'waiting_for_main_category':
                suggestions.append("I'll take you directly to item selection!")
            elif current_step == 'waiting_for_sub_category':
                suggestions.append("Great! Let me show you the specific items.")
        
        if action == 'service_selection':
            suggestions.append("I'll help you choose service type directly!")
        
        return suggestions

    def _enhance_fallback_with_context(self, fallback_result: Dict, user_context: Dict) -> Dict:
        """Enhance fallback response with context-aware suggestions"""
        phone_number = user_context.get('phone_number')
        
        if phone_number and phone_number in self.user_preferences:
            user_prefs = self.user_preferences[phone_number]
            
            # Add personalized fallback suggestions
            if user_prefs.get('favorite_categories'):
                favorite_category = user_prefs['favorite_categories'][0]
                category_names = {1: "المشروبات الباردة", 2: "المشروبات الحارة", 3: "الحلويات والمعجنات"}
                category_name = category_names.get(favorite_category, "المفضلة")
                
                fallback_result['personalized_suggestions'] = [f"جرب {category_name} - فئة مفضلة لديك"]
                fallback_result['context_insights'] = "Based on your preferences, I'm suggesting your favorite category"
        
        return fallback_result