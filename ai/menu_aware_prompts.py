# ai/menu_aware_prompts.py
"""
Simple Menu Awareness Enhancement for AI Prompts
Makes the AI fully aware of the menu structure and able to understand natural language requests
"""
import logging

logger = logging.getLogger(__name__)


class MenuAwarePrompts:
    """Enhanced prompts with simple menu awareness"""

    @staticmethod
    def get_menu_context(database_manager) -> str:
        """Get comprehensive menu context for AI understanding"""
        try:
            # Get all menu data in a structured format
            main_categories = database_manager.get_main_categories()
            menu_context = "COMPLETE MENU KNOWLEDGE:\n"
            menu_context += "=" * 50 + "\n"

            for main_cat in main_categories:
                menu_context += f"\nMAIN CATEGORY {main_cat['id']}: {main_cat['name_ar']} / {main_cat['name_en']}\n"
                menu_context += "-" * 40 + "\n"

                # Get sub-categories
                sub_categories = database_manager.get_sub_categories(main_cat['id'])
                for sub_cat in sub_categories:
                    menu_context += f"   SUB-CATEGORY {sub_cat['id']}: {sub_cat['name_ar']} / {sub_cat['name_en']}\n"

                    # Get items with prices
                    items = database_manager.get_sub_category_items(sub_cat['id'])
                    item_count = 0
                    for item in items:
                        if item_count < 5:  # Show first 5 items per category
                            menu_context += f"      ITEM: {item['item_name_ar']} / {item['item_name_en']} - {item['price']} IQD\n"
                        item_count += 1

                    if len(items) > 5:
                        menu_context += f"      ... and {len(items) - 5} more items in this category\n"

                    menu_context += "\n"

            # Add intelligent attribute mapping for natural language understanding
            menu_context += """
INTELLIGENT UNDERSTANDING GUIDE:
================================

TEMPERATURE PREFERENCES:
- "cold", "iced", "chilled", "بارد", "مثلج", "منعش" → Main Category 1 (Cold Drinks)
- "hot", "warm", "heated", "حار", "ساخن", "دافئ" → Main Category 2 (Hot Drinks)

SWEETNESS PREFERENCES:
- "sweet", "sugar", "حلو", "حلويات", "سكر" → 
  * Drinks: Frappuccino (ID: 2), Milkshakes (ID: 3), Mojito (ID: 6)
  * Food: Cake Slices (ID: 15)
- "bitter", "strong", "قوي", "مر" → Coffee & Espresso (ID: 8)

ENERGY & MOOD:
- "energy", "wake up", "alert", "طاقة", "نشاط", "صحيان" → 
  * Iced Coffee (ID: 1), Coffee & Espresso (ID: 8), Energy Drinks (ID: 7)
- "refresh", "thirsty", "منعش", "عطشان" → 
  * Iced Tea (ID: 4), Fresh Juices (ID: 5), Mojito (ID: 6)
- "comfort", "relax", "مريح", "هادئ" → 
  * Other Hot Drinks (ID: 10), Lattes & Specialties (ID: 9)

DRINK TYPES:
- "coffee", "قهوة" → Iced Coffee (ID: 1), Coffee & Espresso (ID: 8), Lattes (ID: 9)
- "tea", "شاي" → Iced Tea (ID: 4), Other Hot Drinks (ID: 10)
- "juice", "عصير" → Fresh Juices (ID: 5)

FOOD PREFERENCES:
- "eat", "food", "hungry", "اكل", "طعام", "جوعان" → Main Category 3 (Pastries & Sweets)
- "savory", "salty", "مالح" → Toast (ID: 11), Sandwiches (ID: 12), Pies (ID: 14)
- "pastry", "bread", "معجنات", "خبز" → Croissants (ID: 13), Toast (ID: 11)

TEXTURE PREFERENCES:
- "creamy", "smooth", "كريمي", "ناعم" → Frappuccino (ID: 2), Milkshakes (ID: 3), Lattes (ID: 9)
- "fizzy", "bubbly", "غازي" → Mojito (ID: 6), Energy Drinks (ID: 7)
- "thick", "heavy", "ثقيل" → Milkshakes (ID: 3)

SPECIFIC FLAVORS:
- "chocolate", "شوكولاتة" → Look for chocolate items in Frappuccino, Milkshakes, Cake
- "vanilla", "فانيلا" → Look for vanilla items in Frappuccino, Milkshakes, Cake
- "caramel", "كراميل" → Look for caramel items in Frappuccino, Lattes
- "fruit", "فاكهة" → Fresh Juices (ID: 5), Iced Tea (ID: 4)

COMBINATION UNDERSTANDING:
- "cold + sweet" → Frappuccino (ID: 2) or Milkshakes (ID: 3)
- "cold + refreshing" → Iced Tea (ID: 4) or Mojito (ID: 6)
- "cold + energy" → Iced Coffee (ID: 1) or Energy Drinks (ID: 7)
- "hot + strong" → Coffee & Espresso (ID: 8)
- "hot + creamy" → Lattes & Specialties (ID: 9)
- "sweet + food" → Cake Slices (ID: 15)
- "savory + food" → Toast (ID: 11), Sandwiches (ID: 12), Pies (ID: 14)
"""

            return menu_context

        except Exception as e:
            logger.error(f"❌ Error building menu context: {e}")
            return f"Menu context error: {str(e)}"

    @staticmethod
    def get_enhanced_understanding_prompt(user_message: str, current_step: str, context: dict, database_manager) -> str:
        """Get enhanced understanding prompt with menu awareness and context"""
        try:
            # Get comprehensive menu context
            menu_context = MenuAwarePrompts.get_menu_context(database_manager)
            
            # Get user-specific context
            user_context = MenuAwarePrompts._build_user_context(context)
            
            # Get step-specific guidance
            step_guidance = MenuAwarePrompts._get_step_specific_guidance(current_step)
            
            prompt = f"""
ENHANCED MENU-AWARE AI UNDERSTANDING
====================================

CURRENT SITUATION:
- User is at step: {current_step}
- User said: "{user_message}"
- Language preference: {context.get('language_preference', 'arabic')}

USER CONTEXT:
{user_context}

STEP-SPECIFIC GUIDANCE:
{step_guidance}

COMPLETE MENU KNOWLEDGE:
{menu_context}

NATURAL LANGUAGE UNDERSTANDING RULES:
====================================

1. CONTEXT AWARENESS:
   - Consider user's current order progress
   - Use previous selections to guide understanding
   - Remember user's language preference
   - Consider time of day and weather context

2. INTENT RECOGNITION:
   - Look for explicit menu selections (numbers, names)
   - Detect implicit preferences (mood, weather, time)
   - Understand natural language requests
   - Handle multiple requests in one message

3. MENU MAPPING:
   - Map natural language to specific menu items
   - Consider category relationships
   - Handle synonyms and variations
   - Support both Arabic and English

4. VALIDATION:
   - Ensure selections are valid for current step
   - Check item availability
   - Validate quantities and options
   - Provide helpful error messages

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
    "menu_context_used": "specific menu elements that helped understanding",
    "suggested_alternatives": "alternative items if requested item unavailable"
}}

IMPORTANT: Use the complete menu knowledge to provide accurate and helpful responses.
"""
            return prompt
            
        except Exception as e:
            logger.error(f"Error generating enhanced menu-aware prompt: {e}")
            # Fallback to basic prompt
            return MenuAwarePrompts._get_basic_prompt(user_message, current_step, context)

    # NEW: Build user context for better understanding
    @staticmethod
    def _build_user_context(context: dict) -> str:
        """Build comprehensive user context for AI understanding"""
        user_context = []
        
        # Basic user info
        if context.get('customer_name'):
            user_context.append(f"- Customer: {context['customer_name']}")
        
        if context.get('language_preference'):
            user_context.append(f"- Language: {context['language_preference']}")
        
        # Current order progress
        if context.get('selected_main_category'):
            user_context.append(f"- Selected main category: {context['selected_main_category']}")
        
        if context.get('selected_sub_category'):
            user_context.append(f"- Selected sub-category: {context['selected_sub_category']}")
        
        if context.get('selected_item'):
            user_context.append(f"- Selected item: {context['selected_item']}")
        
        # Order context
        if context.get('current_order_items'):
            items = context['current_order_items']
            if items:
                user_context.append(f"- Current order has {len(items)} items")
                for item in items[-3:]:  # Show last 3 items
                    user_context.append(f"  * {item.get('name', 'Unknown')} x{item.get('quantity', 1)}")
        
        # Preferences and patterns
        if context.get('user_preferences'):
            prefs = context['user_preferences']
            for key, value in prefs.items():
                user_context.append(f"- Preference: {key} = {value}")
        
        return "\n".join(user_context) if user_context else "No specific user context available"

    # NEW: Get step-specific guidance with menu awareness
    @staticmethod
    def _get_step_specific_guidance(step: str) -> str:
        """Get step-specific guidance with menu awareness"""
        guidance = {
            'waiting_for_language': """
                LANGUAGE SELECTION WITH MENU AWARENESS:
                - Detect user's preferred language
                - Consider cultural context and greetings
                - Prepare to show menu in detected language
                - Remember language preference for future interactions
            """,
            
            'waiting_for_main_category': """
                MAIN CATEGORY SELECTION WITH MENU AWARENESS:
                - Show all 3 main categories clearly
                - Explain what each category contains
                - Consider user's mood and preferences
                - Suggest popular combinations
            """,
            
            'waiting_for_sub_category': """
                SUB-CATEGORY SELECTION WITH MENU AWARENESS:
                - Show relevant sub-categories for selected main category
                - Highlight popular items in each sub-category
                - Consider user's previous preferences
                - Suggest complementary items
            """,
            
            'waiting_for_item': """
                ITEM SELECTION WITH MENU AWARENESS:
                - Show all items in selected sub-category
                - Include prices and descriptions
                - Highlight popular and recommended items
                - Consider dietary preferences and restrictions
            """,
            
            'waiting_for_quantity': """
                QUANTITY SELECTION WITH MENU AWARENESS:
                - Accept various quantity formats
                - Suggest appropriate quantities based on item type
                - Consider sharing vs. personal use
                - Mention bulk pricing if applicable
            """,
            
            'waiting_for_additional': """
                ADDITIONAL ITEMS WITH MENU AWARENESS:
                - Suggest complementary items
                - Consider popular combinations
                - Mention special offers or deals
                - Respect user's budget and preferences
            """,
            
            'waiting_for_service': """
                SERVICE SELECTION WITH MENU AWARENESS:
                - Explain service options clearly
                - Consider time of day and availability
                - Mention delivery areas and timing
                - Consider user's previous service choices
            """,
            
            'waiting_for_location': """
                LOCATION INPUT WITH MENU AWARENESS:
                - Accept various location formats
                - Confirm delivery area coverage
                - Mention delivery time estimates
                - Consider user's previous delivery locations
            """,
            
            'waiting_for_confirmation': """
                ORDER CONFIRMATION WITH MENU AWARENESS:
                - Show complete order summary
                - Confirm all selections and quantities
                - Mention total cost and delivery fee if applicable
                - Provide modification options
            """
        }
        
        return guidance.get(step, "Use general menu guidance for this step")

    # NEW: Get basic prompt as fallback
    @staticmethod
    def _get_basic_prompt(user_message: str, current_step: str, context: dict) -> str:
        """Get basic prompt as fallback when enhanced prompt fails"""
        return f"""
BASIC AI UNDERSTANDING PROMPT
=============================

CURRENT SITUATION:
- User is at step: {current_step}
- User said: "{user_message}"
- Language preference: {context.get('language_preference', 'arabic')}

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
    "response_message": "natural response to user in their preferred language"
}}
"""

    @staticmethod
    def detect_natural_language_intent(user_message: str) -> dict:
        """Simple detection of natural language intents"""
        message_lower = user_message.lower().strip()

        intent = {
            'is_natural_request': False,
            'temperature': None,
            'sweetness': None,
            'energy': None,
            'food_request': None,
            'drink_type': None
        }

        # Check if this is a natural language request
        natural_indicators = [
            'i want', 'i need', 'something', 'اريد', 'بدي', 'شي', 'شيء',
            'give me', 'اعطني', 'احتاج', 'ممكن'
        ]

        if any(indicator in message_lower for indicator in natural_indicators):
            intent['is_natural_request'] = True

        # Temperature detection
        if any(word in message_lower for word in ['cold', 'iced', 'chilled', 'بارد', 'مثلج', 'منعش']):
            intent['temperature'] = 'cold'
        elif any(word in message_lower for word in ['hot', 'warm', 'حار', 'ساخن', 'دافئ']):
            intent['temperature'] = 'hot'

        # Sweetness detection
        if any(word in message_lower for word in ['sweet', 'sugar', 'حلو', 'حلويات', 'سكر']):
            intent['sweetness'] = 'sweet'
        elif any(word in message_lower for word in ['bitter', 'strong', 'قوي', 'مر']):
            intent['sweetness'] = 'bitter'

        # Energy/mood detection
        if any(word in message_lower for word in ['energy', 'wake up', 'alert', 'طاقة', 'نشاط', 'صحيان']):
            intent['energy'] = 'high'
        elif any(word in message_lower for word in ['refresh', 'thirsty', 'منعش', 'عطشان']):
            intent['energy'] = 'refreshing'
        elif any(word in message_lower for word in ['relax', 'comfort', 'مريح', 'هادئ']):
            intent['energy'] = 'calming'

        # Food vs drink detection
        if any(word in message_lower for word in ['eat', 'food', 'hungry', 'اكل', 'طعام', 'جوعان']):
            intent['food_request'] = True

        # Specific drink type detection
        if any(word in message_lower for word in ['coffee', 'قهوة']):
            intent['drink_type'] = 'coffee'
        elif any(word in message_lower for word in ['tea', 'شاي']):
            intent['drink_type'] = 'tea'
        elif any(word in message_lower for word in ['juice', 'عصير']):
            intent['drink_type'] = 'juice'

        return intent

    @staticmethod
    def map_intent_to_suggestions(intent: dict) -> dict:
        """Map detected intent to menu suggestions"""
        suggestions = {
            'main_category': None,
            'sub_categories': [],
            'confidence': 0.0,
            'reason': ''
        }

        # Food requests
        if intent.get('food_request'):
            suggestions['main_category'] = 3
            if intent.get('sweetness') == 'sweet':
                suggestions['sub_categories'] = [15]  # Cake Slices
                suggestions['reason'] = 'Sweet food option'
            else:
                suggestions['sub_categories'] = [11, 12, 14]  # Toast, Sandwiches, Pies
                suggestions['reason'] = 'Savory food options'
            suggestions['confidence'] = 0.8
            return suggestions

        # Drink requests based on temperature
        if intent.get('temperature') == 'cold':
            suggestions['main_category'] = 1

            if intent.get('sweetness') == 'sweet':
                suggestions['sub_categories'] = [2, 3]  # Frappuccino, Milkshakes
                suggestions['reason'] = 'Cold and sweet drinks'
                suggestions['confidence'] = 0.9
            elif intent.get('energy') == 'high':
                suggestions['sub_categories'] = [1, 7]  # Iced Coffee, Energy Drinks
                suggestions['reason'] = 'Cold energizing drinks'
                suggestions['confidence'] = 0.8
            elif intent.get('energy') == 'refreshing':
                suggestions['sub_categories'] = [4, 6]  # Iced Tea, Mojito
                suggestions['reason'] = 'Cold refreshing drinks'
                suggestions['confidence'] = 0.8
            else:
                suggestions['sub_categories'] = [1, 2, 3, 4, 5, 6, 7]  # All cold drinks
                suggestions['reason'] = 'Cold drink options'
                suggestions['confidence'] = 0.6

        elif intent.get('temperature') == 'hot':
            suggestions['main_category'] = 2

            if intent.get('sweetness') == 'bitter' or intent.get('energy') == 'high':
                suggestions['sub_categories'] = [8]  # Coffee & Espresso
                suggestions['reason'] = 'Strong hot coffee'
                suggestions['confidence'] = 0.8
            elif intent.get('energy') == 'calming':
                suggestions['sub_categories'] = [10]  # Other Hot Drinks
                suggestions['reason'] = 'Comforting hot drinks'
                suggestions['confidence'] = 0.7
            else:
                suggestions['sub_categories'] = [8, 9, 10]  # All hot drinks
                suggestions['reason'] = 'Hot drink options'
                suggestions['confidence'] = 0.6

        # Specific drink type requests
        if intent.get('drink_type') == 'coffee':
            if intent.get('temperature') == 'cold':
                suggestions['sub_categories'] = [1]  # Iced Coffee
            else:
                suggestions['sub_categories'] = [8, 9]  # Coffee & Espresso, Lattes
            suggestions['reason'] = 'Coffee options'
            suggestions['confidence'] = 0.8

        elif intent.get('drink_type') == 'tea':
            if intent.get('temperature') == 'cold':
                suggestions['sub_categories'] = [4]  # Iced Tea
            else:
                suggestions['sub_categories'] = [10]  # Other Hot Drinks
            suggestions['reason'] = 'Tea options'
            suggestions['confidence'] = 0.8

        elif intent.get('drink_type') == 'juice':
            suggestions['sub_categories'] = [5]  # Fresh Juices
            suggestions['reason'] = 'Fresh juice options'
            suggestions['confidence'] = 0.8

        return suggestions