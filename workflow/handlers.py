# workflow/handlers.py - FIXED VERSION with proper AI integration and number handling

import logging
import time
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


# workflow/handlers.py - CRITICAL FIXES

class MessageHandler:
    """Fixed message handler with proper 3-tier menu support"""

    def __init__(self, database_manager, ai_processor, action_executor):
        self.db = database_manager
        self.ai = ai_processor
        self.executor = action_executor

    def handle_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Fixed message handling with proper step mapping"""
        try:
            text = message_data.get('text', {}).get('body', '').strip()
            phone_number = message_data.get('from')
            customer_name = self._extract_customer_name(message_data)

            # Get current session
            session = self.db.get_user_session(phone_number)
            current_step = session.get('current_step') if session else 'waiting_for_language'

            # CRITICAL FIX: Always start fresh if no session
            if not session:
                return self._handle_language_selection(phone_number, text, customer_name)

            # CRITICAL FIX: Proper step handling
            return self._route_to_correct_handler(phone_number, current_step, text, session)

        except Exception as e:
            logger.error(f"❌ Error handling message: {str(e)}")
            return self._create_response("حدث خطأ. الرجاء إعادة المحاولة\nAn error occurred. Please try again")

    def _route_to_correct_handler(self, phone_number: str, current_step: str, text: str, session: Dict) -> Dict:
        """Route to correct handler based on current step with back navigation support"""
        language = session.get('language_preference', 'arabic')
        customer_name = session.get('customer_name', 'Customer')

        # Convert Arabic numerals
        text = self._convert_arabic_numerals(text)

        # Check for back navigation request
        if self._is_back_request(text, language):
            return self._handle_back_navigation(phone_number, current_step, language, session)

        if current_step == 'waiting_for_language':
            return self._handle_language_selection(phone_number, text, customer_name)
        elif current_step == 'waiting_for_category':
            return self._handle_category_selection(phone_number, text, language, session)
        elif current_step == 'waiting_for_sub_category':
            return self._handle_sub_category_selection(phone_number, text, language, session)
        elif current_step == 'waiting_for_item':
            return self._handle_item_selection(phone_number, text, language, session)
        elif current_step == 'waiting_for_quantity':
            return self._handle_quantity_selection(phone_number, text, language, session)
        elif current_step == 'waiting_for_additional':
            return self._handle_additional_items(phone_number, text, language, session)
        elif current_step == 'waiting_for_service':
            return self._handle_service_selection(phone_number, text, language, session)
        elif current_step == 'waiting_for_location':
            return self._handle_location_input(phone_number, text, language, session)
        elif current_step == 'waiting_for_confirmation':
            return self._handle_confirmation(phone_number, text, language, session)
        elif current_step == 'waiting_for_fresh_start':
            return self._handle_fresh_start_after_order(phone_number, text, language, session)
        else:
            # Default to language selection
            return self._handle_language_selection(phone_number, text, customer_name)

    def _handle_language_selection(self, phone_number: str, text: str, customer_name: str) -> Dict:
        """Handle language selection and show main categories"""
        language = self._detect_language(text)

        if not language:
            # Ask for language selection
            return self._create_response(
                "مرحباً بك في مقهى هيف 🏪\n\n"
                "📋 الخطوة 1 من 9: اختيار اللغة\n"
                "الرجاء اختيار لغتك المفضلة:\n"
                "1. العربية\n"
                "2. English\n\n"
                "Welcome to Hef Cafe 🏪\n\n"
                "📋 Step 1 of 9: Language Selection\n"
                "Please select your preferred language:\n"
                "1. العربية (Arabic)\n"
                "2. English"
            )

        # Create session and show main categories
        success = self.db.create_or_update_session(phone_number, 'waiting_for_category', language, customer_name)

        if success:
            main_categories = self.db.get_main_categories()

            if language == 'arabic':
                response = f"أهلاً وسهلاً {customer_name} في مقهى هيف! 🏪\n\n"
                response += "📋 الخطوة 2 من 9: القائمة الرئيسية\n"
                response += "القائمة الرئيسية:\n\n"
                for i, category in enumerate(main_categories, 1):
                    response += f"{i}. {category['name_ar']}\n"
                response += "\nالرجاء اختيار الفئة المطلوبة بالرد بالرقم\n"
                response += "💡 يمكنك كتابة 'رجوع' للعودة للخطوة السابقة"
            else:
                response = f"Welcome {customer_name} to Hef Cafe! 🏪\n\n"
                response += "📋 Step 2 of 9: Main Menu\n"
                response += "Main Menu:\n\n"
                for i, category in enumerate(main_categories, 1):
                    response += f"{i}. {category['name_en']}\n"
                response += "\nPlease select the category by replying with the number\n"
                response += "💡 You can type 'back' to go to the previous step"

            return self._create_response(response)

        return self._create_response("خطأ في النظام\nSystem error")

    def _handle_category_selection(self, phone_number: str, text: str, language: str, session: Dict) -> Dict:
        """Handle main category selection - FIXED to show sub-categories with better validation"""
        number = self._extract_number(text)
        main_categories = self.db.get_main_categories()

        if number and 1 <= number <= len(main_categories):
            selected_category = main_categories[number - 1]

            # Update session with selected main category and move to sub-category selection
            self.db.create_or_update_session(
                phone_number, 'waiting_for_sub_category', language,
                session.get('customer_name'),
                selected_main_category=selected_category['id']
            )

            # Get sub-categories for this main category
            sub_categories = self.db.get_sub_categories(selected_category['id'])

            if language == 'arabic':
                response = f"📋 الخطوة 2 من 9: {selected_category['name_ar']}\n"
                response += f"قائمة {selected_category['name_ar']}:\n\n"
                for i, sub_cat in enumerate(sub_categories, 1):
                    response += f"{i}. {sub_cat['name_ar']}\n"
                response += "\nالرجاء اختيار الفئة الفرعية المطلوبة\n"
                response += "💡 يمكنك كتابة 'رجوع' للعودة للخطوة السابقة"
            else:
                response = f"📋 Step 2 of 9: {selected_category['name_en']}\n"
                response += f"{selected_category['name_en']} Menu:\n\n"
                for i, sub_cat in enumerate(sub_categories, 1):
                    response += f"{i}. {sub_cat['name_en']}\n"
                response += "\nPlease choose the sub-category\n"
                response += "💡 You can type 'back' to go to the previous step"

            return self._create_response(response)

        # Invalid selection - show categories again with better error message
        if language == 'arabic':
            response = "الرجاء اختيار رقم صحيح من القائمة:\n\n"
            for i, cat in enumerate(main_categories, 1):
                response += f"{i}. {cat['name_ar']}\n"
            response += f"\nأرسلت: '{text}' - الرجاء اختيار رقم من 1 إلى {len(main_categories)}"
        else:
            response = "Please choose a valid number from the menu:\n\n"
            for i, cat in enumerate(main_categories, 1):
                response += f"{i}. {cat['name_en']}\n"
            response += f"\nYou sent: '{text}' - Please choose a number from 1 to {len(main_categories)}"

        return self._create_response(response)

    def _handle_sub_category_selection(self, phone_number: str, text: str, language: str, session: Dict) -> Dict:
        """Handle sub-category selection with enhanced Arabic text recognition"""
        selected_main_category_id = session.get('selected_main_category')
        
        if not selected_main_category_id:
            return self._create_response("خطأ في النظام\nSystem error")

        # Convert Arabic numerals first
        text = self._convert_arabic_numerals(text)
        
        # Try number extraction first
        number = self._extract_number(text)
        sub_categories = self.db.get_sub_categories(selected_main_category_id)

        if number and 1 <= number <= len(sub_categories):
            selected_sub_category = sub_categories[number - 1]

            # Update session with selected sub-category and move to item selection
            self.db.create_or_update_session(
                phone_number, 'waiting_for_item', language,
                session.get('customer_name'),
                selected_main_category=selected_main_category_id,
                selected_sub_category=selected_sub_category['id']
            )

            # Get items for this sub-category
            items = self.db.get_sub_category_items(selected_sub_category['id'])

            if language == 'arabic':
                response = f"📋 الخطوة 3 من 9: {selected_sub_category['name_ar']}\n"
                response += f"قائمة {selected_sub_category['name_ar']}:\n\n"
                for i, item in enumerate(items, 1):
                    response += f"{i}. {item['item_name_ar']}\n"
                    response += f"   السعر: {item['price']} دينار\n\n"
                response += "الرجاء اختيار المنتج المطلوب\n"
                response += "💡 يمكنك كتابة 'رجوع' للعودة للخطوة السابقة"
            else:
                response = f"📋 Step 3 of 9: {selected_sub_category['name_en']}\n"
                response += f"{selected_sub_category['name_en']} Menu:\n\n"
                for i, item in enumerate(items, 1):
                    response += f"{i}. {item['item_name_en']}\n"
                    response += f"   Price: {item['price']} IQD\n\n"
                response += "Please select the required item\n"
                response += "💡 You can type 'back' to go to the previous step"

            return self._create_response(response)

        # If no number found, try to match by Arabic text
        if language == 'arabic':
            text_lower = text.lower().strip()
            
            # Enhanced Arabic sub-category mapping
            arabic_sub_category_mapping = {
                'توست': 1,
                'سندويشات': 2, 'سندويشة': 2, 'سندويش': 2,
                'كرواسان': 3, 'كرواسون': 3,
                'فطائر': 4, 'فطاير': 4, 'فطيرة': 4,
                'قطع كيك': 5, 'كيك': 5, 'قطع': 5
            }
            
            # Check for exact matches first
            for arabic_term, sub_cat_number in arabic_sub_category_mapping.items():
                if arabic_term in text_lower or text_lower in arabic_term:
                    if 1 <= sub_cat_number <= len(sub_categories):
                        selected_sub_category = sub_categories[sub_cat_number - 1]
                        
                        # Update session with selected sub-category
                        self.db.create_or_update_session(
                            phone_number, 'waiting_for_item', language,
                            session.get('customer_name'),
                            selected_main_category=selected_main_category_id,
                            selected_sub_category=selected_sub_category['id']
                        )

                        # Get items for this sub-category
                        items = self.db.get_sub_category_items(selected_sub_category['id'])

                        response = f"📋 الخطوة 3 من 9: {selected_sub_category['name_ar']}\n"
                        response += f"قائمة {selected_sub_category['name_ar']}:\n\n"
                        for i, item in enumerate(items, 1):
                            response += f"{i}. {item['item_name_ar']}\n"
                            response += f"   السعر: {item['price']} دينار\n\n"
                        response += "الرجاء اختيار المنتج المطلوب\n"
                        response += "💡 يمكنك كتابة 'رجوع' للعودة للخطوة السابقة"

                        return self._create_response(response)

        # Invalid selection - show sub-categories again
        main_categories = self.db.get_main_categories()
        current_main_category = next((cat for cat in main_categories if cat['id'] == selected_main_category_id), None)

        if language == 'arabic':
            response = f"الرجاء اختيار رقم صحيح من قائمة {current_main_category['name_ar'] if current_main_category else 'الفئة'}:\n\n"
            for i, sub_cat in enumerate(sub_categories, 1):
                response += f"{i}. {sub_cat['name_ar']}\n"
            response += f"\nأرسلت: '{text}' - الرجاء اختيار رقم من 1 إلى {len(sub_categories)}"
        else:
            response = f"Please choose a valid number from {current_main_category['name_en'] if current_main_category else 'category'} menu:\n\n"
            for i, sub_cat in enumerate(sub_categories, 1):
                response += f"{i}. {sub_cat['name_en']}\n"
            response += f"\nYou sent: '{text}' - Please choose a number from 1 to {len(sub_categories)}"

        return self._create_response(response)

    def _handle_item_selection(self, phone_number: str, text: str, language: str, session: Dict) -> Dict:
        """Handle item selection - UPDATED to work with sub-categories"""
        selected_sub_category_id = session.get('selected_sub_category')

        if not selected_sub_category_id:
            return self._create_response("خطأ في النظام\nSystem error")

        # Get items for the selected sub-category
        items = self.db.get_sub_category_items(selected_sub_category_id)
        number = self._extract_number(text)

        if number and 1 <= number <= len(items):
            selected_item = items[number - 1]

            # Update session with selected item
            self.db.create_or_update_session(
                phone_number, 'waiting_for_quantity', language,
                session.get('customer_name'),
                selected_main_category=session.get('selected_main_category'),
                selected_sub_category=selected_sub_category_id,
                selected_item=selected_item['id']
            )

            if language == 'arabic':
                response = f"📋 الخطوة 4 من 9: الكمية\n"
                response += f"✅ تم اختيار: {selected_item['item_name_ar']}\n"
                response += f"💰 السعر: {selected_item['price']} دينار\n\n"
                response += "كم الكمية المطلوبة؟\n"
                response += "💡 يمكنك كتابة 'رجوع' للعودة للخطوة السابقة"
            else:
                response = f"📋 Step 4 of 9: Quantity\n"
                response += f"✅ Selected: {selected_item['item_name_en']}\n"
                response += f"💰 Price: {selected_item['price']} IQD\n\n"
                response += "How many would you like?\n"
                response += "💡 You can type 'back' to go to the previous step"

            return self._create_response(response)

        # Invalid selection - show items again
        sub_categories = self.db.get_sub_categories(session.get('selected_main_category'))
        current_sub_category = next((sub_cat for sub_cat in sub_categories if sub_cat['id'] == selected_sub_category_id), None)

        if language == 'arabic':
            response = f"الرجاء اختيار رقم صحيح من قائمة {current_sub_category['name_ar'] if current_sub_category else 'الفئة'}:\n\n"
            for i, item in enumerate(items, 1):
                response += f"{i}. {item['item_name_ar']} - {item['price']} دينار\n"
            response += f"\nأرسلت: '{text}' - الرجاء اختيار رقم من 1 إلى {len(items)}"
        else:
            response = f"Please choose a valid number from {current_sub_category['name_en'] if current_sub_category else 'category'} menu:\n\n"
            for i, item in enumerate(items, 1):
                response += f"{i}. {item['item_name_en']} - {item['price']} IQD\n"
            response += f"\nYou sent: '{text}' - Please choose a number from 1 to {len(items)}"

        return self._create_response(response)

    def _handle_quantity_selection(self, phone_number: str, text: str, language: str, session: Dict) -> Dict:
        """Handle quantity selection with enhanced Arabic quantity recognition"""
        selected_item_id = session.get('selected_item')

        if not selected_item_id:
            return self._create_response("خطأ في النظام\nSystem error")

        # Enhanced quantity extraction with Arabic word support
        quantity = self._extract_number_enhanced(text)

        if quantity and quantity > 0 and quantity <= 50:
            # Add item to order
            success = self.db.add_item_to_order(phone_number, selected_item_id, quantity)

            if success:
                item = self.db.get_item_by_id(selected_item_id)

                # Update session for additional items
                self.db.create_or_update_session(phone_number, 'waiting_for_additional', language)

                if language == 'arabic':
                    response = f"📋 الخطوة 5 من 9: إضافة المزيد\n"
                    response += f"✅ تم إضافة {item['item_name_ar']} × {quantity} إلى طلبك\n\n"
                    response += "هل تريد إضافة المزيد من الأصناف؟\n\n"
                    response += "1. نعم\n2. لا\n"
                    response += "💡 يمكنك كتابة 'رجوع' للعودة للخطوة السابقة"
                else:
                    response = f"📋 Step 5 of 9: Add More Items\n"
                    response += f"✅ Added {item['item_name_en']} × {quantity} to your order\n\n"
                    response += "Would you like to add more items?\n\n"
                    response += "1. Yes\n2. No\n"
                    response += "💡 You can type 'back' to go to the previous step"

                return self._create_response(response)

        # Invalid quantity - show better error message with examples
        if language == 'arabic':
            response = "❌ الكمية غير صحيحة\n\n"
            response += "يمكنك كتابة:\n"
            response += "• أرقام: 1، 2، 3، 4، 5...\n"
            response += "• كلمات عربية: واحد، اثنين، ثلاثة...\n"
            response += "• كلمات: كوب، قطعة، كوبين...\n\n"
            response += "الرجاء إدخال كمية صحيحة"
        else:
            response = "❌ Invalid quantity\n\n"
            response += "You can write:\n"
            response += "• Numbers: 1, 2, 3, 4, 5...\n"
            response += "• Arabic words: واحد، اثنين، ثلاثة...\n"
            response += "• Words: كوب، قطعة، كوبين...\n\n"
            response += "Please enter a valid quantity"

        return self._create_response(response)

    # Helper methods
    def _detect_language(self, text: str) -> Optional[str]:
        """Detect language from text - ENHANCED to handle incomplete inputs"""
        text_lower = text.lower().strip()

        # Arabic indicators (including partial matches)
        arabic_indicators = [
            'عربي', 'العربية', 'مرحبا', 'مرحبت', 'أهلا', 'اريد', 'بدي', '1', '١',
            'مرح', 'أهل', 'عرب', 'ار', 'بد'
        ]

        # English indicators
        english_indicators = [
            'english', 'hello', 'hi', 'want', 'need', '2', '٢'
        ]

        # Check for Arabic indicators first (including partial matches)
        for indicator in arabic_indicators:
            if indicator in text_lower:
                return 'arabic'

        # Check for English indicators
        for indicator in english_indicators:
            if indicator in text_lower:
                return 'english'

        # Default to Arabic if unclear (most users are Arabic speakers)
        return 'arabic'

    def _convert_arabic_numerals(self, text: str) -> str:
        """Convert Arabic numerals to English"""
        arabic_to_english = {
            '٠': '0', '١': '1', '٢': '2', '٣': '3', '٤': '4',
            '٥': '5', '٦': '6', '٧': '7', '٨': '8', '٩': '9'
        }

        for arabic, english in arabic_to_english.items():
            text = text.replace(arabic, english)

        return text

    def _extract_number(self, text: str) -> Optional[int]:
        """Extract number from text - ENHANCED to handle Arabic characters"""
        import re

        # Convert Arabic numerals first
        text = self._convert_arabic_numerals(text)
        
        # Clean the text - remove Arabic commas, dots, and other punctuation
        text = re.sub(r'[،,\.\s]+', '', text)  # Remove Arabic comma, regular comma, dots, spaces
        
        # Find numbers
        numbers = re.findall(r'\d+', text)

        if numbers:
            number = int(numbers[0])
            # Reasonable validation
            if 1 <= number <= 100:
                return number

        return None

    def _extract_customer_name(self, message_data: Dict) -> str:
        """Extract customer name"""
        if 'contacts' in message_data:
            contacts = message_data.get('contacts', [])
            if contacts and len(contacts) > 0:
                profile = contacts[0].get('profile', {})
                return profile.get('name', 'Customer')
        return 'Customer'

    def _create_response(self, content: str) -> Dict[str, Any]:
        """Create response"""
        if len(content) > 4000:
            content = content[:3900] + "... (تم اختصار الرسالة)"

        return {
            'type': 'text',
            'content': content,
            'timestamp': __import__('datetime').datetime.now().isoformat()
        }

    def _is_back_request(self, text: str, language: str) -> bool:
        """Check if user is requesting to go back"""
        text_lower = text.lower().strip()
        
        if language == 'arabic':
            back_indicators = ['رجوع', 'السابق', 'back', 'previous', 'قبل', 'عودة']
        else:
            back_indicators = ['back', 'previous', 'go back', 'return', 'رجوع']
        
        return any(indicator in text_lower for indicator in back_indicators)

    def _handle_back_navigation(self, phone_number: str, current_step: str, language: str, session: Dict) -> Dict:
        """Handle back navigation requests"""
        try:
            # Define step hierarchy for back navigation
            step_hierarchy = {
                'waiting_for_language': None,  # Can't go back from language selection
                'waiting_for_category': 'waiting_for_language',
                'waiting_for_sub_category': 'waiting_for_category',
                'waiting_for_item': 'waiting_for_sub_category',
                'waiting_for_quantity': 'waiting_for_item',
                'waiting_for_additional': 'waiting_for_quantity',
                'waiting_for_service': 'waiting_for_additional',
                'waiting_for_location': 'waiting_for_service',
                'waiting_for_confirmation': 'waiting_for_location',
                'waiting_for_fresh_start': None  # Can't go back from fresh start choice
            }
            
            previous_step = step_hierarchy.get(current_step)
            
            if not previous_step:
                if language == 'arabic':
                    return self._create_response("لا يمكن العودة من هذه الخطوة. الرجاء المتابعة أو إعادة البدء.")
                else:
                    return self._create_response("Cannot go back from this step. Please continue or restart.")
            
            # Update session to previous step
            self.db.create_or_update_session(phone_number, previous_step, language)
            
            # Generate appropriate response for the previous step
            if previous_step == 'waiting_for_language':
                return self._handle_language_selection(phone_number, "", session.get('customer_name', 'Customer'))
            elif previous_step == 'waiting_for_category':
                return self._handle_category_selection(phone_number, "", language, session)
            elif previous_step == 'waiting_for_sub_category':
                return self._handle_sub_category_selection(phone_number, "", language, session)
            elif previous_step == 'waiting_for_item':
                return self._handle_item_selection(phone_number, "", language, session)
            elif previous_step == 'waiting_for_quantity':
                return self._handle_quantity_selection(phone_number, "", language, session)
            elif previous_step == 'waiting_for_additional':
                return self._handle_additional_items(phone_number, "", language, session)
            elif previous_step == 'waiting_for_service':
                return self._handle_service_selection(phone_number, "", language, session)
            elif previous_step == 'waiting_for_location':
                return self._handle_location_input(phone_number, "", language, session)
            
        except Exception as e:
            logger.error(f"❌ Error handling back navigation: {e}")
            if language == 'arabic':
                return self._create_response("حدث خطأ في العودة. الرجاء إعادة المحاولة.")
            else:
                return self._create_response("Error going back. Please try again.")

    # Add other missing handler methods (additional_items, service_selection, etc.)
    def _handle_additional_items(self, phone_number: str, text: str, language: str, session: Dict) -> Dict:
        """Handle additional items selection"""
        number = self._extract_number(text)

        if number == 1:  # Yes, add more
            self.db.create_or_update_session(phone_number, 'waiting_for_category', language)
            main_categories = self.db.get_main_categories()

            if language == 'arabic':
                response = "📋 الخطوة 2 من 9: إضافة المزيد\n"
                response += "ممتاز! اختر من القائمة الرئيسية:\n\n"
                for i, category in enumerate(main_categories, 1):
                    response += f"{i}. {category['name_ar']}\n"
                response += "\nالرجاء اختيار الفئة المطلوبة\n"
                response += "💡 يمكنك كتابة 'رجوع' للعودة للخطوة السابقة"
            else:
                response = "📋 Step 2 of 9: Add More Items\n"
                response += "Great! Choose from the main menu:\n\n"
                for i, category in enumerate(main_categories, 1):
                    response += f"{i}. {category['name_en']}\n"
                response += "\nPlease choose the category\n"
                response += "💡 You can type 'back' to go to the previous step"

            return self._create_response(response)

        elif number == 2:  # No, proceed to service
            self.db.create_or_update_session(phone_number, 'waiting_for_service', language)

            if language == 'arabic':
                response = "📋 الخطوة 6 من 9: نوع الخدمة\n"
                response += "ممتاز! الآن دعنا نحدد نوع الخدمة:\n\n"
                response += "1. تناول في المقهى\n2. توصيل\n\nالرجاء اختيار نوع الخدمة\n"
                response += "💡 يمكنك كتابة 'رجوع' للعودة للخطوة السابقة"
            else:
                response = "📋 Step 6 of 9: Service Type\n"
                response += "Great! Now let's determine the service type:\n\n"
                response += "1. Dine-in\n2. Delivery\n\nPlease choose the service type\n"
                response += "💡 You can type 'back' to go to the previous step"

            return self._create_response(response)

        # Invalid response
        if language == 'arabic':
            return self._create_response("الرجاء الرد بـ '1' لإضافة المزيد أو '2' للمتابعة")
        else:
            return self._create_response("Please reply with '1' to add more or '2' to continue")

    def _handle_service_selection(self, phone_number: str, text: str, language: str, session: Dict) -> Dict:
        """Handle service type selection with enhanced Arabic understanding and numeric support"""
        try:
            # Convert Arabic numerals first
            text = self._convert_arabic_numerals(text)
            
            # Enhanced service type detection
            text_lower = text.lower().strip()
            
            # Try numeric input first
            number = self._extract_number(text)
            if number == 1:
                # Dine-in service
                self.db.create_or_update_session(phone_number, 'waiting_for_location', language)
                self.db.update_order_details(phone_number, service_type='dine-in')
                
                if language == 'arabic':
                    return self._create_response(
                        "📋 الخطوة 7 من 9\n"
                        "ممتاز! تناول في المقهى 🏪\n"
                        "الرجاء تحديد رقم الطاولة (1-7):\n"
                        "💡 يمكنك كتابة 'رجوع' للعودة للخطوة السابقة"
                    )
                else:
                    return self._create_response(
                        "📋 Step 7 of 9\n"
                        "Perfect! Dine-in service 🏪\n"
                        "Please specify table number (1-7):\n"
                        "💡 You can type 'back' to go to the previous step"
                    )
            elif number == 2:
                # Delivery service
                self.db.create_or_update_session(phone_number, 'waiting_for_location', language)
                self.db.update_order_details(phone_number, service_type='delivery')
                
                if language == 'arabic':
                    return self._create_response(
                        "📋 الخطوة 7 من 9\n"
                        "ممتاز! خدمة التوصيل 🚚\n"
                        "الرجاء إدخال عنوان التوصيل:\n"
                        "💡 يمكنك كتابة 'رجوع' للعودة للخطوة السابقة"
                    )
                else:
                    return self._create_response(
                        "📋 Step 7 of 9\n"
                        "Perfect! Delivery service 🚚\n"
                        "Please enter delivery address:\n"
                        "💡 You can type 'back' to go to the previous step"
                    )
            
            # Service type indicators for text-based detection
            dine_in_indicators = ['بالكهوة', 'في الكهوة', 'في المقهى', 'تناول', 'عندكم', 'عندك', 'في الكافيه']
            delivery_indicators = ['توصيل', 'للبيت', 'للمنزل', 'توصيل للمنزل']
            
            # Check if user is indicating service type
            is_dine_in = any(indicator in text_lower for indicator in dine_in_indicators)
            is_delivery = any(indicator in text_lower for indicator in delivery_indicators)
            
            if is_dine_in:
                # Update session with dine-in service
                self.db.create_or_update_session(phone_number, 'waiting_for_location', language)
                self.db.update_order_details(phone_number, service_type='dine-in')
                
                if language == 'arabic':
                    return self._create_response(
                        "📋 الخطوة 7 من 9\n"
                        "ممتاز! تناول في المقهى 🏪\n"
                        "الرجاء تحديد رقم الطاولة (1-7):\n"
                        "💡 يمكنك كتابة 'رجوع' للعودة للخطوة السابقة"
                    )
                else:
                    return self._create_response(
                        "📋 Step 7 of 9\n"
                        "Perfect! Dine-in service 🏪\n"
                        "Please specify table number (1-7):\n"
                        "💡 You can type 'back' to go to the previous step"
                    )
            
            elif is_delivery:
                # Update session with delivery service
                self.db.create_or_update_session(phone_number, 'waiting_for_location', language)
                self.db.update_order_details(phone_number, service_type='delivery')
                
                if language == 'arabic':
                    return self._create_response(
                        "📋 الخطوة 7 من 9\n"
                        "ممتاز! خدمة التوصيل 🚚\n"
                        "الرجاء إدخال عنوان التوصيل:\n"
                        "💡 يمكنك كتابة 'رجوع' للعودة للخطوة السابقة"
                    )
                else:
                    return self._create_response(
                        "📋 Step 7 of 9\n"
                        "Perfect! Delivery service 🚚\n"
                        "Please enter delivery address:\n"
                        "💡 You can type 'back' to go to the previous step"
                    )
            
            else:
                # Check if user might be asking for coffee instead
                coffee_indicators = ['قهوة', 'كوفي', 'اسبرسو', 'كابتشينو', 'لاتيه']
                if any(indicator in text_lower for indicator in coffee_indicators):
                    if language == 'arabic':
                        return self._create_response(
                            "أفهم أنك تريد قهوة! ☕\n"
                            "لكن أولاً، هل تريد طلبك للتناول في المقهى أم للتوصيل؟\n"
                            "1. تناول في المقهى\n"
                            "2. توصيل\n"
                            "💡 يمكنك كتابة 'رجوع' للعودة للخطوة السابقة"
                        )
                    else:
                        return self._create_response(
                            "I understand you want coffee! ☕\n"
                            "But first, do you want your order for dine-in or delivery?\n"
                            "1. Dine-in\n"
                            "2. Delivery\n"
                            "💡 You can type 'back' to go to the previous step"
                        )
                
                # Default service type question
                if language == 'arabic':
                    return self._create_response(
                        "📋 الخطوة 6 من 9\n"
                        "هل تريد طلبك للتناول في المقهى أم للتوصيل؟\n"
                        "1. تناول في المقهى 🏪\n"
                        "2. توصيل 🚚\n"
                        "💡 يمكنك كتابة 'رجوع' للعودة للخطوة السابقة"
                    )
                else:
                    return self._create_response(
                        "📋 Step 6 of 9\n"
                        "Do you want your order for dine-in or delivery?\n"
                        "1. Dine-in 🏪\n"
                        "2. Delivery 🚚\n"
                        "💡 You can type 'back' to go to the previous step"
                    )
                    
        except Exception as e:
            logger.error(f"❌ Error in service selection: {e}")
            if language == 'arabic':
                return self._create_response("حدث خطأ في اختيار نوع الخدمة. الرجاء إعادة المحاولة.")
            else:
                return self._create_response("Error selecting service type. Please try again.")

    def _handle_location_input(self, phone_number: str, text: str, language: str, session: Dict) -> Dict:
        """Handle location input"""
        location = text.strip()

        if location and len(location) >= 1:
            self.db.update_order_details(phone_number, location=location)
            self.db.create_or_update_session(phone_number, 'waiting_for_confirmation', language)

            # Get order summary
            order = self.db.get_user_order(phone_number)

            if language == 'arabic':
                response = "📋 الخطوة 8 من 9: تأكيد الطلب\n"
                response += "إليك ملخص طلبك:\n\n"
                response += "الأصناف:\n"
                for item in order['items']:
                    response += f"• {item['item_name_ar']} × {item['quantity']} - {item['subtotal']} دينار\n"

                response += f"\nالخدمة: {order['details'].get('service_type', 'غير محدد')}\n"
                response += f"المكان: {location}\n"
                response += f"السعر الإجمالي: {order['total']} دينار\n\n"
                response += "هل تريد تأكيد هذا الطلب؟\n\n1. نعم\n2. لا\n"
                response += "💡 يمكنك كتابة 'رجوع' للعودة للخطوة السابقة"
            else:
                response = "📋 Step 8 of 9: Order Confirmation\n"
                response += "Here is your order summary:\n\n"
                response += "Items:\n"
                for item in order['items']:
                    response += f"• {item['item_name_en']} × {item['quantity']} - {item['subtotal']} IQD\n"

                response += f"\nService: {order['details'].get('service_type', 'Not specified')}\n"
                response += f"Location: {location}\n"
                response += f"Total Price: {order['total']} IQD\n\n"
                response += "Would you like to confirm this order?\n\n1. Yes\n2. No\n"
                response += "💡 You can type 'back' to go to the previous step"

            return self._create_response(response)

        # Invalid location
        if language == 'arabic':
            return self._create_response("الرجاء تحديد المكان بوضوح")
        else:
            return self._create_response("Please specify the location clearly")

    def _handle_confirmation(self, phone_number: str, text: str, language: str, session: Dict) -> Dict:
        """Handle order confirmation with enhanced fresh start flow"""
        try:
            # Enhanced confirmation detection
            text_lower = text.lower().strip()
            
            # Confirmation indicators
            yes_indicators = ['نعم', 'اي', 'ايوا', 'هاهية', 'اوك', 'تمام', 'حسنا', 'yes', 'ok', 'okay']
            no_indicators = ['لا', 'مش', 'لا شكرا', 'no', 'not']
            
            is_yes = any(indicator in text_lower for indicator in yes_indicators)
            is_no = any(indicator in text_lower for indicator in no_indicators)
            
            if is_yes:
                # Complete the order
                order_id = self.db.complete_order(phone_number)
                
                if order_id:
                    if language == 'arabic':
                        response = (
                            f"✅ تم تأكيد طلبك بنجاح!\n"
                            f"رقم الطلب: {order_id}\n"
                            f"شكراً لك لاختيار مقهى هيف! 🙏\n\n"
                            f"🔄 هل تريد طلب جديد؟\n"
                            f"1. نعم، طلب جديد\n"
                            f"2. لا، شكراً"
                        )
                    else:
                        response = (
                            f"✅ Your order has been confirmed successfully!\n"
                            f"Order ID: {order_id}\n"
                            f"Thank you for choosing Hef Cafe! 🙏\n\n"
                            f"🔄 Would you like a new order?\n"
                            f"1. Yes, new order\n"
                            f"2. No, thank you"
                        )
                    
                    # Update session to fresh start state
                    self.db.create_or_update_session(phone_number, 'waiting_for_fresh_start', language)
                    return self._create_response(response)
                else:
                    if language == 'arabic':
                        return self._create_response("❌ حدث خطأ في تأكيد الطلب. الرجاء إعادة المحاولة.")
                    else:
                        return self._create_response("❌ Error confirming order. Please try again.")
            
            elif is_no:
                # Cancel the order and start fresh
                self.db.cancel_order(phone_number)
                self.db.delete_session(phone_number)
                
                if language == 'arabic':
                    return self._create_response(
                        "تم إلغاء الطلب. 🚫\n"
                        "مرحباً! مرحباً بك في مقهى هيف ☕\n"
                        "اختر اللغة المفضلة:\n"
                        "1. العربية\n"
                        "2. English"
                    )
                else:
                    return self._create_response(
                        "Order cancelled. 🚫\n"
                        "Hello! Welcome to Hef Cafe ☕\n"
                        "Choose your preferred language:\n"
                        "1. العربية\n"
                        "2. English"
                    )
            
            else:
                # Unclear response, ask for clarification
                if language == 'arabic':
                    return self._create_response(
                        "📋 الخطوة 8 من 9\n"
                        "هل تريد تأكيد هذا الطلب؟\n"
                        "1. نعم ✅\n"
                        "2. لا ❌\n"
                        "�� يمكنك كتابة 'رجوع' للعودة للخطوة السابقة"
                    )
                else:
                    return self._create_response(
                        "📋 Step 8 of 9\n"
                        "Do you want to confirm this order?\n"
                        "1. Yes ✅\n"
                        "2. No ❌\n"
                        "💡 You can type 'back' to go to the previous step"
                    )
                    
        except Exception as e:
            logger.error(f"❌ Error in confirmation: {e}")
            if language == 'arabic':
                return self._create_response("حدث خطأ في تأكيد الطلب. الرجاء إعادة المحاولة.")
            else:
                return self._create_response("Error confirming order. Please try again.")

    def _handle_fresh_start_after_order(self, phone_number: str, text: str, language: str, session: Dict) -> Dict:
        """Handle fresh start choice after order completion"""
        try:
            text_lower = text.lower().strip()
            
            # Fresh start indicators
            yes_indicators = ['نعم', 'اي', 'ايوا', 'هاهية', 'اوك', 'تمام', 'حسنا', 'yes', 'ok', 'okay']
            no_indicators = ['لا', 'مش', 'لا شكرا', 'no', 'not']
            
            is_yes = any(indicator in text_lower for indicator in yes_indicators)
            is_no = any(indicator in text_lower for indicator in no_indicators)
            
            if is_yes:
                # Start new order
                self.db.delete_session(phone_number)
                
                if language == 'arabic':
                    return self._create_response(
                        "ممتاز! طلب جديد 🆕\n"
                        "مرحباً! مرحباً بك في مقهى هيف ☕\n"
                        "اختر اللغة المفضلة:\n"
                        "1. العربية\n"
                        "2. English"
                    )
                else:
                    return self._create_response(
                        "Perfect! New order 🆕\n"
                        "Hello! Welcome to Hef Cafe ☕\n"
                        "Choose your preferred language:\n"
                        "1. العربية\n"
                        "2. English"
                    )
            
            elif is_no:
                # End conversation gracefully
                if language == 'arabic':
                    return self._create_response(
                        "شكراً لك! 🙏\n"
                        "نتمنى لك يوماً سعيداً! ☀️\n"
                        "نحن هنا دائماً عندما تحتاجنا! 💙"
                    )
                else:
                    return self._create_response(
                        "Thank you! 🙏\n"
                        "Have a wonderful day! ☀️\n"
                        "We're always here when you need us! 💙"
                    )
            
            else:
                # Unclear response, ask for clarification
                if language == 'arabic':
                    return self._create_response(
                        "🔄 هل تريد طلب جديد؟\n"
                        "1. نعم، طلب جديد\n"
                        "2. لا، شكراً"
                    )
                else:
                    return self._create_response(
                        "🔄 Would you like a new order?\n"
                        "1. Yes, new order\n"
                        "2. No, thank you"
                    )
                    
        except Exception as e:
            logger.error(f"❌ Error in fresh start handling: {e}")
            if language == 'arabic':
                return self._create_response("حدث خطأ. الرجاء إعادة المحاولة.")
            else:
                return self._create_response("Error occurred. Please try again.")

    # Enhanced utility methods
    def _convert_arabic_numerals(self, text: str) -> str:
        """Convert Arabic numerals to English"""
        arabic_to_english = {
            '٠': '0', '١': '1', '٢': '2', '٣': '3', '٤': '4',
            '٥': '5', '٦': '6', '٧': '7', '٨': '8', '٩': '9'
        }

        for arabic, english in arabic_to_english.items():
            text = text.replace(arabic, english)

        return text

    def _extract_number_enhanced(self, text: str) -> Optional[int]:
        """ENHANCED: Better number extraction with comprehensive Arabic quantity recognition"""
        import re

        # Convert Arabic numerals first
        text = self._convert_arabic_numerals(text)

        # Extract all numbers
        numbers = re.findall(r'\d+', text)

        if numbers:
            number = int(numbers[0])

            # Basic validation - reject unreasonably large numbers in most contexts
            if number > 1000:
                logger.warning(f"⚠️ Rejecting large number: {number}")
                return None

            return number

        # Enhanced Arabic quantity word recognition
        arabic_quantity_words = {
            # Basic numbers
            'واحد': 1, 'واحدة': 1, 'واحد': 1,
            'اثنين': 2, 'اثنتين': 2, 'اثنان': 2,
            'ثلاثة': 3, 'ثلاث': 3, 'ثلاثه': 3,
            'أربعة': 4, 'أربع': 4, 'اربعة': 4, 'اربع': 4,
            'خمسة': 5, 'خمس': 5, 'خمسه': 5,
            'ستة': 6, 'ست': 6, 'سته': 6,
            'سبعة': 7, 'سبع': 7, 'سبعه': 7,
            'ثمانية': 8, 'ثماني': 8, 'ثمانيه': 8,
            'تسعة': 9, 'تسع': 9, 'تسعه': 9,
            'عشرة': 10, 'عشر': 10, 'عشره': 10,
            
            # Common quantity expressions
            'كوب': 1, 'كوب واحد': 1, 'كوب واحد': 1,
            'كوبين': 2, 'كوبين': 2,
            'ثلاثة أكواب': 3, 'ثلاث اكواب': 3,
            'أربعة أكواب': 4, 'اربع اكواب': 4,
            'خمسة أكواب': 5, 'خمس اكواب': 5,
            
            'قطعة': 1, 'قطعة واحدة': 1, 'قطعة واحدة': 1,
            'قطعتين': 2, 'قطعتين': 2,
            'ثلاث قطع': 3, 'ثلاث قطع': 3,
            'أربع قطع': 4, 'اربع قطع': 4,
            'خمس قطع': 5, 'خمس قطع': 5,
            
            # English numbers
            'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
            'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
            'first': 1, 'second': 2, 'third': 3, 'fourth': 4, 'fifth': 5
        }

        text_lower = text.lower().strip()
        
        # Check for exact matches first
        for word, number in arabic_quantity_words.items():
            if word == text_lower:
                return number
        
        # Check for partial matches
        for word, number in arabic_quantity_words.items():
            if word in text_lower:
                return number

        return None

    def _detect_language_enhanced(self, text: str) -> Optional[str]:
        """Enhanced language detection"""
        text_lower = text.lower().strip()

        # Strong Arabic indicators
        arabic_indicators = [
            'عربي', 'العربية', 'عرب', 'مرحبا', 'أهلا', 'اريد', 'بدي',
            'شو', 'ايش', 'كيف', 'وين'
        ]

        # Strong English indicators
        english_indicators = [
            'english', 'انجليزي', 'hello', 'hi', 'hey', 'want', 'need',
            'order', 'menu', 'what', 'how'
        ]

        # Check for strong indicators first
        if any(indicator in text_lower for indicator in arabic_indicators):
            return 'arabic'
        elif any(indicator in text_lower for indicator in english_indicators):
            return 'english'

        return None

    def _detect_yes_no_enhanced(self, text: str, language: str) -> Optional[str]:
        """Enhanced yes/no detection with Iraqi dialect support"""
        text_lower = text.lower().strip()

        if language == 'arabic':
            yes_indicators = ['نعم', 'ايوه', 'اه', 'صح', 'تمام', 'موافق', 'اكيد', 'طيب', 'حسنا', 'هيه', 'هاهية']
            no_indicators = ['لا', 'كلا', 'مش', 'مو', 'لأ', 'رفض', 'ما بدي', 'مابدي', 'هاهية لا', 'لا هاهية']
        else:
            yes_indicators = ['yes', 'yeah', 'yep', 'sure', 'ok', 'okay', 'confirm', 'agree']
            no_indicators = ['no', 'nope', 'cancel', 'stop', 'abort', 'disagree']

        # Check for no first (more specific patterns)
        for indicator in no_indicators:
            if indicator in text_lower:
                return 'no'

        # Then check for yes
        for indicator in yes_indicators:
            if indicator in text_lower:
                return 'yes'

        return None

    def _match_category_by_name(self, text: str, categories: list, language: str) -> Optional[Dict]:
        """Enhanced category name matching"""
        text_lower = text.lower().strip()

        # Direct name matching
        for category in categories:
            ar_name = category['category_name_ar'].lower()
            en_name = category['category_name_en'].lower()

            if (text_lower == ar_name or text_lower == en_name or
                    text_lower in ar_name or ar_name in text_lower or
                    text_lower in en_name or en_name in text_lower):
                return category

        # Keyword matching
        keyword_mapping = {
            'موهيتو': 7, 'mojito': 7,
            'فرابتشينو': 5, 'frappuccino': 5,
            'ميلك شيك': 8, 'milkshake': 8,
            'توست': 9, 'toast': 9,
            'سندويش': 10, 'sandwich': 10,
            'كرواسان': 12, 'croissant': 12,
            'كيك': 11, 'cake': 11,
            'عصير': 6, 'juice': 6,
            'شاي': 4, 'tea': 4,
            'حار': 1, 'hot': 1,
            'بارد': 2, 'cold': 2,
            'حلو': 3, 'sweet': 3
        }

        for keyword, cat_id in keyword_mapping.items():
            if keyword in text_lower:
                return next((cat for cat in categories if cat['category_id'] == cat_id), None)

        return None

    def _match_item_by_name(self, text: str, items: list, language: str) -> Optional[Dict]:
        """Enhanced item name matching"""
        text_lower = text.lower().strip()

        # Direct name matching with scoring
        best_match = None
        best_score = 0

        for item in items:
            item_name_ar = item['item_name_ar'].lower()
            item_name_en = item['item_name_en'].lower()

            score = 0

            # Exact match gets highest score
            if text_lower == item_name_ar or text_lower == item_name_en:
                return item

            # Partial matches
            if text_lower in item_name_ar or item_name_ar in text_lower:
                score += 3
            if text_lower in item_name_en or item_name_en in text_lower:
                score += 3

            # Word-level matching
            text_words = text_lower.split()
            ar_words = item_name_ar.split()
            en_words = item_name_en.split()

            for word in text_words:
                if word in ar_words or word in en_words:
                    score += 1

            if score > best_score:
                best_score = score
                best_match = item

        # Return match if score is high enough
        if best_score >= 2:
            return best_match

        return None

    def _show_category_items(self, phone_number: str, selected_category: Dict, language: str) -> Dict:
        """Show items for selected category"""

        self.db.create_or_update_session(phone_number, 'waiting_for_item', language,
                                         selected_category=selected_category['category_id'])

        items = self.db.get_category_items(selected_category['category_id'])

        if language == 'arabic':
            response = f"قائمة {selected_category['category_name_ar']}:\n\n"
            for i, item in enumerate(items, 1):
                response += f"{i}. {item['item_name_ar']}\n"
                response += f"   السعر: {item['price']} دينار\n\n"
            response += "الرجاء اختيار المنتج المطلوب"
        else:
            response = f"{selected_category['category_name_en']} Menu:\n\n"
            for i, item in enumerate(items, 1):
                response += f"{i}. {item['item_name_en']}\n"
                response += f"   Price: {item['price']} IQD\n\n"
            response += "Please select the required item"

        return self._create_response(response)

    def _show_quantity_selection(self, phone_number: str, selected_item: Dict, language: str) -> Dict:
        """Show quantity selection for selected item"""

        self.db.create_or_update_session(phone_number, 'waiting_for_quantity', language,
                                         selected_item=selected_item['id'])

        if language == 'arabic':
            response = f"تم اختيار: {selected_item['item_name_ar']}\n"
            response += f"السعر: {selected_item['price']} دينار\n\n"
            response += "كم الكمية المطلوبة؟"
        else:
            response = f"Selected: {selected_item['item_name_en']}\n"
            response += f"Price: {selected_item['price']} IQD\n\n"
            response += "How many would you like?"

        return self._create_response(response)

    def _show_order_confirmation(self, phone_number: str, order: Dict, location: str, language: str) -> Dict:
        """Show order confirmation summary"""

        if language == 'arabic':
            response = "إليك ملخص طلبك:\n\n"
            response += "الأصناف:\n"
            for item in order['items']:
                response += f"• {item['item_name_ar']} × {item['quantity']} - {item['subtotal']} دينار\n"

            service_type = order['details'].get('service_type', 'غير محدد')
            service_type_ar = 'تناول في المقهى' if service_type == 'dine-in' else 'توصيل'

            response += f"\nنوع الخدمة: {service_type_ar}\n"
            response += f"المكان: {location}\n"
            response += f"السعر الإجمالي: {order['total']} دينار\n\n"
            response += "هل تريد تأكيد هذا الطلب؟\n\n1. نعم\n2. لا"
        else:
            response = "Here is your order summary:\n\n"
            response += "Items:\n"
            for item in order['items']:
                response += f"• {item['item_name_en']} × {item['quantity']} - {item['subtotal']} IQD\n"

            response += f"\nService: {order['details'].get('service_type', 'Not specified')}\n"
            response += f"Location: {location}\n"
            response += f"Total Price: {order['total']} IQD\n\n"
            response += "Would you like to confirm this order?\n\n1. Yes\n2. No"

        return self._create_response(response)

    def _get_step_description(self, step: str) -> str:
        """Get human-readable step description"""
        descriptions = {
            'waiting_for_language': 'Choose language preference (Arabic or English)',
            'waiting_for_category': 'Select menu category',
            'waiting_for_item': 'Choose specific item from category',
            'waiting_for_quantity': 'Specify quantity needed',
            'waiting_for_additional': 'Decide if more items needed',
            'waiting_for_service': 'Choose service type (dine-in or delivery)',
            'waiting_for_location': 'Provide location/table number',
            'waiting_for_confirmation': 'Confirm the complete order'
        }
        return descriptions.get(step, 'Unknown step')

    def _extract_customer_name(self, message_data: Dict) -> str:
        """Extract customer name"""
        if 'contacts' in message_data:
            contacts = message_data.get('contacts', [])
            if contacts and len(contacts) > 0:
                profile = contacts[0].get('profile', {})
                return profile.get('name', 'Customer')
        return 'Customer'

    def _create_response(self, content: str) -> Dict[str, Any]:
        """Create standardized response format"""
        if len(content) > 4000:
            content = content[:3900] + "... (تم اختصار الرسالة)"

        return {
            'type': 'text',
            'content': content,
            'timestamp': datetime.now().isoformat()
        }

    def _show_sub_categories(self, phone_number: str, selected_main_category: Dict, language: str) -> Dict:
        """Show sub categories for selected main category"""
        sub_categories = self.db.get_sub_categories(selected_main_category['id'])
        
        if language == 'arabic':
            response = f"قائمة {selected_main_category['name_ar']}:\n\n"
            for i, sub_cat in enumerate(sub_categories, 1):
                response += f"{i}. {sub_cat['name_ar']}\n"
            response += "\nالرجاء اختيار الفئة الفرعية المطلوبة"
        else:
            response = f"{selected_main_category['name_en']} Menu:\n\n"
            for i, sub_cat in enumerate(sub_categories, 1):
                response += f"{i}. {sub_cat['name_en']}\n"
            response += "\nPlease choose the sub-category"
        
        return self._create_response(response)

    def _show_sub_category_items(self, phone_number: str, selected_sub_category: Dict, language: str) -> Dict:
        """Show items for selected sub category"""
        items = self.db.get_sub_category_items(selected_sub_category['id'])
        
        if language == 'arabic':
            response = f"قائمة {selected_sub_category['name_ar']}:\n\n"
            for i, item in enumerate(items, 1):
                response += f"{i}. {item['item_name_ar']}\n"
                response += f"   السعر: {item['price']} دينار\n\n"
            response += "الرجاء اختيار المنتج المطلوب"
        else:
            response = f"{selected_sub_category['name_en']} Menu:\n\n"
            for i, item in enumerate(items, 1):
                response += f"{i}. {item['item_name_en']}\n"
                response += f"   Price: {item['price']} IQD\n\n"
            response += "Please choose the item"
        
        return self._create_response(response)

    def _match_main_category_by_name(self, text: str, main_categories: list, language: str) -> Optional[Dict]:
        """Enhanced main category matching with natural language understanding"""
        text_lower = text.lower().strip()

        # Direct name matching
        for category in main_categories:
            ar_name = category['name_ar'].lower()
            en_name = category['name_en'].lower()

            if (text_lower == ar_name or text_lower == en_name or
                    text_lower in ar_name or ar_name in text_lower or
                    text_lower in en_name or en_name in text_lower):
                return category

        # Enhanced keyword matching with natural language
        keyword_mapping = {
            # Cold Drinks
            'cold': 1, 'بارد': 1, 'مشروبات باردة': 1, 'باردة': 1, 'شي بارد': 1, 'مشروب بارد': 1,
            'iced': 1, 'مثلج': 1, 'ايس': 1,
            
            # Hot Drinks
            'hot': 2, 'حار': 2, 'مشروبات حارة': 2, 'حارة': 2, 'شي حار': 2, 'مشروب حار': 2,
            'ساخن': 2, 'ساخنة': 2, 'قهوة': 2, 'coffee': 2, 'tea': 2, 'شاي': 2,
            
            # Pastries & Sweets
            'pastry': 3, 'حلويات': 3, 'معجنات': 3, 'sweets': 3, 'حلو': 3, 'حلى': 3,
            'شي حلو': 3, 'حلويات ومعجنات': 3, 'كيك': 3, 'cake': 3, 'toast': 3, 'توست': 3,
            'sandwich': 3, 'سندويش': 3, 'croissant': 3, 'كرواسان': 3,
        }

        # Check for exact keyword matches
        for keyword, category_id in keyword_mapping.items():
            if keyword in text_lower:
                return next((cat for cat in main_categories if cat['id'] == category_id), None)

        # Intent-based matching
        if any(word in text_lower for word in ['اريد شي', 'بدي شي', 'want something', 'need something']):
            # Try to determine intent from context
            if any(word in text_lower for word in ['بارد', 'cold', 'مثلج', 'iced']):
                return next((cat for cat in main_categories if cat['id'] == 1), None)
            elif any(word in text_lower for word in ['حار', 'hot', 'ساخن', 'قهوة', 'coffee']):
                return next((cat for cat in main_categories if cat['id'] == 2), None)
            elif any(word in text_lower for word in ['حلو', 'sweet', 'حلويات', 'كيك', 'cake']):
                return next((cat for cat in main_categories if cat['id'] == 3), None)

        # Fuzzy matching for typos
        import difflib
        
        all_names = []
        for category in main_categories:
            all_names.append(category['name_ar'].lower())
            all_names.append(category['name_en'].lower())
        
        # Common variations and typos
        variations = {
            'مشروبات باردة': 'المشروبات الباردة',
            'مشروبات حارة': 'المشروبات الحارة',
            'حلويات': 'الحلويات والمعجنات',
            'معجنات': 'الحلويات والمعجنات',
            'cold drinks': 'Cold Drinks',
            'hot drinks': 'Hot Drinks',
            'pastries': 'Pastries & Sweets',
        }
        
        # Check variations
        for variation, correct_name in variations.items():
            if variation in text_lower:
                return next((cat for cat in main_categories if correct_name in cat['name_ar'] or correct_name in cat['name_en']), None)
        
        # Fuzzy string matching
        best_match = None
        best_ratio = 0
        
        for name in all_names:
            ratio = difflib.SequenceMatcher(None, text_lower, name).ratio()
            if ratio > 0.6 and ratio > best_ratio:  # 60% similarity threshold
                best_ratio = ratio
                best_match = name
        
        if best_match:
            return next((cat for cat in main_categories 
                        if best_match in cat['name_ar'].lower() or best_match in cat['name_en'].lower()), None)

        return None

    def _match_sub_category_by_name(self, text: str, sub_categories: list, language: str) -> Optional[Dict]:
        """Enhanced sub category matching with natural language understanding"""
        text_lower = text.lower().strip()

        # Direct name matching
        for sub_category in sub_categories:
            ar_name = sub_category['name_ar'].lower()
            en_name = sub_category['name_en'].lower()

            if (text_lower == ar_name or text_lower == en_name or
                    text_lower in ar_name or ar_name in text_lower or
                    text_lower in en_name or en_name in text_lower):
                return sub_category

        # Enhanced keyword matching with synonyms and typos
        keyword_mapping = {
            # Cold Drinks
            'frappuccino': 2, 'فرابتشينو': 2, 'فراب': 2,
            'milkshake': 3, 'ميلك شيك': 3, 'شيك': 3, 'ميلك': 3,
            'iced tea': 4, 'شاي مثلج': 4, 'شاي': 4, 'مثلج': 4,
            'juice': 5, 'عصير': 5, 'عصائر': 5, 'عصائر طازجة': 5, 'طازجة': 5,
            'mojito': 6, 'موهيتو': 6,
            'energy': 7, 'طاقة': 7, 'مشروبات الطاقة': 7, 'مشروب طاقة': 7, 'مشروبات طاقة': 7,
            'soda': 7, 'صودا': 7, 'ماء': 7, 'water': 7,
            
            # Hot Drinks
            'coffee': 8, 'قهوة': 8, 'اسبرسو': 8, 'espresso': 8,
            'latte': 9, 'لاتيه': 9, 'كابتشينو': 9, 'cappuccino': 9,
            'hot': 10, 'ساخن': 10, 'شاي عراقي': 10, 'iraqi tea': 10,
            
            # Pastries & Sweets
            'toast': 11, 'توست': 11,
            'sandwich': 12, 'سندويش': 12, 'سندويشات': 12,
            'croissant': 13, 'كرواسان': 13,
            'pie': 14, 'فطيرة': 14, 'فطائر': 14,
            'cake': 15, 'كيك': 15, 'حلو': 15, 'حلويات': 15, 'حلى': 15,
        }

        # Check for exact keyword matches
        for keyword, sub_category_id in keyword_mapping.items():
            if keyword in text_lower:
                return next((sub_cat for sub_cat in sub_categories if sub_cat['id'] == sub_category_id), None)

        # Fuzzy matching for typos and variations
        import difflib
        
        # Create a list of all possible names
        all_names = []
        for sub_cat in sub_categories:
            all_names.append(sub_cat['name_ar'].lower())
            all_names.append(sub_cat['name_en'].lower())
        
        # Add common variations and typos
        variations = {
            'مشوربات الطاقة': 'مشروبات الطاقة',
            'مشروب طاقة': 'مشروبات الطاقة',
            'مشروبات طاقة': 'مشروبات الطاقة',
            'عصير طازج': 'عصائر طازجة',
            'عصائر طازج': 'عصائر طازجة',
            'شاي مثلج': 'شاي مثلج',
            'ميلك شيك': 'ميلك شيك',
            'فرابتشينو': 'فرابتشينو',
            'موهيتو': 'موهيتو',
            'توست': 'توست',
            'سندويشات': 'سندويشات',
            'كرواسان': 'كرواسان',
            'فطائر': 'فطائر',
            'كيك': 'قطع كيك',
            'حلويات': 'قطع كيك',
            'حلو': 'قطع كيك',
        }
        
        # Check variations
        for variation, correct_name in variations.items():
            if variation in text_lower:
                return next((sub_cat for sub_cat in sub_categories if correct_name in sub_cat['name_ar'].lower()), None)
        
        # Fuzzy string matching
        best_match = None
        best_ratio = 0
        
        for name in all_names:
            ratio = difflib.SequenceMatcher(None, text_lower, name).ratio()
            if ratio > 0.6 and ratio > best_ratio:  # 60% similarity threshold
                best_ratio = ratio
                best_match = name
        
        if best_match:
            return next((sub_cat for sub_cat in sub_categories 
                        if best_match in sub_cat['name_ar'].lower() or best_match in sub_cat['name_en'].lower()), None)

        return None

    def _get_smart_suggestions(self, text: str, sub_categories: list, language: str) -> str:
        """Generate smart suggestions for unclear input"""
        text_lower = text.lower().strip()
        
        suggestions = []
        
        # Check for common patterns
        if 'طاقة' in text_lower or 'energy' in text_lower:
            suggestions.append("مشروبات الطاقة")
        if 'عصير' in text_lower or 'juice' in text_lower:
            suggestions.append("عصائر طازجة")
        if 'شاي' in text_lower or 'tea' in text_lower:
            suggestions.append("شاي مثلج")
        if 'حلو' in text_lower or 'sweet' in text_lower:
            suggestions.append("قطع كيك")
        if 'بارد' in text_lower or 'cold' in text_lower:
            suggestions.append("ايس كوفي")
        
        if suggestions:
            if language == 'arabic':
                return f"هل تقصد: {', '.join(suggestions)}؟"
            else:
                return f"Did you mean: {', '.join(suggestions)}?"
        
        return ""

    def _handle_quantity_selection_enhanced(self, phone_number: str, text: str, language: str, session: Dict) -> Dict:
        """Enhanced quantity selection with better number extraction"""

        selected_item_id = session.get('selected_item')

        if not selected_item_id:
            return self._create_response(
                "خطأ في النظام. الرجاء إعادة البدء\nSystem error. Please restart")

        # Enhanced number extraction for quantities
        quantity = self._extract_number_enhanced(text)

        # Additional validation for quantity context
        if quantity and quantity > 0 and quantity <= 50:  # Reasonable quantity limit
            # Add item to order
            success = self.db.add_item_to_order(phone_number, selected_item_id, quantity)

            if success:
                item = self.db.get_item_by_id(selected_item_id)
                self.db.create_or_update_session(phone_number, 'waiting_for_additional', language, 
                                               session.get('customer_name'), session.get('selected_main_category'), 
                                               session.get('selected_sub_category'))

                if language == 'arabic':
                    response = f"تم إضافة {item['item_name_ar']} × {quantity} إلى طلبك\n\n"
                    response += "هل تريد إضافة المزيد من الأصناف؟\n\n"
                    response += "1. نعم\n"
                    response += "2. لا"
                else:
                    response = f"Added {item['item_name_en']} × {quantity} to your order\n\n"
                    response += "Would you like to add more items?\n\n"
                    response += "1. Yes\n"
                    response += "2. No"

                return self._create_response(response)

        # Invalid quantity
        if language == 'arabic':
            response = "الكمية غير صحيحة. الرجاء إدخال رقم صحيح للكمية (مثل 1، 2، 3)"
        else:
            response = "Invalid quantity. Please enter a valid number for quantity (like 1, 2, 3)"

        return self._create_response(response)

    def _handle_ai_result(self, phone_number: str, ai_result: Dict, session: Dict, language: str) -> Dict:
        """Handle AI processing result"""
        try:
            # Extract action from AI result
            action = ai_result.get('action', '')
            
            if action == 'language_selection':
                return self._handle_language_selection_enhanced(phone_number, ai_result.get('message', ''), session.get('customer_name', 'Customer'))
            elif action == 'show_main_categories':
                return self._handle_main_category_selection_enhanced(phone_number, ai_result.get('message', ''), language, session)
            elif action == 'show_sub_categories':
                return self._handle_sub_category_selection_enhanced(phone_number, ai_result.get('message', ''), language, session)
            elif action == 'show_items':
                return self._handle_item_selection_enhanced(phone_number, ai_result.get('message', ''), language, session)
            elif action == 'ask_quantity':
                return self._handle_quantity_selection_enhanced(phone_number, ai_result.get('message', ''), language, session)
            elif action == 'ask_additional':
                return self._handle_additional_items_enhanced(phone_number, ai_result.get('message', ''), language, session)
            elif action == 'ask_service':
                return self._handle_service_selection_enhanced(phone_number, ai_result.get('message', ''), language, session)
            elif action == 'ask_location':
                return self._handle_location_input_enhanced(phone_number, ai_result.get('message', ''), language, session)
            elif action == 'confirm_order':
                return self._handle_confirmation_enhanced(phone_number, ai_result.get('message', ''), language, session)
            else:
                # Fallback to enhanced processing
                return self._enhanced_fallback_processing(phone_number, session.get('current_step', 'waiting_for_language'), 
                                                        ai_result.get('message', ''), session.get('customer_name', 'Customer'), session, language)
        except Exception as e:
            logger.error(f"❌ Error handling AI result: {e}")
            # Fallback to enhanced processing
            return self._enhanced_fallback_processing(phone_number, session.get('current_step', 'waiting_for_language'), 
                                                    ai_result.get('message', ''), session.get('customer_name', 'Customer'), session, language)