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
            result = self._parse_enhanced_response(ai_response, current_step, processed_message, user_context)
            
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
- "ساخن" or "حار" or "مشروب ساخن" or "مشروبات ساخنة" or "هوت درينكز" or "هوت درينك" = Hot drinks (Main category 2)
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
- "اسبرسو" or "تركي" or "قهوة واسبرسو" or "coffee and espresso" or "coffee & espresso" = Coffee & Espresso (Sub-category 1 of Hot Drinks, Database ID: 8)
- "لاتيه" or "كابتشينو" or "latte" or "cappuccino" = Latte & Special Drinks (Sub-category 2 of Hot Drinks, Database ID: 9)

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
- multi_item_selection: User is selecting multiple items in one message (e.g., "واحد لاتيه فانيلا وواحد لاتيه كراميل")
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
- GREETING DETECTION: When user says greetings like "Hello", "Hi", "مرحبا", "أهلا", always detect the language and set it in extracted_data.language

CRITICAL CONTEXT-AWARE RULES:
1. **Intelligent Suggestion Context**: When user is already in a sub-category (waiting_for_sub_category step) and expresses preferences like "I'm very hungry", "I want something sweet", etc., suggest specific items within that sub-category, NOT the main category again.

2. **Mixed Input Priority**: When user provides mixed input like "نعم أريد الساندويت" (yes I want sandwich) at the waiting_for_sub_category step:
   - PRIORITIZE sub-category selection over yes/no interpretation
   - Extract "ساندويت" (sandwich) as sub_category_name
   - Use action "sub_category_selection" NOT "yes_no"
   - This applies to any mixed input where a sub-category name is mentioned

3. **Sub-Category Context Awareness**: Always check the current main category context before making suggestions:
   - If in Cold Drinks (Category 1): Only suggest sub-categories 1-7
   - If in Hot Drinks (Category 2): Only suggest sub-categories 1-3  
   - If in Pastries & Sweets (Category 3): Only suggest sub-categories 1-5

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

User: "latte" (at sub-category step for Hot Drinks)
Response: {
    "understood_intent": "User wants to select latte sub-category",
    "confidence": "high",
    "action": "sub_category_selection",
    "extracted_data": {
        "sub_category_id": 9,
        "sub_category_name": "Lattes & Specialties"
    },
    "response_message": "Great choice! Here are the latte options:\n\n1. Cappuccino - 5000 IQD\n2. Spanish Latte (Hot) - 6000 IQD\n3. Caramel Latte - 5000 IQD\n4. Vanilla Latte - 5000 IQD\n5. Hazelnut Latte - 5000 IQD\n6. Hef Latte - 6000 IQD\n\nPlease choose the number of the item you prefer!"
}

User: "نعم أريد الساندويت" (at waiting_for_sub_category step for Pastries & Sweets)
Response: {
    "understood_intent": "User wants to select sandwiches sub-category",
    "confidence": "high",
    "action": "sub_category_selection",
    "extracted_data": {
        "sub_category_id": 12,
        "sub_category_name": "Sandwiches"
    },
    "response_message": "Great choice! You've selected sandwiches. Here are the options available:\n\n1. Halloumi Cheese Sandwich - 3000 IQD\n2. Chicken Fajita Sandwich - 3000 IQD\n3. Diet Chicken & Veggies Sandwich - 3000 IQD\n4. Turkey Sandwich - 3000 IQD\n5. Roast Beef Sandwich - 3000 IQD\n\nPlease choose the number of the sandwich you prefer!"
}

User: "I'm very hungry" (at waiting_for_sub_category step for Pastries & Sweets)
Response: {
    "understood_intent": "User is hungry and wants food suggestions within current sub-category",
    "confidence": "high",
    "action": "intelligent_suggestion",
    "extracted_data": {
        "suggested_sub_category": 2
    },
    "response_message": "I understand you're very hungry! Since you're in the Pastries & Sweets category, I recommend our delicious sandwiches - they're perfect for satisfying hunger:\n\n1. Halloumi Cheese Sandwich - 3000 IQD\n2. Chicken Fajita Sandwich - 3000 IQD\n3. Diet Chicken & Veggies Sandwich - 3000 IQD\n4. Turkey Sandwich - 3000 IQD\n5. Roast Beef Sandwich - 3000 IQD\n\nPlease choose the number of the sandwich you prefer!"
}

