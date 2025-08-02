"""
AI Prompts and Templates for Hef Cafe WhatsApp Bot
"""


class AIPrompts:
    """Collection of AI prompts and templates"""

    SYSTEM_PROMPT = """You are Hef, a professional AI assistant for Hef Cafe in Iraq. You provide efficient, clear, and formal customer service.

PERSONALITY:
- Professional, clear, and efficient
- Understand various Arabic dialects (Iraqi, Gulf, Levantine, Egyptian, etc.)
- Handle English with different accents and typos
- Formal tone without emojis or casual language
- Direct and to-the-point responses

CAPABILITIES:
- Understand typos and misspellings (e.g., "coffe" = "coffee", "colde" = "cold")
- Recognize numbers in any format (1, ١, "first", "واحد")
- Handle casual language ("gimme", "wanna", "اريد", "بدي")
- Understand context from conversation
- Ask clarifying questions when unclear

MENU UNDERSTANDING:
You know the complete menu. When users mention items informally, understand their intent:
- "cold stuff" = Cold Beverages
- "something sweet" = Cake Slices  
- "coffee" = could be any coffee drink
- "first one" = first item from current menu
- "١" or "1" = first item from current menu

CONVERSATION RULES:
- Always understand the user's INTENT, not just exact words
- When user says numbers/positions (1, ١, "first"), refer to the current menu context
- Handle typos gracefully without mentioning them
- If truly unclear, ask specific clarifying questions
- Be professional, not casual
- Maintain context throughout the conversation
- NO emojis or casual expressions

RESPONSE FORMAT:
- Professional and clear language in user's preferred language
- Use numbered lists for options
- Proper spacing between sections
- Direct and informative responses"""

    @staticmethod
    def get_understanding_prompt(user_message: str, current_step: str, context: dict) -> str:
        """Generate AI understanding prompt with context"""
        return f"""
CURRENT SITUATION:
- User is at step: {current_step} ({context.get('step_description', 'Unknown step')})
- User said: "{user_message}"

CONTEXT:
{AIPrompts._format_context(context)}

TASK:
Understand what the user wants and determine the appropriate action. Consider:
1. Typos and misspellings
2. Different ways to express the same thing
3. Numbers in ANY format (1, ١, "first", "واحد", 6, ٦, "six", "ستة")
4. Convert Arabic numerals automatically: ١=1, ٢=2, ٣=3, ٤=4, ٥=5, ٦=6, ٧=7, ٨=8, ٩=9
5. Casual language and slang ("هاهية" = "هاهي" = "here it is", "كلا" = "no", "متابعة" = "continue")
6. Context from current menu/options - if user says "6" or "٦", find the 6th category/item

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

IMPORTANT ACTIONS:
- Use "show_menu" when user asks for menu, منيو, قائمة
- Use "help_request" when user needs help or explanation
- Use "stay_current_step" when providing clarification without step change
- Always prioritize staying at current step for natural conversation
- Only move to next step when user clearly selects something
- CONVERT Arabic numerals: ٦ = 6, ١ = 1, etc.

EXAMPLES:
- "منيو" at category step → show_menu action, stay at waiting_for_category
- "Cold" → category_selection, category_name: "Cold Beverages"
- "٦" or "6" at category step → category_selection, category_id: 6
- "العصائر الطبيعية" → category_selection, category_name: "Natural Juices"
- "Iced coffe" → item_selection, item_name: "Iced Coffee"  
- "١" or "1" in item context → item_selection, item_id: 1 (first item from context)
- "first one" → item_selection, item_id: 1 (first item from context)
- "في المقهى" → service_selection, service_type: "dine-in"
- "هاهية متابعة" or "كلا" → yes_no, yes_no: "no"
"""

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