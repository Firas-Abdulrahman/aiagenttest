# workflow/handlers.py - FIXED VERSION with proper AI integration and number handling

import logging
import time
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)






class MessageHandler:
    """Enhanced message handler with proper AI integration and fixed number handling"""

    def __init__(self, database_manager, ai_processor, action_executor):
        self.db = database_manager
        self.ai = ai_processor
        self.executor = action_executor
        self.processing_lock = {}

    def handle_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced message handling with proper AI integration"""
        try:
            # Extract message details
            text = message_data.get('text', {}).get('body', '').strip()
            phone_number = message_data.get('from')
            customer_name = self._extract_customer_name(message_data)
            message_id = message_data.get('id', str(time.time()))

            # Prevent duplicate processing
            lock_key = f"{phone_number}_{message_id}"
            if lock_key in self.processing_lock:
                logger.warning(f" Duplicate message processing prevented for {phone_number}")
                return self._create_response("Processing...")

            self.processing_lock[lock_key] = True

            try:
                logger.info(f"📨 Processing message '{text}' from {phone_number}")

                # FIXED: Always try AI first, then fallback
                response = self._process_with_ai_first(phone_number, text, customer_name)

                # Log response
                self.db.log_conversation(phone_number, 'ai_response', response['content'])

                return response

            finally:
                # Clean up lock
                if lock_key in self.processing_lock:
                    del self.processing_lock[lock_key]

        except Exception as e:
            logger.error(f"❌ Error handling message: {str(e)}")
            return self._create_response("حدث خطأ. الرجاء إعادة المحاولة\nAn error occurred. Please try again")

    def _process_with_ai_first(self, phone_number: str, text: str, customer_name: str) -> Dict:
        """Process message with AI first, fallback to enhanced processing"""
        try:
            # Get current session
            session = self.db.get_user_session(phone_number)
            current_step = session.get('current_step') if session else 'waiting_for_language'
            language = session.get('language_preference') if session else None

            # CRITICAL FIX: Always start with language selection if no session exists
            if not session:
                return self._handle_language_selection_enhanced(phone_number, text, customer_name)

            # CRITICAL FIX: If user says "hello" or similar at any step, restart the conversation
            text_lower = text.lower().strip()
            if any(greeting in text_lower for greeting in ['مرحبا', 'هلا', 'hello', 'hi', 'hey']):
                logger.info("🔄 User said hello, restarting conversation")
                try:
                    self.db.delete_session(phone_number)
                except Exception as e:
                    logger.warning(f"⚠️ Could not delete session: {e}")
                return self._handle_language_selection_enhanced(phone_number, text, customer_name)

            # Convert Arabic numerals early
            text = self._convert_arabic_numerals(text)

            # Try AI processing first
            if self.ai.is_available():
                logger.info("🤖 Using AI processing")
                ai_result = self.ai.understand_message(text, current_step, self._build_enhanced_context(session, current_step))
                
                if ai_result and self._validate_ai_result(ai_result, current_step):
                    # AI understood correctly, use its result
                    return self._handle_ai_result(phone_number, ai_result, session, language)
                else:
                    logger.warning("⚠️ AI result invalid, using enhanced fallback")
            else:
                logger.info("🔄 AI not available, using enhanced fallback")

            # Enhanced fallback processing
            return self._enhanced_fallback_processing(phone_number, current_step, text, customer_name, session, language)

        except Exception as e:
            logger.error(f"❌ Error in AI processing: {e}")
            # Fallback to basic language selection
            return self._handle_language_selection_enhanced(phone_number, text, customer_name)

    def _build_enhanced_context(self, session: Dict, current_step: str) -> Dict:
        """Build comprehensive context for AI understanding"""
        context = {
            'current_step': current_step,
            'step_description': self._get_step_description(current_step),
            'available_categories': [],
            'current_category_items': [],
            'current_order': {},
            'language': session.get('language_preference') if session else None,
            'session_data': session or {}
        }

        # Add categories if relevant
        if current_step in ['waiting_for_language', 'waiting_for_category']:
            context['available_categories'] = self.db.get_available_categories()

        # Add items if in item selection
        if current_step == 'waiting_for_item' and session and session.get('selected_category'):
            context['current_category_items'] = self.db.get_category_items(session['selected_category'])

        # Add current order if exists
        if session:
            context['current_order'] = self.db.get_user_order(session['phone_number']) if 'phone_number' in str(
                session) else {}

        return context

    def _validate_ai_result(self, ai_result: Dict, current_step: str) -> bool:
        """Validate AI result makes sense for current step"""
        if not ai_result or not ai_result.get('action'):
            return False

        action = ai_result.get('action')
        confidence = ai_result.get('confidence', 'low')

        # Reject low confidence results for critical steps
        if confidence == 'low' and current_step in ['waiting_for_quantity', 'waiting_for_confirmation']:
            logger.warning(f"⚠️ Rejecting low confidence AI result for critical step {current_step}")
            return False

        # Validate action makes sense for step
        valid_actions_by_step = {
            'waiting_for_language': ['language_selection'],
            'waiting_for_category': ['category_selection', 'show_menu', 'help_request'],
            'waiting_for_item': ['item_selection', 'category_selection', 'show_menu'],
            'waiting_for_quantity': ['quantity_selection'],
            'waiting_for_additional': ['yes_no'],
            'waiting_for_service': ['service_selection'],
            'waiting_for_location': ['location_input'],
            'waiting_for_confirmation': ['yes_no', 'confirmation']
        }

        valid_actions = valid_actions_by_step.get(current_step, [])
        if valid_actions and action not in valid_actions:
            logger.warning(f"⚠️ Invalid action {action} for step {current_step}")
            return False

        return True

    def _enhanced_fallback_processing(self, phone_number: str, current_step: str, text: str,
                                    customer_name: str, session: Dict, language: str) -> Dict:
        """Enhanced fallback processing for all steps"""
        logger.info(f"🔄 Enhanced fallback processing for step: {current_step}")

        if current_step == 'waiting_for_language':
            return self._handle_language_selection_enhanced(phone_number, text, customer_name)

        elif current_step == 'waiting_for_main_category':
            return self._handle_main_category_selection_enhanced(phone_number, text, language, session)

        elif current_step == 'waiting_for_sub_category':
            return self._handle_sub_category_selection_enhanced(phone_number, text, language, session)

        elif current_step == 'waiting_for_item':
            return self._handle_item_selection_enhanced(phone_number, text, language, session)

        elif current_step == 'waiting_for_quantity':
            return self._handle_quantity_selection_enhanced(phone_number, text, language, session)

        elif current_step == 'waiting_for_additional':
            return self._handle_additional_items_enhanced(phone_number, text, language, session)

        elif current_step == 'waiting_for_service':
            return self._handle_service_selection_enhanced(phone_number, text, language, session)

        elif current_step == 'waiting_for_location':
            return self._handle_location_input_enhanced(phone_number, text, language, session)

        elif current_step == 'waiting_for_confirmation':
            return self._handle_confirmation_enhanced(phone_number, text, language, session)

        else:
            # Unknown step, restart conversation
            logger.warning(f"⚠️ Unknown step: {current_step}, restarting conversation")
            return self._handle_language_selection_enhanced(phone_number, text, customer_name)

    def _handle_language_selection_enhanced(self, phone_number: str, text: str, customer_name: str) -> Dict:
        """Enhanced language selection with better Arabic detection"""

        # Detect language
        language = self._detect_language_enhanced(text)

        if language == 'arabic':
            # Create session and show main categories
            self.db.create_or_update_session(phone_number, 'waiting_for_main_category', 'arabic', customer_name)
            
            response = f"أهلاً وسهلاً {customer_name} في مقهى هيف!\n\n"
            response += "القائمة الرئيسية:\n\n"
            
            main_categories = self.db.get_main_categories()
            for i, category in enumerate(main_categories, 1):
                response += f"{i}. {category['name_ar']}\n"
            
            response += "\nالرجاء اختيار الفئة المطلوبة بالرد بالرقم"
            
        elif language == 'english':
            # Create session and show main categories
            self.db.create_or_update_session(phone_number, 'waiting_for_main_category', 'english', customer_name)
            
            response = f"Welcome {customer_name} to Hef Cafe!\n\n"
            response += "Main Menu:\n\n"
            
            main_categories = self.db.get_main_categories()
            for i, category in enumerate(main_categories, 1):
                response += f"{i}. {category['name_en']}\n"
            
            response += "\nPlease choose the category by replying with the number"
            
        else:
            # Default to Arabic
            self.db.create_or_update_session(phone_number, 'waiting_for_main_category', 'arabic', customer_name)
            
            response = f"أهلاً وسهلاً {customer_name} في مقهى هيف!\n\n"
            response += "القائمة الرئيسية:\n\n"
            
            main_categories = self.db.get_main_categories()
            for i, category in enumerate(main_categories, 1):
                response += f"{i}. {category['name_ar']}\n"
            
            response += "\nالرجاء اختيار الفئة المطلوبة بالرد بالرقم"

        return self._create_response(response)

    def _handle_main_category_selection_enhanced(self, phone_number: str, text: str, language: str, session: Dict) -> Dict:
        """Enhanced main category selection with name matching"""

        # Try number first
        number = self._extract_number_enhanced(text)
        main_categories = self.db.get_main_categories()

        if number and 1 <= number <= len(main_categories):
            selected_category = main_categories[number - 1]
            self.db.create_or_update_session(phone_number, 'waiting_for_sub_category', language, 
                                           session.get('customer_name'), selected_category['id'])
            return self._show_sub_categories(phone_number, selected_category, language)

        # Try category name matching
        selected_category = self._match_main_category_by_name(text, main_categories, language)
        if selected_category:
            self.db.create_or_update_session(phone_number, 'waiting_for_sub_category', language, 
                                           session.get('customer_name'), selected_category['id'])
            return self._show_sub_categories(phone_number, selected_category, language)

        # Show main categories again
        if language == 'arabic':
            response = "الرقم أو اسم الفئة غير صحيح. الرجاء اختيار من القائمة:\n\n"
            for i, cat in enumerate(main_categories, 1):
                response += f"{i}. {cat['name_ar']}\n"
        else:
            response = "Invalid number or category name. Please choose from the menu:\n\n"
            for i, cat in enumerate(main_categories, 1):
                response += f"{i}. {cat['name_en']}\n"

        return self._create_response(response)

    def _handle_sub_category_selection_enhanced(self, phone_number: str, text: str, language: str, session: Dict) -> Dict:
        """Enhanced sub category selection with better error handling and suggestions"""

        selected_main_category_id = session.get('selected_main_category')
        if not selected_main_category_id:
            return self._create_response(
                "خطأ في النظام. الرجاء إعادة البدء\nSystem error. Please restart")

        sub_categories = self.db.get_sub_categories(selected_main_category_id)

        # Try number first
        number = self._extract_number_enhanced(text)
        if number and 1 <= number <= len(sub_categories):
            selected_sub_category = sub_categories[number - 1]
            self.db.create_or_update_session(phone_number, 'waiting_for_item', language, 
                                           session.get('customer_name'), selected_main_category_id, selected_sub_category['id'])
            return self._show_sub_category_items(phone_number, selected_sub_category, language)

        # Try enhanced sub category name matching
        selected_sub_category = self._match_sub_category_by_name(text, sub_categories, language)
        if selected_sub_category:
            self.db.create_or_update_session(phone_number, 'waiting_for_item', language, 
                                           session.get('customer_name'), selected_main_category_id, selected_sub_category['id'])
            return self._show_sub_category_items(phone_number, selected_sub_category, language)

        # Check if user wants to go back to main categories
        if self._wants_to_change_category(text, language):
            return self._suggest_category_change(phone_number, text, language, session)

        # Show sub categories again with smart suggestions
        main_categories = self.db.get_main_categories()
        current_main_category = next((cat for cat in main_categories if cat['id'] == selected_main_category_id), None)

        # Get smart suggestions
        suggestions = self._get_smart_suggestions(text, sub_categories, language)

        if language == 'arabic':
            response = f"أعتذر، لم أفهم طلبك '{text}'.\n\n"
            if suggestions:
                response += f"{suggestions}\n\n"
            response += f"الرجاء اختيار من قائمة {current_main_category['name_ar'] if current_main_category else 'الفئة'}:\n\n"
            for i, sub_cat in enumerate(sub_categories, 1):
                response += f"{i}. {sub_cat['name_ar']}\n"
            response += "\nأو اكتب اسم الفئة الفرعية"
        else:
            response = f"Sorry, I didn't understand '{text}'.\n\n"
            if suggestions:
                response += f"{suggestions}\n\n"
            response += f"Please choose from {current_main_category['name_en'] if current_main_category else 'category'} list:\n\n"
            for i, sub_cat in enumerate(sub_categories, 1):
                response += f"{i}. {sub_cat['name_en']}\n"
            response += "\nOr type the sub-category name"

        return self._create_response(response)

    def _wants_to_change_category(self, text: str, language: str) -> bool:
        """Check if user wants to change to a different main category"""
        text_lower = text.lower().strip()
        
        # Keywords indicating they want something different
        change_indicators = {
            'arabic': ['اريد شي', 'بدي شي', 'شي اخر', 'غير', 'مختلف', 'حلو', 'حلويات', 'حار', 'ساخن'],
            'english': ['want something', 'need something', 'different', 'other', 'sweet', 'hot', 'cold']
        }
        
        indicators = change_indicators.get(language, change_indicators['arabic'])
        return any(indicator in text_lower for indicator in indicators)

    def _suggest_category_change(self, phone_number: str, text: str, language: str, session: Dict) -> Dict:
        """Suggest changing to a different main category"""
        text_lower = text.lower().strip()
        
        # Determine which category they might want
        suggested_category = None
        
        if any(word in text_lower for word in ['حلو', 'حلويات', 'حلى', 'sweet']):
            suggested_category = 3  # Pastries & Sweets
        elif any(word in text_lower for word in ['حار', 'ساخن', 'hot']):
            suggested_category = 2  # Hot Drinks
        elif any(word in text_lower for word in ['بارد', 'cold']):
            suggested_category = 1  # Cold Drinks
        
        if suggested_category:
            main_categories = self.db.get_main_categories()
            target_category = next((cat for cat in main_categories if cat['id'] == suggested_category), None)
            
            if target_category:
                if language == 'arabic':
                    response = f"أعتذر، أنت الآن في قائمة المشروبات الباردة.\n"
                    response += f"للحلويات، اختر 'الحلويات والمعجنات' من القائمة الرئيسية.\n\n"
                    response += "هل تريد العودة للقائمة الرئيسية؟\n"
                    response += "1. نعم\n"
                    response += "2. لا، أبقى هنا"
                else:
                    response = f"Sorry, you're currently in the Cold Drinks menu.\n"
                    response += f"For sweets, choose 'Pastries & Sweets' from the main menu.\n\n"
                    response += "Would you like to go back to the main menu?\n"
                    response += "1. Yes\n"
                    response += "2. No, stay here"
                
                return self._create_response(response)
        
        # If we can't determine, just show main categories
        return self._handle_main_category_selection_enhanced(phone_number, text, language, session)

    def _handle_item_selection_enhanced(self, phone_number: str, text: str, language: str, session: Dict) -> Dict:
        """Enhanced item selection with name matching"""

        selected_sub_category_id = session.get('selected_sub_category')
        if not selected_sub_category_id:
            return self._create_response(
                "خطأ في النظام. الرجاء إعادة البدء\nSystem error. Please restart")

        items = self.db.get_sub_category_items(selected_sub_category_id)

        # Try number first
        number = self._extract_number_enhanced(text)
        if number and 1 <= number <= len(items):
            selected_item = items[number - 1]
            return self._show_quantity_selection(phone_number, selected_item, language)

        # Try item name matching
        selected_item = self._match_item_by_name(text, items, language)
        if selected_item:
            return self._show_quantity_selection(phone_number, selected_item, language)

        # Show items again
        sub_categories = self.db.get_sub_categories(session.get('selected_main_category', 0))
        current_sub_category = next((sub_cat for sub_cat in sub_categories if sub_cat['id'] == selected_sub_category_id), None)

        if language == 'arabic':
            response = f"المنتج غير محدد. الرجاء اختيار من قائمة {current_sub_category['name_ar'] if current_sub_category else 'الفئة'}:\n\n"
            for i, item in enumerate(items, 1):
                response += f"{i}. {item['item_name_ar']} - {item['price']} دينار\n"
        else:
            response = f"Item not specified. Please choose from {current_sub_category['name_en'] if current_sub_category else 'category'} list:\n\n"
            for i, item in enumerate(items, 1):
                response += f"{i}. {item['item_name_en']} - {item['price']} IQD\n"

        return self._create_response(response)

    def _handle_additional_items_enhanced(self, phone_number: str, text: str, language: str, session: Dict) -> Dict:
        """Enhanced additional items handling with better yes/no detection"""

        number = self._extract_number_enhanced(text)
        yes_no = self._detect_yes_no_enhanced(text, language)

        if number == 1 or yes_no == 'yes':
            # Go back to main categories for more items
            self.db.create_or_update_session(phone_number, 'waiting_for_main_category', language, 
                                           session.get('customer_name'))
            
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

        elif number == 2 or yes_no == 'no':
            # Proceed to service selection
            self.db.create_or_update_session(phone_number, 'waiting_for_service', language)
            
            if language == 'arabic':
                response = "ممتاز! الآن دعنا نحدد نوع الخدمة:\n\n"
                response += "1. تناول في المقهى\n"
                response += "2. توصيل\n\n"
                response += "الرجاء اختيار نوع الخدمة"
            else:
                response = "Great! Now let's determine the service type:\n\n"
                response += "1. Dine in\n"
                response += "2. Delivery\n\n"
                response += "Please choose the service type"

            return self._create_response(response)

        # Invalid response
        if language == 'arabic':
            return self._create_response("الرجاء الرد بـ '1' لإضافة المزيد أو '2' للمتابعة")
        else:
            return self._create_response("Please reply with '1' to add more or '2' to continue")

    def _handle_service_selection_enhanced(self, phone_number: str, text: str, language: str, session: Dict) -> Dict:
        """Enhanced service selection"""

        number = self._extract_number_enhanced(text)
        text_lower = text.lower().strip()

        service_type = None
        if number == 1 or any(word in text_lower for word in ['مقهى', 'داخل', 'هنا', 'dine', 'in']):
            service_type = 'dine-in'
        elif number == 2 or any(word in text_lower for word in ['توصيل', 'بيت', 'منزل', 'delivery', 'home']):
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

    def _handle_location_input_enhanced(self, phone_number: str, text: str, language: str, session: Dict) -> Dict:
        """Enhanced location input handling"""

        location = text.strip()

        if location and len(location) >= 1:  # Accept any reasonable location
            self.db.update_order_details(phone_number, location=location)
            self.db.create_or_update_session(phone_number, 'waiting_for_confirmation', language)

            # Get order summary
            order = self.db.get_user_order(phone_number)
            return self._show_order_confirmation(phone_number, order, location, language)

        # Invalid location
        if language == 'arabic':
            return self._create_response("الرجاء تحديد المكان بوضوح")
        else:
            return self._create_response("Please specify the location clearly")

    def _handle_confirmation_enhanced(self, phone_number: str, text: str, language: str, session: Dict) -> Dict:
        """Enhanced confirmation handling with better Arabic numeral support and error handling"""

        number = self._extract_number_enhanced(text)
        yes_no = self._detect_yes_no_enhanced(text, language)

        if number == 1 or yes_no == 'yes':
            # Complete order with better error handling
            try:
                # Get order details BEFORE completing the order
                order = self.db.get_user_order(phone_number)
                total_amount = order.get('total', 0) if order else 0
                
                # Now complete the order
                order_id = self.db.complete_order(phone_number)

                if order_id:
                    # Replace this part:
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
                else:
                    # Order completion failed
                    if language == 'arabic':
                        return self._create_response("عذراً، حدث خطأ في إتمام الطلب. الرجاء المحاولة مرة أخرى")
                    else:
                        return self._create_response("Sorry, there was an error completing your order. Please try again")

            except Exception as e:
                logger.error(f"❌ Error completing order: {e}")
                if language == 'arabic':
                    return self._create_response("عذراً، حدث خطأ في إتمام الطلب. الرجاء المحاولة مرة أخرى")
                else:
                    return self._create_response("Sorry, there was an error completing your order. Please try again")

        elif number == 2 or yes_no == 'no':
            # Cancel order with better error handling
            try:
                customer_name = session.get('customer_name', 'Customer')
                
                # Cancel order and restart
                success = self.db.delete_session(phone_number)
                
                # Create personalized cancellation message
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
                    return self._create_response("عذراً، حدث خطأ في إلغاء الطلب. الرجاء المحاولة مرة أخرى")
                else:
                    return self._create_response("Sorry, there was an error cancelling your order. Please try again")

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