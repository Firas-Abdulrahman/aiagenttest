# ai/prompts.py - FIXED to return proper JSON

"""
Fixed AI Prompts for Hef Cafe WhatsApp Bot - Ensures proper JSON responses
"""


# ai/prompts.py - FIXED VERSION

class AIPrompts:
    """Fixed AI prompts that return proper JSON"""

    SYSTEM_PROMPT = """You are an AI assistant for Hef Cafe's WhatsApp ordering bot..."""

    @staticmethod
    def get_understanding_prompt(user_message: str, current_step: str, context: dict) -> str:
        """Generate AI understanding prompt with context - FIXED VERSION"""
        return f"""
CURRENT SITUATION:
- User is at step: {current_step} ({context.get('step_description', 'Unknown step')})
- User said: "{user_message}"

CONTEXT:
{AIPrompts._format_context(context)}

SPECIAL RULES:
1. Convert Arabic numerals automatically: ١=1, ٢=2, ٣=3, ٤=4, ٥=5, ٦=6, ٧=7, ٨=8, ٩=9

{AIPrompts._get_step_specific_rules(current_step)}  # FIXED: Removed extra parameter

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

EXAMPLES FOR {current_step}:
{AIPrompts._get_examples_for_step(current_step)}"""

    # NEW: Enhanced understanding prompt with conversation context
    @staticmethod
    def get_enhanced_understanding_prompt(user_message: str, current_step: str, context: dict, conversation_history: list = None) -> str:
        """Generate enhanced AI understanding prompt with conversation context"""
        prompt = f"""
ENHANCED AI UNDERSTANDING PROMPT
================================

CURRENT SITUATION:
- User is at step: {current_step} ({context.get('step_description', 'Unknown step')})
- User said: "{user_message}"
- Language preference: {context.get('language_preference', 'arabic')}

CONTEXT:
{AIPrompts._format_context(context)}

CONVERSATION HISTORY (Last 5 exchanges):
{AIPrompts._format_conversation_history(conversation_history) if conversation_history else 'No conversation history available'}

USER PREFERENCES & PATTERNS:
{AIPrompts._format_user_preferences(context)}

STEP-SPECIFIC INTELLIGENCE:
{AIPrompts._get_enhanced_step_rules(current_step)}

MENU AWARENESS:
{AIPrompts._get_menu_intelligence(current_step, context)}

SPECIAL RULES:
1. Convert Arabic numerals automatically: ١=1, ٢=2, ٣=3, ٤=4, ٥=5, ٦=6, ٧=7, ٨=8, ٩=9
2. Consider conversation history for context
3. Use user preferences when available
4. Provide bilingual responses when appropriate

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

EXAMPLES FOR {current_step}:
{AIPrompts._get_examples_for_step(current_step)}

IMPORTANT: Use conversation history and user preferences to provide more accurate responses.
"""
        return prompt

    # NEW: Format conversation history for AI understanding
    @staticmethod
    def _format_conversation_history(conversation_history: list) -> str:
        """Format conversation history for AI understanding"""
        if not conversation_history:
            return "No conversation history available"
        
        formatted = []
        for i, exchange in enumerate(conversation_history[-5:], 1):  # Last 5 exchanges
            user_msg = exchange.get('user_message', '')[:80]  # First 80 chars
            ai_action = exchange.get('ai_result', {}).get('action', 'unknown')
            success = exchange.get('success', False)
            
            formatted.append(f"{i}. User: {user_msg}...")
            formatted.append(f"   AI Action: {ai_action} (success: {success})")
        
        return "\n".join(formatted)

    # NEW: Format user preferences and patterns
    @staticmethod
    def _format_user_preferences(context: dict) -> str:
        """Format user preferences and patterns for AI understanding"""
        preferences = []
        
        if context.get('language_preference'):
            preferences.append(f"- Language: {context['language_preference']}")
        
        if context.get('selected_main_category'):
            preferences.append(f"- Preferred main category: {context['selected_main_category']}")
        
        if context.get('selected_sub_category'):
            preferences.append(f"- Preferred sub-category: {context['selected_sub_category']}")
        
        if context.get('customer_name'):
            preferences.append(f"- Customer name: {context['customer_name']}")
        
        # Add any other preferences from context
        for key, value in context.items():
            if key.startswith('pref_') and value:
                preferences.append(f"- {key[5:]}: {value}")
        
        return "\n".join(preferences) if preferences else "No specific user preferences available"

    # NEW: Enhanced step rules with intelligence
    @staticmethod
    def _get_enhanced_step_rules(step: str) -> str:
        """Get enhanced step-specific rules with intelligence"""
        enhanced_rules = {
            'waiting_for_language': """
                ENHANCED LANGUAGE SELECTION RULES:
                - Detect if user is speaking Arabic or English
                - Arabic indicators: مرحبا, أهلا, هلا, عربي, العربية, سلام, صباح الخير
                - English indicators: hello, hi, hey, english, en, good morning, good afternoon
                - Look for cultural greetings and time-based greetings
                - Consider user's previous language preferences if available
                - If unclear, default to Arabic but offer both options
                - Response: Show main categories in detected language with bilingual options
            """,

            'waiting_for_main_category': """
                ENHANCED MAIN CATEGORY SELECTION RULES:
                - Accept numbers 1-3 for main categories
                - Accept category names: Cold Drinks, Hot Drinks, Pastries & Sweets
                - Arabic names: المشروبات الباردة, المشروبات الحارة, الحلويات والمعجنات
                - Keywords: cold, hot, pastry, sweets, بارد, حار, حلويات, معجنات
                - Look for mood indicators: "I'm tired" → Hot Drinks, "I'm hot" → Cold Drinks
                - Consider time of day: morning → Hot Drinks, afternoon → Cold Drinks
                - Look for health indicators: "I need energy" → Coffee, "I'm thirsty" → Cold Drinks
                - Response: Show sub-categories for selected main category
            """,

            'waiting_for_sub_category': """
                ENHANCED SUB-CATEGORY SELECTION RULES:
                - Accept numbers 1-N for sub-categories within the selected main category
                - Accept sub-category names based on main category
                - Look for specific preferences: "I want something sweet" → Frappuccino/Milkshakes
                - Consider temperature preferences: "I want it cold" → Iced options
                - Look for texture preferences: "I want something creamy" → Frappuccino/Lattes
                - Consider energy needs: "I need caffeine" → Coffee options
                - Response: Show items within selected sub-category
            """,

            'waiting_for_item': """
                ENHANCED ITEM SELECTION RULES:
                - Accept numbers 1-N for items within the selected sub-category
                - Accept item names (partial matching is fine)
                - Support both Arabic and English item names
                - Look for flavor preferences: "I want chocolate" → Chocolate items
                - Consider dietary preferences: "I don't want dairy" → Non-dairy options
                - Look for size preferences: "I want a large" → Large size options
                - Consider price sensitivity: "I want something affordable" → Lower price items
                - Response: Ask for quantity
            """,

            'waiting_for_quantity': """
                ENHANCED QUANTITY SELECTION RULES:
                - Numbers are ALWAYS quantities (1-50)
                - Support Arabic numerals: ١٢٣٤٥٦٧٨٩٠
                - Support English numerals: 1234567890
                - Support word numbers: خمسة, five, ثلاثة, three, عشرة, ten
                - Look for quantity indicators: "a lot", "many", "few", "كثير", "قليل"
                - Consider context: "for my family" → suggest higher quantities
                - Reject unreasonable quantities (>50)
                - Response: Ask if they want to add more items
            """,

            'waiting_for_additional': """
                ENHANCED ADDITIONAL SELECTION RULES:
                - Look for yes/no indicators: yes, no, نعم, لا, sure, of course
                - Consider user's order patterns and preferences
                - Look for specific requests: "I want a cake too", "add some pastries"
                - Suggest common additions based on their current order
                - Consider complementary items: coffee + pastry, cold drink + snack
                - Response: Process additional items or move to service selection
            """,

            'waiting_for_service': """
                ENHANCED SERVICE SELECTION RULES:
                - Accept dine-in/delivery preferences
                - Look for service indicators: "I want to eat here", "deliver to my home"
                - Consider user's previous service choices if available
                - Look for location indicators in the message
                - Consider time of day: late night → delivery, lunch time → dine-in
                - Response: Ask for location if delivery, or move to confirmation if dine-in
            """,

            'waiting_for_location': """
                ENHANCED LOCATION INPUT RULES:
                - Accept any location description: address, landmark, area name
                - Look for address components: street names, building numbers, areas
                - Consider user's previous delivery locations if available
                - Accept informal descriptions: "near the mall", "in the city center"
                - Support both Arabic and English location descriptions
                - Response: Confirm location and move to order summary
            """,

            'waiting_for_confirmation': """
                ENHANCED CONFIRMATION RULES:
                - Look for confirmation/denial: yes, no, confirm, cancel, نعم, لا, تأكيد
                - Consider user's order history and preferences
                - Look for modification requests: "change quantity", "add more items"
                - Provide clear confirmation options with order summary
                - Consider user's comfort level with the order
                - Response: Confirm order or handle modifications
            """
        }
        
        return enhanced_rules.get(step, AIPrompts._get_step_specific_rules(step))

    # NEW: Menu intelligence for better understanding
    @staticmethod
    def _get_menu_intelligence(step: str, context: dict) -> str:
        """Get menu intelligence for the current step"""
        intelligence = {
            'waiting_for_language': """
                MENU INTELLIGENCE:
                - We have 3 main categories: Cold Drinks, Hot Drinks, Food
                - Cold Drinks are popular in hot weather and afternoons
                - Hot Drinks are popular in mornings and cold weather
                - Food items are available throughout the day
            """,
            
            'waiting_for_main_category': """
                MENU INTELLIGENCE:
                - Category 1 (Cold Drinks): Iced Coffee, Frappuccino, Milkshakes, Iced Tea, Fresh Juices, Mojito, Energy Drinks
                - Category 2 (Hot Drinks): Coffee & Espresso, Lattes & Specialties, Other Hot Drinks
                - Category 3 (Food): Toast, Sandwiches, Croissants, Pies, Cake Slices
                - Cold drinks are refreshing and popular in warm weather
                - Hot drinks provide comfort and energy
                - Food items complement both drink categories
            """,
            
            'waiting_for_sub_category': """
                MENU INTELLIGENCE:
                - Each main category has 3-4 sub-categories
                - Sub-categories group similar items together
                - Consider user's mood and preferences when suggesting
                - Popular combinations: Coffee + Pastry, Cold Drink + Snack
            """,
            
            'waiting_for_item': """
                MENU INTELLIGENCE:
                - Items within sub-categories have different flavors and prices
                - Consider user's taste preferences and budget
                - Popular items: Iced Coffee, Frappuccino, Coffee & Espresso
                - Seasonal items may have special pricing
            """,
            
            'waiting_for_quantity': """
                MENU INTELLIGENCE:
                - Most items are priced per unit
                - Bulk orders may have special pricing
                - Consider user's needs: personal use vs. sharing
                - Popular quantities: 1 (personal), 2-3 (sharing), 5+ (events)
            """
        }
        
        return intelligence.get(step, "Use general menu knowledge for this step")

    @staticmethod
    def _get_step_specific_rules(step: str) -> str:  # FIXED: Only takes step parameter
        """Get step-specific rules for AI understanding"""
        rules = {
            'waiting_for_language': """
                LANGUAGE SELECTION RULES:
                - Detect if user is speaking Arabic or English
                - Arabic indicators: مرحبا, أهلا, هلا, عربي, العربية
                - English indicators: hello, hi, hey, english, en
                - If unclear, default to Arabic
                - Response: Show main categories in detected language
            """,

            'waiting_for_main_category': """
                MAIN CATEGORY SELECTION RULES:
                - Accept numbers 1-3 for main categories
                - Accept category names: Cold Drinks, Hot Drinks, Pastries & Sweets
                - Arabic names: المشروبات الباردة, المشروبات الحارة, الحلويات والمعجنات
                - Keywords: cold, hot, pastry, sweets, بارد, حار, حلويات, معجنات
                - Response: Show sub-categories for selected main category
            """,

            'waiting_for_sub_category': """
                SUB-CATEGORY SELECTION RULES:
                - Accept numbers 1-N for sub-categories within the selected main category
                - Accept sub-category names based on main category
                - Response: Show items within selected sub-category
            """,

            'waiting_for_item': """
                ITEM SELECTION RULES:
                - Accept numbers 1-N for items within the selected sub-category
                - Accept item names (partial matching is fine)
                - Support both Arabic and English item names
                - Response: Ask for quantity
            """,

            'waiting_for_quantity': """
                QUANTITY SELECTION RULES:
                - Numbers are ALWAYS quantities (1-50)
                - Support Arabic numerals: ١٢٣٤٥٦٧٨٩٠
                - Support English numerals: 1234567890
                - Support word numbers: خمسة, five, ثلاثة, three
                - Reject unreasonable quantities (>50)
                - Response: Ask if they want to add more items
            """,

            'waiting_for_additional': """
                ADDITIONAL ITEMS RULES:
                - 1 = Yes (add more items) → Go back to main categories
                - 2 = No (proceed to service) → Continue to service selection
                - Accept: نعم, لا, yes, no, ايوه, لا هاهية, هاهية لا
                - Response: Either show main categories again or proceed to service
            """,

            'waiting_for_service': """
                SERVICE SELECTION RULES:
                - 1 = Dine in (تناول في المقهى)
                - 2 = Delivery (توصيل)
                - Accept service type names and descriptions
                - Keywords: dine, delivery, توصيل, مقهى, في المقهى
                - Response: Ask for location/table number
            """,

            'waiting_for_location': """
                LOCATION SELECTION RULES:
                - For dine-in: Accept table numbers 1-7
                - For delivery: Accept address descriptions
                - Support Arabic numerals for table numbers
                - Keywords: طاولة, table, منضدة, address, عنوان
                - Response: Show order summary and ask for confirmation
            """,

            'waiting_for_confirmation': """
                ORDER CONFIRMATION RULES:
                - 1 = Yes (confirm order) → Complete order
                - 2 = No (cancel order) → Cancel and restart
                - Accept: نعم, لا, yes, no, تأكيد, إلغاء
                - Response: Complete order or cancel based on choice
            """
        }

        return rules.get(step, "No specific rules for this step.")

    @staticmethod
    def _get_examples_for_step(current_step: str) -> str:
        """Get specific examples for current step"""
        examples = {
            'waiting_for_language': '''
"1" → language_selection, language: "arabic"
"٢" → language_selection, language: "english"  
"عربي" → language_selection, language: "arabic"
"english" → language_selection, language: "english"
"مرحبا" → language_selection, language: "arabic"
''',
            'waiting_for_category': '''
"1" → category_selection, category_id: 1
"٧" → category_selection, category_id: 7
"موهيتو" → category_selection, category_id: 7, category_name: "موهيتو"
"frappuccino" → category_selection, category_id: 5, category_name: "فرابتشينو"
"toast" → category_selection, category_id: 9, category_name: "توست"
''',
            'waiting_for_item': '''
"1" → item_selection, item_id: 1
"٢" → item_selection, item_id: 2
"شاي مثلج بالليمون" → item_selection, item_name: "شاي مثلج بالليمون"
"lemon iced tea" → item_selection, item_name: "Iced Lemon Tea"
''',
            'waiting_for_quantity': '''
"٥" → quantity_selection, quantity: 5
"5" → quantity_selection, quantity: 5
"خمسة" → quantity_selection, quantity: 5
"five" → quantity_selection, quantity: 5
"10" → quantity_selection, quantity: 10
''',
            'waiting_for_additional': '''
"نعم" → yes_no, yes_no: "yes"
"1" → yes_no, yes_no: "yes"
"لا" → yes_no, yes_no: "no"
"2" → yes_no, yes_no: "no"
''',
            'waiting_for_service': '''
"1" → service_selection, service_type: "dine-in"
"dine in" → service_selection, service_type: "dine-in"
"في المقهى" → service_selection, service_type: "dine-in"
"2" → service_selection, service_type: "delivery"
"توصيل" → service_selection, service_type: "delivery"
''',
            'waiting_for_location': '''
"table 3" → location_input, location: "table 3"
"طاولة ٥" → location_input, location: "طاولة ٥"
"Baghdad, Karrada" → location_input, location: "Baghdad, Karrada"
''',
            'waiting_for_confirmation': '''
"نعم" → yes_no, yes_no: "yes"
"1" → yes_no, yes_no: "yes"  
"لا" → yes_no, yes_no: "no"
"cancel" → yes_no, yes_no: "no"
'''
        }

        return examples.get(current_step, "No specific examples")

    @staticmethod
    def _format_context(context: dict) -> str:
        """Format context for AI prompt"""
        import json
        return json.dumps(context, ensure_ascii=False, indent=2)

    @staticmethod
    def get_response_templates(language: str) -> dict:
        """Get response templates for different languages"""
        if language == 'arabic':
            return {
                'welcome': "مرحباً بك في مقهى هيف\n\nالرجاء اختيار لغتك المفضلة:\n1. العربية\n2. English",
                'categories': "ماذا تريد أن تطلب؟ الرجاء اختيار فئة بالرد بالرقم:",
                'items': "اكتب رقم المنتج أو اسمه",
                'quantity': "كم الكمية المطلوبة؟",
                'additional': "هل تريد إضافة المزيد من الأصناف؟\n\n1. نعم\n2. لا",
                'service': "هل تريد طلبك للتناول في المقهى أم للتوصيل؟\n\n1. تناول في المقهى\n2. توصيل",
                'location_dine': "الرجاء تحديد رقم الطاولة (1-7):",
                'location_delivery': "الرجاء مشاركة موقعك وأي تعليمات خاصة:",
                'confirmation': "هل تريد تأكيد هذا الطلب؟\n\n1. نعم\n2. لا",
                'order_complete': "شكراً لك! تم وضع طلبك بنجاح",
                'error': "عذراً، حدث خطأ. الرجاء إعادة المحاولة",
                'invalid_input': "الرجاء إدخال اختيار صحيح",
                'item_added': "تم إضافة المنتج إلى طلبك",
                'order_cancelled': "تم إلغاء الطلب. شكراً لك {customer_name} لزيارة مقهى هيف.\n\nيمكنك البدء بطلب جديد في أي وقت بإرسال 'مرحبا'"
            }
        else:
            return {
                'welcome': "Welcome to Hef Cafe\n\nPlease select your preferred language:\n1. العربية (Arabic)\n2. English",
                'categories': "What would you like to order? Please select a category by replying with the number:",
                'items': "Type the item number or name",
                'quantity': "How many would you like?",
                'additional': "Would you like to add more items?\n\n1. Yes\n2. No",
                'service': "Do you want your order for dine-in or delivery?\n\n1. Dine-in\n2. Delivery",
                'location_dine': "Please provide your table number (1-7):",
                'location_delivery': "Please share your location and any special instructions:",
                'confirmation': "Would you like to confirm this order?\n\n1. Yes\n2. No",
                'order_complete': "Thank you! Your order has been placed successfully",
                'error': "Sorry, something went wrong. Please try again",
                'invalid_input': "Please enter a valid choice",
                'item_added': "Item added to your order",
                'order_cancelled': "Order cancelled. Thank you {customer_name} for visiting Hef Cafe.\n\nYou can start a new order anytime by sending 'hello'"
            }

    @staticmethod
    def get_menu_display_template(language: str, categories: list) -> str:
        """Get menu display template"""
        if language == 'arabic':
            template = "القائمة الرئيسية:\n\n"
            for i, cat in enumerate(categories, 1):
                template += f"{i}. {cat['category_name_ar']}\n"
            template += "\nاختر الفئة المطلوبة"
        else:
            template = "Main Menu:\n\n"
            for i, cat in enumerate(categories, 1):
                template += f"{i}. {cat['category_name_en']}\n"
            template += "\nChoose the required category"

        return template

    @staticmethod
    def get_items_display_template(language: str, category_name: str, items: list) -> str:
        """Get items display template"""
        if language == 'arabic':
            template = f"قائمة {category_name}:\n\n"
            for i, item in enumerate(items, 1):
                template += f"{i}. {item['item_name_ar']}\n"
                template += f"   السعر: {item['price']} دينار\n\n"
            template += "اختر المنتج المطلوب"
        else:
            template = f"{category_name} Menu:\n\n"
            for i, item in enumerate(items, 1):
                template += f"{i}. {item['item_name_en']}\n"
                template += f"   Price: {item['price']} IQD\n\n"
            template += "Choose the required item"

        return template

    @staticmethod
    def get_order_summary_template(language: str, order: dict, location: str) -> str:
        """Get order summary template"""
        if language == 'arabic':
            template = "إليك ملخص طلبك:\n\n"
            template += "الأصناف:\n"
            for item in order['items']:
                template += f"• {item['item_name_ar']} × {item['quantity']} - {item['subtotal']} دينار\n"

            template += f"\nالخدمة: {order['details'].get('service_type', 'غير محدد')}\n"
            template += f"المكان: {location}\n"
            template += f"السعر الإجمالي: {order['total']} دينار\n\n"
            template += "هل تريد تأكيد هذا الطلب؟\n\n1. نعم\n2. لا"
        else:
            template = "Here is your order summary:\n\n"
            template += "Items:\n"
            for item in order['items']:
                template += f"• {item['item_name_en']} × {item['quantity']} - {item['subtotal']} IQD\n"

            template += f"\nService: {order['details'].get('service_type', 'Not specified')}\n"
            template += f"Location: {location}\n"
            template += f"Total Price: {order['total']} IQD\n\n"
            template += "Would you like to confirm this order?\n\n1. Yes\n2. No"

        return template

    @staticmethod
    def get_order_confirmation_template(language: str, order_id: str, total_amount: int) -> str:
        """Get order confirmation template - UPDATED to remove emojis and specific sentences"""
        if language == 'arabic':
            template = f"تم تأكيد طلبك بنجاح!\n\n"
            template += f"رقم الطلب: {order_id}\n"
            template += f"المبلغ الإجمالي: {total_amount} دينار\n\n"
            template += f"شكراً لك لاختيار مقهى هيف!"
        else:
            template = f"Your order has been confirmed successfully!\n\n"
            template += f"Order ID: {order_id}\n"
            template += f"Total Amount: {total_amount} IQD\n\n"
            template += f"Thank you for choosing Hef Cafe!"

        return template