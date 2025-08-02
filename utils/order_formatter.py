from typing import Dict, List


class OrderFormatter:
    """Utilities for formatting orders and menu items"""

    @staticmethod
    def format_menu_categories(categories: List[Dict], language: str = 'arabic') -> str:
        """Format menu categories for display"""
        if not categories:
            return "لا توجد فئات متاحة\nNo categories available"

        if language == 'arabic':
            formatted = "القائمة الرئيسية:\n\n"
            for i, cat in enumerate(categories, 1):
                formatted += f"{i}. {cat['category_name_ar']}\n"
            formatted += "\nالرجاء اختيار الفئة المطلوبة بالرد بالرقم"
        else:
            formatted = "Main Menu:\n\n"
            for i, cat in enumerate(categories, 1):
                formatted += f"{i}. {cat['category_name_en']}\n"
            formatted += "\nPlease select the required category by replying with the number"

        return formatted

    @staticmethod
    def format_menu_items(items: List[Dict], category_name: str, language: str = 'arabic') -> str:
        """Format menu items for display"""
        if not items:
            return "لا توجد عناصر متاحة\nNo items available"

        if language == 'arabic':
            formatted = f"قائمة {category_name}:\n\n"
            for i, item in enumerate(items, 1):
                formatted += f"{i}. {item['item_name_ar']}\n"
                formatted += f"   السعر: {item['price']} دينار\n\n"
            formatted += "الرجاء اختيار المنتج المطلوب"
        else:
            formatted = f"{category_name} Menu:\n\n"
            for i, item in enumerate(items, 1):
                formatted += f"{i}. {item['item_name_en']}\n"
                formatted += f"   Price: {item['price']} IQD\n\n"
            formatted += "Please select the required item"

        return formatted

    @staticmethod
    def format_order_summary(order: Dict, language: str = 'arabic') -> str:
        """Format complete order summary"""
        if not order or not order.get('items'):
            if language == 'arabic':
                return "لا توجد عناصر في طلبك"
            else:
                return "No items in your order"

        if language == 'arabic':
            summary = "ملخص طلبك:\n\n"
            summary += "الأصناف:\n"
            for item in order['items']:
                summary += f"• {item['item_name_ar']} × {item['quantity']} - {item['subtotal']} دينار\n"

            details = order.get('details', {})
            if details.get('service_type'):
                service_ar = 'تناول في المقهى' if details['service_type'] == 'dine-in' else 'توصيل'
                summary += f"\nنوع الخدمة: {service_ar}"

            if details.get('location'):
                summary += f"\nالمكان: {details['location']}"

            summary += f"\n\nالمجموع الكلي: {order.get('total', 0)} دينار"
        else:
            summary = "Your Order Summary:\n\n"
            summary += "Items:\n"
            for item in order['items']:
                summary += f"• {item['item_name_en']} × {item['quantity']} - {item['subtotal']} IQD\n"

            details = order.get('details', {})
            if details.get('service_type'):
                summary += f"\nService Type: {details['service_type'].title()}"

            if details.get('location'):
                summary += f"\nLocation: {details['location']}"

            summary += f"\n\nTotal: {order.get('total', 0)} IQD"

        return summary

    @staticmethod
    def format_order_confirmation(order_id: str, total_amount: int, language: str = 'arabic') -> str:
        """Format order confirmation message"""
        if language == 'arabic':
            message = f"🎉 تم تأكيد طلبك بنجاح!\n\n"
            message += f" رقم الطلب: {order_id}\n"
            message += f" المبلغ الإجمالي: {total_amount} دينار\n\n"
            message += f" سنقوم بإشعارك عندما يصبح طلبك جاهزاً\n"
            message += f"شكراً لك لاختيار مقهى هيف! ☕"
        else:
            message = f"🎉 Your order has been confirmed successfully!\n\n"
            message += f" Order ID: {order_id}\n"
            message += f" Total Amount: {total_amount} IQD\n\n"
            message += f" We'll notify you when your order is ready\n"
            message += f"Thank you for choosing Hef Cafe! "

        return message

    @staticmethod
    def format_price(amount: int, currency: str = "دينار") -> str:
        """Format price with currency"""
        return f"{amount:,} {currency}"

    @staticmethod
    def format_item_with_price(item: Dict, language: str = 'arabic') -> str:
        """Format single item with price"""
        if language == 'arabic':
            return f"{item['item_name_ar']} - {item['price']} دينار"
        else:
            return f"{item['item_name_en']} - {item['price']} IQD"

    @staticmethod
    def format_category_header(category: Dict, language: str = 'arabic') -> str:
        """Format category header"""
        if language == 'arabic':
            return f" قائمة {category['category_name_ar']}"
        else:
            return f" {category['category_name_en']} Menu"

    @staticmethod
    def format_quantity_prompt(item: Dict, language: str = 'arabic') -> str:
        """Format quantity selection prompt"""
        if language == 'arabic':
            prompt = f"تم اختيار: {item['item_name_ar']}\n"
            prompt += f"السعر: {item['price']} دينار\n\n"
            prompt += "كم الكمية المطلوبة؟ (اكتب رقم)"
        else:
            prompt = f"Selected: {item['item_name_en']}\n"
            prompt += f"Price: {item['price']} IQD\n\n"
            prompt += "How many would you like? (type a number)"

        return prompt

    @staticmethod
    def format_service_selection(language: str = 'arabic') -> str:
        """Format service type selection"""
        if language == 'arabic':
            message = "الآن دعنا نحدد نوع الخدمة:\n\n"
            message += "1️⃣ تناول في المقهى\n"
            message += "2️⃣ توصيل\n\n"
            message += "الرجاء اختيار نوع الخدمة"
        else:
            message = "Now let's determine the service type:\n\n"
            message += "1️⃣ Dine-in\n"
            message += "2️⃣ Delivery\n\n"
            message += "Please select the service type"

        return message

    @staticmethod
    def format_additional_items_prompt(language: str = 'arabic') -> str:
        """Format additional items prompt"""
        if language == 'arabic':
            message = "هل تريد إضافة المزيد من الأصناف؟\n\n"
            message += "1️⃣ نعم - أضافة المزيد\n"
            message += "2️⃣ لا - إكمال الطلب\n\n"
            message += "الرجاء الاختيار"
        else:
            message = "Would you like to add more items?\n\n"
            message += "1️⃣ Yes - Add more items\n"
            message += "2️⃣ No - Complete order\n\n"
            message += "Please choose"

        return message


