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
        """Route to correct handler based on current step"""
        language = session.get('language_preference', 'arabic')
        customer_name = session.get('customer_name', 'Customer')

        # Convert Arabic numerals
        text = self._convert_arabic_numerals(text)

        if current_step == 'waiting_for_language':
            return self._handle_language_selection(phone_number, text, customer_name)

        elif current_step == 'waiting_for_category':  # FIXED: Use correct step name
            return self._handle_category_selection(phone_number, text, language, session)

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

        else:
            # Unknown step, restart
            logger.warning(f"⚠️ Unknown step: {current_step}, restarting")
            return self._handle_language_selection(phone_number, text, customer_name)

    def _handle_language_selection(self, phone_number: str, text: str, customer_name: str) -> Dict:
        """Handle language selection and show main categories"""
        language = self._detect_language(text)

        if not language:
            # Ask for language selection
            return self._create_response(
                "مرحباً بك في مقهى هيف\n\n"
                "الرجاء اختيار لغتك المفضلة:\n"
                "1. العربية\n"
                "2. English\n\n"
                "Welcome to Hef Cafe\n\n"
                "Please select your preferred language:\n"
                "1. العربية (Arabic)\n"
                "2. English"
            )

        # Create session and show main categories
        success = self.db.create_or_update_session(phone_number, 'waiting_for_category', language, customer_name)

        if success:
            main_categories = self.db.get_main_categories()

            if language == 'arabic':
                response = f"أهلاً وسهلاً {customer_name} في مقهى هيف!\n\n"
                response += "القائمة الرئيسية:\n\n"
                for i, category in enumerate(main_categories, 1):
                    response += f"{i}. {category['name_ar']}\n"
                response += "\nالرجاء اختيار الفئة المطلوبة بالرد بالرقم"
            else:
                response = f"Welcome {customer_name} to Hef Cafe!\n\n"
                response += "Main Menu:\n\n"
                for i, category in enumerate(main_categories, 1):
                    response += f"{i}. {category['name_en']}\n"
                response += "\nPlease select the category by replying with the number"

            return self._create_response(response)

        return self._create_response("خطأ في النظام\nSystem error")

    def _handle_category_selection(self, phone_number: str, text: str, language: str, session: Dict) -> Dict:
        """Handle main category selection"""
        number = self._extract_number(text)
        main_categories = self.db.get_main_categories()

        if number and 1 <= number <= len(main_categories):
            selected_category = main_categories[number - 1]

            # Update session with selected main category
            self.db.create_or_update_session(
                phone_number, 'waiting_for_item', language,
                session.get('customer_name'),
                selected_main_category=selected_category['id']
            )

            # Get all items for this main category (simplified approach)
            items = self.db.get_category_items(selected_category['id'])

            if language == 'arabic':
                response = f"قائمة {selected_category['name_ar']}:\n\n"
                for i, item in enumerate(items, 1):
                    response += f"{i}. {item['item_name_ar']}\n"
                    response += f"   السعر: {item['price']} دينار\n\n"
                response += "الرجاء اختيار المنتج المطلوب"
            else:
                response = f"{selected_category['name_en']} Menu:\n\n"
                for i, item in enumerate(items, 1):
                    response += f"{i}. {item['item_name_en']}\n"
                    response += f"   Price: {item['price']} IQD\n\n"
                response += "Please select the required item"

            return self._create_response(response)

        # Invalid selection
        if language == 'arabic':
            response = "الرقم غير صحيح. الرجاء اختيار من القائمة:\n\n"
            for i, cat in enumerate(main_categories, 1):
                response += f"{i}. {cat['name_ar']}\n"
        else:
            response = "Invalid number. Please choose from the menu:\n\n"
            for i, cat in enumerate(main_categories, 1):
                response += f"{i}. {cat['name_en']}\n"

        return self._create_response(response)

    def _handle_item_selection(self, phone_number: str, text: str, language: str, session: Dict) -> Dict:
        """Handle item selection"""
        selected_main_category_id = session.get('selected_main_category')

        if not selected_main_category_id:
            return self._create_response("خطأ في النظام\nSystem error")

        items = self.db.get_category_items(selected_main_category_id)
        number = self._extract_number(text)

        if number and 1 <= number <= len(items):
            selected_item = items[number - 1]

            # Update session with selected item
            self.db.create_or_update_session(
                phone_number, 'waiting_for_quantity', language,
                session.get('customer_name'),
                selected_main_category=selected_main_category_id,
                selected_item=selected_item['id']
            )

            if language == 'arabic':
                response = f"تم اختيار: {selected_item['item_name_ar']}\n"
                response += f"السعر: {selected_item['price']} دينار\n\n"
                response += "كم الكمية المطلوبة؟"
            else:
                response = f"Selected: {selected_item['item_name_en']}\n"
                response += f"Price: {selected_item['price']} IQD\n\n"
                response += "How many would you like?"

            return self._create_response(response)

        # Invalid selection - show items again
        main_categories = self.db.get_main_categories()
        current_main_category = next((cat for cat in main_categories if cat['id'] == selected_main_category_id), None)

        if language == 'arabic':
            response = f"الرقم غير صحيح. الرجاء اختيار من قائمة {current_main_category['name_ar'] if current_main_category else 'الفئة'}:\n\n"
            for i, item in enumerate(items, 1):
                response += f"{i}. {item['item_name_ar']} - {item['price']} دينار\n"
        else:
            response = f"Invalid number. Please choose from {current_main_category['name_en'] if current_main_category else 'category'} menu:\n\n"
            for i, item in enumerate(items, 1):
                response += f"{i}. {item['item_name_en']} - {item['price']} IQD\n"

        return self._create_response(response)

    def _handle_quantity_selection(self, phone_number: str, text: str, language: str, session: Dict) -> Dict:
        """Handle quantity selection - FIXED"""
        selected_item_id = session.get('selected_item')

        if not selected_item_id:
            return self._create_response("خطأ في النظام\nSystem error")

        quantity = self._extract_number(text)

        if quantity and quantity > 0 and quantity <= 50:
            # Add item to order
            success = self.db.add_item_to_order(phone_number, selected_item_id, quantity)

            if success:
                item = self.db.get_item_by_id(selected_item_id)

                # Update session for additional items
                self.db.create_or_update_session(phone_number, 'waiting_for_additional', language)

                if language == 'arabic':
                    response = f"تم إضافة {item['item_name_ar']} × {quantity} إلى طلبك\n\n"
                    response += "هل تريد إضافة المزيد من الأصناف؟\n\n"
                    response += "1. نعم\n2. لا"
                else:
                    response = f"Added {item['item_name_en']} × {quantity} to your order\n\n"
                    response += "Would you like to add more items?\n\n"
                    response += "1. Yes\n2. No"

                return self._create_response(response)

        # Invalid quantity
        if language == 'arabic':
            return self._create_response("الكمية غير صحيحة. الرجاء إدخال رقم صحيح (1، 2، 3...)")
        else:
            return self._create_response("Invalid quantity. Please enter a valid number (1, 2, 3...)")

    # Helper methods
    def _detect_language(self, text: str) -> Optional[str]:
        """Detect language from text"""
        text_lower = text.lower().strip()

        # Arabic indicators
        if any(indicator in text_lower for indicator in ['عربي', 'العربية', 'مرحبا', 'أهلا', 'اريد', '1', '١']):
            return 'arabic'

        # English indicators
        if any(indicator in text_lower for indicator in ['english', 'hello', 'hi', '2', '٢']):
            return 'english'

        # Default to Arabic if unclear
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
        """Extract number from text"""
        import re

        # Convert Arabic numerals first
        text = self._convert_arabic_numerals(text)

        # Find numbers
        numbers = re.findall(r'\d+', text)

        if numbers:
            return int(numbers[0])

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

    # Add other missing handler methods (additional_items, service_selection, etc.)
    def _handle_additional_items(self, phone_number: str, text: str, language: str, session: Dict) -> Dict:
        """Handle additional items selection"""
        number = self._extract_number(text)

        if number == 1:  # Yes, add more
            self.db.create_or_update_session(phone_number, 'waiting_for_category', language)
            main_categories = self.db.get_main_categories()

            if language == 'arabic':
                response = "ممتاز! اختر من القائمة الرئيسية:\n\n"
                for i, category in enumerate(main_categories, 1):
                    response += f"{i}. {category['name_ar']}\n"
                response += "\nالرجاء اختيار الفئة المطلوبة"
            else:
                response = "Great! Choose from the main menu:\n\n"
                for i, category in enumerate(main_categories, 1):
                    response += f"{i}. {category['name_en']}\n"
                response += "\nPlease choose the category"

            return self._create_response(response)

        elif number == 2:  # No, proceed to service
            self.db.create_or_update_session(phone_number, 'waiting_for_service', language)

            if language == 'arabic':
                response = "ممتاز! الآن دعنا نحدد نوع الخدمة:\n\n"
                response += "1. تناول في المقهى\n2. توصيل\n\nالرجاء اختيار نوع الخدمة"
            else:
                response = "Great! Now let's determine the service type:\n\n"
                response += "1. Dine-in\n2. Delivery\n\nPlease choose the service type"

            return self._create_response(response)

        # Invalid response
        if language == 'arabic':
            return self._create_response("الرجاء الرد بـ '1' لإضافة المزيد أو '2' للمتابعة")
        else:
            return self._create_response("Please reply with '1' to add more or '2' to continue")

    def _handle_service_selection(self, phone_number: str, text: str, language: str, session: Dict) -> Dict:
        """Handle service type selection"""
        number = self._extract_number(text)

        service_type = None
        if number == 1:
            service_type = 'dine-in'
        elif number == 2:
            service_type = 'delivery'

        if service_type:
            self.db.update_order_details(phone_number, service_type=service_type)
            self.db.create_or_update_session(phone_number, 'waiting_for_location', language)

            if language == 'arabic':
                if service_type == 'dine-in':
                    response = "ممتاز! الرجاء تحديد رقم الطاولة (1-7):"
                else:
                    response = "ممتاز! الرجاء مشاركة موقعك أو عنوانك:"
            else:
                if service_type == 'dine-in':
                    response = "Great! Please specify your table number (1-7):"
                else:
                    response = "Great! Please share your location or address:"

            return self._create_response(response)

        # Invalid service type
        if language == 'arabic':
            response = "الرجاء اختيار:\n1. تناول في المقهى\n2. توصيل"
        else:
            response = "Please choose:\n1. Dine-in\n2. Delivery"

        return self._create_response(response)

    def _handle_location_input(self, phone_number: str, text: str, language: str, session: Dict) -> Dict:
        """Handle location input"""
        location = text.strip()

        if location and len(location) >= 1:
            self.db.update_order_details(phone_number, location=location)
            self.db.create_or_update_session(phone_number, 'waiting_for_confirmation', language)

            # Get order summary
            order = self.db.get_user_order(phone_number)

            if language == 'arabic':
                response = "إليك ملخص طلبك:\n\n"
                response += "الأصناف:\n"
                for item in order['items']:
                    response += f"• {item['item_name_ar']} × {item['quantity']} - {item['subtotal']} دينار\n"

                response += f"\nالخدمة: {order['details'].get('service_type', 'غير محدد')}\n"
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

        # Invalid location
        if language == 'arabic':
            return self._create_response("الرجاء تحديد المكان بوضوح")
        else:
            return self._create_response("Please specify the location clearly")

    def _handle_confirmation(self, phone_number: str, text: str, language: str, session: Dict) -> Dict:
        """Handle order confirmation"""
        number = self._extract_number(text)

        if number == 1:  # Confirm order
            try:
                order = self.db.get_user_order(phone_number)
                total_amount = order.get('total', 0)

                order_id = self.db.complete_order(phone_number)

                if order_id:
                    if language == 'arabic':
                        response = f"تم تأكيد طلبك بنجاح!\n\n"
                        response += f"رقم الطلب: {order_id}\n"
                        response += f"المبلغ الإجمالي: {total_amount} دينار\n\n"
                        response += f"شكراً لك لاختيار مقهى هيف!"
                    else:
                        response = f"Your order has been confirmed successfully!\n\n"
                        response += f"Order ID: {order_id}\n"
                        response += f"Total Amount: {total_amount} IQD\n\n"
                        response += f"Thank you for choosing Hef Cafe!"

                    return self._create_response(response)

            except Exception as e:
                logger.error(f"❌ Error completing order: {e}")
                if language == 'arabic':
                    return self._create_response("عذراً، حدث خطأ في إتمام الطلب")
                else:
                    return self._create_response("Sorry, there was an error completing your order")

        elif number == 2:  # Cancel order
            try:
                customer_name = session.get('customer_name', 'Customer')
                self.db.delete_session(phone_number)

                if language == 'arabic':
                    response = f"تم إلغاء الطلب. شكراً لك {customer_name} لزيارة مقهى هيف.\n\n"
                    response += "يمكنك البدء بطلب جديد في أي وقت بإرسال 'مرحبا'"
                else:
                    response = f"Order cancelled. Thank you {customer_name} for visiting Hef Cafe.\n\n"
                    response += "You can start a new order anytime by sending 'hello'"

                return self._create_response(response)

            except Exception as e:
                logger.error(f"❌ Error cancelling order: {e}")
                if language == 'arabic':
                    return self._create_response("عذراً، حدث خطأ في إلغاء الطلب")
                else:
                    return self._create_response("Sorry, there was an error cancelling your order")

        # Invalid confirmation
        if language == 'arabic':
            return self._create_response("الرجاء الرد بـ '1' للتأكيد أو '2' للإلغاء")
        else:
            return self._create_response("Please reply with '1' to confirm or '2' to cancel")
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
        """ENHANCED: Better number extraction with validation"""
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

        # Try word numbers
        word_numbers = {
            'واحد': 1, 'اثنين': 2, 'ثلاثة': 3, 'اربعة': 4, 'خمسة': 5,
            'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
            'first': 1, 'second': 2, 'third': 3, 'fourth': 4, 'fifth': 5
        }

        text_lower = text.lower()
        for word, number in word_numbers.items():
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