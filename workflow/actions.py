import logging
import sqlite3
from typing import Dict, Any
from datetime import datetime
from ai.prompts import AIPrompts

logger = logging.getLogger(__name__)


class ActionExecutor:
    """Execute actions determined by AI understanding"""

    def __init__(self, database_manager):
        self.db = database_manager

    def execute_action(self, phone_number: str, ai_result: Dict, session: Dict, customer_name: str) -> Dict:
        """Execute the action determined by AI with flexible workflow support"""
        action = ai_result.get('action')
        extracted_data = ai_result.get('extracted_data', {})
        response_message = ai_result.get('response_message', '')
        clarification_needed = ai_result.get('clarification_needed', False)
        current_step = session.get('current_step') if session else 'waiting_for_language'

        logger.info(f"🎯 Executing action: {action}")

        # If AI needs clarification, return clarification question
        if clarification_needed:
            clarification_question = ai_result.get('clarification_question', 'Could you please clarify?')
            return self._create_response(clarification_question)

        try:
            # Handle staying at current step for clarification/help
            if action == 'stay_current_step':
                return self._create_response(response_message)

            # Handle specific actions based on AI understanding
            if action == 'language_selection':
                return self._execute_language_selection(phone_number, extracted_data, customer_name, response_message)

            elif action == 'category_selection':
                return self._execute_category_selection(phone_number, extracted_data, response_message, session)

            elif action == 'item_selection':
                return self._execute_item_selection(phone_number, extracted_data, response_message, session)

            elif action == 'quantity_selection':
                return self._execute_quantity_selection(phone_number, extracted_data, response_message, session)

            elif action == 'yes_no':
                return self._execute_yes_no_action(phone_number, extracted_data, response_message, session)

            elif action == 'service_selection':
                return self._execute_service_selection(phone_number, extracted_data, response_message, session)

            elif action == 'location_input':
                return self._execute_location_input(phone_number, extracted_data, response_message, session)

            elif action == 'confirmation':
                return self._execute_confirmation(phone_number, extracted_data, response_message, session)

            elif action == 'show_menu':
                return self._execute_show_menu(phone_number, current_step, response_message, session)

            elif action == 'help_request':
                return self._execute_help_request(phone_number, current_step, response_message, session)

            else:
                # AI provided a natural response without specific action
                return self._create_response(response_message)

        except Exception as e:
            logger.error(f"❌ Error executing action {action}: {e}")
            return self._create_response(
                "عذراً، حدث خطأ. هل يمكنك المحاولة مرة أخرى؟\nSorry, something went wrong. Can you try again?")

    def _execute_language_selection(self, phone_number: str, extracted_data: Dict, customer_name: str,
                                    response_message: str) -> Dict:
        """Execute language selection with AI understanding"""
        language = extracted_data.get('language')

        if language and self.db.validate_step_transition(phone_number, 'waiting_for_category'):
            success = self.db.create_or_update_session(phone_number, 'waiting_for_category', language, customer_name)

            if success:
                categories = self.db.get_available_categories()

                # Use AI response or generate professional response
                if not response_message:
                    response_message = AIPrompts.get_menu_display_template(language, categories)

                return self._create_response(response_message)

        # Language not detected, ask properly
        return self._create_response(
            f"مرحباً بك في مقهى هيف\n\n"
            f"الرجاء اختيار لغتك المفضلة:\n"
            f"1. العربية\n"
            f"2. English\n\n"
            f"Welcome to Hef Cafe\n\n"
            f"Please select your preferred language:\n"
            f"1. العربية (Arabic)\n"
            f"2. English"
        )

    def _execute_category_selection(self, phone_number: str, extracted_data: Dict, response_message: str,
                                    session: Dict) -> Dict:
        """Execute category selection with AI understanding"""
        language = session['language_preference'] if session else 'arabic'

        # Get category by ID or name
        category_id = extracted_data.get('category_id')
        category_name = extracted_data.get('category_name')

        categories = self.db.get_available_categories()
        selected_category = None

        # Find category by ID
        if category_id:
            selected_category = next((cat for cat in categories if cat['category_id'] == category_id), None)

        # Find category by name if not found by ID
        if not selected_category and category_name:
            name_lower = category_name.lower().strip()
            for cat in categories:
                if (name_lower in cat['category_name_ar'].lower() or
                        name_lower in cat['category_name_en'].lower() or
                        cat['category_name_ar'].lower() in name_lower or
                        cat['category_name_en'].lower() in name_lower):
                    selected_category = cat
                    break

        if selected_category and self.db.validate_step_transition(phone_number, 'waiting_for_item'):
            # Store selected category
            self.db.create_or_update_session(phone_number, 'waiting_for_item', language,
                                             selected_category=selected_category['category_id'])

            # Get items for category
            items = self.db.get_category_items(selected_category['category_id'])

            # Use AI response or generate template
            if not response_message:
                category_name_display = selected_category['category_name_ar'] if language == 'arabic' else \
                selected_category['category_name_en']
                response_message = AIPrompts.get_items_display_template(language, category_name_display, items)

            return self._create_response(response_message)

        # Category not found, ask again professionally
        response_message = AIPrompts.get_menu_display_template(language, categories)
        return self._create_response(response_message)

    def _execute_item_selection(self, phone_number: str, extracted_data: Dict, response_message: str,
                                session: Dict) -> Dict:
        """Execute item selection with AI understanding"""
        language = session['language_preference'] if session else 'arabic'
        selected_category_id = session.get('selected_category') if session else None

        if not selected_category_id:
            return self._create_response(
                "خطأ في النظام. الرجاء إعادة البدء\nSystem error. Please restart")

        # Get items for current category
        items = self.db.get_category_items(selected_category_id)

        # Find item by ID, name, or position
        item_id = extracted_data.get('item_id')
        item_name = extracted_data.get('item_name')
        selected_item = None

        # Find by direct item ID
        if item_id:
            selected_item = next((item for item in items if item['id'] == item_id), None)

        # Find by position (if item_id represents position like 1, 2, 3)
        if not selected_item and item_id and 1 <= item_id <= len(items):
            selected_item = items[item_id - 1]

        # Find by name with fuzzy matching
        if not selected_item and item_name:
            name_lower = item_name.lower().strip()
            for item in items:
                if (name_lower in item['item_name_ar'].lower() or
                        name_lower in item['item_name_en'].lower() or
                        item['item_name_ar'].lower() in name_lower or
                        item['item_name_en'].lower() in name_lower):
                    selected_item = item
                    break

        if selected_item and self.db.validate_step_transition(phone_number, 'waiting_for_quantity'):
            # Store selected item
            self.db.create_or_update_session(phone_number, 'waiting_for_quantity', language,
                                             selected_item=selected_item['id'])

            # Ask for quantity professionally
            if not response_message:
                if language == 'arabic':
                    response_message = f"تم اختيار: {selected_item['item_name_ar']}\n"
                    response_message += f"السعر: {selected_item['price']} دينار\n\n"
                    response_message += "كم الكمية المطلوبة؟"
                else:
                    response_message = f"Selected: {selected_item['item_name_en']}\n"
                    response_message += f"Price: {selected_item['price']} IQD\n\n"
                    response_message += "How many would you like?"

            return self._create_response(response_message)

        # Item not found, ask again professionally
        if language == 'arabic':
            response_message = "المنتج غير محدد\n\nالرجاء اختيار رقم المنتج أو كتابة اسمه بدقة"
        else:
            response_message = "Item not specified\n\nPlease select the item number or type its name accurately"

        return self._create_response(response_message)

    def _execute_quantity_selection(self, phone_number: str, extracted_data: Dict, response_message: str,
                                    session: Dict) -> Dict:
        """Execute quantity selection with AI understanding"""
        language = session['language_preference'] if session else 'arabic'
        selected_item_id = session.get('selected_item') if session else None
        quantity = extracted_data.get('quantity')

        if not selected_item_id:
            return self._create_response(
                "خطأ في النظام. الرجاء إعادة البدء\nSystem error. Please restart")

        if quantity and quantity > 0 and self.db.validate_step_transition(phone_number, 'waiting_for_additional'):
            # Add item to order
            success = self.db.add_item_to_order(phone_number, selected_item_id, quantity)

            if success:
                item = self.db.get_item_by_id(selected_item_id)
                self.db.create_or_update_session(phone_number, 'waiting_for_additional', language)

                # Professional additional items question
                if not response_message:
                    templates = AIPrompts.get_response_templates(language)
                    response_message = templates['additional']

                return self._create_response(response_message)

        # Invalid quantity
        if language == 'arabic':
            response_message = "الكمية غير صحيحة\n\nالرجاء إدخال رقم صحيح للكمية"
        else:
            response_message = "Invalid quantity\n\nPlease enter a valid number for quantity"

        return self._create_response(response_message)

    def _execute_yes_no_action(self, phone_number: str, extracted_data: Dict, response_message: str,
                               session: Dict) -> Dict:
        """Execute yes/no actions based on current step"""
        language = session['language_preference'] if session else 'arabic'
        current_step = session['current_step'] if session else 'waiting_for_language'
        yes_no = extracted_data.get('yes_no')

        if current_step == 'waiting_for_additional':
            if yes_no == 'yes':
                if self.db.validate_step_transition(phone_number, 'waiting_for_category'):
                    self.db.create_or_update_session(phone_number, 'waiting_for_category', language)
                    categories = self.db.get_available_categories()
                    response_message = AIPrompts.get_menu_display_template(language, categories)
                    return self._create_response(response_message)

            elif yes_no == 'no':
                if self.db.validate_step_transition(phone_number, 'waiting_for_service'):
                    self.db.create_or_update_session(phone_number, 'waiting_for_service', language)
                    templates = AIPrompts.get_response_templates(language)
                    response_message = templates['service']
                    return self._create_response(response_message)

        elif current_step == 'waiting_for_confirmation':
            if yes_no == 'yes':
                # Complete order with proper final confirmation
                order_id = self.db.complete_order(phone_number)
                if order_id:
                    # Get order details before deletion
                    order = self.db.get_user_order(phone_number)
                    total_amount = sum(item.get('subtotal', 0) for item in order.get('items', []))

                    response_message = AIPrompts.get_order_confirmation_template(language, order_id, total_amount)
                    return self._create_response(response_message)

            elif yes_no == 'no':
                # Cancel order and restart
                self.db.delete_session(phone_number)
                templates = AIPrompts.get_response_templates(language)
                response_message = templates['order_cancelled']
                return self._create_response(response_message)

        # Default response if unclear
        return self._create_response(response_message or "هل تقصد نعم أو لا؟\nDo you mean yes or no?")

    def _execute_service_selection(self, phone_number: str, extracted_data: Dict, response_message: str,
                                   session: Dict) -> Dict:
        """Execute service type selection with AI understanding"""
        language = session['language_preference'] if session else 'arabic'
        service_type = extracted_data.get('service_type')

        if service_type and self.db.validate_step_transition(phone_number, 'waiting_for_location'):
            # Update service type
            self.db.update_order_details(phone_number, service_type=service_type)
            self.db.create_or_update_session(phone_number, 'waiting_for_location', language)

            # Ask for location details after service selection
            if not response_message:
                templates = AIPrompts.get_response_templates(language)
                if service_type == 'dine-in':
                    response_message = templates['location_dine']
                else:  # delivery
                    response_message = templates['location_delivery']

            return self._create_response(response_message)

        # Service type not clear
        templates = AIPrompts.get_response_templates(language)
        response_message = templates['service']
        return self._create_response(response_message)

    def _execute_location_input(self, phone_number: str, extracted_data: Dict, response_message: str,
                                session: Dict) -> Dict:
        """Execute location input with AI understanding"""
        language = session['language_preference'] if session else 'arabic'
        location = extracted_data.get('location')

        if location:
            # Store location and move to confirmation
            self.db.update_order_details(phone_number, location=location)

            if self.db.validate_step_transition(phone_number, 'waiting_for_confirmation'):
                self.db.create_or_update_session(phone_number, 'waiting_for_confirmation', language)

                # Get order summary
                order = self.db.get_user_order(phone_number)

                if not response_message:
                    response_message = AIPrompts.get_order_summary_template(language, order, location)

                return self._create_response(response_message)

        # Location not clear
        if language == 'arabic':
            response_message = "الرجاء تحديد المكان بوضوح"
        else:
            response_message = "Please specify the location clearly"

        return self._create_response(response_message)

    def _execute_confirmation(self, phone_number: str, extracted_data: Dict, response_message: str,
                              session: Dict) -> Dict:
        """Execute order confirmation"""
        # This is handled by yes_no_action, so just return the AI response
        return self._create_response(response_message or "تأكد الطلب؟\nConfirm the order?")

    def _execute_show_menu(self, phone_number: str, current_step: str, response_message: str,
                           session: Dict) -> Dict:
        """Show menu based on current step"""
        language = session['language_preference'] if session else 'arabic'

        if current_step == 'waiting_for_category':
            # Stay at category step, show categories
            categories = self.db.get_available_categories()
            response_message = AIPrompts.get_menu_display_template(language, categories)
            return self._create_response(response_message)

        elif current_step == 'waiting_for_item' and session and session.get('selected_category'):
            # Stay at item step, show items for current category
            items = self.db.get_category_items(session['selected_category'])
            categories = self.db.get_available_categories()
            current_category = next(
                (cat for cat in categories if cat['category_id'] == session['selected_category']), None)

            if current_category:
                category_name_display = current_category['category_name_ar'] if language == 'arabic' else \
                current_category['category_name_en']
                response_message = AIPrompts.get_items_display_template(language, category_name_display, items)
                return self._create_response(response_message)

        # Default menu response
        return self._create_response(
            response_message or "القائمة متاحة. ما الذي تريد أن تراه؟\nMenu available. What would you like to see?")

    def _execute_help_request(self, phone_number: str, current_step: str, response_message: str,
                              session: Dict) -> Dict:
        """Handle help requests based on current step"""
        language = session['language_preference'] if session else 'arabic'

        if current_step == 'waiting_for_category':
            if language == 'arabic':
                response_message = "المساعدة - الفئات المتاحة:\n\n"
                response_message += "اختر رقم الفئة أو اكتب اسمها\n"
                response_message += "يمكنك كتابة 'منيو' لرؤية القائمة الكاملة"
            else:
                response_message = "Help - Available categories:\n\n"
                response_message += "Choose category number or type its name\n"
                response_message += "You can type 'menu' to see the full menu"

        elif current_step == 'waiting_for_item':
            if language == 'arabic':
                response_message = "المساعدة:\n\n"
                response_message += "اختر رقم المنتج من القائمة أعلاه\n"
                response_message += "أو اكتب اسم المنتج بدقة"
            else:
                response_message = "Help:\n\n"
                response_message += "Choose item number from menu above\n"
                response_message += "Or type the item name accurately"

        else:
            if language == 'arabic':
                response_message = "كيف يمكنني مساعدتك؟"
            else:
                response_message = "How can I help you?"

        return self._create_response(response_message)

    def _create_response(self, content: str) -> Dict[str, Any]:
        """Create standardized response format"""
        # Ensure message doesn't exceed WhatsApp limits
        if len(content) > 4000:
            content = content[:3900] + "... (تم اختصار الرسالة)"

        return {
            'type': 'text',
            'content': content,
            'timestamp': datetime.now().isoformat()
        }