# utils/session_manager.py - Complete session manager

import logging
from datetime import datetime, timedelta
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class SessionManager:
    """Utility class for managing user sessions and state"""

    @staticmethod
    def is_session_expired(session: Dict, timeout_minutes: int = 30) -> bool:
        """Check if a session has expired"""
        if not session:
            return True

        last_update = session.get('updated_at')
        if not last_update:
            return True

        try:
            last_update_time = datetime.fromisoformat(last_update.replace('Z', '+00:00'))
            time_diff = datetime.now() - last_update_time
            return time_diff.total_seconds() > (timeout_minutes * 60)
        except Exception as e:
            logger.warning(f"⚠️ Error parsing session time: {e}")
            return True

    @staticmethod
    def detect_fresh_start_intent(message: str, current_step: str) -> bool:
        """Detect if user wants to start fresh conversation"""
        message_lower = message.lower().strip()

        # Greeting words that might indicate fresh start
        greetings = ['مرحبا', 'السلام عليكم', 'أهلا', 'hello', 'hi', 'hey']

        # If user just says greeting and not at initial steps, might want fresh start
        if (any(greeting in message_lower for greeting in greetings) and
                len(message.strip()) <= 15 and
                current_step not in ['waiting_for_language', 'waiting_for_category']):
            return True

        return False

    @staticmethod
    def detect_new_order_keywords(message: str, language: str = 'arabic') -> bool:
        """Detect explicit new order keywords"""
        message_lower = message.lower().strip()

        if language == 'arabic':
            keywords = [
                'طلب جديد', 'طلبية جديدة', 'ابدأ من جديد', 'من البداية',
                'لا طلب جديد', 'اريد طلب جديد', 'بدي طلب جديد',
                'ألغي الطلب', 'ابدأ من الأول', 'بداية جديدة'
            ]
        else:
            keywords = [
                'new order', 'fresh order', 'start over', 'start fresh',
                'no new order', 'begin again', 'restart', 'cancel order',
                'fresh start'
            ]

        return any(keyword in message_lower for keyword in keywords)

    @staticmethod
    def get_session_summary(session: Dict) -> str:
        """Get a human-readable session summary"""
        if not session:
            return "No active session"

        summary = f"Step: {session.get('current_step', 'Unknown')}"

        if session.get('language_preference'):
            summary += f", Language: {session['language_preference']}"

        if session.get('selected_category'):
            summary += f", Category: {session['selected_category']}"

        if session.get('selected_item'):
            summary += f", Item: {session['selected_item']}"

        return summary

    @staticmethod
    def should_reset_session(session: Dict, user_message: str) -> bool:
        """Comprehensive check if session should be reset"""
        # No session means fresh start
        if not session:
            return False

        # Check expiration
        if SessionManager.is_session_expired(session):
            return True

        # Check fresh start intent
        current_step = session.get('current_step', 'waiting_for_language')
        if SessionManager.detect_fresh_start_intent(user_message, current_step):
            return True

        # Check new order keywords
        language = session.get('language_preference', 'arabic')
        if SessionManager.detect_new_order_keywords(user_message, language):
            return True

        return False

    @staticmethod
    def validate_step_transition(from_step: str, to_step: str) -> bool:
        """Validate if step transition is allowed"""
        allowed_transitions = {
            'waiting_for_language': ['waiting_for_category'],
            'waiting_for_category': ['waiting_for_item'],
            'waiting_for_item': ['waiting_for_quantity'],
            'waiting_for_quantity': ['waiting_for_additional'],
            'waiting_for_additional': ['waiting_for_category', 'waiting_for_service'],
            'waiting_for_service': ['waiting_for_location'],
            'waiting_for_location': ['waiting_for_confirmation'],
            'waiting_for_confirmation': ['completed', 'waiting_for_language']
        }

        return to_step in allowed_transitions.get(from_step, [])

    @staticmethod
    def get_next_valid_steps(current_step: str) -> List[str]:
        """Get list of valid next steps"""
        transitions = {
            'waiting_for_language': ['waiting_for_category'],
            'waiting_for_category': ['waiting_for_item'],
            'waiting_for_item': ['waiting_for_quantity'],
            'waiting_for_quantity': ['waiting_for_additional'],
            'waiting_for_additional': ['waiting_for_category', 'waiting_for_service'],
            'waiting_for_service': ['waiting_for_location'],
            'waiting_for_location': ['waiting_for_confirmation'],
            'waiting_for_confirmation': ['completed', 'waiting_for_language']
        }

        return transitions.get(current_step, [])

    @staticmethod
    def format_session_for_logging(session: Dict) -> str:
        """Format session data for logging"""
        if not session:
            return "No session"

        return (f"Phone: {session.get('phone_number', 'Unknown')[:10]}... | "
                f"Step: {session.get('current_step', 'Unknown')} | "
                f"Lang: {session.get('language_preference', 'Unknown')} | "
                f"Category: {session.get('selected_category', 'None')} | "
                f"Item: {session.get('selected_item', 'None')}")