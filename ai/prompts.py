# ai/prompts.py - ENHANCED AI prompts for better understanding

"""
Enhanced AI Prompts for Hef Cafe WhatsApp Bot with better context understanding
"""


class AIPrompts:
    """Enhanced AI prompts with better context understanding"""

    SYSTEM_PROMPT = """You are Hef, a professional AI assistant for Hef Cafe in Iraq. You excel at understanding user intent in both Arabic and English.

CORE CAPABILITIES:
- Understand Arabic dialects (Iraqi, Gulf, Levantine, Egyptian, etc.)
- Handle English with various accents and typos
- Process Arabic numerals (١٢٣٤٥٦٧٨٩٠) and English numerals (1234567890)
- Understand context from conversation flow
- Recognize item names and category names in both languages

CRITICAL UNDERSTANDING RULES:
1. NUMBERS: Convert Arabic numerals automatically (١=1, ٢=2, ٣=3, ٤=4, ٥=5, ٦=6, ٧=7, ٨=8, ٩=9, ٠=0)
2. CONTEXT MATTERS: A number's meaning depends on the current step
3. QUANTITY CONTEXT: Numbers in quantity step are ALWAYS quantities, never language choices
4. CATEGORY NAMES: Recognize both Arabic and English category names
5. ITEM NAMES: Match partial item names intelligently

WORKFLOW STEPS UNDERSTANDING:
- waiting_for_language: Only accept 1/2 or clear language indicators
- waiting_for_category: Accept numbers 1-13 or category names
- waiting_for_item: Accept numbers 1-N or item names
- waiting_for_quantity: Numbers are ALWAYS quantities (1-50)
- waiting_for_additional: Accept yes/no responses
- waiting_for_service: Accept service type choices
- waiting_for_location: Accept location descriptions
- waiting_for_confirmation: Accept yes/no responses

MENU KNOWLEDGE:
Categories (1-13):
1. المشروبات الحارة / Hot Beverages
2. المشروبات الباردة / Cold Beverages  
3. الحلويات / Sweets
4. الشاي المثلج / Iced Tea
5. فرابتشينو / Frappuccino
6. العصائر الطبيعية / Natural Juices
7. موهيتو / Mojito
8. ميلك شيك / Milkshake
9. توست / Toast
10. سندويشات / Sandwiches
11. قطع الكيك / Cake Slices
12. كرواسان / Croissants
13. فطائر مالحة / Savory Pies

RESPONSE FORMAT:
- Always provide exactly ONE action
- Be helpful and professional
- Use appropriate language (Arabic/English)
- Provide clear, actionable responses"""

    @staticmethod
    def get_understanding_prompt(user_message: str, current_step: str, context: dict) -> str:
        """Generate enhanced AI understanding prompt with better context"""
        return f"""
ANALYZE THIS MESSAGE:
User Message: "{user_message}"
Current Step: {current_step}
Language: {context.get('language', 'arabic')}

CONTEXT INFORMATION:
Step Description: {context.get('step_description', 'Unknown')}
Available Categories: {len(context.get('available_categories', []))} categories
Current Category Items: {len(context.get('current_category_items', []))} items
Session Data: {context.get('session_data', {})}

CRITICAL ANALYSIS RULES:
1. CONVERT NUMERALS: ١=1, ٢=2, ٣=3, ٤=4, ٥=5, ٦=6, ٧=7, ٨=8, ٩=9, ٠=0
2. CONTEXT INTERPRETATION:
   - If step is "waiting_for_quantity" → numbers are ALWAYS quantities
   - If step is "waiting_for_language" → only 1/2 are language choices
   - If step is "waiting_for_category" → numbers 1-13 are category selections
   - If step is "waiting_for_item" → numbers refer to item positions

SPECIFIC STEP ANALYSIS:

{AIPrompts._get_step_specific_guidance(current_step, context)}

RESPOND WITH JSON:
{{
    "understood_intent": "clear description of user intent",
    "confidence": "high/medium/low",
    "action": "single_action_type",
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
    "clarification_question": "question if clarification needed",
    "response_message": "helpful response in user's language"
}}

EXAMPLES FOR CURRENT STEP ({current_step}):
{AIPrompts._get_examples_for_step(current_step)}

IMPORTANT:
- NEVER interpret quantities as language selections
- ALWAYS consider current step context
- Convert Arabic numerals before interpretation
- Provide helpful, contextual responses
"""

    @staticmethod
    def _get_step_specific_guidance(current_step: str, context: dict) -> str:
        """Get specific guidance for current step"""
        if current_step == 'waiting_for_language':
            return """
LANGUAGE STEP ANALYSIS:
- Only "1" or "١" = Arabic selection
- Only "2" or "٢" = English selection  
- Arabic words like "عربي", "العربية" = Arabic
- English words like "english", "انجليزي" = English
- Greetings like "مرحبا" = Arabic preference
- Greetings like "hello" = English preference
- IGNORE: Any other numbers (they don't mean language choice)
"""

        elif current_step == 'waiting_for_category':
            categories = context.get('available_categories', [])
            category_list = "\n".join([f"- {i+1} = {cat['category_name_ar']} / {cat['category_name_en']}"
                                     for i, cat in enumerate(categories)])
            return f"""
CATEGORY STEP ANALYSIS:
Available Categories:
{category_list}

- Numbers 1-13 refer to category positions
- Category names in Arabic or English are direct selections
- Keywords like "موهيتو", "فرابتشينو", "توست" match specific categories
"""

        elif current_step == 'waiting_for_item':
            items = context.get('current_category_items', [])
            if items:
                item_list = "\n".join([f"- {i+1} = {item['item_name_ar']} / {item['item_name_en']}"
                                     for i, item in enumerate(items)])
                return f"""
ITEM STEP ANALYSIS:
Available Items:
{item_list}

- Numbers 1-{len(items)} refer to item positions
- Item names in Arabic or English are direct selections
- Partial names are acceptable (e.g., "موهيتو الكلاسيكي" = "موهيتو كلاسيكي")
"""

        elif current_step == 'waiting_for_quantity':
            return """
QUANTITY STEP ANALYSIS:
- ANY NUMBER is a quantity (1-50 range typical)
- ٥ = 5 (quantity of 5 items)
- "خمسة" = 5 (quantity of 5 items)  
- "five" = 5 (quantity of 5 items)
- NEVER interpret as language choice or category
- CONTEXT: User is specifying how many items they want
"""

        elif current_step == 'waiting_for_additional':
            return """
ADDITIONAL ITEMS ANALYSIS:
- "نعم"/"yes"/"1"/"١" = wants more items
- "لا"/"no"/"2"/"٢" = no more items, proceed to service
- Context: User deciding if they want to add more items to order
"""

        elif current_step == 'waiting_for_service':
            return """
SERVICE TYPE ANALYSIS:
- "1"/"١"/"مقهى"/"داخل"/"هنا"/"dine"/"in" = dine-in
- "2"/"٢"/"توصيل"/"بيت"/"منزل"/"delivery"/"home" = delivery
- Context: User choosing where to consume their order
"""

        elif current_step == 'waiting_for_location':
            return """
LOCATION ANALYSIS:
- Any text describing a location/table/address
- Table numbers for dine-in (1-7)
- Address descriptions for delivery
- Context: User providing where they are or want delivery
"""

        elif current_step == 'waiting_for_confirmation':
            return """
CONFIRMATION ANALYSIS:
- "نعم"/"yes"/"1"/"١" = confirm order
- "لا"/"no"/"2"/"٢" = cancel order
- Context: Final order confirmation before processing
"""

        return "General analysis - determine intent based on message content"

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
"5" → language_selection with clarification (not a language choice)
''',
            'waiting_for_category': '''
