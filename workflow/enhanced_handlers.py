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
            
            # Build initial user context (may be updated after session reset)
            current_step = session.get('current_step') if session else 'waiting_for_language'
            user_context = self._build_user_context(phone_number, session, current_step)
            
            # Check for session reset (fresh start intent or timeout)
            should_reset = self._should_reset_session(session, text)
            if should_reset:
                logger.info(f"🔄 Resetting session for {phone_number} due to fresh start intent or timeout")
                
                # Special case: If we're in confirmation step and user sends greeting, 
                # use fresh start flow instead of just clearing
                if session and session.get('current_step') == 'waiting_for_confirmation':
                    logger.info(f"🔄 Using fresh start flow for post-order greeting")
                    return self._handle_fresh_start_after_order(phone_number, session, user_context)
                else:
                    # Clear any existing order and session completely
                    self.db.cancel_order(phone_number)
                    self.db.delete_session(phone_number)
                    session = None
                    logger.info(f"✅ Session and order cleared for {phone_number}")
                    
                    # Update context after session reset
                    current_step = 'waiting_for_language'
                    user_context = self._build_user_context(phone_number, session, current_step)
            else:
                logger.info(f"📋 Session check for {phone_number}: should_reset={should_reset}, current_step={session.get('current_step') if session else 'None'}")

            # AI-First Processing: Try AI understanding first
            logger.info(f"🔍 AI Status: ai={self.ai is not None}, available={self.ai.is_available() if self.ai else False}")
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
                    logger.info(f"✅ AI result: {ai_result.get('action')} with confidence {ai_result.get('confidence')}")
                    return self._handle_ai_result(phone_number, ai_result, session, user_context)
                else:
                    logger.info(f"🔄 AI confidence low ({ai_result.get('confidence') if ai_result else 'None'}), falling back to structured processing")
            else:
                logger.info(f"⚠️ AI not available (ai: {self.ai is not None}, available: {self.ai.is_available() if self.ai else False}), using structured processing")

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
            'selected_item': session.get('selected_item'),
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
            main_cat_id = session['selected_main_category']
            logger.info(f"🔍 Debug _build_user_context: main_cat_id type={type(main_cat_id)}, value={main_cat_id}")
            
            # Ensure main_cat_id is an integer
            if isinstance(main_cat_id, dict):
                logger.warning(f"⚠️ main_cat_id is a dict in _build_user_context: {main_cat_id}")
                main_cat_id = main_cat_id.get('id', main_cat_id)
                logger.info(f"🔧 Converted main_cat_id to: {main_cat_id}")
            elif not isinstance(main_cat_id, int):
                logger.warning(f"⚠️ main_cat_id is not int in _build_user_context: {type(main_cat_id)} = {main_cat_id}")
                try:
                    main_cat_id = int(main_cat_id)
                    logger.info(f"🔧 Converted main_cat_id to int: {main_cat_id}")
                except (ValueError, TypeError):
                    logger.error(f"❌ Cannot convert main_cat_id to int in _build_user_context: {main_cat_id}")
                    context['available_categories'] = []
                else:
                    context['available_categories'] = self.db.get_sub_categories(main_cat_id)
            else:
                context['available_categories'] = self.db.get_sub_categories(main_cat_id)
        elif current_step == 'waiting_for_item' and session.get('selected_sub_category'):
            sub_cat_id = session['selected_sub_category']
            logger.info(f"🔍 Debug _build_user_context: sub_cat_id type={type(sub_cat_id)}, value={sub_cat_id}")
            
            # Ensure sub_cat_id is an integer
            if isinstance(sub_cat_id, dict):
                logger.warning(f"⚠️ sub_cat_id is a dict in _build_user_context: {sub_cat_id}")
                sub_cat_id = sub_cat_id.get('id', sub_cat_id)
                logger.info(f"🔧 Converted sub_cat_id to: {sub_cat_id}")
            elif not isinstance(sub_cat_id, int):
                logger.warning(f"⚠️ sub_cat_id is not int in _build_user_context: {type(sub_cat_id)} = {sub_cat_id}")
                try:
                    sub_cat_id = int(sub_cat_id)
                    logger.info(f"🔧 Converted sub_cat_id to int: {sub_cat_id}")
                except (ValueError, TypeError):
                    logger.error(f"❌ Cannot convert sub_cat_id to int in _build_user_context: {sub_cat_id}")
                    context['current_category_items'] = []
                else:
                    context['current_category_items'] = self.db.get_sub_category_items(sub_cat_id)
            else:
                context['current_category_items'] = self.db.get_sub_category_items(sub_cat_id)

        return context

    def _handle_ai_result(self, phone_number: str, ai_result: Dict, session: Dict, user_context: Dict) -> Dict:
        """Handle AI understanding result with appropriate actions"""
        action = ai_result.get('action')
        extracted_data = ai_result.get('extracted_data', {})
        current_step = user_context.get('current_step')

        logger.info(f"🎯 AI Action: {action} at step {current_step}")

        # Handle intelligent suggestions (items/categories) that can work across steps
        if action == 'intelligent_suggestion':
            return self._handle_intelligent_suggestion(phone_number, ai_result, session, user_context)

        # Handle specific step-based actions
        if action == 'language_selection':
            return self._handle_ai_language_selection(phone_number, extracted_data, session)
        elif action == 'category_selection':
            return self._handle_ai_category_selection(phone_number, extracted_data, session, user_context)
        elif action == 'item_selection':
            # Special handling for item selection - can work across different steps
            return self._handle_intelligent_item_selection(phone_number, extracted_data, session, user_context)
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
        elif action == 'back_navigation':
            return self._handle_back_navigation(phone_number, session, user_context)
        else:
            logger.warning(f"⚠️ Unknown AI action: {action}")
            return self._create_response(self._get_fallback_message(current_step, user_context.get('language', 'arabic')))

    def _handle_intelligent_suggestion(self, phone_number: str, ai_result: Dict, session: Dict, user_context: Dict) -> Dict:
        """Handle intelligent suggestions from AI"""
        extracted_data = ai_result.get('extracted_data', {})
        response_message = ai_result.get('response_message', '')
        language = user_context.get('language', 'arabic')
        current_step = user_context.get('current_step')

        logger.info(f"🧠 Intelligent suggestion: step={current_step}, data={extracted_data}")

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
            main_category_id = session.get('selected_main_category')
            logger.info(f"🔍 Debug: main_category_id type={type(main_category_id)}, value={main_category_id}")
            if not main_category_id:
                logger.error(f"❌ No selected_main_category in session for {phone_number}")
                return self._create_response("خطأ في النظام. الرجاء البدء من جديد")
            
            # Ensure main_category_id is an integer
            if isinstance(main_category_id, dict):
                logger.warning(f"⚠️ main_category_id is a dict: {main_category_id}")
                main_category_id = main_category_id.get('id', main_category_id)
                logger.info(f"🔧 Converted main_category_id to: {main_category_id}")
            elif not isinstance(main_category_id, int):
                logger.warning(f"⚠️ main_category_id is not int: {type(main_category_id)} = {main_category_id}")
                try:
                    main_category_id = int(main_category_id)
                    logger.info(f"🔧 Converted main_category_id to int: {main_category_id}")
                except (ValueError, TypeError):
                    logger.error(f"❌ Cannot convert main_category_id to int: {main_category_id}")
                    return self._create_response("خطأ في النظام. الرجاء البدء من جديد")
                
            sub_categories = self.db.get_sub_categories(main_category_id)
            logger.info(f"🔍 Sub-category selection: suggested={suggested_sub_category}, available={len(sub_categories)}")
            
            if 1 <= suggested_sub_category <= len(sub_categories):
                selected_sub_category = sub_categories[suggested_sub_category - 1]
                
                # Update session
                self.db.create_or_update_session(
                    phone_number, 'waiting_for_item', language,
                    session.get('customer_name'),
                    selected_main_category=main_category_id,
                    selected_sub_category=selected_sub_category['id']
                )
                
                # Show items
                return self._show_sub_category_items(phone_number, selected_sub_category, language)
            else:
                logger.warning(f"⚠️ Invalid sub-category number: {suggested_sub_category}, max: {len(sub_categories)}")
                return self._create_response(f"الرقم غير صحيح. الرجاء اختيار من 1 إلى {len(sub_categories)}")

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
            sub_category_id = session.get('selected_sub_category')
            logger.info(f"🔍 Debug _handle_ai_item_selection: sub_category_id type={type(sub_category_id)}, value={sub_category_id}")
            
            # Ensure sub_category_id is an integer
            if isinstance(sub_category_id, dict):
                logger.warning(f"⚠️ sub_category_id is a dict in _handle_ai_item_selection: {sub_category_id}")
                sub_category_id = sub_category_id.get('id', sub_category_id)
                logger.info(f"🔧 Converted sub_category_id to: {sub_category_id}")
            elif not isinstance(sub_category_id, int):
                logger.warning(f"⚠️ sub_category_id is not int in _handle_ai_item_selection: {type(sub_category_id)} = {sub_category_id}")
                try:
                    sub_category_id = int(sub_category_id)
                    logger.info(f"🔧 Converted sub_category_id to int: {sub_category_id}")
                except (ValueError, TypeError):
                    logger.error(f"❌ Cannot convert sub_category_id to int in _handle_ai_item_selection: {sub_category_id}")
                    return self._create_response("خطأ في النظام. الرجاء المحاولة مرة أخرى")
            
            items = self.db.get_sub_category_items(sub_category_id)
            if 1 <= item_id <= len(items):
                selected_item = items[item_id - 1]
                
                # Update session
                self.db.create_or_update_session(
                    phone_number, 'waiting_for_quantity', language,
                    session.get('customer_name'),
                    selected_main_category=session.get('selected_main_category'),
                    selected_sub_category=session.get('selected_sub_category'),
                    selected_item=selected_item['id']
                )
                
                return self._show_quantity_selection(phone_number, selected_item, language)

        elif item_name:
            # Item name matching
            sub_category_id = session.get('selected_sub_category')
            logger.info(f"🔍 Debug _handle_ai_item_selection (item_name): sub_category_id type={type(sub_category_id)}, value={sub_category_id}")
            
            # Ensure sub_category_id is an integer
            if isinstance(sub_category_id, dict):
                logger.warning(f"⚠️ sub_category_id is a dict in _handle_ai_item_selection (item_name): {sub_category_id}")
                sub_category_id = sub_category_id.get('id', sub_category_id)
                logger.info(f"🔧 Converted sub_category_id to: {sub_category_id}")
            elif not isinstance(sub_category_id, int):
                logger.warning(f"⚠️ sub_category_id is not int in _handle_ai_item_selection (item_name): {type(sub_category_id)} = {sub_category_id}")
                try:
                    sub_category_id = int(sub_category_id)
                    logger.info(f"🔧 Converted sub_category_id to int: {sub_category_id}")
                except (ValueError, TypeError):
                    logger.error(f"❌ Cannot convert sub_category_id to int in _handle_ai_item_selection (item_name): {sub_category_id}")
                    return self._create_response("خطأ في النظام. الرجاء المحاولة مرة أخرى")
            
            items = self.db.get_sub_category_items(sub_category_id)
            matched_item = self._match_item_by_name(item_name, items, language)
            
            if matched_item:
                # Update session
                self.db.create_or_update_session(
                    phone_number, 'waiting_for_quantity', language,
                    session.get('customer_name'),
                    selected_main_category=session.get('selected_main_category'),
                    selected_sub_category=session.get('selected_sub_category'),
                    selected_item=matched_item['id']
                )
                
                return self._show_quantity_selection(phone_number, matched_item, language)

        return self._create_response(self._get_fallback_message('waiting_for_item', language))

    def _handle_intelligent_item_selection(self, phone_number: str, extracted_data: Dict, session: Dict, user_context: Dict) -> Dict:
        """Handle intelligent item selection that can work across different steps"""
        item_name = extracted_data.get('item_name')
        item_id = extracted_data.get('item_id')
        language = user_context.get('language', 'arabic')
        current_step = user_context.get('current_step')
        
        logger.info(f"🧠 Intelligent item selection: '{item_name}' at step '{current_step}'")
        
        # If we have a direct item ID, use it
        if item_id:
            return self._handle_ai_item_selection(phone_number, extracted_data, session, user_context)
        
        # If we have an item name, we need to find it intelligently
        if item_name:
            # First, try to find the item in the current context
            if current_step == 'waiting_for_item' and session.get('selected_sub_category'):
                # We're already at item selection step, try to match in current sub-category
                sub_category_id = session['selected_sub_category']
                logger.info(f"🔍 Debug _handle_intelligent_item_selection: sub_category_id type={type(sub_category_id)}, value={sub_category_id}")
                
                # Ensure sub_category_id is an integer
                if isinstance(sub_category_id, dict):
                    logger.warning(f"⚠️ sub_category_id is a dict in _handle_intelligent_item_selection: {sub_category_id}")
                    sub_category_id = sub_category_id.get('id', sub_category_id)
                    logger.info(f"🔧 Converted sub_category_id to: {sub_category_id}")
                elif not isinstance(sub_category_id, int):
                    logger.warning(f"⚠️ sub_category_id is not int in _handle_intelligent_item_selection: {type(sub_category_id)} = {sub_category_id}")
                    try:
                        sub_category_id = int(sub_category_id)
                        logger.info(f"🔧 Converted sub_category_id to int: {sub_category_id}")
                    except (ValueError, TypeError):
                        logger.error(f"❌ Cannot convert sub_category_id to int in _handle_intelligent_item_selection: {sub_category_id}")
                        return self._create_response("خطأ في النظام. الرجاء المحاولة مرة أخرى")
                
                items = self.db.get_sub_category_items(sub_category_id)
                matched_item = self._match_item_by_name(item_name, items, language)
                
                if matched_item:
                    logger.info(f"✅ Found item '{item_name}' in current sub-category")
                    return self._handle_ai_item_selection(phone_number, {
                        'item_id': None,
                        'item_name': item_name
                    }, session, user_context)
            
            # If not found in current context, search across all sub-categories
            logger.info(f"🔍 Searching for item '{item_name}' across all sub-categories")
            
            # Get all main categories and search through their sub-categories
            main_categories = self.db.get_main_categories()
            
            for main_cat in main_categories:
                sub_categories = self.db.get_sub_categories(main_cat['id'])
                
                for sub_cat in sub_categories:
                    items = self.db.get_sub_category_items(sub_cat['id'])
                    matched_item = self._match_item_by_name(item_name, items, language)
                    
                    if matched_item:
                        logger.info(f"✅ Found item '{item_name}' in sub-category '{sub_cat['name_ar']}'")
                        
                        # Update session to reflect the found item's context
                        logger.info(f"🔧 Setting selected_item to {matched_item['id']} for item '{matched_item['item_name_ar']}'")
                        self.db.create_or_update_session(
                            phone_number, 'waiting_for_quantity', language,
                            session.get('customer_name'),
                            selected_main_category=main_cat['id'],
                            selected_sub_category=sub_cat['id'],
                            selected_item=matched_item['id']
                        )
                        
                        # Show quantity selection for the found item
                        return self._show_quantity_selection(phone_number, matched_item, language)
            
            # Item not found anywhere
            logger.warning(f"❌ Item '{item_name}' not found in any sub-category")
            if language == 'arabic':
                return self._create_response(f"عذراً، لم نجد '{item_name}' في قائمتنا. الرجاء اختيار من القائمة المتاحة.")
            else:
                return self._create_response(f"Sorry, we couldn't find '{item_name}' in our menu. Please select from the available options.")
        
        # Fallback to regular item selection
        return self._handle_ai_item_selection(phone_number, extracted_data, session, user_context)

    def _handle_ai_quantity_selection(self, phone_number: str, extracted_data: Dict, session: Dict, user_context: Dict) -> Dict:
        """Handle AI quantity selection"""
        quantity = extracted_data.get('quantity')
        language = user_context.get('language')

        if quantity and isinstance(quantity, int) and 1 <= quantity <= 50:
            # Add item to order
            item_id = session.get('selected_item')
            logger.info(f"🔧 Adding to order: item_id={item_id}, quantity={quantity} for {phone_number}")
            if item_id:
                success = self.db.add_item_to_order(phone_number, item_id, quantity)
                
                if success:
                    # Update session - clear selected_item to prevent re-adding
                    self.db.create_or_update_session(
                        phone_number, 'waiting_for_additional', language,
                        session.get('customer_name'),
                        selected_main_category=session.get('selected_main_category'),
                        selected_sub_category=session.get('selected_sub_category'),
                        selected_item=None  # Clear selected item
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
                else:
                    return self._create_response("حدث خطأ في إضافة المنتج. الرجاء المحاولة مرة أخرى")
            else:
                return self._create_response("خطأ في النظام. الرجاء البدء من جديد")

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
            # Update session step
            self.db.create_or_update_session(
                phone_number, 'waiting_for_location', language,
                session.get('customer_name')
            )
            
            # Update order details with service type
            self.db.update_order_details(phone_number, service_type=service_type)
            
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
            # Update session step
            self.db.create_or_update_session(
                phone_number, 'waiting_for_confirmation', language,
                session.get('customer_name')
            )
            
            # Update order details with location
            self.db.update_order_details(phone_number, location=location)
            
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

    def _handle_back_navigation(self, phone_number: str, session: Dict, user_context: Dict) -> Dict:
        """Handle back navigation request"""
        current_step = user_context.get('current_step')
        language = user_context.get('language', 'arabic')
        
        logger.info(f"🔙 Back navigation requested from step: {current_step}")
        
        # Define step transitions for going back
        back_transitions = {
            'waiting_for_sub_category': 'waiting_for_category',
            'waiting_for_item': 'waiting_for_sub_category', 
            'waiting_for_quantity': 'waiting_for_item',
            'waiting_for_additional': 'waiting_for_quantity',
            'waiting_for_service': 'waiting_for_category',  # Go back to main menu
            'waiting_for_location': 'waiting_for_service',
            'waiting_for_confirmation': 'waiting_for_location'
        }
        
        previous_step = back_transitions.get(current_step)
        
        if not previous_step:
            # Can't go back further
            if language == 'arabic':
                message = "لا يمكن الرجوع أكثر من ذلك. هذه هي البداية."
            else:
                message = "Cannot go back further. This is the beginning."
            return self._create_response(message)
        
        # Clear appropriate session data and navigate back
        if previous_step == 'waiting_for_category':
            self.db.create_or_update_session(
                phone_number, previous_step, language,
                session.get('customer_name'),
                selected_main_category=None,
                selected_sub_category=None,
                selected_item=None
            )
            return self._show_main_categories(phone_number, language)
            
        elif previous_step == 'waiting_for_sub_category':
            self.db.create_or_update_session(
                phone_number, previous_step, language,
                session.get('customer_name'),
                selected_main_category=session.get('selected_main_category'),
                selected_sub_category=None,
                selected_item=None
            )
            main_category_id = session.get('selected_main_category')
            if main_category_id:
                main_categories = self.db.get_main_categories()
                for cat in main_categories:
                    if cat['id'] == main_category_id:
                        return self._show_sub_categories(phone_number, cat, language)
            return self._show_main_categories(phone_number, language)
            
        # Default: update step and show appropriate message
        self.db.create_or_update_session(
            phone_number, previous_step, language,
            session.get('customer_name')
        )
        
        if language == 'arabic':
            message = "تم الرجوع للخطوة السابقة"
        else:
            message = "Returned to previous step"
        return self._create_response(message)

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
            
        elif current_step == 'waiting_for_fresh_start_choice':
            return self._handle_structured_fresh_start_choice(phone_number, text, session, user_context)
            
        else:
            return self._create_response(self._get_fallback_message(current_step, language))

    def _handle_structured_language_selection(self, phone_number: str, text: str, session: Dict) -> Dict:
        """Handle language selection with structured logic"""
        text_lower = text.lower().strip()
        
        # Check for Arabic greetings first
        arabic_greetings = ['مرحبا', 'السلام', 'هلا', 'أهلا', 'السلام عليكم']
        english_greetings = ['hello', 'hi', 'hey', 'good morning', 'good afternoon']
        
        if any(greeting in text_lower for greeting in arabic_greetings):
            language = 'arabic'
            logger.info(f"🌍 Arabic language detected for greeting: '{text}'")
        elif any(greeting in text_lower for greeting in english_greetings):
            language = 'english'
            logger.info(f"🌍 English language detected for greeting: '{text}'")
        else:
            # Default to Arabic for unknown input
            language = 'arabic'
            logger.info(f"🌍 Defaulting to Arabic for input: '{text}'")
                
        # Update session
        self.db.create_or_update_session(
            phone_number, 'waiting_for_category', language,
            session.get('customer_name')
        )
        
        return self._show_main_categories(phone_number, language)

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
        """Handle sub-category selection with enhanced number extraction"""
        language = user_context.get('language', 'arabic')
        main_category_id = session.get('selected_main_category')
        
        if not main_category_id:
            return self._create_response("خطأ في النظام. الرجاء المحاولة مرة أخرى.")
        
        # Try to extract number from mixed input (e.g., "4 iced tea" -> "4")
        import re
        number_match = re.search(r'\d+', text)
        if number_match:
            try:
                sub_category_num = int(number_match.group())
                
                # Ensure main_category_id is an integer
                logger.info(f"🔍 Debug _handle_structured_sub_category_selection: main_category_id type={type(main_category_id)}, value={main_category_id}")
                if isinstance(main_category_id, dict):
                    logger.warning(f"⚠️ main_category_id is a dict in _handle_structured_sub_category_selection: {main_category_id}")
                    main_category_id = main_category_id.get('id', main_category_id)
                    logger.info(f"🔧 Converted main_category_id to: {main_category_id}")
                elif not isinstance(main_category_id, int):
                    logger.warning(f"⚠️ main_category_id is not int in _handle_structured_sub_category_selection: {type(main_category_id)} = {main_category_id}")
                    try:
                        main_category_id = int(main_category_id)
                        logger.info(f"🔧 Converted main_category_id to int: {main_category_id}")
                    except (ValueError, TypeError):
                        logger.error(f"❌ Cannot convert main_category_id to int in _handle_structured_sub_category_selection: {main_category_id}")
                        return self._create_response("خطأ في النظام. الرجاء المحاولة مرة أخرى")
                
                sub_categories = self.db.get_sub_categories(main_category_id)
                
                logger.info(f"🔢 Extracted sub-category number: {sub_category_num} from '{text}'")
                
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
                pass  # Fall through to name matching
        
        # Try to match by name
        # Ensure main_category_id is an integer (reuse the same logic)
        if isinstance(main_category_id, dict):
            logger.warning(f"⚠️ main_category_id is a dict in _handle_structured_sub_category_selection (name matching): {main_category_id}")
            main_category_id = main_category_id.get('id', main_category_id)
            logger.info(f"🔧 Converted main_category_id to: {main_category_id}")
        elif not isinstance(main_category_id, int):
            logger.warning(f"⚠️ main_category_id is not int in _handle_structured_sub_category_selection (name matching): {type(main_category_id)} = {main_category_id}")
            try:
                main_category_id = int(main_category_id)
                logger.info(f"🔧 Converted main_category_id to int: {main_category_id}")
            except (ValueError, TypeError):
                logger.error(f"❌ Cannot convert main_category_id to int in _handle_structured_sub_category_selection (name matching): {main_category_id}")
                return self._create_response("خطأ في النظام. الرجاء المحاولة مرة أخرى")
        
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
            # Show available sub-categories
            return self._show_sub_categories(phone_number, main_category_id, language)

    def _handle_structured_item_selection(self, phone_number: str, text: str, session: Dict, user_context: Dict) -> Dict:
        """Handle item selection with structured logic"""
        language = user_context.get('language', 'arabic')
        sub_category_id = session.get('selected_sub_category')
        
        if not sub_category_id:
            return self._create_response("خطأ في النظام. الرجاء البدء من جديد")
        
        # Try to extract number
        try:
            item_num = int(text.strip())
            
            # Ensure sub_category_id is an integer
            logger.info(f"🔍 Debug _handle_structured_item_selection: sub_category_id type={type(sub_category_id)}, value={sub_category_id}")
            if isinstance(sub_category_id, dict):
                logger.warning(f"⚠️ sub_category_id is a dict in _handle_structured_item_selection: {sub_category_id}")
                sub_category_id = sub_category_id.get('id', sub_category_id)
                logger.info(f"🔧 Converted sub_category_id to: {sub_category_id}")
            elif not isinstance(sub_category_id, int):
                logger.warning(f"⚠️ sub_category_id is not int in _handle_structured_item_selection: {type(sub_category_id)} = {sub_category_id}")
                try:
                    sub_category_id = int(sub_category_id)
                    logger.info(f"🔧 Converted sub_category_id to int: {sub_category_id}")
                except (ValueError, TypeError):
                    logger.error(f"❌ Cannot convert sub_category_id to int in _handle_structured_item_selection: {sub_category_id}")
                    return self._create_response("خطأ في النظام. الرجاء المحاولة مرة أخرى")
            
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
            # Ensure sub_category_id is an integer (reuse the same logic)
            if isinstance(sub_category_id, dict):
                logger.warning(f"⚠️ sub_category_id is a dict in _handle_structured_item_selection (name matching): {sub_category_id}")
                sub_category_id = sub_category_id.get('id', sub_category_id)
                logger.info(f"🔧 Converted sub_category_id to: {sub_category_id}")
            elif not isinstance(sub_category_id, int):
                logger.warning(f"⚠️ sub_category_id is not int in _handle_structured_item_selection (name matching): {type(sub_category_id)} = {sub_category_id}")
                try:
                    sub_category_id = int(sub_category_id)
                    logger.info(f"🔧 Converted sub_category_id to int: {sub_category_id}")
                except (ValueError, TypeError):
                    logger.error(f"❌ Cannot convert sub_category_id to int in _handle_structured_item_selection (name matching): {sub_category_id}")
                    return self._create_response("خطأ في النظام. الرجاء المحاولة مرة أخرى")
            
            items = self.db.get_sub_category_items(sub_category_id)
            logger.info(f"🔍 Matching item '{text}' against {len(items)} items in sub-category {sub_category_id}")
            
            # Log available items for debugging
            for i, item in enumerate(items[:5]):  # Show first 5 items
                logger.info(f"  Item {i+1}: {item['item_name_ar']} (ID: {item['id']})")
            
            matched_item = self._match_item_by_name(text, items, language)
            
            if matched_item:
                logger.info(f"✅ Matched item: {matched_item['item_name_ar']} (ID: {matched_item['id']})")
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
        
        logger.info(f"🔢 Processing quantity selection: text='{text}', item_id={item_id}")
        
        if not item_id:
            logger.error(f"❌ No selected_item in session for {phone_number}")
            return self._create_response("خطأ في النظام. الرجاء البدء من جديد")
        
        # Extract number from text (including Arabic numerals)
        import re
        
        # Convert Arabic numerals to English
        arabic_to_english = {
            '٠': '0', '١': '1', '٢': '2', '٣': '3', '٤': '4',
            '٥': '5', '٦': '6', '٧': '7', '٨': '8', '٩': '9'
        }
        
        processed_text = text
        for arabic, english in arabic_to_english.items():
            processed_text = processed_text.replace(arabic, english)
        
        # Also handle Arabic words for numbers
        arabic_number_words = {
            'صفر': '0', 'واحد': '1', 'اثنين': '2', 'ثلاثة': '3', 'اربعة': '4',
            'خمسة': '5', 'ستة': '6', 'سبعة': '7', 'ثمانية': '8', 'تسعة': '9',
            'عشرة': '10', 'احدى عشر': '11', 'اثنا عشر': '12'
        }
        
        for arabic_word, english_num in arabic_number_words.items():
            if arabic_word in processed_text.lower():
                processed_text = processed_text.replace(arabic_word, english_num)
        
        # Extract numbers
        numbers = re.findall(r'\d+', processed_text)
        
        logger.info(f"🔢 Number extraction: original='{text}', processed='{processed_text}', found={numbers}")
        
        if numbers:
            quantity = int(numbers[0])
            logger.info(f"🔢 Extracted quantity: {quantity}")
            if quantity > 0 and quantity <= 50:  # Reasonable limit
                # Add item to order
                success = self.db.add_item_to_order(phone_number, item_id, quantity)
                
                if success:
                    # Update session - clear selected_item to prevent re-adding
                    self.db.create_or_update_session(
                        phone_number, 'waiting_for_additional', language,
                        session.get('customer_name'),
                        selected_main_category=session.get('selected_main_category'),
                        selected_sub_category=session.get('selected_sub_category'),
                        selected_item=None  # Clear selected item
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
            else:
                return self._create_response("الرجاء إدخال عدد صحيح بين 1 و 50")
        
        return self._create_response("الرجاء إدخال عدد صحيح (مثال: 5 أو خمسة)")

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

    def _handle_structured_fresh_start_choice(self, phone_number: str, text: str, session: Dict, user_context: Dict) -> Dict:
        """Handle user's choice for fresh start after order"""
        language = user_context.get('language', 'arabic')
        
        # Extract number from input
        import re
        number_match = re.search(r'\d+', text)
        if number_match:
            choice = int(number_match.group())
            
            if choice == 1:
                # Start new order - clear everything
                self.db.cancel_order(phone_number)
                self.db.delete_session(phone_number)
                
                if language == 'arabic':
                    return self._create_response("ممتاز! اختر من القائمة الرئيسية:\n\n1. المشروبات الباردة\n2. المشروبات الحارة\n3. الحلويات والمعجنات\n\nالرجاء اختيار الفئة المطلوبة")
                else:
                    return self._create_response("Great! Choose from the main menu:\n\n1. Cold Drinks\n2. Hot Drinks\n3. Pastries & Sweets\n\nPlease select the required category")
            
            elif choice == 2:
                # Keep previous order - restore to confirmation step
                self.db.create_or_update_session(
                    phone_number, 'waiting_for_confirmation', language,
                    session.get('customer_name')
                )
                
                # Get current order and show confirmation
                current_order = self.db.get_current_order(phone_number)
                if current_order:
                    return self._show_order_confirmation(phone_number, current_order, language)
                else:
                    return self._create_response("لا يوجد طلب سابق للاحتفاظ به.")
        
        # Invalid choice
        if language == 'arabic':
            return self._create_response("الرجاء اختيار 1 لبدء طلب جديد أو 2 للاحتفاظ بالطلب السابق")
        else:
            return self._create_response("Please choose 1 to start new order or 2 to keep previous order")

    # Helper methods for UI generation
    def _show_main_categories(self, phone_number: str, language: str) -> Dict:
        """Show main categories"""
        categories = self.db.get_main_categories()
        
        if language == 'arabic':
            message = "ممتاز! اختر من القائمة الرئيسية:\n\n"
            for i, cat in enumerate(categories, 1):
                message += f"{i}. {cat['name_ar']}\n"
            message += "\nالرجاء اختيار الفئة المطلوبة\n\n🔙 اكتب 'رجوع' للعودة للخطوة السابقة"
        else:
            message = "Great! Choose from the main menu:\n\n"
            for i, cat in enumerate(categories, 1):
                message += f"{i}. {cat['name_en']}\n"
            message += "\nPlease select the required category\n\n🔙 Type 'back' to go to previous step"
        
        return self._create_response(message)

    def _show_sub_categories(self, phone_number: str, main_category, language: str) -> Dict:
        """Show sub-categories for selected main category"""
        # Handle both Dict and int inputs
        if isinstance(main_category, dict):
            main_category_id = main_category['id']
            category_name_ar = main_category['name_ar']
            category_name_en = main_category['name_en']
        else:
            # Assume it's an integer ID
            main_category_id = main_category
            # Get category details from database
            main_categories = self.db.get_main_categories()
            selected_category = None
            for cat in main_categories:
                if cat['id'] == main_category_id:
                    selected_category = cat
                    break
            
            if selected_category:
                category_name_ar = selected_category['name_ar']
                category_name_en = selected_category['name_en']
            else:
                category_name_ar = "فئة غير معروفة"
                category_name_en = "Unknown Category"
        
        sub_categories = self.db.get_sub_categories(main_category_id)
        
        if language == 'arabic':
            message = f"قائمة {category_name_ar}:\n\n"
            for i, sub_cat in enumerate(sub_categories, 1):
                message += f"{i}. {sub_cat['name_ar']}\n"
            message += "\nالرجاء اختيار الفئة الفرعية المطلوبة\n\n🔙 اكتب 'رجوع' للعودة للخطوة السابقة"
        else:
            message = f"{category_name_en} Menu:\n\n"
            for i, sub_cat in enumerate(sub_categories, 1):
                message += f"{i}. {sub_cat['name_en']}\n"
            message += "\nPlease select the required sub-category\n\n🔙 Type 'back' to go to previous step"
        
        return self._create_response(message)



    def _show_sub_category_items(self, phone_number: str, sub_category: Dict, language: str) -> Dict:
        """Show items for selected sub-category"""
        sub_category_id = sub_category['id']
        logger.info(f"🔍 Debug _show_sub_category_items: sub_category_id type={type(sub_category_id)}, value={sub_category_id}")
        
        # Ensure sub_category_id is an integer
        if isinstance(sub_category_id, dict):
            logger.warning(f"⚠️ sub_category_id is a dict in _show_sub_category_items: {sub_category_id}")
            sub_category_id = sub_category_id.get('id', sub_category_id)
            logger.info(f"🔧 Converted sub_category_id to: {sub_category_id}")
        elif not isinstance(sub_category_id, int):
            logger.warning(f"⚠️ sub_category_id is not int in _show_sub_category_items: {type(sub_category_id)} = {sub_category_id}")
            try:
                sub_category_id = int(sub_category_id)
                logger.info(f"🔧 Converted sub_category_id to int: {sub_category_id}")
            except (ValueError, TypeError):
                logger.error(f"❌ Cannot convert sub_category_id to int in _show_sub_category_items: {sub_category_id}")
                return self._create_response("خطأ في النظام. الرجاء المحاولة مرة أخرى")
        
        items = self.db.get_sub_category_items(sub_category_id)
        
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

    def _show_order_confirmation(self, phone_number: str, order: Dict, language: str) -> Dict:
        """Show order confirmation with current items"""
        if language == 'arabic':
            response = "إليك ملخص طلبك:\n\n"
            response += "الأصناف:\n"
            
            for item in order.get('items', []):
                response += f"• {item['item_name_ar']} × {item['quantity']} - {item['total_price']} دينار\n"
            
            response += f"\nالخدمة: {order.get('service_type', 'غير محدد')}"
            response += f"\nالمكان: {order.get('location', 'غير محدد')}"
            response += f"\nالسعر الإجمالي: {order.get('total_amount', 0)} دينار\n\n"
            response += "هل تريد تأكيد هذا الطلب؟\n\n1. نعم\n2. لا"
        else:
            response = "Here's your order summary:\n\n"
            response += "Items:\n"
            
            for item in order.get('items', []):
                response += f"• {item['item_name_en']} × {item['quantity']} - {item['total_price']} IQD\n"
            
            response += f"\nService: {order.get('service_type', 'Not specified')}"
            response += f"\nLocation: {order.get('location', 'Not specified')}"
            response += f"\nTotal Amount: {order.get('total_amount', 0)} IQD\n\n"
            response += "Do you want to confirm this order?\n\n1. Yes\n2. No"
        
        return self._create_response(response)

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

    def _handle_fresh_start_after_order(self, phone_number: str, session: Dict, user_context: Dict) -> Dict:
        """Handle fresh start after order completion"""
        language = user_context.get('language', 'arabic')
        
        # Update session to fresh start choice step
        self.db.create_or_update_session(
            phone_number, 'waiting_for_fresh_start_choice', language,
            session.get('customer_name')
        )
        
        if language == 'arabic':
            message = "مرحباً! هل تريد:\n\n1️⃣ بدء طلب جديد\n2️⃣ الاحتفاظ بالطلب السابق"
        else:
            message = "Hello! Would you like to:\n\n1️⃣ Start new order\n2️⃣ Keep previous order"
        
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
        """Match item by name with enhanced partial matching and energy drink handling"""
        # Clean the input - remove numbers and extra spaces
        import re
        cleaned_text = re.sub(r'\d+', '', text).strip()
        text_lower = cleaned_text.lower().strip()
        
        logger.info(f"🔍 Matching '{text}' (cleaned: '{cleaned_text}') against {len(items)} items")
        
        # Special handling for energy drinks
        energy_terms = ['طاقة', 'مشروب طاقة', 'مشروبات طاقة', 'ريد بول', 'red bull', 'monster', 'energy drink', 'energy']
        if any(term in text_lower for term in energy_terms):
            for item in items:
                item_name_lower = item['item_name_ar'].lower() if language == 'arabic' else item['item_name_en'].lower()
                if any(energy_term in item_name_lower for energy_term in ['طاقة', 'energy']):
                    logger.info(f"✅ Energy drink match: '{item_name_lower}'")
                    return item
        
        # First try exact substring matching
        for item in items:
            if language == 'arabic':
                item_name_lower = item['item_name_ar'].lower()
                logger.info(f"  Checking: '{text_lower}' in '{item_name_lower}' = {text_lower in item_name_lower}")
                if text_lower in item_name_lower:
                    return item
            else:
                item_name_lower = item['item_name_en'].lower()
                logger.info(f"  Checking: '{text_lower}' in '{item_name_lower}' = {text_lower in item_name_lower}")
                if text_lower in item_name_lower:
                    return item
        
        # If no exact match, try word-based matching
        text_words = set(text_lower.split())
        for item in items:
            if language == 'arabic':
                item_name_lower = item['item_name_ar'].lower()
                item_words = set(item_name_lower.split())
                # Check if any word from input matches any word in item name
                if text_words & item_words:  # Intersection
                    logger.info(f"  Word match found: {text_words} ∩ {item_words} = {text_words & item_words}")
                    return item
            else:
                item_name_lower = item['item_name_en'].lower()
                item_words = set(item_name_lower.split())
                # Check if any word from input matches any word in item name
                if text_words & item_words:  # Intersection
                    logger.info(f"  Word match found: {text_words} ∩ {item_words} = {text_words & item_words}")
                    return item
        
        logger.info(f"❌ No match found for '{text}' (cleaned: '{cleaned_text}')")
        return None

    def _get_fallback_message(self, step: str, language: str) -> str:
        """Get fallback message for unknown step"""
        messages = {
            # Arabic
            'waiting_for_language': 'الرجاء اختيار اللغة:\n1. العربية\n2. English',
            'waiting_for_category': 'الرجاء اختيار الفئة المطلوبة',
            'waiting_for_sub_category': 'الرجاء اختيار الفئة الفرعية المطلوبة',
            'waiting_for_item': 'الرجاء اختيار المنتج المطلوب',
            'waiting_for_quantity': 'الرجاء إدخال الكمية المطلوبة',
            'waiting_for_additional': 'هل تريد إضافة المزيد من الأصناف؟\n1. نعم\n2. لا',
            'waiting_for_service': 'هل تريد طلبك للتناول في المقهى أم للتوصيل؟\n1. تناول في المقهى\n2. توصيل',
            'waiting_for_location': 'الرجاء تحديد رقم الطاولة (1-7):',
            'waiting_for_confirmation': 'هل تريد تأكيد هذا الطلب؟\n1. نعم\n2. لا',
            'waiting_for_fresh_start_choice': 'هل تريد:\n1️⃣ بدء طلب جديد\n2️⃣ الاحتفاظ بالطلب السابق',
            
            # English
            'waiting_for_language_en': 'Please select language:\n1. العربية\n2. English',
            'waiting_for_category_en': 'Please select the required category',
            'waiting_for_sub_category_en': 'Please select the required sub-category',
            'waiting_for_item_en': 'Please select the required item',
            'waiting_for_quantity_en': 'Please enter the required quantity',
            'waiting_for_additional_en': 'Do you want to add more items?\n1. Yes\n2. No',
            'waiting_for_service_en': 'Do you want your order for dine-in or delivery?\n1. Dine-in\n2. Delivery',
            'waiting_for_location_en': 'Please specify table number (1-7):',
            'waiting_for_confirmation_en': 'Do you want to confirm this order?\n1. Yes\n2. No',
            'waiting_for_fresh_start_choice_en': 'Would you like to:\n1️⃣ Start new order\n2️⃣ Keep previous order'
        }
        
        if language == 'arabic':
            return messages.get(step, 'عذراً، حدث خطأ. الرجاء المحاولة مرة أخرى.')
        else:
            return messages.get(f"{step}_en", 'Sorry, an error occurred. Please try again.')

    def _should_reset_session(self, session: Dict, user_message: str) -> bool:
        """Check if session should be reset due to timeout or greeting"""
        if not session:
            logger.debug("🔄 No session found, no reset needed")
            return False

        # Check session timeout (30 minutes)
        last_update = session.get('updated_at')
        if last_update:
            try:
                from datetime import datetime, timezone
                # Handle both ISO format and simple format
                if 'Z' in last_update:
                    last_update_time = datetime.fromisoformat(last_update.replace('Z', '+00:00'))
                else:
                    last_update_time = datetime.fromisoformat(last_update)
                
                # Make both datetimes timezone-aware for comparison
                now = datetime.now(timezone.utc)
                if last_update_time.tzinfo is None:
                    last_update_time = last_update_time.replace(tzinfo=timezone.utc)
                
                time_diff = now - last_update_time
                if time_diff.total_seconds() > 1800:  # 30 minutes
                    logger.info(f"⏰ Session timeout detected: {time_diff.total_seconds()} seconds")
                    return True
            except Exception as e:
                logger.warning(f"⚠️ Error parsing session time: {e}")
                return True

        # Check for greeting words that might indicate a fresh start
        greeting_words = ['مرحبا', 'السلام عليكم', 'أهلا', 'hello', 'hi', 'hey']
        user_lower = user_message.lower().strip()
        current_step = session.get('current_step')

        logger.debug(f"🔍 Session reset check: message='{user_message}', current_step='{current_step}'")

        # Special case: If we're in confirmation step and user sends a greeting, 
        # it means they want a fresh start after order completion
        if (current_step == 'waiting_for_confirmation' and 
            any(greeting in user_lower for greeting in greeting_words) and
            len(user_message.strip()) <= 15):
            logger.info(f"🔄 Post-order fresh start detected for message: '{user_message}'")
            return True

        # Only reset if it's clearly a greeting and not at language selection step
        # Also, don't reset if we're in confirmation step and user says yes/no
        if (any(greeting in user_lower for greeting in greeting_words) and
                len(user_message.strip()) <= 15 and  # Allow slightly longer greetings
                current_step not in ['waiting_for_language', 'waiting_for_category', 'waiting_for_confirmation'] and
                # Make sure it's not just a number or other input
                not user_message.strip().isdigit() and
                not any(char.isdigit() for char in user_message)):
            logger.info(f"🔄 Fresh start intent detected for message: '{user_message}' at step '{current_step}'")
            return True

        logger.debug(f"❌ No reset needed for message: '{user_message}' at step '{current_step}'")
        return False

    def _extract_customer_name(self, message_data: Dict) -> str:
        """Extract customer name from message data"""
        profile = message_data.get('profile', {})
        return profile.get('name', 'Customer')

    def _create_response(self, content: str) -> Dict[str, Any]:
        """Create response structure"""
        return {
            'type': 'text',
            'content': content
        } 