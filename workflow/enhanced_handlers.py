# workflow/enhanced_handlers.py
"""
Enhanced Message Handlers with Deep AI Integration
Provides natural language understanding while maintaining structured workflow
"""

import logging
import time
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class EnhancedMessageHandler:
    """Enhanced message handler with deep AI integration for natural language understanding"""

    def __init__(self, database_manager, enhanced_ai_processor, action_executor):
        self.db = database_manager
        self.ai = enhanced_ai_processor  # Enhanced AI processor
        self.executor = action_executor

    def handle_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced message handling with AI-first approach"""
        try:
            text = message_data.get('text', {}).get('body', '').strip()
            phone_number = message_data.get('from')
            customer_name = self._extract_customer_name(message_data)

            # Get current session
            session = self.db.get_user_session(phone_number)
            current_step = session.get('current_step') if session else 'waiting_for_language'

            # Build comprehensive user context
            user_context = self._build_user_context(phone_number, session, current_step)

            # AI-First Processing: Try AI understanding first
            if self.ai and self.ai.is_available():
                logger.info(f"🧠 Using enhanced AI for message: '{text}' at step '{current_step}'")
                ai_result = self.ai.understand_natural_language(
                    user_message=text,
                    current_step=current_step,
                    user_context=user_context,
                    language=session.get('language_preference', 'arabic') if session else 'arabic'
                )
                
                # Handle AI result
                if ai_result and ai_result.get('confidence') != 'low':
                    return self._handle_ai_result(phone_number, ai_result, session, user_context)
                else:
                    logger.info("🔄 AI confidence low, falling back to structured processing")

            # Fallback to structured processing
            return self._handle_structured_message(phone_number, text, current_step, session, user_context)

        except Exception as e:
            logger.error(f"❌ Error in enhanced message handling: {str(e)}")
            return self._create_response("حدث خطأ. الرجاء إعادة المحاولة\nAn error occurred. Please try again")

    def _build_user_context(self, phone_number: str, session: Dict, current_step: str) -> Dict:
        """Build comprehensive user context for AI understanding"""
        context = {
            'phone_number': phone_number,
            'current_step': current_step,
            'language': session.get('language_preference', 'arabic') if session else 'arabic',
            'customer_name': session.get('customer_name', 'Customer') if session else 'Customer',
            'selected_main_category': session.get('selected_main_category'),
            'selected_sub_category': session.get('selected_sub_category'),
            'last_selected_item': session.get('last_selected_item'),
            'order_history': [],
            'current_order_items': [],
            'available_categories': [],
            'current_category_items': [],
            'conversation_history': []
        }

        # Get current order items
        if session:
            current_order = self.db.get_current_order(phone_number)
            if current_order:
                context['current_order_items'] = current_order.get('items', [])
                context['order_history'] = self.db.get_order_history(phone_number)

        # Get available categories based on current step
        if current_step == 'waiting_for_category':
            context['available_categories'] = self.db.get_main_categories()
        elif current_step == 'waiting_for_sub_category' and session.get('selected_main_category'):
            context['available_categories'] = self.db.get_sub_categories(session['selected_main_category'])
        elif current_step == 'waiting_for_item' and session.get('selected_sub_category'):
            context['current_category_items'] = self.db.get_sub_category_items(session['selected_sub_category'])

        return context

    def _handle_ai_result(self, phone_number: str, ai_result: Dict, session: Dict, user_context: Dict) -> Dict:
        """Handle AI understanding result with appropriate actions"""
        action = ai_result.get('action')
        extracted_data = ai_result.get('extracted_data', {})
        response_message = ai_result.get('response_message', '')
        language = user_context.get('language', 'arabic')

        logger.info(f"🤖 AI Action: {action} with data: {extracted_data}")

        try:
            if action == 'intelligent_suggestion':
                return self._handle_intelligent_suggestion(phone_number, ai_result, session, user_context)

            elif action == 'language_selection':
                return self._handle_ai_language_selection(phone_number, extracted_data, session)

            elif action == 'category_selection':
                return self._handle_ai_category_selection(phone_number, extracted_data, session, user_context)

            elif action == 'item_selection':
                return self._handle_ai_item_selection(phone_number, extracted_data, session, user_context)

            elif action == 'quantity_selection':
                return self._handle_ai_quantity_selection(phone_number, extracted_data, session, user_context)

            elif action == 'yes_no':
                return self._handle_ai_yes_no(phone_number, extracted_data, session, user_context)

            elif action == 'service_selection':
                return self._handle_ai_service_selection(phone_number, extracted_data, session, user_context)

            elif action == 'location_input':
                return self._handle_ai_location_input(phone_number, extracted_data, session, user_context)

            elif action == 'confirmation':
                return self._handle_ai_confirmation(phone_number, extracted_data, session, user_context)

            elif action == 'show_menu':
                return self._handle_ai_show_menu(phone_number, session, user_context)

            elif action == 'help_request':
                return self._handle_ai_help_request(phone_number, session, user_context)

            else:
                logger.warning(f"⚠️ Unknown AI action: {action}")
                return self._create_response(response_message or self._get_fallback_message(user_context['current_step'], language))

        except Exception as e:
            logger.error(f"❌ Error handling AI result: {e}")
            return self._create_response(self._get_fallback_message(user_context['current_step'], language))

    def _handle_intelligent_suggestion(self, phone_number: str, ai_result: Dict, session: Dict, user_context: Dict) -> Dict:
        """Handle intelligent suggestions from AI"""
        extracted_data = ai_result.get('extracted_data', {})
        response_message = ai_result.get('response_message', '')
        language = user_context.get('language', 'arabic')
        current_step = user_context.get('current_step')

        # Handle main category suggestions
        suggested_main_category = extracted_data.get('suggested_main_category')
        if suggested_main_category and current_step == 'waiting_for_category':
            # Get the suggested main category
            main_categories = self.db.get_main_categories()
            if 1 <= suggested_main_category <= len(main_categories):
                selected_category = main_categories[suggested_main_category - 1]
                
                # Update session
                self.db.create_or_update_session(
                    phone_number, 'waiting_for_sub_category', language,
                    session.get('customer_name'),
                    selected_main_category=selected_category['id']
                )
                
                # Show sub-categories
                return self._show_sub_categories(phone_number, selected_category, language)

        # Handle sub-category suggestions
        suggested_sub_category = extracted_data.get('suggested_sub_category')
        if suggested_sub_category and current_step == 'waiting_for_sub_category':
            # Get the suggested sub-category
            sub_categories = self.db.get_sub_categories(session.get('selected_main_category'))
            if 1 <= suggested_sub_category <= len(sub_categories):
                selected_sub_category = sub_categories[suggested_sub_category - 1]
                
                # Update session
                self.db.create_or_update_session(
                    phone_number, 'waiting_for_item', language,
                    session.get('customer_name'),
                    selected_main_category=session.get('selected_main_category'),
                    selected_sub_category=selected_sub_category['id']
                )
                
                # Show items
                return self._show_sub_category_items(phone_number, selected_sub_category, language)

        # If no specific suggestions, use the AI's response message
        if response_message:
            return self._create_response(response_message)
        else:
            return self._create_response(self._get_fallback_message(current_step, language))

    def _handle_ai_language_selection(self, phone_number: str, extracted_data: Dict, session: Dict) -> Dict:
        """Handle AI language selection"""
        language = extracted_data.get('language')
        
        if language not in ['arabic', 'english']:
            return self._create_response("الرجاء اختيار لغة صحيحة\nPlease select a valid language")

        # Create session with language preference
        self.db.create_or_update_session(
            phone_number, 'waiting_for_category', language,
            session.get('customer_name') if session else 'Customer'
        )

        # Show main categories
        return self._show_main_categories(phone_number, language)

    def _handle_ai_category_selection(self, phone_number: str, extracted_data: Dict, session: Dict, user_context: Dict) -> Dict:
        """Handle AI category selection"""
        category_id = extracted_data.get('category_id')
        category_name = extracted_data.get('category_name')
        language = user_context.get('language')

        if category_id:
            # Direct category ID selection
            main_categories = self.db.get_main_categories()
            if 1 <= category_id <= len(main_categories):
                selected_category = main_categories[category_id - 1]
                
                # Update session
                self.db.create_or_update_session(
                    phone_number, 'waiting_for_sub_category', language,
                    session.get('customer_name'),
                    selected_main_category=selected_category['id']
                )
                
                return self._show_sub_categories(phone_number, selected_category, language)

        elif category_name:
            # Category name matching
            main_categories = self.db.get_main_categories()
            matched_category = self._match_category_by_name(category_name, main_categories, language)
            
            if matched_category:
                # Update session
                self.db.create_or_update_session(
                    phone_number, 'waiting_for_sub_category', language,
                    session.get('customer_name'),
                    selected_main_category=matched_category['id']
                )
                
                return self._show_sub_categories(phone_number, matched_category, language)

        return self._create_response(self._get_fallback_message('waiting_for_category', language))

    def _handle_ai_item_selection(self, phone_number: str, extracted_data: Dict, session: Dict, user_context: Dict) -> Dict:
        """Handle AI item selection"""
        item_id = extracted_data.get('item_id')
        item_name = extracted_data.get('item_name')
        language = user_context.get('language')

        if item_id:
            # Direct item ID selection
            items = self.db.get_sub_category_items(session.get('selected_sub_category'))
            if 1 <= item_id <= len(items):
                selected_item = items[item_id - 1]
                
                # Update session
                self.db.create_or_update_session(
                    phone_number, 'waiting_for_quantity', language,
                    session.get('customer_name'),
                    selected_main_category=session.get('selected_main_category'),
                    selected_sub_category=session.get('selected_sub_category'),
                    last_selected_item=selected_item['id']
                )
                
                return self._show_quantity_selection(phone_number, selected_item, language)

        elif item_name:
            # Item name matching
            items = self.db.get_sub_category_items(session.get('selected_sub_category'))
            matched_item = self._match_item_by_name(item_name, items, language)
            
            if matched_item:
                # Update session
                self.db.create_or_update_session(
                    phone_number, 'waiting_for_quantity', language,
                    session.get('customer_name'),
                    selected_main_category=session.get('selected_main_category'),
                    selected_sub_category=session.get('selected_sub_category'),
                    last_selected_item=matched_item['id']
                )
                
                return self._show_quantity_selection(phone_number, matched_item, language)

        return self._create_response(self._get_fallback_message('waiting_for_item', language))

    def _handle_ai_quantity_selection(self, phone_number: str, extracted_data: Dict, session: Dict, user_context: Dict) -> Dict:
        """Handle AI quantity selection"""
        quantity = extracted_data.get('quantity')
        language = user_context.get('language')

        if quantity and isinstance(quantity, int) and 1 <= quantity <= 50:
            # Add item to order
            item_id = session.get('last_selected_item')
            if item_id:
                self.db.add_item_to_order(phone_number, item_id, quantity)
                
                # Update session
                self.db.create_or_update_session(
                    phone_number, 'waiting_for_additional', language,
                    session.get('customer_name'),
                    selected_main_category=session.get('selected_main_category'),
                    selected_sub_category=session.get('selected_sub_category')
                )
                
                # Get item details for confirmation
                items = self.db.get_sub_category_items(session.get('selected_sub_category'))
                selected_item = next((item for item in items if item['id'] == item_id), None)
                
                if selected_item:
                    if language == 'arabic':
                        message = f"تم إضافة {selected_item['item_name_ar']} × {quantity} إلى طلبك\n\nهل تريد إضافة المزيد من الأصناف؟\n\n1. نعم\n2. لا"
                    else:
                        message = f"Added {selected_item['item_name_en']} × {quantity} to your order\n\nWould you like to add more items?\n\n1. Yes\n2. No"
                    
                    return self._create_response(message)

        return self._create_response(self._get_fallback_message('waiting_for_quantity', language))

    def _handle_ai_yes_no(self, phone_number: str, extracted_data: Dict, session: Dict, user_context: Dict) -> Dict:
        """Handle AI yes/no responses"""
        yes_no = extracted_data.get('yes_no')
        language = user_context.get('language')
        current_step = user_context.get('current_step')

        if yes_no == 'yes':
            if current_step == 'waiting_for_additional':
                # Show main categories again
                self.db.create_or_update_session(
                    phone_number, 'waiting_for_category', language,
                    session.get('customer_name')
                )
                return self._show_main_categories(phone_number, language)
            
            elif current_step == 'waiting_for_confirmation':
                # Confirm order
                return self._confirm_order(phone_number, session, user_context)

        elif yes_no == 'no':
            if current_step == 'waiting_for_additional':
                # Proceed to service selection
                self.db.create_or_update_session(
                    phone_number, 'waiting_for_service', language,
                    session.get('customer_name')
                )
                return self._show_service_selection(phone_number, language)
            
            elif current_step == 'waiting_for_confirmation':
                # Cancel order
                return self._cancel_order(phone_number, session, user_context)

        return self._create_response(self._get_fallback_message(current_step, language))

    def _handle_ai_service_selection(self, phone_number: str, extracted_data: Dict, session: Dict, user_context: Dict) -> Dict:
        """Handle AI service selection"""
        service_type = extracted_data.get('service_type')
        language = user_context.get('language')

        if service_type in ['dine-in', 'delivery']:
            # Update session
            self.db.create_or_update_session(
                phone_number, 'waiting_for_location', language,
                session.get('customer_name'),
                service_type=service_type
            )
            
            if service_type == 'dine-in':
                if language == 'arabic':
                    message = "الرجاء تحديد رقم الطاولة (1-7):"
                else:
                    message = "Please provide your table number (1-7):"
            else:
                if language == 'arabic':
                    message = "الرجاء مشاركة موقعك وأي تعليمات خاصة:"
                else:
                    message = "Please share your location and any special instructions:"
            
            return self._create_response(message)

        return self._create_response(self._get_fallback_message('waiting_for_service', language))

    def _handle_ai_location_input(self, phone_number: str, extracted_data: Dict, session: Dict, user_context: Dict) -> Dict:
        """Handle AI location input"""
        location = extracted_data.get('location')
        language = user_context.get('language')

        if location and len(location.strip()) > 0:
            # Update session
            self.db.create_or_update_session(
                phone_number, 'waiting_for_confirmation', language,
                session.get('customer_name'),
                location=location
            )
            
            # Show order summary
            return self._show_order_summary(phone_number, session, user_context, location)

        return self._create_response(self._get_fallback_message('waiting_for_location', language))

    def _handle_ai_confirmation(self, phone_number: str, extracted_data: Dict, session: Dict, user_context: Dict) -> Dict:
        """Handle AI confirmation"""
        # This would handle direct confirmation without yes/no
        return self._confirm_order(phone_number, session, user_context)

    def _handle_ai_show_menu(self, phone_number: str, session: Dict, user_context: Dict) -> Dict:
        """Handle AI show menu request"""
        language = user_context.get('language')
        current_step = user_context.get('current_step')

        if current_step == 'waiting_for_category':
            return self._show_main_categories(phone_number, language)
        elif current_step == 'waiting_for_sub_category':
            main_categories = self.db.get_main_categories()
            selected_category = next((cat for cat in main_categories if cat['id'] == session.get('selected_main_category')), None)
            if selected_category:
                return self._show_sub_categories(phone_number, selected_category, language)
        elif current_step == 'waiting_for_item':
            sub_categories = self.db.get_sub_categories(session.get('selected_main_category'))
            selected_sub_category = next((cat for cat in sub_categories if cat['id'] == session.get('selected_sub_category')), None)
            if selected_sub_category:
                return self._show_sub_category_items(phone_number, selected_sub_category, language)

        return self._create_response(self._get_fallback_message(current_step, language))

    def _handle_ai_help_request(self, phone_number: str, session: Dict, user_context: Dict) -> Dict:
        """Handle AI help request"""
        language = user_context.get('language')
        current_step = user_context.get('current_step')

        if language == 'arabic':
            help_messages = {
                'waiting_for_category': 'يمكنك اختيار رقم من 1 إلى 3، أو قل لي ما تريد بالضبط مثل "مشروب بارد" أو "شيء حلو"',
                'waiting_for_sub_category': 'اختر رقم الفئة الفرعية، أو قل لي ما تريد مثل "قهوة" أو "عصير"',
                'waiting_for_item': 'اختر رقم المنتج، أو قل لي اسم المنتج الذي تريده',
                'waiting_for_quantity': 'اكتب الكمية المطلوبة (رقم من 1 إلى 50)',
                'waiting_for_additional': 'اكتب "نعم" لإضافة المزيد، أو "لا" للمتابعة',
                'waiting_for_service': 'اكتب "1" للتناول في المقهى، أو "2" للتوصيل',
                'waiting_for_location': 'اكتب رقم الطاولة (1-7) للتناول في المقهى، أو العنوان للتوصيل',
                'waiting_for_confirmation': 'اكتب "نعم" لتأكيد الطلب، أو "لا" للإلغاء'
            }
        else:
            help_messages = {
                'waiting_for_category': 'You can choose a number from 1 to 3, or tell me exactly what you want like "cold drink" or "something sweet"',
                'waiting_for_sub_category': 'Choose the sub-category number, or tell me what you want like "coffee" or "juice"',
                'waiting_for_item': 'Choose the item number, or tell me the name of the item you want',
                'waiting_for_quantity': 'Enter the quantity needed (number from 1 to 50)',
                'waiting_for_additional': 'Type "yes" to add more, or "no" to continue',
                'waiting_for_service': 'Type "1" for dine-in, or "2" for delivery',
                'waiting_for_location': 'Enter table number (1-7) for dine-in, or address for delivery',
                'waiting_for_confirmation': 'Type "yes" to confirm order, or "no" to cancel'
            }

        help_message = help_messages.get(current_step, 'I can help you with your order. What would you like to know?')
        return self._create_response(help_message)

    def _handle_structured_message(self, phone_number: str, text: str, current_step: str, session: Dict, user_context: Dict) -> Dict:
        """Fallback to structured message processing when AI is not available"""
        logger.info(f"🔄 Using structured processing for: '{text}' at step '{current_step}'")
        
        language = user_context.get('language', 'arabic')
        
        # Handle different steps with structured logic
        if current_step == 'waiting_for_language':
            return self._handle_structured_language_selection(phone_number, text, session)
            
        elif current_step == 'waiting_for_category':
            return self._handle_structured_category_selection(phone_number, text, session, user_context)
            
        elif current_step == 'waiting_for_sub_category':
            return self._handle_structured_sub_category_selection(phone_number, text, session, user_context)
            
        elif current_step == 'waiting_for_item':
            return self._handle_structured_item_selection(phone_number, text, session, user_context)
            
        elif current_step == 'waiting_for_quantity':
            return self._handle_structured_quantity_selection(phone_number, text, session, user_context)
            
        elif current_step == 'waiting_for_additional':
            return self._handle_structured_additional_selection(phone_number, text, session, user_context)
            
        else:
            return self._create_response(self._get_fallback_message(current_step, language))

    def _handle_structured_language_selection(self, phone_number: str, text: str, session: Dict) -> Dict:
        """Handle language selection with structured logic"""
        text_lower = text.lower().strip()
        
        if any(word in text_lower for word in ['مرحبا', 'السلام', 'هلا', 'hello', 'hi']):
            # Default to Arabic for Arabic greetings
            if any(word in text_lower for word in ['مرحبا', 'السلام', 'هلا']):
                language = 'arabic'
            else:
                language = 'english'
                
            # Update session
            self.db.create_or_update_session(
                phone_number, 'waiting_for_category', language,
                session.get('customer_name')
            )
            
            return self._show_main_categories(phone_number, language)
        
        return self._create_response("الرجاء إرسال 'مرحبا' للبدء\nPlease send 'hello' to start")

    def _handle_structured_category_selection(self, phone_number: str, text: str, session: Dict, user_context: Dict) -> Dict:
        """Handle category selection with structured logic"""
        language = user_context.get('language', 'arabic')
        
        # Try to extract number
        try:
            category_num = int(text.strip())
            categories = self.db.get_main_categories()
            
            if 1 <= category_num <= len(categories):
                selected_category = categories[category_num - 1]
                
                # Update session
                self.db.create_or_update_session(
                    phone_number, 'waiting_for_sub_category', language,
                    session.get('customer_name'),
                    selected_main_category=selected_category['id']
                )
                
                return self._show_sub_categories(phone_number, selected_category, language)
            else:
                return self._create_response(f"الرقم غير صحيح. الرجاء اختيار من 1 إلى {len(categories)}")
                
        except ValueError:
            # Try to match by name
            categories = self.db.get_main_categories()
            matched_category = self._match_category_by_name(text, categories, language)
            
            if matched_category:
                # Update session
                self.db.create_or_update_session(
                    phone_number, 'waiting_for_sub_category', language,
                    session.get('customer_name'),
                    selected_main_category=matched_category['id']
                )
                
                return self._show_sub_categories(phone_number, matched_category, language)
            else:
                return self._create_response("الرجاء اختيار رقم من القائمة أو كتابة اسم الفئة")

    def _handle_structured_sub_category_selection(self, phone_number: str, text: str, session: Dict, user_context: Dict) -> Dict:
        """Handle sub-category selection with structured logic"""
        language = user_context.get('language', 'arabic')
        main_category_id = session.get('selected_main_category')
        
        if not main_category_id:
            return self._create_response("خطأ في النظام. الرجاء البدء من جديد")
        
        # Try to extract number
        try:
            sub_category_num = int(text.strip())
            sub_categories = self.db.get_sub_categories(main_category_id)
            
            if 1 <= sub_category_num <= len(sub_categories):
                selected_sub_category = sub_categories[sub_category_num - 1]
                
                # Update session
                self.db.create_or_update_session(
                    phone_number, 'waiting_for_item', language,
                    session.get('customer_name'),
                    selected_main_category=main_category_id,
                    selected_sub_category=selected_sub_category['id']
                )
                
                return self._show_sub_category_items(phone_number, selected_sub_category, language)
            else:
                return self._create_response(f"الرقم غير صحيح. الرجاء اختيار من 1 إلى {len(sub_categories)}")
                
        except ValueError:
            # Try to match by name
            sub_categories = self.db.get_sub_categories(main_category_id)
            matched_sub_category = self._match_category_by_name(text, sub_categories, language)
            
            if matched_sub_category:
                # Update session
                self.db.create_or_update_session(
                    phone_number, 'waiting_for_item', language,
                    session.get('customer_name'),
                    selected_main_category=main_category_id,
                    selected_sub_category=matched_sub_category['id']
                )
                
                return self._show_sub_category_items(phone_number, matched_sub_category, language)
            else:
                return self._create_response("الرجاء اختيار رقم من القائمة أو كتابة اسم الفئة الفرعية")

    def _handle_structured_item_selection(self, phone_number: str, text: str, session: Dict, user_context: Dict) -> Dict:
        """Handle item selection with structured logic"""
        language = user_context.get('language', 'arabic')
        sub_category_id = session.get('selected_sub_category')
        
        if not sub_category_id:
            return self._create_response("خطأ في النظام. الرجاء البدء من جديد")
        
        # Try to extract number
        try:
            item_num = int(text.strip())
            items = self.db.get_sub_category_items(sub_category_id)
            
            if 1 <= item_num <= len(items):
                selected_item = items[item_num - 1]
                
                # Update session
                self.db.create_or_update_session(
                    phone_number, 'waiting_for_quantity', language,
                    session.get('customer_name'),
                    selected_main_category=session.get('selected_main_category'),
                    selected_sub_category=sub_category_id,
                    selected_item=selected_item['id']
                )
                
                return self._show_quantity_selection(phone_number, selected_item, language)
            else:
                return self._create_response(f"الرقم غير صحيح. الرجاء اختيار من 1 إلى {len(items)}")
                
        except ValueError:
            # Try to match by name
            items = self.db.get_sub_category_items(sub_category_id)
            matched_item = self._match_item_by_name(text, items, language)
            
            if matched_item:
                # Update session
                self.db.create_or_update_session(
                    phone_number, 'waiting_for_quantity', language,
                    session.get('customer_name'),
                    selected_main_category=session.get('selected_main_category'),
                    selected_sub_category=sub_category_id,
                    selected_item=matched_item['id']
                )
                
                return self._show_quantity_selection(phone_number, matched_item, language)
            else:
                return self._create_response("الرجاء اختيار رقم من القائمة أو كتابة اسم المنتج")

    def _handle_structured_quantity_selection(self, phone_number: str, text: str, session: Dict, user_context: Dict) -> Dict:
        """Handle quantity selection with structured logic"""
        language = user_context.get('language', 'arabic')
        item_id = session.get('selected_item')
        
        if not item_id:
            return self._create_response("خطأ في النظام. الرجاء البدء من جديد")
        
        # Extract number from text
        import re
        numbers = re.findall(r'\d+', text)
        
        if numbers:
            quantity = int(numbers[0])
            if quantity > 0:
                # Add item to order
                success = self.db.add_item_to_order(phone_number, item_id, quantity)
                
                if success:
                    # Update session
                    self.db.create_or_update_session(
                        phone_number, 'waiting_for_additional', language,
                        session.get('customer_name')
                    )
                    
                    if language == 'arabic':
                        message = f"تم إضافة المنتج إلى طلبك\n"
                        message += "هل تريد إضافة المزيد من الأصناف؟\n\n"
                        message += "1. نعم\n"
                        message += "2. لا"
                    else:
                        message = f"Item added to your order\n"
                        message += "Would you like to add more items?\n\n"
                        message += "1. Yes\n"
                        message += "2. No"
                    
                    return self._create_response(message)
                else:
                    return self._create_response("حدث خطأ في إضافة المنتج. الرجاء المحاولة مرة أخرى")
        
        return self._create_response("الرجاء إدخال عدد صحيح")

    def _handle_structured_additional_selection(self, phone_number: str, text: str, session: Dict, user_context: Dict) -> Dict:
        """Handle additional item selection with structured logic"""
        language = user_context.get('language', 'arabic')
        
        # Check for yes/no
        text_lower = text.lower().strip()
        
        if any(word in text_lower for word in ['نعم', 'yes', '1']):
            # Reset to category selection
            self.db.create_or_update_session(
                phone_number, 'waiting_for_category', language,
                session.get('customer_name')
            )
            
            return self._show_main_categories(phone_number, language)
            
        elif any(word in text_lower for word in ['لا', 'no', '2']):
            # Move to service selection
            self.db.create_or_update_session(
                phone_number, 'waiting_for_service', language,
                session.get('customer_name')
            )
            
            return self._show_service_selection(phone_number, language)
        
        return self._create_response("الرجاء الرد بـ '1' لإضافة المزيد أو '2' للمتابعة")

    # Helper methods for UI generation
    def _show_main_categories(self, phone_number: str, language: str) -> Dict:
        """Show main categories"""
        categories = self.db.get_main_categories()
        
        if language == 'arabic':
            message = "ممتاز! اختر من القائمة الرئيسية:\n\n"
            for i, cat in enumerate(categories, 1):
                message += f"{i}. {cat['name_ar']}\n"
            message += "\nالرجاء اختيار الفئة المطلوبة"
        else:
            message = "Great! Choose from the main menu:\n\n"
            for i, cat in enumerate(categories, 1):
                message += f"{i}. {cat['name_en']}\n"
            message += "\nPlease select the required category"
        
        return self._create_response(message)

    def _show_sub_categories(self, phone_number: str, main_category: Dict, language: str) -> Dict:
        """Show sub-categories for selected main category"""
        sub_categories = self.db.get_sub_categories(main_category['id'])
        
        if language == 'arabic':
            message = f"قائمة {main_category['name_ar']}:\n\n"
            for i, sub_cat in enumerate(sub_categories, 1):
                message += f"{i}. {sub_cat['name_ar']}\n"
            message += "\nالرجاء اختيار الفئة الفرعية المطلوبة"
        else:
            message = f"{main_category['name_en']} Menu:\n\n"
            for i, sub_cat in enumerate(sub_categories, 1):
                message += f"{i}. {sub_cat['name_en']}\n"
            message += "\nPlease select the required sub-category"
        
        return self._create_response(message)

    def _show_sub_category_items(self, phone_number: str, sub_category: Dict, language: str) -> Dict:
        """Show items for selected sub-category"""
        items = self.db.get_sub_category_items(sub_category['id'])
        
        if language == 'arabic':
            message = f"قائمة {sub_category['name_ar']}:\n\n"
            for i, item in enumerate(items, 1):
                message += f"{i}. {item['item_name_ar']}\n"
                message += f"   السعر: {item['price']} دينار\n\n"
            message += "الرجاء اختيار المنتج المطلوب"
        else:
            message = f"{sub_category['name_en']} Menu:\n\n"
            for i, item in enumerate(items, 1):
                message += f"{i}. {item['item_name_en']}\n"
                message += f"   Price: {item['price']} IQD\n\n"
            message += "Please select the required item"
        
        return self._create_response(message)

    def _show_quantity_selection(self, phone_number: str, selected_item: Dict, language: str) -> Dict:
        """Show quantity selection for selected item"""
        if language == 'arabic':
            message = f"تم اختيار: {selected_item['item_name_ar']}\n"
            message += f"السعر: {selected_item['price']} دينار\n"
            message += "كم الكمية المطلوبة؟"
        else:
            message = f"Selected: {selected_item['item_name_en']}\n"
            message += f"Price: {selected_item['price']} IQD\n"
            message += "How many would you like?"
        
        return self._create_response(message)

    def _show_service_selection(self, phone_number: str, language: str) -> Dict:
        """Show service selection"""
        if language == 'arabic':
            message = "هل تريد طلبك للتناول في المقهى أم للتوصيل؟\n\n"
            message += "1. تناول في المقهى\n"
            message += "2. توصيل"
        else:
            message = "Do you want your order for dine-in or delivery?\n\n"
            message += "1. Dine-in\n"
            message += "2. Delivery"
        
        return self._create_response(message)

    def _show_order_summary(self, phone_number: str, session: Dict, user_context: Dict, location: str) -> Dict:
        """Show order summary"""
        current_order = self.db.get_current_order(phone_number)
        language = user_context.get('language')
        
        if not current_order or not current_order.get('items'):
            return self._create_response("لا توجد أصناف في طلبك\nNo items in your order")

        if language == 'arabic':
            message = "إليك ملخص طلبك:\n\n"
            message += "الأصناف:\n"
            for item in current_order['items']:
                message += f"• {item['item_name_ar']} × {item['quantity']} - {item['subtotal']} دينار\n"
            
            message += f"\nالخدمة: {session.get('service_type', 'غير محدد')}\n"
            message += f"المكان: {location}\n"
            message += f"السعر الإجمالي: {current_order['total']} دينار\n\n"
            message += "هل تريد تأكيد هذا الطلب؟\n\n1. نعم\n2. لا"
        else:
            message = "Here is your order summary:\n\n"
            message += "Items:\n"
            for item in current_order['items']:
                message += f"• {item['item_name_en']} × {item['quantity']} - {item['subtotal']} IQD\n"
            
            message += f"\nService: {session.get('service_type', 'Not specified')}\n"
            message += f"Location: {location}\n"
            message += f"Total Price: {current_order['total']} IQD\n\n"
            message += "Would you like to confirm this order?\n\n1. Yes\n2. No"
        
        return self._create_response(message)

    def _confirm_order(self, phone_number: str, session: Dict, user_context: Dict) -> Dict:
        """Confirm order"""
        # Complete the order
        order_id = self.db.complete_order(phone_number)
        language = user_context.get('language')
        
        if order_id:
            if language == 'arabic':
                message = f"تم تأكيد طلبك بنجاح!\n\n"
                message += f"رقم الطلب: {order_id}\n"
                message += f"شكراً لك لاختيار مقهى هيف!"
            else:
                message = f"Your order has been confirmed successfully!\n\n"
                message += f"Order ID: {order_id}\n"
                message += f"Thank you for choosing Hef Cafe!"
        else:
            if language == 'arabic':
                message = "عذراً، حدث خطأ في تأكيد الطلب. الرجاء إعادة المحاولة"
            else:
                message = "Sorry, there was an error confirming your order. Please try again"
        
        return self._create_response(message)

    def _cancel_order(self, phone_number: str, session: Dict, user_context: Dict) -> Dict:
        """Cancel order"""
        self.db.cancel_order(phone_number)
        language = user_context.get('language')
        customer_name = session.get('customer_name', 'Customer')
        
        if language == 'arabic':
            message = f"تم إلغاء الطلب. شكراً لك {customer_name} لزيارة مقهى هيف.\n\n"
            message += "يمكنك البدء بطلب جديد في أي وقت بإرسال 'مرحبا'"
        else:
            message = f"Order cancelled. Thank you {customer_name} for visiting Hef Cafe.\n\n"
            message += "You can start a new order anytime by sending 'hello'"
        
        return self._create_response(message)

    # Utility methods
    def _match_category_by_name(self, text: str, categories: list, language: str) -> Optional[Dict]:
        """Match category by name"""
        text_lower = text.lower().strip()
        
        for category in categories:
            if language == 'arabic':
                if text_lower in category['name_ar'].lower():
                    return category
            else:
                if text_lower in category['name_en'].lower():
                    return category
        
        return None

    def _match_item_by_name(self, text: str, items: list, language: str) -> Optional[Dict]:
        """Match item by name"""
        text_lower = text.lower().strip()
        
        for item in items:
            if language == 'arabic':
                if text_lower in item['item_name_ar'].lower():
                    return item
            else:
                if text_lower in item['item_name_en'].lower():
                    return item
        
        return None

    def _get_fallback_message(self, current_step: str, language: str) -> str:
        """Get fallback message for current step"""
        if language == 'arabic':
            messages = {
                'waiting_for_language': 'الرجاء اختيار لغتك المفضلة:\n1. العربية\n2. English',
                'waiting_for_category': 'الرجاء اختيار من القائمة:\n1. المشروبات الباردة\n2. المشروبات الحارة\n3. الحلويات والمعجنات',
                'waiting_for_sub_category': 'الرجاء اختيار الفئة الفرعية المطلوبة',
                'waiting_for_item': 'الرجاء اختيار المنتج المطلوب',
                'waiting_for_quantity': 'كم الكمية المطلوبة؟',
                'waiting_for_additional': 'هل تريد إضافة المزيد من الأصناف؟\n1. نعم\n2. لا',
                'waiting_for_service': 'هل تريد طلبك للتناول في المقهى أم للتوصيل؟\n1. تناول في المقهى\n2. توصيل',
                'waiting_for_location': 'الرجاء تحديد رقم الطاولة (1-7) أو العنوان',
                'waiting_for_confirmation': 'هل تريد تأكيد هذا الطلب؟\n1. نعم\n2. لا'
            }
        else:
            messages = {
                'waiting_for_language': 'Please select your preferred language:\n1. العربية (Arabic)\n2. English',
                'waiting_for_category': 'Please select from the menu:\n1. Cold Drinks\n2. Hot Drinks\n3. Pastries & Sweets',
                'waiting_for_sub_category': 'Please select the required sub-category',
                'waiting_for_item': 'Please select the required item',
                'waiting_for_quantity': 'How many would you like?',
                'waiting_for_additional': 'Would you like to add more items?\n1. Yes\n2. No',
                'waiting_for_service': 'Do you want your order for dine-in or delivery?\n1. Dine-in\n2. Delivery',
                'waiting_for_location': 'Please provide your table number (1-7) or address',
                'waiting_for_confirmation': 'Would you like to confirm this order?\n1. Yes\n2. No'
            }
        
        return messages.get(current_step, 'Please provide a valid response.')

    def _extract_customer_name(self, message_data: Dict) -> str:
        """Extract customer name from message data"""
        profile = message_data.get('profile', {})
        return profile.get('name', 'Customer')

    def _create_response(self, content: str) -> Dict[str, Any]:
        """Create response structure"""
        return {
            'response_type': 'text',
            'content': content,
            'timestamp': datetime.now().isoformat()
        } 