"1" → category_selection, category_id: 1
"٧" → category_selection, category_id: 7
"موهيتو" → category_selection, category_id: 7, category_name: "موهيتو"
"frappuccino" → category_selection, category_id: 5, category_name: "فرابتشينو"
"toast" → category_selection, category_id: 9, category_name: "توست"
''',
            'waiting_for_item': '''
"1" → item_selection, item_id: 1 (first item from context)
"٢" → item_selection, item_id: 2 (second item from context)
"موهيتو كلاسيكي" → item_selection, item_name: "موهيتو كلاسيكي"
"classic mojito" → item_selection, item_name: "Classic Mojito"
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

        return examples.get(current_step, "No specific examples for this step")

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
                'order_cancelled': "تم إلغاء الطلب"
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
                'order_cancelled': "Order cancelled"
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
        """Get order confirmation template"""
        if language == 'arabic':
            template = f"شكراً لك! تم وضع طلبك بنجاح. سنقوم بإشعارك بمجرد أن يصبح جاهزاً.\n\n"
            template += f"تفاصيل الطلب:\n"
            template += f"رقم الطلب: {order_id}\n"
            template += f"السعر الإجمالي: {total_amount} دينار\n\n"
            template += f"مجموعك هو {total_amount} دينار. الرجاء دفع هذا المبلغ للكاشير عند المنضدة."
        else:
            template = f"Thank you! Your order has been placed successfully. We'll notify you once it's ready.\n\n"
            template += f"Order Details:\n"
            template += f"Order ID: {order_id}\n"
            template += f"Total Price: {total_amount} IQD\n\n"
            template += f"Your total is {total_amount} IQD. Please pay this amount to the cashier at the counter."

        return template