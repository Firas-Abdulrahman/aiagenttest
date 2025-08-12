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

MULTI-ITEM ORDER PROCESSING:
- When user says "و" (and) or "واحد ... وواحد ...", extract multiple items
- Example: "اريد واحد لاتيه مثلج فانيلا وواحد لاتيه مثلج كراميل"
  → Extract: [{"item_name": "لاتيه مثلج فانيلا", "quantity": 1}, {"item_name": "لاتيه مثلج كراميل", "quantity": 1}]
- Use "multi_item_selection" action for multiple items
- For single items, use "item_selection" action

QUANTITY EXPRESSIONS:
- "واحد" = 1, "اثنين" = 2, "ثلاثة" = 3, etc.
- "كوب" = 1, "كوبين" = 2, "ثلاثة أكواب" = 3
- "قطعة" = 1, "قطعتين" = 2, "ثلاث قطع" = 3
- Arabic numerals: ١ = 1, ٢ = 2, ٣ = 3, etc.

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
        """Enhanced AI understanding prompt with complete menu awareness"""

        # Get comprehensive menu context
        menu_context = MenuAwarePrompts.get_menu_context(database_manager)

        return f"""You are an intelligent AI assistant for Hef Cafe with COMPLETE MENU KNOWLEDGE. You can understand natural language requests and intelligently suggest menu items.

🚨 CRITICAL INSTRUCTION FOR waiting_for_additional STEP:
When the user is at the "waiting_for_additional" step and they say "نعم" (Arabic for Yes), you MUST set yes_no="yes" in your response.
When the user is at the "waiting_for_additional" step and they say "لا" (Arabic for No), you MUST set yes_no="no" in your response.
This is a CRITICAL requirement - do NOT misinterpret these Arabic words.

EXAMPLE: If user says "نعم" at waiting_for_additional step, your response MUST include "yes_no": "yes"

{menu_context}

CURRENT CONVERSATION STATE:
==========================
- User is at step: {current_step}
- User said: "{user_message}"
- Language preference: {context.get('language', 'arabic')}
- Available main categories: {len(context.get('available_categories', []))}
- Current category items: {len(context.get('current_category_items', []))}

INTELLIGENT RESPONSE RULES:
==========================
1. NATURAL LANGUAGE UNDERSTANDING:
   - Analyze the user's natural language request
   - Map their preferences to menu categories and items
   - Provide intelligent suggestions based on their needs

2. EXAMPLES OF INTELLIGENT UNDERSTANDING:
   - "I want something cold and sweet" → Suggest Frappuccino (ID: 2) or Milkshakes (ID: 3)
   - "اريد شي بارد ومنعش" → Suggest Iced Tea (ID: 4) or Mojito (ID: 6)
   - "I need energy" → Suggest Coffee & Espresso (ID: 8) or Iced Coffee (ID: 1)
   - "بدي شي حلو اكله" → Suggest Cake Slices (ID: 15)
   - "Something to wake me up" → Suggest strong Coffee & Espresso (ID: 8)
   - "اريد مشروب ساخن" → Suggest Main Category 2 (Hot Drinks)
   - "I want food" → Suggest Main Category 3 (Pastries & Sweets)

3. RESPONSE STRATEGY:
   - If you can identify specific preferences, suggest the most suitable sub-category
   - If request is broad, suggest the appropriate main category
   - Always explain WHY you're suggesting something
   - Use the user's preferred language

4. WORKFLOW STEPS:
   - waiting_for_language: Detect language preference
   - waiting_for_main_category: User selects from 3 main categories
   - waiting_for_sub_category: User selects specific sub-category (e.g., "موهيتو", "ايس كوفي", "فرابتشينو")
   - waiting_for_item: User selects specific item (e.g., "موهيتو ازرق", "ايس امريكانو")
   - waiting_for_quantity: User specifies how many
   - waiting_for_additional: Ask if they want more items
   - waiting_for_service: Dine-in or delivery
   - waiting_for_location: Table number or address
   - waiting_for_confirmation: Final order confirmation

5. STEP-SPECIFIC RULES:
   - At waiting_for_category: If user says "1" or "١", use action "category_selection" with suggested_main_category=1
   - At waiting_for_category: If user says "2" or "٢", use action "category_selection" with suggested_main_category=2  
   - At waiting_for_category: If user says "3" or "٣", use action "category_selection" with suggested_main_category=3
   - At waiting_for_category: If user says "4" or "٤", use action "category_selection" with suggested_main_category=1 (Cold Drinks)
   - At waiting_for_category: If user says "5" or "٥", use action "category_selection" with suggested_main_category=1 (Cold Drinks)
   - At waiting_for_category: If user says "6" or "٦", use action "category_selection" with suggested_main_category=1 (Cold Drinks)
   - At waiting_for_category: If user says "7" or "٧", use action "category_selection" with suggested_main_category=1 (Cold Drinks)
   - At waiting_for_sub_category: If user says "موهيتو", use action "sub_category_selection"
   - At waiting_for_sub_category: If user says "موهيتو ازرق", use action "item_selection"
   - At waiting_for_item: If user says "موهيتو", navigate to mojito sub-category
   - At waiting_for_item: If user says "موهيتو ازرق", select that specific item
   - At waiting_for_additional: If user says "1" or "نعم" or "yes" or "اي", use action "yes_no" with yes_no="yes"
   - At waiting_for_additional: If user says "2" or "لا" or "no" or "لأ", use action "yes_no" with yes_no="no"
   - At waiting_for_service: If user says "1" or "١" or "في المقهى" or "داخل" or "dine", use action "service_selection" with service_type="dine-in"
   - At waiting_for_service: If user says "2" or "٢" or "توصيل" or "delivery", use action "service_selection" with service_type="delivery"
   - At waiting_for_service: If user says "3" or "4" or "5" or "6" or "7" or "8" or "9" or "10" or "11" or "12" or any number > 2, DO NOT accept it as valid service selection

RESPOND WITH CLEAN JSON (no extra text):
=======================================
{{
    "understood_intent": "Clear description of what the user wants",
    "confidence": "high/medium/low",
    "action": "intelligent_suggestion/language_selection/category_selection/sub_category_selection/item_selection/multi_item_selection/quantity_selection/yes_no/service_selection/location_input/confirmation/show_menu",
    "extracted_data": {{
        "language": "arabic/english/null",
        "suggested_main_category": "number if you can intelligently suggest main category",
        "suggested_sub_category": "number if you can intelligently suggest specific sub-category",
        "sub_category_id": "number or null",
        "sub_category_name": "string or null",
        "category_id": "number or null",
        "item_id": "number or null",
        "item_name": "string or null",
        "quantity": "number or null",
        "yes_no": "yes/no/null",
        "service_type": "dine-in/delivery/null",
        "location": "string or null",
        "multi_items": "array of objects with item_name and quantity for multi-item orders"
    }},
    "clarification_needed": false,
    "response_message": "Helpful response in user's language with intelligent suggestions and explanation"

IMPORTANT VALIDATION RULES:
==========================
- For service_selection: ONLY accept "1" or "2" as valid numbers. Numbers 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, etc. are INVALID for service selection.
- If user enters invalid service number, return error message asking them to choose 1 or 2 only."
}}

CRITICAL EXAMPLES:
==================
User: "1" (at waiting_for_category step)
Response: {{
    "understood_intent": "User wants to select main category number 1 (Cold Drinks)",
    "confidence": "high",
    "action": "category_selection",
    "extracted_data": {{
        "language": "arabic",
        "suggested_main_category": 1,
        "suggested_sub_category": null,
        "category_id": null,
        "item_id": null,
        "quantity": null,
        "yes_no": null,
        "service_type": null,
        "location": null
    }},
    "clarification_needed": false,
    "response_message": "ممتاز! لقد اخترت المشروبات الباردة. الآن، إليك الخيارات المتاحة:\\n\\n1. ايس كوفي\\n2. فرابتشينو\\n3. ميلك شيك\\n4. شاي مثلج\\n5. عصائر طازجة\\n6. موهيتو\\n7. مشروبات الطاقة\\n\\nاختر رقم الفئة التي تفضلها!"
}}

User: "4" (at waiting_for_category step)
Response: {{
    "understood_intent": "User wants to select main category number 1 (Cold Drinks)",
    "confidence": "high",
    "action": "category_selection",
    "extracted_data": {{
        "language": "arabic",
        "suggested_main_category": 1,
        "suggested_sub_category": null,
        "category_id": null,
        "item_id": null,
        "quantity": null,
        "yes_no": null,
        "service_type": null,
        "location": null
    }},
    "clarification_needed": false,
    "response_message": "ممتاز! لقد اخترت المشروبات الباردة. الآن، إليك الخيارات المتاحة:\\n\\n1. ايس كوفي\\n2. فرابتشينو\\n3. ميلك شيك\\n4. شاي مثلج\\n5. عصائر طازجة\\n6. موهيتو\\n7. مشروبات الطاقة\\n\\nاختر رقم الفئة التي تفضلها!"
}}

User: "6" (at waiting_for_category step)
Response: {{
    "understood_intent": "User wants to select main category number 1 (Cold Drinks)",
    "confidence": "high",
    "action": "category_selection",
    "extracted_data": {{
        "language": "arabic",
        "suggested_main_category": 1,
        "suggested_sub_category": null,
        "category_id": null,
        "item_id": null,
        "quantity": null,
        "yes_no": null,
        "service_type": null,
        "location": null
    }},
    "clarification_needed": false,
    "response_message": "ممتاز! لقد اخترت المشروبات الباردة. الآن، إليك الخيارات المتاحة:\\n\\n1. ايس كوفي\\n2. فرابتشينو\\n3. ميلك شيك\\n4. شاي مثلج\\n5. عصائر طازجة\\n6. موهيتو\\n7. مشروبات الطاقة\\n\\nاختر رقم الفئة التي تفضلها!"
}}

User: "اريد واحد موهيتو رمان وواحد موهيتو خوخ"
Response: {{
    "understood_intent": "User wants to order 1 Pomegranate Mojito and 1 Peach Mojito",
    "confidence": "high",
    "action": "multi_item_selection",
    "extracted_data": {{
        "language": "arabic",
        "suggested_main_category": null,
        "suggested_sub_category": null,
        "category_id": null,
        "item_id": null,
        "quantity": null,
        "yes_no": null,
        "service_type": null,
        "location": null,
        "multi_items": [
            {{"item_name": "موهيتو رمان", "quantity": 1}},
            {{"item_name": "موهيتو خوخ", "quantity": 1}}
        ]
    }},
    "clarification_needed": false,
    "response_message": "ممتاز! تم اختيار 1 موهيتو رمان و1 موهيتو خوخ. كم الكمية المطلوبة لكل منهما؟"
}}

User: "I want something cold and sweet"
Response: {{
    "understood_intent": "User wants a cold and sweet drink",
    "confidence": "high",
    "action": "intelligent_suggestion",
    "extracted_data": {{
        "language": "english",
        "suggested_main_category": 1,
        "suggested_sub_category": 2,
        "category_id": null,
        "item_id": null,
        "quantity": null,
        "yes_no": null,
        "service_type": null,
        "location": null
    }},
    "clarification_needed": false,
    "response_message": "I understand you want something cold and sweet! Perfect choice for a refreshing treat.\\n\\nI recommend our Frappuccinos - they're cold, creamy, and deliciously sweet:\\n\\n1. Caramel Frappuccino - 5000 IQD\\n2. Vanilla Frappuccino - 5000 IQD\\n3. Hazelnut Frappuccino - 5000 IQD\\n4. Chocolate Frappuccino - 5000 IQD\\n\\nOr try our Milkshakes if you prefer something thicker and creamier!\\n\\nChoose a number or tell me which one sounds good to you!"
}}

User: "اريد شي بارد ومنعش"
Response: {{
    "understood_intent": "User wants something cold and refreshing",
    "confidence": "high", 
    "action": "intelligent_suggestion",
    "extracted_data": {{
        "language": "arabic",
        "suggested_main_category": 1,
        "suggested_sub_category": 4,
        "category_id": null,
        "item_id": null,
        "quantity": null,
        "yes_no": null,
        "service_type": null,
        "location": null
    }},
    "clarification_needed": false,
    "response_message": "فهمت أنك تريد شيء بارد ومنعش! اختيار ممتاز لإنعاش يومك.\\n\\nأنصحك بالشاي المثلج - بارد ومنعش تماماً:\\n\\n1. شاي مثلج بالخوخ - 5000 دينار\\n2. شاي مثلج بفاكهة العاطفة - 5000 دينار\\n\\nأو جرب الموهيتو إذا كنت تحب شيء أكثر انتعاشاً مع النعناع!\\n\\nاختر الرقم أو قلي أيش يعجبك!"
}}

User: "موهيتو" (at waiting_for_sub_category step)
Response: {{
    "understood_intent": "User wants to select mojito sub-category",
    "confidence": "high",
    "action": "sub_category_selection",
    "extracted_data": {{
        "language": "arabic",
        "sub_category_name": "موهيتو",
        "sub_category_id": 6,
        "category_id": null,
        "item_id": null,
        "quantity": null,
        "yes_no": null,
        "service_type": null,
        "location": null
    }},
    "clarification_needed": false,
    "response_message": "ممتاز! سأعرض لك قائمة الموهيتو:\\n\\n1. موهيتو ازرق - 5000 دينار\\n2.  . موهيتو توت ازرق - 5000 دينار\\n3. موهيتو روزبيري - 5000 دينار\\n4. موهيتو فراولة - 5000 دينار\\n5. موهيتو بينا كولادا - 5000 دينار\\n6. موهيتو علكة - 5000 دينار\\n7. موهيتو دراغون - 5000 دينار\\n8. موهيتو هيف - 5000 دينار\\n9. . موهيتو خوخ - 5000 دينار\\n\\nاختر الرقم الذي تفضله!"
}}

User: "موهيتو" (at waiting_for_item step)
Response: {{
    "understood_intent": "User wants to navigate to mojito sub-category",
    "confidence": "high",
    "action": "sub_category_selection",
    "extracted_data": {{
        "language": "arabic",
        "sub_category_name": "موهيتو",
        "sub_category_id": 6,
        "category_id": null,
        "item_id": null,
        "quantity": null,
        "yes_no": null,
        "service_type": null,
        "location": null
    }},
    "clarification_needed": false,
    "response_message": "ممتاز! سأعرض لك قائمة الموهيتو:\\n\\n1. موهيتو ازرق - 5000 دينار\\n2. موهيتو فاكهة العاطفة - 5000 دينار\\n3. موهيتو توت ازرق - 5000 دينار\\n4. موهيتو روزبيري - 5000 دينار\\n5. موهيتو فراولة - 5000 دينار\\n6. موهيتو بينا كولادا - 5000 دينار\\n7. موهيتو علكة - 5000 دينار\\n8. موهيتو دراغون - 5000 دينار\\n9. موهيتو هيف - 5000 دينار\\n10. موهيتو رمان - 5000 دينار\\n11. موهيتو خوخ - 5000 دينار\\n\\nاختر الرقم الذي تفضله!"
}}

User: "موهيتو ازرق" (at waiting_for_item step)
Response: {{
    "understood_intent": "User wants to order Blue Mojito specifically",
    "confidence": "high",
    "action": "item_selection",
    "extracted_data": {{
        "language": "arabic",
        "item_name": "موهيتو ازرق",
        "item_id": null,
        "category_id": null,
        "quantity": null,
        "yes_no": null,
        "service_type": null,
        "location": null
    }},
    "clarification_needed": false,
    "response_message": "ممتاز! تم اختيار: موهيتو ازرق\\nالسعر: 5000 دينار\\nكم الكمية المطلوبة؟"
}}

User: "ايس كوفي" (at waiting_for_sub_category step)
Response: {{
    "understood_intent": "User wants to select iced coffee sub-category",
    "confidence": "high",
    "action": "sub_category_selection",
    "extracted_data": {{
        "language": "arabic",
        "sub_category_name": "ايس كوفي",
        "sub_category_id": 1,
        "category_id": null,
        "item_id": null,
        "quantity": null,
        "yes_no": null,
        "service_type": null,
        "location": null
    }},
    "clarification_needed": false,
    "response_message": "ممتاز! سأعرض لك قائمة ايس كوفي:\\n\\n1. ايس كوفي - 3000 دينار\\n2. ايس امريكانو - 4000 دينار\\n3. لاتيه مثلج عادي - 4000 دينار\\n4. لاتيه مثلج كراميل - 5000 دينار\\n5. لاتيه مثلج فانيلا - 5000 دينار\\n6. لاتيه مثلج بندق - 5000 دينار\\n7. ايس موكا - 5000 دينار\\n8. لاتيه اسباني مثلج - 6000 دينار\\n\\nاختر الرقم الذي تفضله!"
}}

User: "1" (at waiting_for_additional step)
Response: {{
    "understood_intent": "User wants to add more items to their order",
    "confidence": "high",
    "action": "yes_no",
    "extracted_data": {{
        "language": "arabic",
        "category_id": null,
        "item_id": null,
        "quantity": null,
        "yes_no": "yes",
        "service_type": null,
        "location": null
    }},
    "clarification_needed": false,
    "response_message": "ممتاز! سأعرض لك قائمة الأصناف مرة أخرى:\\n\\n1. مشروبات باردة\\n2. مشروبات ساخنة\\n3. معجنات وحلويات\\n\\nاختر رقم الصنف الذي تريده:"
}}

User: "2" (at waiting_for_additional step)
Response: {{
    "understood_intent": "User wants to finish their order and not add more items",
    "confidence": "high",
    "action": "yes_no",
    "extracted_data": {{
        "language": "arabic",
        "category_id": null,
        "item_id": null,
        "quantity": null,
        "yes_no": "no",
        "service_type": null,
        "location": null
    }},
    "clarification_needed": false,
    "response_message": "ممتاز! لننتقل إلى اختيار نوع الخدمة. هل تفضل تناول الطعام في المقهى أم التوصيل للمنزل؟"
}}

User: "نعم" (at waiting_for_additional step)
Response: {{
    "understood_intent": "User wants to add more items to their order",
    "confidence": "high",
    "action": "yes_no",
    "extracted_data": {{
        "language": "arabic",
        "category_id": null,
        "item_id": null,
        "quantity": null,
        "yes_no": "yes",
        "service_type": null,
        "location": null
    }},
    "clarification_needed": false,
    "response_message": "ممتاز! سأعرض لك قائمة الأصناف مرة أخرى:\\n\\n1. مشروبات باردة\\n2. مشروبات ساخنة\\n3. معجنات وحلويات\\n\\nاختر رقم الصنف الذي تريده:"
}}

User: "لا" (at waiting_for_additional step)
Response: {{
    "understood_intent": "User wants to finish their order and not add more items",
    "confidence": "high",
    "action": "yes_no",
    "extracted_data": {{
        "language": "arabic",
        "category_id": null,
        "item_id": null,
        "quantity": null,
        "yes_no": "no",
        "service_type": null,
        "location": null
    }},
    "clarification_needed": false,
    "response_message": "ممتاز! لننتقل إلى اختيار نوع الخدمة. هل تفضل تناول الطعام في المقهى أم التوصيل للمنزل؟"
}}

Now analyze the user's message and respond with appropriate JSON."""

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