User: "٥" (at waiting_for_sub_category step for Cold Drinks)
Response: {
    "understood_intent": "User wants to select sub-category number 5",
    "confidence": "high",
    "action": "sub_category_selection",
    "extracted_data": {
        "sub_category_id": 5,
        "sub_category_name": "عصائر طازجة"
    },
    "response_message": "ممتاز! سأعرض لك قائمة العصائر الطازجة:\n\n1. عصير برتقال طازج - 3000 دينار\n2. عصير تفاح طازج - 3000 دينار\n3. عصير جزر طازج - 3000 دينار\n\nاختر الرقم الذي تفضله!"
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
}

User: "Hello" (at language step)
Response: {
    "understood_intent": "User is greeting and initiating conversation",
    "confidence": "high",
    "action": "language_selection",
    "extracted_data": {
        "language": "english"
    },
    "response_message": "Hello! Please select your language preference:\n1. Arabic\n2. English"
}

User: "مرحبا" (at language step)
Response: {
    "understood_intent": "User is greeting and initiating conversation",
    "confidence": "high",
    "action": "language_selection",
    "extracted_data": {
        "language": "arabic"
    },
    "response_message": "مرحبا! الرجاء اختيار لغتك المفضلة:\n1. العربية\n2. English"
}"""

    def _build_enhanced_context(self, current_step: str, user_context: Dict, language: str) -> Dict:
        """Build comprehensive context for AI understanding with enhanced menu awareness"""
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

        # ENHANCED FIX: Add comprehensive menu context for better AI understanding
        if self.database_manager:
            try:
                # Get basic menu context
                context['menu_context'] = MenuAwarePrompts.get_menu_context(self.database_manager)
                
                # Add comprehensive item list for AI-driven matching
                if current_step in ['waiting_for_quick_order', 'waiting_for_item']:
                    all_items = self._get_all_menu_items()
                    context['all_available_items'] = all_items
                    context['item_matching_context'] = self._format_items_for_ai(all_items, language)
                    
                # Add category-specific items if available
                if user_context.get('current_category_items'):
                    context['current_category_items'] = user_context.get('current_category_items')
                    context['category_item_matching'] = self._format_items_for_ai(user_context.get('current_category_items'), language)
                    
                # CRITICAL FIX: Add quick order mode context to prevent intelligent suggestions
                if current_step == 'waiting_for_quick_order':
                    context['quick_order_mode'] = True
                    context['quick_order_instructions'] = """
                    QUICK ORDER MODE - CRITICAL INSTRUCTIONS:
                    - User is in QUICK ORDER mode - they know what they want
                    - User wants to place a DIRECT ORDER, not browse categories
                    - DO NOT suggest categories or ask for preferences
                    - DO NOT use 'intelligent_suggestion' action
                    - Extract item name and quantity directly from their message
                    - Use 'item_selection' action for single items
                    - Use 'multi_item_selection' action for multiple items
                    - Response should confirm the item selection and proceed to quantity
                    """
                    
            except Exception as e:
                logger.warning(f"Could not get enhanced menu context: {e}")
                context['menu_context'] = "Menu context unavailable"

        return context
    
    def _get_all_menu_items(self) -> List[Dict]:
        """Get all menu items for AI context"""
        try:
            all_items = []
            main_categories = self.database_manager.get_main_categories()
            
            for category in main_categories:
                sub_categories = self.database_manager.get_sub_categories(category['id'])
                for sub_category in sub_categories:
                    items = self.database_manager.get_sub_category_items(sub_category['id'])
                    all_items.extend(items)
            
            return all_items
        except Exception as e:
            logger.warning(f"Could not get all menu items: {e}")
            return []
    
    def _format_items_for_ai(self, items: List[Dict], language: str) -> str:
        """Format items for AI understanding with variations and synonyms"""
        if not items:
            return "No items available"
        
        formatted_items = []
        for item in items:
            item_name = item.get('item_name_ar' if language == 'arabic' else 'item_name_en', '')
            item_id = item.get('id', '')
            price = item.get('price', '')
            
            # Add common variations and synonyms
            variations = self._get_item_variations(item_name, language)
            
            formatted_items.append(f"ID: {item_id} | Name: {item_name} | Price: {price} | Variations: {', '.join(variations)}")
        
        return "\n".join(formatted_items)
    
    def _get_item_variations(self, item_name: str, language: str) -> List[str]:
        """Get common variations and synonyms for an item"""
        variations = [item_name.lower()]
        
        # Common misspellings and variations
        if language == 'arabic':
            # Arabic variations
            if 'عصير' in item_name:
                variations.extend(['عصير', 'عصير', 'عصير'])
            if 'فراولة' in item_name:
                variations.extend(['فراوله', 'فراول', 'فراوله'])
            if 'توست' in item_name:
                variations.extend(['تست', 'توس', 'تست'])
            if 'قهوة' in item_name:
                variations.extend(['قهوه', 'قهو', 'قهو'])
        else:
            # English variations
            if 'juice' in item_name.lower():
                variations.extend(['juice', 'juice', 'juice'])
            if 'strawberry' in item_name.lower():
                variations.extend(['strawbery', 'strawberi', 'strawber'])
            if 'toast' in item_name.lower():
                variations.extend(['toas', 'tost', 'toas'])
            if 'coffee' in item_name.lower():
                variations.extend(['coffe', 'cofee', 'cofe'])
        
        return list(set(variations))  # Remove duplicates

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
                
                - CRITICAL MIXED INPUT HANDLING: When user provides mixed input like "نعم أريد الساندويت" (yes I want sandwich):
                  * PRIORITIZE sub-category selection over yes/no interpretation
                  * Extract "ساندويت" (sandwich) as sub_category_name
                  * Use action "sub_category_selection" NOT "yes_no"
                  * This applies to any mixed input where a sub-category name is mentioned
                
                - CONTEXT-AWARE INTELLIGENT SUGGESTIONS: When user expresses preferences like "I'm very hungry", "I want something sweet":
                  * If in Pastries & Sweets: Suggest specific sub-categories (e.g., sandwiches for hunger)
                  * If in Hot Drinks: Suggest specific sub-categories (e.g., lattes for sweet drinks)
                  * If in Cold Drinks: Suggest specific sub-categories (e.g., frappuccinos for sweet drinks)
                  * NEVER suggest the main category again when already in a sub-category context
                
                - CRITICAL: When user provides a number at waiting_for_sub_category step, ALWAYS use action "sub_category_selection" NOT "category_selection"
                - CRITICAL: Extract the number as sub_category_id (1-based index) NOT suggested_main_category
                - IMPORTANT: If user provides mixed input like "4 iced tea", extract the number (4) for sub-category selection
                - If user asks for specific item (e.g., "موهيتو", "coffee", "iced tea"), use action "item_selection"
                - If user asks for sub-category type (e.g., "عصائر", "hot drinks"), use action "intelligent_suggestion"
                - If user provides just a number, use action "sub_category_selection" with sub_category_id
                - NEVER suggest sub-category numbers higher than 7 for Cold Drinks or 3 for Hot Drinks
                - Response: For items, directly show quantity selection; for categories, show sub-category items
            """,
            
            'waiting_for_item': """
                - Accept: numbers (which are item IDs), item names, descriptions.
                - CRITICAL: If user provides a number (including Arabic numerals ١,٢,٣,٤,٥,٦,٧,٨,٩,٠), it is ALWAYS an item ID for selection.
                - CRITICAL: NEVER interpret numbers as yes/no responses at this step.
                - CRITICAL: Numbers like "٢" (Arabic 2) should be converted to "2" and treated as item selection.
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

    def _parse_enhanced_response(self, ai_response: str, current_step: str, user_message: str, user_context: Dict = None) -> Optional[Dict]:
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
                if not self._validate_enhanced_result(result, current_step, user_message, user_context):
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
            if not self._validate_enhanced_result(result, current_step, user_message, user_context):
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

    def _validate_enhanced_result(self, result: Dict, current_step: str, user_message: str, user_context: Dict = None) -> bool:
        """Validate enhanced AI result for current step"""
        action = result.get('action')
        extracted_data = result.get('extracted_data', {})
        
        # CRITICAL FIX: Always accept these actions regardless of step
        always_valid_actions = ['intelligent_suggestion', 'back_navigation', 'conversational_response', 'help_request']
        if action in always_valid_actions:
            return True
        
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
            'waiting_for_fresh_start_choice': self._validate_fresh_start_choice_step,
            'waiting_for_quick_order': self._validate_quick_order_step,
            'waiting_for_quick_order_quantity': self._validate_quick_order_quantity_step,
            'waiting_for_quick_order_service': self._validate_quick_order_service_step
        }
        
        validator = validators.get(current_step)
        if validator:
            # Run step-specific validation
            return validator(result, extracted_data, user_message, user_context)
        
        # If no step-specific validator, accept the result
        return True

    def _validate_quick_order_step(self, result: Dict, extracted_data: Dict, user_message: str, user_context: Dict = None) -> bool:
        """Validate quick order step"""
        action = result.get('action')
        valid_actions = ['item_selection', 'multi_item_selection', 'service_selection', 'location_input', 'conversational_response']
        
        # IMPORTANT: In quick order mode, users want to place DIRECT ORDERS
        # DO NOT allow intelligent_suggestion as it will show categories instead of processing the order
        if action == 'intelligent_suggestion':
            # Convert intelligent suggestion to item selection for quick order
            logger.info(f"🔄 Converting intelligent_suggestion to item_selection for quick order step")
            result['action'] = 'item_selection'
            
            # Extract item name from the user message
            item_name = user_message.strip()
            if user_context and user_context.get('language') == 'arabic':
                # For Arabic, use the message as item name
                extracted_data['item_name'] = item_name
                extracted_data['quantity'] = 1  # Default quantity
                result['understood_intent'] = f"User wants to order {item_name} (quick order mode)"
            else:
                # For English, use the message as item name
                extracted_data['item_name'] = item_name
                extracted_data['quantity'] = 1  # Default quantity
                result['understood_intent'] = f"User wants to order {item_name} (quick order mode)"
            
            result['extracted_data'] = extracted_data
            return True
        
        if action not in valid_actions:
            return False
        
        # For quick order, we accept any item selection or service-related actions
        return True
    
    def _validate_quick_order_quantity_step(self, result: Dict, extracted_data: Dict, user_message: str, user_context: Dict = None) -> bool:
        """Validate quick order quantity step"""
        action = result.get('action')
        valid_actions = ['quantity_selection', 'conversational_response']
        
        # If user is typing an item name instead of quantity, guide them
        if action == 'item_selection':
            # Convert to conversational response to guide user
            result['action'] = 'conversational_response'
            result['response_message'] = "الرجاء اختيار الكمية من الأزرار المعروضة أعلاه، أو اكتب رقم من 1 إلى 10."
            result['understood_intent'] = "User typed item name instead of quantity, need to guide them"
            return True
        
        if action not in valid_actions:
            return False
        return True
    
    def _validate_quick_order_service_step(self, result: Dict, extracted_data: Dict, user_message: str, user_context: Dict = None) -> bool:
        """Validate quick order service step"""
        action = result.get('action')
        valid_actions = ['service_selection', 'conversational_response']
        
        if action not in valid_actions:
            return False
        return True

    def _validate_language_step(self, result: Dict, extracted_data: Dict, user_message: str, user_context: Dict = None) -> bool:
        """Validate language selection step"""
        action = result.get('action')
        logger.debug(f"DEBUG: _validate_language_step - action: {action}, extracted_data: {extracted_data}")
        
        if action not in ['language_selection', 'intelligent_suggestion']:
            logger.debug(f"DEBUG: _validate_language_step - Invalid action: {action}")
            return False
        
        if action == 'language_selection':
            language = extracted_data.get('language')
            logger.debug(f"DEBUG: _validate_language_step - language: {language}")
            
            # If language is null or invalid, try to detect it from the user message
            if language not in ['arabic', 'english']:
                logger.info(f"🔧 Language not detected properly, attempting to detect from message: '{user_message}'")
                detected_language = self._detect_language_fallback(user_message)
                if detected_language:
                    logger.info(f"🔧 Auto-detected language: {detected_language} from message: '{user_message}'")
                    extracted_data['language'] = detected_language
                    result['extracted_data'] = extracted_data
                    return True
                else:
                    logger.debug(f"DEBUG: _validate_language_step - Could not detect language from: {user_message}")
                    return False
        
        logger.debug(f"DEBUG: _validate_language_step - Validation passed")
        return True

    def _validate_category_step(self, result: Dict, extracted_data: Dict, user_message: str, user_context: Dict = None) -> bool:
        """Validate category selection step with two-button interface support"""
        action = result.get('action')
        valid_actions = ['category_selection', 'quick_order_selection', 'explore_menu_selection', 'intelligent_suggestion', 'show_menu', 'help_request', 'conversational_response', 'language_selection', 'item_selection', 'multi_item_selection']
        
        if action not in valid_actions:
            return False
        
        # Define user_message_lower at the top for use in all checks
        user_message_lower = user_message.lower().strip()
        
        # Handle greetings at category step - treat as session reset
        if action == 'language_selection':
            # Convert language_selection to conversational_response for category step
            logger.info(f"🔄 Converting language_selection to conversational_response for category step")
            result['action'] = 'conversational_response'
            result['understood_intent'] = "User greeted at category step, should show interactive buttons"
            result['response_message'] = "مرحبا! يبدو أنك تريد البدء من جديد. الرجاء اختيار طريقة الطلب من الأزرار أدناه."
            result['show_interactive_buttons'] = True  # Flag to show interactive buttons
            return True
        
        # Handle quick_order text being interpreted as item_selection
        if action == 'item_selection' and user_message_lower in ['quick_order', 'الطلب السريع']:
            logger.info(f"🔄 Converting item_selection to quick_order_selection for '{user_message}'")
            result['action'] = 'quick_order_selection'
            result['understood_intent'] = "User wants to use quick order mode"
            result['extracted_data'] = {}
            return True
        
        # CRITICAL FIX: Handle direct item orders at category step
        if action in ['item_selection', 'multi_item_selection']:
            logger.info(f"🔄 Converting {action} to quick_order_selection for direct order: '{user_message}'")
            result['action'] = 'quick_order_selection'
            result['understood_intent'] = f"User wants to place a direct order: {user_message}"
            result['extracted_data'] = extracted_data  # Keep the extracted data for quick order processing
            result['direct_order'] = True  # Flag to indicate this is a direct order
            return True
        
        # Get order mode from context
        order_mode = user_context.get('order_mode') if user_context else None
        
        # Extra validation for numeric inputs at category step (for explore mode) - PRIORITY
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
        
        # Handle button clicks (only if not in explore mode) - SECONDARY
        if order_mode != 'explore' and user_message_lower in ['quick_order', 'الطلب السريع', '1', '١']:
            # Quick order selection
            result['action'] = 'quick_order_selection'
            result['understood_intent'] = "User wants to use quick order mode"
            result['extracted_data'] = extracted_data
            logger.info(f"🔧 Quick order selection detected: {user_message}")
            return True
        elif user_message_lower in ['explore_menu', 'استكشاف القائمة']:
            # Explore menu selection (allow even if already in explore mode to prevent loops)
            result['action'] = 'explore_menu_selection'
            result['understood_intent'] = "User wants to explore the menu"
            result['extracted_data'] = extracted_data
            logger.info(f"🔧 Explore menu selection detected: {user_message}")
            return True
        
        # Handle traditional category selection
        if action == 'category_selection':
            category_id = extracted_data.get('category_id')
            if category_id and (category_id < 1 or category_id > 3):
                return False
        
        return True

    def _validate_sub_category_step(self, result: Dict, extracted_data: Dict, user_message: str, user_context: Dict = None) -> bool:
        """Validate sub-category selection step"""
        action = result.get('action')
        # Accept explicit sub_category_selection in addition to others
        valid_actions = ['sub_category_selection', 'category_selection', 'item_selection', 'intelligent_suggestion', 'conversational_response']

        if action not in valid_actions:
            return False

        return True

    def _validate_item_step(self, result: Dict, extracted_data: Dict, user_message: str, user_context: Dict = None) -> bool:
        """Validate item selection step with multi-item support"""
        action = result.get('action')
        valid_actions = ['item_selection', 'multi_item_selection', 'category_selection', 'intelligent_suggestion', 'conversational_response']
        
        if action not in valid_actions:
            return False
        
        # ENHANCED FIX: Convert Arabic numerals to English for processing
        arabic_to_english = {
            '٠': '0', '١': '1', '٢': '2', '٣': '3', '٤': '4',
            '٥': '5', '٦': '6', '٧': '7', '٨': '8', '٩': '9'
        }
        
        user_message_lower = user_message.lower().strip()
        processed_message = user_message_lower
        
        for arabic, english in arabic_to_english.items():
            processed_message = processed_message.replace(arabic, english)
        
        # CRITICAL FIX: Enhanced validation for numeric inputs at item step
        if processed_message in ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10']:
            # Force correct interpretation for item step - NEVER interpret as yes/no
            forced_item_id = int(processed_message)
            
            # Override AI's incorrect interpretation
            extracted_data['item_id'] = forced_item_id  # Set item_id directly
            extracted_data['item_name'] = None  # Clear item_name if it was set by AI
            extracted_data['yes_no'] = None  # Clear any yes_no interpretation
            result['extracted_data'] = extracted_data
            result['action'] = 'item_selection'
            result['understood_intent'] = f"User wants to select item number {forced_item_id}"
            logger.info(f"🔧 CRITICAL FIX: Corrected item selection: '{user_message}' -> item_id={forced_item_id} (was incorrectly interpreted as yes_no)")
            return True
        
        # Check for multi-item indicators in the message
        if 'و' in user_message and ('واحد' in user_message or 'one' in user_message.lower()):
            # If AI didn't detect multi-item but message suggests it, fix it
            if action == 'item_selection':
                logger.info(f"🔧 Detected multi-item pattern in message, updating action")
                result['action'] = 'multi_item_selection'
                # Extract multiple items from the message
                multi_items = self._extract_multiple_items(user_message)
                if multi_items:
                    result['extracted_data']['multi_items'] = multi_items
                    result['understood_intent'] = f"User wants to order multiple items: {', '.join([item.get('item_name', '') for item in multi_items])}"
        
        return True
    
    def _extract_multiple_items(self, message: str) -> List[Dict]:
        """Extract multiple items from a message containing 'و' (and)"""
        items = []
        
        # Convert Arabic numerals to English for processing
        arabic_to_english = {
            '٠': '0', '١': '1', '٢': '2', '٣': '3', '٤': '4',
            '٥': '5', '٦': '6', '٧': '7', '٨': '8', '٩': '9'
        }
        
        processed_message = message
        for arabic, english in arabic_to_english.items():
            processed_message = processed_message.replace(arabic, english)
        
        # Split by 'و' (and) to get individual item requests
        parts = processed_message.split('و')
        
        for part in parts:
            part = part.strip()
            if not part:
                continue
                
            # Extract quantity and item name from each part
            quantity = 1  # Default quantity
            item_name = part
            
            # Look for quantity indicators (both Arabic words and numbers)
            quantity_patterns = {
                'واحد': 1, 'اثنين': 2, 'ثلاثة': 3, 'اربعة': 4, 'خمسة': 5,
                'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5
            }
            
            # First check for Arabic word quantities
            for pattern, qty in quantity_patterns.items():
                if pattern in part:
                    quantity = qty
                    # Remove quantity from item name
                    item_name = part.replace(pattern, '').strip()
                    break
            
            # If no word quantity found, look for numeric quantities
            if quantity == 1:
                import re
                numbers = re.findall(r'\d+', part)
                if numbers:
                    quantity = int(numbers[0])
                    # Remove the number from item name
                    item_name = re.sub(r'\d+', '', part).strip()
            
            # Clean up item name
            item_name = item_name.replace('اريد', '').replace('بدي', '').strip()
            
            # Handle common typos in mojito
            item_name = item_name.replace('موهيطة', 'موهيتو').replace('موهيطو', 'موهيتو')
            
            if item_name:
                items.append({
                    'item_name': item_name,
                    'quantity': quantity
                })
        
        return items

    def _validate_quantity_step(self, result: Dict, extracted_data: Dict, user_message: str, user_context: Dict = None) -> bool:
        """Validate quantity selection step with enhanced flexibility"""
        action = result.get('action')
        
        # Convert Arabic numerals to English for processing
        arabic_to_english = {
            '٠': '0', '١': '1', '٢': '2', '٣': '3', '٤': '4',
            '٥': '5', '٦': '6', '٧': '7', '٨': '8', '٩': '9'
        }
        
        processed_message = user_message
        for arabic, english in arabic_to_english.items():
            processed_message = processed_message.replace(arabic, english)
        
        # Extract number from message if AI didn't
        import re
        numbers = re.findall(r'\d+', processed_message)
        
        # If AI returned wrong action but we can extract quantity, fix it
        if action != 'quantity_selection' and numbers:
            quantity = int(numbers[0])
            if 1 <= quantity <= 50:
                logger.info(f"🔧 Fixing AI misinterpretation: {action} -> quantity_selection for quantity {quantity}")
                result['action'] = 'quantity_selection'
                result['extracted_data'] = {'quantity': quantity}
                result['understood_intent'] = f"User wants to specify a quantity of {quantity}"
                result['confidence'] = 'high'
                return True
        
        # Standard validation for correct action
        if action == 'quantity_selection':
            quantity = extracted_data.get('quantity')
            if isinstance(quantity, int) and 1 <= quantity <= 50:
                return True
            elif isinstance(quantity, str) and quantity.isdigit():
                # Convert string to int
                quantity_int = int(quantity)
                if 1 <= quantity_int <= 50:
                    result['extracted_data']['quantity'] = quantity_int
                    return True
        
        # If we have a clear number in the message, accept it even with wrong action
        if numbers:
            quantity = int(numbers[0])
            if 1 <= quantity <= 50:
                logger.info(f"🔧 Accepting quantity {quantity} from message despite AI action {action}")
                result['action'] = 'quantity_selection'
                result['extracted_data'] = {'quantity': quantity}
                result['understood_intent'] = f"User wants to specify a quantity of {quantity}"
                result['confidence'] = 'high'
                return True
        
        return False

    def _validate_additional_step(self, result: Dict, extracted_data: Dict, user_message: str, user_context: Dict = None) -> bool:
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

    def _validate_service_step(self, result: Dict, extracted_data: Dict, user_message: str, user_context: Dict = None) -> bool:
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

    def _validate_location_step(self, result: Dict, extracted_data: Dict, user_message: str, user_context: Dict = None) -> bool:
        """Validate location input step with enhanced table number validation"""
        action = result.get('action')
        
        # CRITICAL FIX: Allow more flexible actions for location step
        valid_actions = ['location_input', 'conversational_response', 'intelligent_suggestion']
        if action not in valid_actions:
            return False
        
        if action == 'location_input':
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

    def _validate_confirmation_step(self, result: Dict, extracted_data: Dict, user_message: str, user_context: Dict = None) -> bool:
        """Validate confirmation step"""
        action = result.get('action')
        
        # CRITICAL FIX: Allow more flexible actions for confirmation step
        valid_actions = ['yes_no', 'confirmation', 'conversational_response', 'intelligent_suggestion', 'back_navigation']
        if action not in valid_actions:
            return False
        
        if action == 'yes_no':
            yes_no = extracted_data.get('yes_no')
            if yes_no not in ['yes', 'no']:
                return False
        
        return True

    def _validate_fresh_start_choice_step(self, result: Dict, extracted_data: Dict, user_message: str, user_context: Dict = None) -> bool:
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
        
        # Arabic indicators (including greetings)
        arabic_indicators = ['عربي', 'العربية', 'مرحبا', 'أهلا', 'السلام', 'هلا', 'اريد', 'بدي', 'ممكن', 'شكرا']
        
        # English indicators (including greetings)
        english_indicators = ['english', 'hello', 'hi', 'hey', 'good morning', 'good afternoon', 'want', 'need', 'please', 'thanks']
        
        # Check for Arabic indicators first
        if any(indicator in message_lower for indicator in arabic_indicators):
            return 'arabic'
        
        # Check for English indicators
        if any(indicator in message_lower for indicator in english_indicators):
            return 'english'
        
        # Check for numeric selection
        if message_lower.strip() == '1':
            return 'arabic'
        elif message_lower.strip() == '2':
            return 'english'
        
        # Default to English for unknown input (since most voice input is in English)
        return 'english'

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