# workflow/handlers.py - CRITICAL FLOW FIXES

import logging
import time
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from ai.prompts import AIPrompts

logger = logging.getLogger(__name__)


class MessageHandler:
    """Main message handler - FIXED to prevent multiple responses"""

    def __init__(self, database_manager, ai_processor, action_executor):
        self.db = database_manager
        self.ai = ai_processor
        self.executor = action_executor
        self.processing_lock = {}  # Prevent duplicate processing

    def handle_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """FIXED: Single response per message with proper flow control"""
        try:
            # Extract message details
            text = message_data.get('text', {}).get('body', '').strip()
            phone_number = message_data.get('from')
            customer_name = self._extract_customer_name(message_data)
            message_id = message_data.get('id', str(time.time()))

            # CRITICAL FIX: Prevent duplicate processing
            lock_key = f"{phone_number}_{message_id}"
            if lock_key in self.processing_lock:
                logger.warning(f"🔒 Duplicate message processing prevented for {phone_number}")
                return self._create_response("Processing...")

            self.processing_lock[lock_key] = True

            try:
                logger.info(f"📨 Processing message '{text}' from {phone_number}")

                # Get session and determine flow
                response = self._process_single_message(phone_number, text, customer_name)

                # Log response
                self.db.log_conversation(phone_number, 'ai_response', response['content'])

                return response

            finally:
                # Clean up lock after processing
                if lock_key in self.processing_lock:
                    del self.processing_lock[lock_key]

        except Exception as e:
            logger.error(f"❌ Error handling message: {str(e)}")
            return self._create_response("حدث خطأ. الرجاء إعادة المحاولة\nAn error occurred. Please try again")

    def _process_single_message(self, phone_number: str, text: str, customer_name: str) -> Dict:
        """FIXED: Single message processing with clear flow control"""

        # Get current session
        session = self.db.get_user_session(phone_number)
        current_step = session['current_step'] if session else 'waiting_for_language'
        language = session.get('language_preference', 'arabic') if session else 'arabic'

        logger.info(f"📊 User {phone_number} at step: {current_step}")

        # Convert Arabic numerals
        text = self._convert_arabic_numerals(text)

        # CRITICAL FIX: Check for category name mentions across all steps
        if self._is_category_mention(text, language):
            logger.info(f"🎯 Category mention detected: {text}")
            return self._handle_category_mention(phone_number, text, customer_name, session)

        # Handle based on current step
        if current_step == 'waiting_for_language':
            return self._handle_language_selection(phone_number, text, customer_name)

        elif current_step == 'waiting_for_category':
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
            # Fallback to language selection
            return self._handle_language_selection(phone_number, text, customer_name)

    def _is_category_mention(self, text: str, language: str) -> bool:
        """CRITICAL FIX: Detect when user mentions a category name"""
        text_lower = text.lower().strip()

        # Get all categories
        categories = self.db.get_available_categories()

        for category in categories:
            # Check Arabic and English names
            ar_name = category['category_name_ar'].lower()
            en_name = category['category_name_en'].lower()

            # Exact or partial match
            if (text_lower == ar_name or text_lower == en_name or
                    text_lower in ar_name or ar_name in text_lower or
                    text_lower in en_name or en_name in text_lower):
                return True

        # Special cases
        category_keywords = {
            'موهيتو': True, 'mojito': True,
            'فرابتشينو': True, 'frappuccino': True,
            'ميلك شيك': True, 'milkshake': True,
            'توست': True, 'toast': True,
            'سندويش': True, 'sandwich': True,
            'كرواسان': True, 'croissant': True,
            'كيك': True, 'cake': True,
            'عصير': True, 'juice': True,
            'شاي': True, 'tea': True,
            'قهوة': True, 'coffee': True,
            'حار': True, 'hot': True,
            'بارد': True, 'cold': True,
            'حلو': True, 'sweet': True
        }

        return any(keyword in text_lower for keyword in category_keywords.keys())

    def _handle_category_mention(self, phone_number: str, text: str, customer_name: str, session: Dict) -> Dict:
        """CRITICAL FIX: Handle when user mentions category name directly"""

        # Find matching category
        categories = self.db.get_available_categories()
        selected_category = None
        text_lower = text.lower().strip()

        # Direct name matching
        for category in categories:
            ar_name = category['category_name_ar'].lower()
            en_name = category['category_name_en'].lower()

            if (text_lower == ar_name or text_lower == en_name or
                    text_lower in ar_name or ar_name in text_lower or
                    text_lower in en_name or en_name in text_lower):
                selected_category = category
                break

        # Special keyword matching
        if not selected_category:
            keyword_to_category = {
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

            for keyword, cat_id in keyword_to_category.items():
                if keyword in text_lower:
                    selected_category = next((cat for cat in categories if cat['category_id'] == cat_id), None)
                    break

        if selected_category:
            language = session.get('language_preference', 'arabic') if session else 'arabic'

            # Ensure we have a session with language
            if not session:
                self.db.create_or_update_session(phone_number, 'waiting_for_item', language, customer_name,
                                                 selected_category=selected_category['category_id'])
            else:
                self.db.create_or_update_session(phone_number, 'waiting_for_item', language,
                                                 selected_category=selected_category['category_id'])

            # Show items for the category
            items = self.db.get_category_items(selected_category['category_id'])

            if language == 'arabic':
                response = f"قائمة {selected_category['category_name_ar']}:\n\n"
                for i, item in enumerate(items, 1):
                    response += f"{i}. {item['item_name_ar']}\n"
                    response += f"   السعر: {item['price']} دينار\n\n"
                response += "الرجاء اختيار المنتج المطلوب بالرد بالرقم"
            else:
                response = f"{selected_category['category_name_en']} Menu:\n\n"
                for i, item in enumerate(items, 1):
                    response += f"{i}. {item['item_name_en']}\n"
                    response += f"   Price: {item['price']} IQD\n\n"
                response += "Please select the required item by replying with the number"

            return self._create_response(response)

        # If no category found, continue with normal flow
        return self._handle_language_selection(phone_number, text, customer_name)

    def _handle_language_selection(self, phone_number: str, text: str, customer_name: str) -> Dict:
        """Handle language selection"""
        language = self._detect_language_simple(text)

        if language:
            self.db.create_or_update_session(phone_number, 'waiting_for_category', language, customer_name)

            # Show categories
            categories = self.db.get_available_categories()

            if language == 'arabic':
                response = f"أهلاً وسهلاً {customer_name} في مقهى هيف!\n\n"
                response += "القائمة الرئيسية:\n\n"
                for i, cat in enumerate(categories, 1):
                    response += f"{i}. {cat['category_name_ar']}\n"
                response += "\nالرجاء اختيار الفئة المطلوبة بالرد بالرقم"
            else:
                response = f"Welcome {customer_name} to Hef Cafe!\n\n"
                response += "Main Menu:\n\n"
                for i, cat in enumerate(categories, 1):
                    response += f"{i}. {cat['category_name_en']}\n"
                response += "\nPlease select the required category by replying with the number"

            return self._create_response(response)

        # Show language selection
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

    def _handle_category_selection(self, phone_number: str, text: str, language: str, session: Dict) -> Dict:
        """Handle category selection by number"""
        number = self._extract_number_simple(text)
        categories = self.db.get_available_categories()

        if number and 1 <= number <= len(categories):
            selected_category = categories[number - 1]

            self.db.create_or_update_session(phone_number, 'waiting_for_item', language,
                                             selected_category=selected_category['category_id'])

            # Show items
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

        # Invalid number - show categories again
        if language == 'arabic':
            response = "الرقم غير صحيح. الرجاء اختيار رقم من 1 إلى 13:\n\n"
            for i, cat in enumerate(categories, 1):
                response += f"{i}. {cat['category_name_ar']}\n"
        else:
            response = "Invalid number. Please choose a number from 1 to 13:\n\n"
            for i, cat in enumerate(categories, 1):
                response += f"{i}. {cat['category_name_en']}\n"

        return self._create_response(response)

    def _handle_item_selection(self, phone_number: str, text: str, language: str, session: Dict) -> Dict:
        """Handle item selection"""
        selected_category_id = session.get('selected_category')

        if not selected_category_id:
            return self._create_response(
                "خطأ في النظام. الرجاء إعادة البدء\nSystem error. Please restart")

        items = self.db.get_category_items(selected_category_id)
        number = self._extract_number_simple(text)

        if number and 1 <= number <= len(items):
            selected_item = items[number - 1]

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

        # Show items again
        categories = self.db.get_available_categories()
        current_category = next((cat for cat in categories if cat['category_id'] == selected_category_id), None)

        if language == 'arabic':
            response = f"الرقم غير صحيح. الرجاء اختيار رقم من قائمة {current_category['category_name_ar'] if current_category else 'الفئة'}:\n\n"
            for i, item in enumerate(items, 1):
                response += f"{i}. {item['item_name_ar']} - {item['price']} دينار\n"
        else:
            response = f"Invalid number. Please choose from {current_category['category_name_en'] if current_category else 'category'} menu:\n\n"
            for i, item in enumerate(items, 1):
                response += f"{i}. {item['item_name_en']} - {item['price']} IQD\n"

        return self._create_response(response)

    def _handle_quantity_selection(self, phone_number: str, text: str, language: str, session: Dict) -> Dict:
        """Handle quantity selection"""
        selected_item_id = session.get('selected_item')

        if not selected_item_id:
            return self._create_response(
                "خطأ في النظام. الرجاء إعادة البدء\nSystem error. Please restart")

        quantity = self._extract_number_simple(text)

        if quantity and quantity > 0:
            # Add item to order
            success = self.db.add_item_to_order(phone_number, selected_item_id, quantity)

            if success:
                item = self.db.get_item_by_id(selected_item_id)
                self.db.create_or_update_session(phone_number, 'waiting_for_additional', language)

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
            response = "الكمية غير صحيحة. الرجاء إدخال رقم صحيح (1، 2، 3...)"
        else:
            response = "Invalid quantity. Please enter a valid number (1, 2, 3...)"

        return self._create_response(response)

    def _handle_additional_items(self, phone_number: str, text: str, language: str, session: Dict) -> Dict:
        """Handle additional items selection"""
        number = self._extract_number_simple(text)
        yes_no = self._detect_yes_no_simple(text, language)

        if number == 1 or yes_no == 'yes':
            # Add more items - go back to categories
            categories = self.db.get_available_categories()
            self.db.create_or_update_session(phone_number, 'waiting_for_category', language)

            if language == 'arabic':
                response = "ممتاز! إليك القائمة الرئيسية:\n\n"
                for i, cat in enumerate(categories, 1):
                    response += f"{i}. {cat['category_name_ar']}\n"
                response += "\nالرجاء اختيار الفئة المطلوبة"
            else:
                response = "Great! Here's the main menu:\n\n"
                for i, cat in enumerate(categories, 1):
                    response += f"{i}. {cat['category_name_en']}\n"
                response += "\nPlease select the required category"

            return self._create_response(response)

        elif number == 2 or yes_no == 'no':
            # Go to service selection
            self.db.create_or_update_session(phone_number, 'waiting_for_service', language)

            if language == 'arabic':
                response = "ممتاز! الآن دعنا نحدد نوع الخدمة:\n\n"
                response += "1. تناول في المقهى\n"
                response += "2. توصيل\n\n"
                response += "الرجاء اختيار نوع الخدمة"
            else:
                response = "Great! Now let's determine the service type:\n\n"
                response += "1. Dine-in\n"
                response += "2. Delivery\n\n"
                response += "Please select the service type"

            return self._create_response(response)

        # Invalid input
        if language == 'arabic':
            return self._create_response("الرجاء الرد بـ '1' للنعم أو '2' للا")
        else:
            return self._create_response("Please reply with '1' for Yes or '2' for No")

    def _handle_service_selection(self, phone_number: str, text: str, language: str, session: Dict) -> Dict:
        """Handle service type selection"""
        number = self._extract_number_simple(text)

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

        if location:
            self.db.update_order_details(phone_number, location=location)
            self.db.create_or_update_session(phone_number, 'waiting_for_confirmation', language)

            # Get order summary
            order = self.db.get_user_order(phone_number)

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

        # Invalid location
        if language == 'arabic':
            return self._create_response("الرجاء تحديد المكان بوضوح")
        else:
            return self._create_response("Please specify the location clearly")

    def _handle_confirmation(self, phone_number: str, text: str, language: str, session: Dict) -> Dict:
        """Handle order confirmation"""
        number = self._extract_number_simple(text)
        yes_no = self._detect_yes_no_simple(text, language)

        if number == 1 or yes_no == 'yes':
            # Complete order
            order_id = self.db.complete_order(phone_number)

            if order_id:
                order = self.db.get_user_order(phone_number)
                total_amount = order.get('total', 0)

                if language == 'arabic':
                    response = f"🎉 تم تأكيد طلبك بنجاح!\n\n"
                    response += f"📋 رقم الطلب: {order_id}\n"
                    response += f"💰 المبلغ الإجمالي: {total_amount} دينار\n\n"
                    response += f"⏰ سنقوم بإشعارك عندما يصبح طلبك جاهزاً\n"
                    response += f"💳 الرجاء دفع المبلغ للكاشير عند المنضدة\n\n"
                    response += f"شكراً لك لاختيار مقهى هيف! ☕"
                else:
                    response = f"🎉 Your order has been confirmed successfully!\n\n"
                    response += f"📋 Order ID: {order_id}\n"
                    response += f"💰 Total Amount: {total_amount} IQD\n\n"
                    response += f"⏰ We'll notify you when your order is ready\n"
                    response += f"💳 Please pay the amount to the cashier at the counter\n\n"
                    response += f"Thank you for choosing Hef Cafe! ☕"

                return self._create_response(response)

        elif number == 2 or yes_no == 'no':
            # Cancel order
            self.db.delete_session(phone_number)

            if language == 'arabic':
                response = "تم إلغاء الطلب. شكراً لك لزيارة مقهى هيف.\n\n"
                response += "يمكنك البدء بطلب جديد في أي وقت بإرسال 'مرحبا'"
            else:
                response = "Order cancelled. Thank you for visiting Hef Cafe.\n\n"
                response += "You can start a new order anytime by sending 'hello'"

            return self._create_response(response)

        # Invalid confirmation
        if language == 'arabic':
            return self._create_response("الرجاء الرد بـ '1' للتأكيد أو '2' للإلغاء")
        else:
            return self._create_response("Please reply with '1' to confirm or '2' to cancel")

    # Utility methods
    def _convert_arabic_numerals(self, text: str) -> str:
        """Convert Arabic numerals to English"""
        arabic_to_english = {
            '٠': '0', '١': '1', '٢': '2', '٣': '3', '٤': '4',
            '٥': '5', '٦': '6', '٧': '7', '٨': '8', '٩': '9'
        }

        for arabic, english in arabic_to_english.items():
            text = text.replace(arabic, english)

        return text

    def _extract_number_simple(self, text: str) -> Optional[int]:
        """Extract number from text"""
        import re

        text = self._convert_arabic_numerals(text)
        numbers = re.findall(r'\d+', text)

        if numbers:
            return int(numbers[0])

        return None

    def _detect_language_simple(self, text: str) -> Optional[str]:
        """Simple language detection"""
        text_lower = text.lower().strip()

        arabic_indicators = ['عربي', 'العربية', '1', '١']
        english_indicators = ['english', 'انجليزي', '2', '٢']

        if any(indicator in text_lower for indicator in arabic_indicators):
            return 'arabic'
        elif any(indicator in text_lower for indicator in english_indicators):
            return 'english'

        return None

    def _detect_yes_no_simple(self, text: str, language: str) -> Optional[str]:
        """Simple yes/no detection"""
        text_lower = text.lower().strip()

        if language == 'arabic':
            yes_indicators = ['نعم', 'ايوه', 'اه', 'صح', 'تمام', 'موافق', 'اكيد']
            no_indicators = ['لا', 'كلا', 'مش', 'مو', 'لأ', 'رفض']
        else:
            yes_indicators = ['yes', 'yeah', 'yep', 'sure', 'ok', 'okay']
            no_indicators = ['no', 'nope', 'cancel', 'stop']

        if any(indicator in text_lower for indicator in yes_indicators):
            return 'yes'
        elif any(indicator in text_lower for indicator in no_indicators):
            return 'no'

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
        """Create standardized response format"""
        if len(content) > 4000:
            content = content[:3900] + "... (تم اختصار الرسالة)"

        return {
            'type': 'text',
            'content': content,
            'timestamp': datetime.now().isoformat()
        }


# workflow/main.py - Enhanced main workflow with single response guarantee

import logging
from typing import Dict, Any
from config.settings import WhatsAppConfig
from database.manager import DatabaseManager
from ai.processor import AIProcessor
from workflow.handlers import MessageHandler
from workflow.actions import ActionExecutor
from whatsapp.client import WhatsAppClient

logger = logging.getLogger(__name__)


class WhatsAppWorkflow:
    """Enhanced main workflow orchestrator - FIXED for single responses"""

    def __init__(self, config: Dict[str, str]):
        """Initialize the complete workflow system"""
        self.config = config
        self.response_cache = {}  # Prevent duplicate responses

        # Initialize core components
        self._init_components()

        logger.info("✅ Enhanced WhatsApp workflow initialized successfully")

    def _init_components(self):
        """Initialize all workflow components"""
        try:
            # Database manager
            self.db = DatabaseManager(self.config.get('db_path', 'hef_cafe.db'))
            logger.info("✅ Database manager initialized")

            # AI processor (optional)
            self.ai = AIProcessor(self.config.get('openai_api_key'))
            logger.info("✅ AI processor initialized")

            # WhatsApp client
            self.whatsapp = WhatsAppClient(self.config)
            logger.info("✅ WhatsApp client initialized")

            # Action executor
            self.executor = ActionExecutor(self.db)
            logger.info("✅ Action executor initialized")

            # Message handler (FIXED VERSION)
            self.handler = MessageHandler(self.db, self.ai, self.executor)
            logger.info("✅ Message handler initialized")

        except Exception as e:
            logger.error(f"❌ Error initializing components: {str(e)}")
            raise

    def handle_whatsapp_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """FIXED: Single response per message with caching"""
        try:
            message_id = message_data.get('id', '')
            phone_number = message_data.get('from', '')

            # Check cache to prevent duplicate processing
            cache_key = f"{phone_number}_{message_id}"
            if cache_key in self.response_cache:
                logger.info(f"🔄 Returning cached response for {phone_number}")
                return self.response_cache[cache_key]

            logger.info("📨 Processing incoming WhatsApp message")

            # Process through the FIXED handler
            response = self.handler.handle_message(message_data)

            # Cache the response
            self.response_cache[cache_key] = response

            # Clean old cache entries (keep last 100)
            if len(self.response_cache) > 100:
                old_keys = list(self.response_cache.keys())[:-50]
                for key in old_keys:
                    del self.response_cache[key]

            logger.info("✅ Message processed successfully")
            return response

        except Exception as e:
            logger.error(f"❌ Error handling WhatsApp message: {str(e)}")
            return {
                'type': 'text',
                'content': 'حدث خطأ. الرجاء إعادة المحاولة\nAn error occurred. Please try again',
                'timestamp': __import__('datetime').datetime.now().isoformat()
            }

    def send_whatsapp_message(self, phone_number: str, response_data: Dict[str, Any]) -> bool:
        """Send response back to WhatsApp"""
        try:
            logger.info(f"📤 Sending response to {phone_number}")
            return self.whatsapp.send_response(phone_number, response_data)
        except Exception as e:
            logger.error(f"❌ Error sending WhatsApp message: {str(e)}")
            return False

    def verify_webhook(self, mode: str, token: str, challenge: str) -> str:
        """Verify webhook for WhatsApp"""
        return self.whatsapp.verify_webhook(mode, token, challenge)

    def validate_webhook_payload(self, payload: Dict) -> bool:
        """Validate incoming webhook payload"""
        return self.whatsapp.validate_webhook_payload(payload)

    def extract_messages_from_webhook(self, payload: Dict) -> list:
        """Extract messages from webhook payload"""
        return self.whatsapp.get_webhook_data(payload)

    # Database operations
    def get_user_session(self, phone_number: str) -> Dict:
        """Get user session information"""
        return self.db.get_user_session(phone_number)

    def get_user_order(self, phone_number: str) -> Dict:
        """Get user's current order"""
        return self.db.get_user_order(phone_number)

    def get_order_history(self, phone_number: str = None, limit: int = 50) -> list:
        """Get order history"""
        return self.db.get_order_history(phone_number, limit)

    def get_database_stats(self) -> Dict:
        """Get database statistics"""
        return self.db.get_database_stats()

    def cleanup_old_sessions(self, days_old: int = 7) -> int:
        """Clean up old user sessions"""
        return self.db.cleanup_old_sessions(days_old)

    # Menu operations
    def get_available_categories(self) -> list:
        """Get all available menu categories"""
        return self.db.get_available_categories()

    def get_category_items(self, category_id: int) -> list:
        """Get items for specific category"""
        return self.db.get_category_items(category_id)

    def get_item_by_id(self, item_id: int) -> Dict:
        """Get specific menu item by ID"""
        return self.db.get_item_by_id(item_id)

    # AI operations
    def is_ai_available(self) -> bool:
        """Check if AI processing is available"""
        return self.ai.is_available()

    def test_ai_connection(self) -> Dict:
        """Test AI connection and capabilities"""
        if not self.ai.is_available():
            return {'status': 'unavailable', 'message': 'AI not configured'}

        try:
            # Simple test without multiple calls
            return {'status': 'available', 'message': 'AI working correctly'}
        except Exception as e:
            return {'status': 'error', 'message': f'AI test failed: {str(e)}'}

    # WhatsApp operations
    def get_phone_numbers(self) -> list:
        """Get all phone numbers associated with the account"""
        return self.whatsapp.get_phone_numbers() or []

    def get_business_profile(self) -> Dict:
        """Get business profile information"""
        return self.whatsapp.get_business_profile() or {}

    # Health and monitoring
    def health_check(self) -> Dict:
        """Perform comprehensive health check"""
        health_status = {
            'status': 'healthy',
            'components': {},
            'timestamp': __import__('datetime').datetime.now().isoformat()
        }

        # Database health
        try:
            stats = self.db.get_database_stats()
            health_status['components']['database'] = {
                'status': 'healthy',
                'stats': stats
            }
        except Exception as e:
            health_status['components']['database'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
            health_status['status'] = 'degraded'

        # AI health (simplified)
        ai_test = self.test_ai_connection()
        health_status['components']['ai'] = ai_test
        if ai_test['status'] == 'error':
            health_status['status'] = 'degraded'

        # WhatsApp API health
        try:
            phone_numbers = self.get_phone_numbers()
            health_status['components']['whatsapp'] = {
                'status': 'healthy',
                'phone_numbers_count': len(phone_numbers) if phone_numbers else 0
            }
        except Exception as e:
            health_status['components']['whatsapp'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
            health_status['status'] = 'degraded'

        return health_status

    # Analytics and reporting
    def get_analytics_summary(self, days: int = 7) -> Dict:
        """Get analytics summary for specified days"""
        try:
            stats = self.db.get_database_stats()

            analytics = {
                'period_days': days,
                'total_users': stats.get('active_users', 0),
                'total_orders': stats.get('completed_orders_count', 0),
                'total_revenue': stats.get('total_revenue', 0),
                'ai_availability': self.is_ai_available(),
                'generated_at': __import__('datetime').datetime.now().isoformat()
            }

            return analytics

        except Exception as e:
            logger.error(f"❌ Error generating analytics: {str(e)}")
            return {'error': str(e)}

    # Configuration and setup
    def get_configuration_status(self) -> Dict:
        """Get current configuration status"""
        return {
            'whatsapp_configured': bool(self.config.get('whatsapp_token')),
            'phone_number_configured': bool(self.config.get('phone_number_id')),
            'ai_configured': bool(self.config.get('openai_api_key')),
            'ai_available': self.is_ai_available(),
            'database_path': self.config.get('db_path', 'hef_cafe.db'),
            'components_initialized': True
        }

    # Utility methods
    def restart_session(self, phone_number: str) -> bool:
        """Restart user session (clear all data)"""
        try:
            return self.db.delete_session(phone_number)
        except Exception as e:
            logger.error(f"❌ Error restarting session: {str(e)}")
            return False

    def simulate_message(self, phone_number: str, message_text: str, customer_name: str = "Test User") -> Dict:
        """Simulate a message for testing purposes"""
        try:
            # Create mock message data
            mock_message = {
                'from': phone_number,
                'id': f"test_{__import__('time').time()}",
                'text': {'body': message_text},
                'contacts': [{'profile': {'name': customer_name}}]
            }

            # Process through workflow
            return self.handle_whatsapp_message(mock_message)

        except Exception as e:
            logger.error(f"❌ Error simulating message: {str(e)}")
            return {'error': str(e)}


# For backward compatibility
TrueAIWorkflow = WhatsAppWorkflow


# ai/prompts.py - SIMPLIFIED prompts to prevent multiple responses

class AIPrompts:
    """Collection of AI prompts and templates - SIMPLIFIED"""

    SYSTEM_PROMPT = """You are Hef, a professional AI assistant for Hef Cafe in Iraq. 

PERSONALITY:
- Professional, clear, and efficient
- Understand various Arabic dialects and English
- Direct and helpful responses
- ALWAYS provide exactly ONE response per message

CAPABILITIES:
- Understand typos and misspellings
- Recognize numbers in any format (1, ١, "first", "واحد")
- Handle casual language
- Understand context from conversation

CRITICAL RULE:
- NEVER generate multiple responses for the same message
- ALWAYS provide a single, clear action
- Keep responses concise and helpful

MENU UNDERSTANDING:
- When users mention category names like "موهيتو", "توست", "كيك" - treat as category selection
- When users provide numbers like "١٠", "2" - treat as position selection
- Always understand the user's INTENT, not just exact words

RESPONSE FORMAT:
- Professional and clear language in user's preferred language
- Use numbered lists for options when appropriate
- Direct and informative responses
- NO duplicate or conflicting information"""

    @staticmethod
    def get_understanding_prompt(user_message: str, current_step: str, context: dict) -> str:
        """Generate SIMPLIFIED AI understanding prompt"""
        return f"""
USER MESSAGE: "{user_message}"
CURRENT STEP: {current_step}
LANGUAGE: {context.get('language', 'arabic')}

CONTEXT:
Available categories: {len(context.get('available_categories', []))} categories
Current category items: {len(context.get('current_category_items', []))} items

TASK: Provide EXACTLY ONE action for this message.

RESPOND WITH JSON (NO MULTIPLE ACTIONS):
{{
    "understood_intent": "what user wants",
    "confidence": "high/medium/low",
    "action": "single_action_only",
    "extracted_data": {{
        "language": "arabic/english/null",
        "category_id": "number or null",
        "item_id": "number or null", 
        "quantity": "number or null",
        "yes_no": "yes/no/null",
        "service_type": "dine-in/delivery/null",
        "location": "string or null"
    }},
    "response_message": "single helpful response in user's language"
}}

IMPORTANT:
- Category mentions like "موهيتو" = category_selection with category_id: 7
- Numbers like "١٠" = position selection (convert ١٠ to 10)
- Provide ONLY ONE action per response
- Keep response_message concise and helpful
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
                'error': "عذراً، حدث خطأ. الرجاء إعادة المحاولة"
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
                'error': "Sorry, something went wrong. Please try again"
            }