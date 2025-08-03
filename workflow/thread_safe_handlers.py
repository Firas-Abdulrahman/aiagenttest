# workflow/thread_safe_handlers.py - NEW FILE
"""
Thread-safe message handlers with proper user isolation
"""
import logging
import time
from typing import Dict, Any, Optional
from datetime import datetime

from utils.thread_safe_session import session_manager
from database.thread_safe_manager import ThreadSafeDatabaseManager

logger = logging.getLogger(__name__)


class ThreadSafeMessageHandler:
    """Thread-safe message handler with user isolation"""

    def __init__(self, database_manager: ThreadSafeDatabaseManager, ai_processor=None, action_executor=None):
        self.db = database_manager
        self.ai = ai_processor
        self.executor = action_executor

    def handle_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Main message handling with thread safety and user isolation"""

        # Extract basic message info
        phone_number = message_data.get('from')
        message_id = message_data.get('id', f"msg_{time.time()}")
        text = message_data.get('text', {}).get('body', '').strip()

        if not phone_number:
            return self._create_error_response("Invalid phone number")

        # Check for message duplication
        if session_manager.is_message_duplicate(phone_number, message_id):
            logger.warning(f"🔄 Duplicate message detected for {phone_number}")
            return self._create_response("Message already processed")

        # Use user-specific lock for entire processing
        try:
            with session_manager.user_session_lock(phone_number):
                return self._process_user_message_safely(phone_number, text, message_data)

        except TimeoutError:
            logger.error(f"⏰ Timeout acquiring lock for user {phone_number}")
            return self._create_error_response(
                "الخدمة مشغولة حالياً. الرجاء إعادة المحاولة خلال ثواني\n"
                "Service busy. Please try again in a few seconds"
            )
        except Exception as e:
            logger.error(f"❌ Error processing message for {phone_number}: {e}")
            return self._create_error_response(
                "حدث خطأ. الرجاء إعادة المحاولة\n"
                "An error occurred. Please try again"
            )

    def _process_user_message_safely(self, phone_number: str, text: str, message_data: Dict) -> Dict:
        """Process user message within user lock"""

        # Mark user as processing
        session_manager.set_user_processing(phone_number, True)

        try:
            # Extract customer info
            customer_name = self._extract_customer_name(message_data)

            # Get current user state
            user_state = session_manager.get_user_state(phone_number)
            current_step = user_state.current_step if user_state else 'waiting_for_language'
            language = user_state.language_preference if user_state else None

            logger.info(f"👤 Processing for {phone_number}: '{text}' at step '{current_step}'")

            # Log conversation
            self.db.log_conversation(phone_number, 'user_message', text, current_step=current_step)

            # Route to appropriate handler based on current step
            response = self._route_message_by_step(phone_number, current_step, text, customer_name, user_state)

            # Log response
            self.db.log_conversation(phone_number, 'bot_response', response.get('content', ''))

            return response

        finally:
            # Always clear processing flag
            session_manager.set_user_processing(phone_number, False)

    def _route_message_by_step(self, phone_number: str, current_step: str, text: str,
                               customer_name: str, user_state) -> Dict:
        """Route message to appropriate handler based on current step"""

        # Convert Arabic numerals for consistency
        text = self._convert_arabic_numerals(text)

        # Check for restart commands
        if self._is_restart_command(text):
            self.db.delete_session(phone_number)
            return self._handle_language_selection(phone_number, text, customer_name)

        # Route based on current step
        if current_step == 'waiting_for_language':
            return self._handle_language_selection(phone_number, text, customer_name)

        elif current_step == 'waiting_for_category':
            language = user_state.language_preference if user_state else 'arabic'
            return self._handle_category_selection(phone_number, text, language, customer_name)

        elif current_step == 'waiting_for_item':
            language = user_state.language_preference if user_state else 'arabic'
            return self._handle_item_selection(phone_number, text, language, user_state)

        elif current_step == 'waiting_for_quantity':
            language = user_state.language_preference if user_state else 'arabic'
            return self._handle_quantity_selection(phone_number, text, language, user_state)

        elif current_step == 'waiting_for_additional':
            language = user_state.language_preference if user_state else 'arabic'
            return self._handle_additional_selection(phone_number, text, language)

        elif current_step == 'waiting_for_service':
            language = user_state.language_preference if user_state else 'arabic'
            return self._handle_service_selection(phone_number, text, language)

        elif current_step == 'waiting_for_location':
            language = user_state.language_preference if user_state else 'arabic'
            return self._handle_location_input(phone_number, text, language)

        elif current_step == 'waiting_for_confirmation':
            language = user_state.language_preference if user_state else 'arabic'
            return self._handle_order_confirmation(phone_number, text, language)

        else:
            # Unknown step - restart
            logger.warning(f"⚠️ Unknown step '{current_step}' for user {phone_number}")
            self.db.delete_session(phone_number)
            return self._handle_language_selection(phone_number, text, customer_name)

    def _handle_language_selection(self, phone_number: str, text: str, customer_name: str) -> Dict:
        """Handle language selection step"""
        language = self._detect_language(text)

        if language:
            # Create session and move to category selection
            success = self.db.create_or_update_session(
                phone_number, 'waiting_for_category', language, customer_name
            )

            if success:
                # Show main categories
                main_categories = self.db.get_main_categories()

                if language == 'arabic':
                    response = f"أهلاً وسهلاً {customer_name} في مقهى هيف! ☕\n\n"
                    response += "القائمة الرئيسية:\n\n"
                    for i, category in enumerate(main_categories, 1):
                        response += f"{i}. {category['name_ar']}\n"
                    response += "\nالرجاء اختيار الفئة المطلوبة بالرد بالرقم"
                else:
                    response = f"Welcome {customer_name} to Hef Cafe! ☕\n\n"
                    response += "Main Menu:\n\n"
                    for i, category in enumerate(main_categories, 1):
                        response += f"{i}. {category['name_en']}\n"
                    response += "\nPlease select the category by replying with the number"

                return self._create_response(response)

        # Language not detected - show language selection
        return self._create_response(
            "مرحباً بك في مقهى هيف ☕\n\n"
            "الرجاء اختيار لغتك المفضلة:\n"
            "1. العربية\n"
            "2. English\n\n"
            "Welcome to Hef Cafe ☕\n\n"
            "Please select your preferred language:\n"
            "1. العربية (Arabic)\n"
            "2. English"
        )

    def _handle_category_selection(self, phone_number: str, text: str, language: str, customer_name: str) -> Dict:
        """Handle main category selection"""
        number = self._extract_number(text)
        main_categories = self.db.get_main_categories()

        if number and 1 <= number <= len(main_categories):
            selected_category = main_categories[number - 1]

            # Update session with selected category
            success = self.db.create_or_update_session(
                phone_number, 'waiting_for_item', language, customer_name,
                selected_main_category=selected_category['id']
            )

            if success:
                # Get items for this category
                items = self.db.get_category_items(selected_category['id'])

                if language == 'arabic':
                    response = f"قائمة {selected_category['name_ar']}:\n\n"
                    for i, item in enumerate(items, 1):
                        response += f"{i}. {item['item_name_ar']}\n"
                        response += f"   السعر: {item['price']:,} دينار\n\n"
                    response += "الرجاء اختيار المنتج المطلوب بالرد بالرقم"
                else:
                    response = f"{selected_category['name_en']} Menu:\n\n"
                    for i, item in enumerate(items, 1):
                        response += f"{i}. {item['item_name_en']}\n"
                        response += f"   Price: {item['price']:,} IQD\n\n"
                    response += "Please select the item by replying with the number"

                return self._create_response(response)

        # Invalid selection - show categories again
        if language == 'arabic':
            response = "الرقم غير صحيح. الرجاء اختيار من القائمة:\n\n"
            for i, cat in enumerate(main_categories, 1):
                response += f"{i}. {cat['name_ar']}\n"
            response += "\nالرجاء الاختيار بالرقم"
        else:
            response = "Invalid number. Please choose from the menu:\n\n"
            for i, cat in enumerate(main_categories, 1):
                response += f"{i}. {cat['name_en']}\n"
            response += "\nPlease choose by number"

        return self._create_response(response)

    def _handle_item_selection(self, phone_number: str, text: str, language: str, user_state) -> Dict:
        """Handle item selection"""
        if not user_state or not user_state.selected_main_category:
            return self._create_error_response("خطأ في النظام\nSystem error")

        items = self.db.get_category_items(user_state.selected_main_category)
        number = self._extract_number(text)

        if number and 1 <= number <= len(items):
            selected_item = items[number - 1]

            # Update session with selected item
            success = self.db.create_or_update_session(
                phone_number, 'waiting_for_quantity', language, user_state.customer_name,
                selected_main_category=user_state.selected_main_category,
                selected_item=selected_item['id']
            )

            if success:
                if language == 'arabic':
                    response = f"تم اختيار: {selected_item['item_name_ar']}\n"
                    response += f"السعر: {selected_item['price']:,} دينار\n\n"
                    response += "كم الكمية المطلوبة؟ (اكتب رقم من 1 إلى 10)"
                else:
                    response = f"Selected: {selected_item['item_name_en']}\n"
                    response += f"Price: {selected_item['price']:,} IQD\n\n"
                    response += "How many would you like? (enter a number from 1 to 10)"

                return self._create_response(response)

        # Invalid selection - show items again
        main_categories = self.db.get_main_categories()
        current_category = next(
            (cat for cat in main_categories if cat['id'] == user_state.selected_main_category),
            None
        )

        if language == 'arabic':
            response = f"الرقم غير صحيح. الرجاء اختيار من قائمة {current_category['name_ar'] if current_category else 'الفئة'}:\n\n"
            for i, item in enumerate(items, 1):
                response += f"{i}. {item['item_name_ar']} - {item['price']:,} دينار\n"
            response += "\nالرجاء الاختيار بالرقم"
        else:
            response = f"Invalid number. Please choose from {current_category['name_en'] if current_category else 'category'} menu:\n\n"
            for i, item in enumerate(items, 1):
                response += f"{i}. {item['item_name_en']} - {item['price']:,} IQD\n"
            response += "\nPlease choose by number"

        return self._create_response(response)

    def _handle_quantity_selection(self, phone_number: str, text: str, language: str, user_state) -> Dict:
        """Handle quantity selection"""
        if not user_state or not user_state.selected_item:
            return self._create_error_response("خطأ في النظام\nSystem error")

        quantity = self._extract_number(text)

        if quantity and 1 <= quantity <= 10:  # Reasonable quantity limit
            # Add item to order
            success = self.db.add_item_to_order(phone_number, user_state.selected_item, quantity)

            if success:
                item = self.db.get_item_by_id(user_state.selected_item)

                # Update session to additional items step
                self.db.create_or_update_session(
                    phone_number, 'waiting_for_additional', language, user_state.customer_name
                )

                if language == 'arabic':
                    response = f"✅ تم إضافة {item['item_name_ar']} × {quantity} إلى طلبك\n\n"
                    response += "هل تريد إضافة المزيد من الأصناف؟\n\n"
                    response += "1. نعم - إضافة المزيد\n"
                    response += "2. لا - إكمال الطلب"
                else:
                    response = f"✅ Added {item['item_name_en']} × {quantity} to your order\n\n"
                    response += "Would you like to add more items?\n\n"
                    response += "1. Yes - Add more\n"
                    response += "2. No - Complete order"

                return self._create_response(response)

        # Invalid quantity
        if language == 'arabic':
            response = "الكمية غير صحيحة. الرجاء إدخال رقم من 1 إلى 10"
        else:
            response = "Invalid quantity. Please enter a number from 1 to 10"

        return self._create_response(response)

    def _handle_additional_selection(self, phone_number: str, text: str, language: str) -> Dict:
        """Handle additional items selection"""
        number = self._extract_number(text)

        if number == 1:  # Add more items
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
                response += "\nPlease choose the required category"

            return self._create_response(response)

        elif number == 2:  # Complete order
            self.db.create_or_update_session(phone_number, 'waiting_for_service', language)

            if language == 'arabic':
                response = "ممتاز! الآن دعنا نحدد نوع الخدمة:\n\n"
                response += "1. تناول في المقهى 🏪\n"
                response += "2. توصيل 🚗\n\n"
                response += "الرجاء اختيار نوع الخدمة"
            else:
                response = "Great! Now let's determine the service type:\n\n"
                response += "1. Dine-in 🏪\n"
                response += "2. Delivery 🚗\n\n"
                response += "Please choose the service type"

            return self._create_response(response)

        # Invalid choice
        if language == 'arabic':
            response = "الرجاء الاختيار:\n1. نعم\n2. لا"
        else:
            response = "Please choose:\n1. Yes\n2. No"

        return self._create_response(response)

    def _handle_service_selection(self, phone_number: str, text: str, language: str) -> Dict:
        """Handle service type selection"""
        number = self._extract_number(text)

        service_type = None
        if number == 1:
            service_type = 'dine-in'
        elif number == 2:
            service_type = 'delivery'

        if service_type:
            # Update order details
            self.db.update_order_details(phone_number, service_type=service_type)
            self.db.create_or_update_session(phone_number, 'waiting_for_location', language)

            if language == 'arabic':
                if service_type == 'dine-in':
                    response = "ممتاز! الرجاء تحديد رقم الطاولة (1-20):"
                else:
                    response = "ممتاز! الرجاء كتابة عنوانك أو إرسال موقعك:"
            else:
                if service_type == 'dine-in':
                    response = "Great! Please specify your table number (1-20):"
                else:
                    response = "Great! Please write your address or send your location:"

            return self._create_response(response)

        # Invalid service selection
        if language == 'arabic':
            response = "الرجاء الاختيار:\n1. تناول في المقهى\n2. توصيل"
        else:
            response = "Please choose:\n1. Dine-in\n2. Delivery"

        return self._create_response(response)

    def _handle_location_input(self, phone_number: str, text: str, language: str) -> Dict:
        """Handle location input"""
        location = text.strip()

        if location and len(location) >= 2:
            # Update order details with location
            self.db.update_order_details(phone_number, location=location)
            self.db.create_or_update_session(phone_number, 'waiting_for_confirmation', language)

            # Get order summary
            order = self.db.get_user_order(phone_number)

            if order and order['items']:
                if language == 'arabic':
                    response = "📋 ملخص طلبك:\n\n"
                    response += "الأصناف:\n"
                    for item in order['items']:
                        response += f"• {item['item_name_ar']} × {item['quantity']} - {item['subtotal']:,} دينار\n"

                    service_type = order['details'].get('service_type', 'غير محدد')
                    service_ar = 'تناول في المقهى' if service_type == 'dine-in' else 'توصيل'

                    response += f"\nنوع الخدمة: {service_ar}\n"
                    response += f"المكان: {location}\n"
                    response += f"💰 السعر الإجمالي: {order['total']:,} دينار\n\n"
                    response += "هل تريد تأكيد هذا الطلب؟\n\n"
                    response += "1. نعم - تأكيد الطلب ✅\n"
                    response += "2. لا - إلغاء الطلب ❌"
                else:
                    response = "📋 Your Order Summary:\n\n"
                    response += "Items:\n"
                    for item in order['items']:
                        response += f"• {item['item_name_en']} × {item['quantity']} - {item['subtotal']:,} IQD\n"

                    response += f"\nService: {order['details'].get('service_type', 'Not specified').title()}\n"
                    response += f"Location: {location}\n"
                    response += f"💰 Total Price: {order['total']:,} IQD\n\n"
                    response += "Would you like to confirm this order?\n\n"
                    response += "1. Yes - Confirm Order ✅\n"
                    response += "2. No - Cancel Order ❌"

                return self._create_response(response)

        # Invalid location
        if language == 'arabic':
            response = "الرجاء تحديد المكان بوضوح (على الأقل حرفين)"
        else:
            response = "Please specify the location clearly (at least 2 characters)"

        return self._create_response(response)

    def _handle_order_confirmation(self, phone_number: str, text: str, language: str) -> Dict:
        """Handle final order confirmation"""
        number = self._extract_number(text)

        if number == 1:  # Confirm order
            try:
                # Get order total before completion
                order = self.db.get_user_order(phone_number)
                total_amount = order.get('total', 0) if order else 0

                # Complete the order
                order_id = self.db.complete_order(phone_number)

                if order_id:
                    if language == 'arabic':
                        response = f"🎉 تم تأكيد طلبك بنجاح!\n\n"
                        response += f"📋 رقم الطلب: {order_id}\n"
                        response += f"💰 المبلغ الإجمالي: {total_amount:,} دينار\n\n"
                        response += f"⏰ سيكون طلبك جاهز خلال 10-15 دقيقة\n"
                        response += f"💳 الرجاء دفع المبلغ عند الاستلام\n\n"
                        response += f"شكراً لك لاختيار مقهى هيف! ☕"
                    else:
                        response = f"🎉 Your order has been confirmed successfully!\n\n"
                        response += f"📋 Order ID: {order_id}\n"
                        response += f"💰 Total Amount: {total_amount:,} IQD\n\n"
                        response += f"⏰ Your order will be ready in 10-15 minutes\n"
                        response += f"💳 Please pay the amount upon pickup/delivery\n\n"
                        response += f"Thank you for choosing Hef Cafe! ☕"

                    return self._create_response(response)

            except Exception as e:
                logger.error(f"❌ Error completing order for {phone_number}: {e}")

                if language == 'arabic':
                    response = "عذراً، حدث خطأ في إتمام الطلب. الرجاء إعادة المحاولة"
                else:
                    response = "Sorry, there was an error completing your order. Please try again"

                return self._create_response(response)

        elif number == 2:  # Cancel order
            try:
                # Get customer name before deletion
                user_state = session_manager.get_user_state(phone_number)
                customer_name = user_state.customer_name if user_state else 'Customer'

                # Delete session and order
                self.db.delete_session(phone_number)

                if language == 'arabic':
                    response = f"❌ تم إلغاء الطلب.\n\n"
                    response += f"شكراً لك {customer_name} لزيارة مقهى هيف.\n"
                    response += f"يمكنك البدء بطلب جديد في أي وقت بإرسال 'مرحبا' ☕"
                else:
                    response = f"❌ Order cancelled.\n\n"
                    response += f"Thank you {customer_name} for visiting Hef Cafe.\n"
                    response += f"You can start a new order anytime by sending 'hello' ☕"

                return self._create_response(response)

            except Exception as e:
                logger.error(f"❌ Error cancelling order for {phone_number}: {e}")

                if language == 'arabic':
                    response = "حدث خطأ في إلغاء الطلب"
                else:
                    response = "Error cancelling order"

                return self._create_response(response)

        # Invalid confirmation choice
        if language == 'arabic':
            response = "الرجاء الاختيار:\n1. نعم - تأكيد\n2. لا - إلغاء"
        else:
            response = "Please choose:\n1. Yes - Confirm\n2. No - Cancel"

        return self._create_response(response)

    # Utility Methods
    def _is_restart_command(self, text: str) -> bool:
        """Check if text is a restart command"""
        restart_words = [
            'مرحبا', 'hello', 'hi', 'start', 'restart', 'طلب جديد', 'new order',
            'ابدأ من جديد', 'start over', 'السلام عليكم', 'أهلا'
        ]
        text_lower = text.lower().strip()
        return any(word in text_lower for word in restart_words)

    def _detect_language(self, text: str) -> Optional[str]:
        """Detect language from user input"""
        text_lower = text.lower().strip()

        # Strong Arabic indicators
        arabic_indicators = [
            'عربي', 'العربية', 'مرحبا', 'أهلا', 'اريد', 'بدي', '1', '١'
        ]

        # Strong English indicators
        english_indicators = [
            'english', 'hello', 'hi', 'want', 'need', '2', '٢'
        ]

        if any(indicator in text_lower for indicator in arabic_indicators):
            return 'arabic'
        elif any(indicator in text_lower for indicator in english_indicators):
            return 'english'

        # Default to Arabic for ambiguous cases
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
            number = int(numbers[0])
            # Reasonable validation
            if 1 <= number <= 100:
                return number

        return None

    def _extract_customer_name(self, message_data: Dict) -> str:
        """Extract customer name from message data"""
        if 'contacts' in message_data:
            contacts = message_data.get('contacts', [])
            if contacts and len(contacts) > 0:
                profile = contacts[0].get('profile', {})
                name = profile.get('name', '').strip()
                if name and len(name) <= 50:
                    return name

        # Fallback to generic name
        phone = message_data.get('from', '')
        if phone:
            return f"Customer {phone[-4:]}"

        return "Valued Customer"

    def _create_response(self, content: str) -> Dict[str, Any]:
        """Create standardized response"""
        # Truncate if too long
        if len(content) > 4000:
            content = content[:3900] + "...\n(تم اختصار الرسالة)"

        return {
            'type': 'text',
            'content': content,
            'timestamp': datetime.now().isoformat()
        }

    def _create_error_response(self, message: str) -> Dict[str, Any]:
        """Create error response"""
        return self._create_response(message)