class OrderManager:
    """Specialized order management operations"""

    def __init__(self, database_manager):
        self.db = database_manager

    def calculate_order_total(self, phone_number: str) -> int:
        """Calculate total amount for user's order"""
        order = self.db.get_user_order(phone_number)
        return sum(item.get('subtotal', 0) for item in order.get('items', []))

    def format_order_summary(self, phone_number: str, language: str = 'arabic') -> str:
        """Format order summary for display"""
        order = self.db.get_user_order(phone_number)

        if not order['items']:
            if language == 'arabic':
                return "لا توجد عناصر في طلبك"
            else:
                return "No items in your order"

        if language == 'arabic':
            summary = "ملخص طلبك:\n\n"
            for item in order['items']:
                summary += f"• {item['item_name_ar']} × {item['quantity']} - {item['subtotal']} دينار\n"
            summary += f"\nالمجموع: {order['total']} دينار"
        else:
            summary = "Your order summary:\n\n"
            for item in order['items']:
                summary += f"• {item['item_name_en']} × {item['quantity']} - {item['subtotal']} IQD\n"
            summary += f"\nTotal: {order['total']} IQD"

        return summary

    def validate_order_completion(self, phone_number: str) -> tuple[bool, str]:
        """Validate if order can be completed"""
        order = self.db.get_user_order(phone_number)

        if not order['items']:
            return False, "No items in order"

        if not order['details'].get('service_type'):
            return False, "Service type not specified"

        if not order['details'].get('location'):
            return False, "Location not specified"

        if order['total'] <= 0:
            return False, "Invalid order total"

        return True, "Order is valid"

    def clear_user_order(self, phone_number: str) -> bool:
        """Clear user's current order"""
        return self.db.delete_session(phone_number)