# workflow/enhanced_handlers.py
"""
Enhanced Message Handlers with Deep AI Integration
Provides natural language understanding while maintaining structured workflow
"""

import logging
import time
from typing import Dict, Any, Optional, List
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
            user_context = self._build_user_context(phone_number, session, current_step, text)
            
            # Update user context with extracted customer name
            user_context['customer_name'] = customer_name
            
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
                    user_context = self._build_user_context(phone_number, session, current_step, text)
                    user_context['customer_name'] = customer_name
            else:
                logger.info(f"📋 Session check for {phone_number}: should_reset={should_reset}, current_step={session.get('current_step') if session else 'None'}")

            # Hybrid AI + Structured Processing
            logger.info(f"🔍 AI Status: ai={self.ai is not None}, available={self.ai.is_available() if self.ai else False}")
            ai_result = None
            
            if self.ai and self.ai.is_available():
                logger.info(f"🧠 Using enhanced AI for message: '{text}' at step '{current_step}'")
                # Determine language safely
                language = 'arabic'  # Default
                if session:
                    language = session.get('language_preference', 'arabic')
                
                ai_result = self.ai.understand_natural_language(
                    user_message=text,
                    current_step=current_step,
                    user_context=user_context,
                    language=language
                )
                
                # Handle AI result with hybrid approach
                if ai_result:
                    confidence = ai_result.get('confidence', 'low')
                    logger.info(f"✅ AI result: {ai_result.get('action')} with confidence {confidence}")
                    
                    # Use AI result if confidence is medium or high
                    if confidence in ['medium', 'high']:
                        return self._handle_ai_result(phone_number, ai_result, session, user_context)
                    else:
                        logger.info(f"🔄 AI confidence low ({confidence}), using hybrid processing")
                else:
                    logger.info(f"⚠️ No AI result, using structured processing")
            else:
                logger.info(f"⚠️ AI not available, using structured processing")

            # Hybrid processing: Use AI insights even with low confidence
            if ai_result and ai_result.get('confidence') == 'low':
                return self._handle_hybrid_processing(phone_number, text, ai_result, current_step, session, user_context)
            
            # Fallback to structured processing
            return self._handle_structured_message(phone_number, text, current_step, session, user_context)

        except Exception as e:
            logger.error(f"❌ Error in enhanced message handling: {str(e)}")
            return self._create_response("حدث خطأ. الرجاء إعادة المحاولة\nAn error occurred. Please try again")

    def _handle_hybrid_processing(self, phone_number: str, text: str, ai_result: Dict, current_step: str, session: Dict, user_context: Dict) -> Dict:
        """Handle hybrid processing using AI insights with low confidence"""
        logger.info(f"🔄 Using hybrid processing for step: {current_step}")
        
        # Extract useful information from AI result even with low confidence
        extracted_data = ai_result.get('extracted_data', {})
        action = ai_result.get('action')
        
        # Try to use AI insights for specific steps
        if current_step == 'waiting_for_quantity':
            # AI might have extracted quantity even with low confidence
            quantity = extracted_data.get('quantity')
            if quantity and isinstance(quantity, (int, str)):
                try:
                    quantity_int = int(quantity)
                    if 1 <= quantity_int <= 50:
                        logger.info(f"🔧 Using AI-extracted quantity: {quantity_int}")
                        return self._handle_ai_quantity_selection(phone_number, {'quantity': quantity_int}, session, user_context)
                except (ValueError, TypeError):
                    pass
        
        elif current_step == 'waiting_for_additional':
            # AI might have detected yes/no even with low confidence
            yes_no = extracted_data.get('yes_no')
            if yes_no in ['yes', 'no']:
                logger.info(f"🔧 Using AI-extracted yes/no: {yes_no}")
                return self._handle_ai_yes_no(phone_number, {'yes_no': yes_no}, session, user_context)
        
        elif current_step == 'waiting_for_item':
            # AI might have extracted item information
            item_name = extracted_data.get('item_name')
            if item_name:
                logger.info(f"🔧 Using AI-extracted item: {item_name}")
                return self._handle_intelligent_item_selection(phone_number, extracted_data, session, user_context)
        
        # If AI insights aren't useful, fall back to structured processing
        logger.info(f"🔄 AI insights not useful for hybrid processing, using structured fallback")
        return self._handle_structured_message(phone_number, text, current_step, session, user_context)

    def _build_user_context(self, phone_number: str, session: Dict, current_step: str, original_message: str = '') -> Dict:
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
            'conversation_history': [],
            'original_user_message': original_message
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
        elif current_step == 'waiting_for_sub_category' and session and session.get('selected_main_category'):
            main_cat_id = session.get('selected_main_category')
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
        elif current_step == 'waiting_for_item' and session and session.get('selected_sub_category'):
            sub_cat_id = session.get('selected_sub_category')
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
        elif action == 'sub_category_selection':
            # Handle sub-category selection (e.g., user asks for "موهيتو" sub-category)
            return self._handle_sub_category_selection(phone_number, extracted_data, session, user_context)
        elif action == 'item_selection':
            # Check if we're in quick order mode
            if session.get('order_mode') == 'quick':
                return self._handle_quick_order_item_selection(phone_number, extracted_data, session, user_context)
            
            # Check if we're at the right step for item selection
            current_step = user_context.get('current_step')
            if current_step == 'waiting_for_sub_category':
                # User is trying to select an item while still at sub-category step
                # This might be a sub-category selection instead
                item_name = extracted_data.get('item_name')
                if item_name and item_name.lower() in ['موهيتو', 'mojito']:
                    logger.info(f"🔄 Converting item_selection to sub_category_selection for '{item_name}' at step '{current_step}'")
                    # Convert to sub-category selection
                    return self._handle_sub_category_selection(phone_number, {
                        'sub_category_name': item_name,
                        'sub_category_id': 6  # Mojito sub-category ID
                    }, session, user_context)
                else:
                    # Invalid - user must select sub-category first
                    language = user_context.get('language', 'arabic')
                    if language == 'arabic':
                        return self._create_response("الرجاء اختيار الفئة الفرعية أولاً قبل اختيار المنتج المحدد.")
                    else:
                        return self._create_response("Please select a sub-category first before selecting a specific item.")
            
            # Special handling for item selection - can work across different steps
            return self._handle_intelligent_item_selection(phone_number, extracted_data, session, user_context)
        elif action == 'multi_item_selection':
            # Handle multiple items in one message
            return self._handle_multi_item_selection(phone_number, extracted_data, session, user_context)
        elif action == 'quick_order_selection':
            # Handle quick order mode selection
            return self._handle_quick_order_selection(phone_number, extracted_data, session, user_context)
        elif action == 'explore_menu_selection':
            # Handle explore menu mode selection
            return self._handle_explore_menu_selection(phone_number, extracted_data, session, user_context)
        elif action == 'quantity_selection' and session.get('order_mode') == 'quick':
            # Handle quick order quantity selection
            return self._handle_quick_order_quantity(phone_number, extracted_data, session, user_context)
        elif action == 'service_selection' and session.get('order_mode') == 'quick':
            # Handle quick order service selection
            return self._handle_quick_order_service(phone_number, extracted_data, session, user_context)
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
        elif action == 'conversational_response':
            return self._handle_conversational_response(phone_number, ai_result, session, user_context)
        else:
            logger.warning(f"⚠️ Unknown AI action: {action}")
            return self._create_response(self._get_fallback_message(current_step, user_context.get('language', 'arabic')))

    def _handle_multi_item_selection(self, phone_number: str, extracted_data: Dict, session: Dict, user_context: Dict) -> Dict:
        """Handle multiple item selection in one message"""
        multi_items = extracted_data.get('multi_items', [])
        language = user_context.get('language', 'arabic')
        
        # If AI didn't extract multi_items but we have the action, try to extract from the original message
        if not multi_items:
            logger.info("🔧 AI didn't extract multi_items, attempting to extract from original message")
            original_message = user_context.get('original_user_message', '')
            if original_message:
                # Use the enhanced processor's extraction method
                from ai.enhanced_processor import EnhancedAIProcessor
                temp_processor = EnhancedAIProcessor()
                multi_items = temp_processor._extract_multiple_items(original_message)
                logger.info(f"🔧 Extracted {len(multi_items)} items from original message: {multi_items}")
        
        if not multi_items:
            logger.warning("⚠️ No multi-items found in extracted data or original message")
            return self._create_response("لم أفهم العناصر المطلوبة. الرجاء المحاولة مرة أخرى.")
        
        logger.info(f"🛒 Processing multi-item order: {len(multi_items)} items")
        
        # Process each item
        processed_items = []
        failed_items = []
        
        for item_data in multi_items:
            item_name = item_data.get('item_name', '').strip()
            quantity = item_data.get('quantity', 1)
            
            if not item_name:
                continue
                
            # Try to match the item
            matched_item = self._match_item_from_context(item_name, user_context)
            
            if matched_item:
                processed_items.append({
                    'item_id': matched_item['id'],
                    'item_name': matched_item['item_name_ar'],
                    'quantity': quantity,
                    'price': matched_item['price']
                })
                logger.info(f"✅ Matched item: {item_name} (ID: {matched_item['id']})")
            else:
                failed_items.append(item_name)
                logger.warning(f"❌ Could not match item: {item_name}")
        
        if not processed_items:
            return self._create_response("لم أتمكن من العثور على أي من العناصر المطلوبة. الرجاء المحاولة مرة أخرى.")
        
        # Add items to order
        for item in processed_items:
            self.db.add_item_to_order(phone_number, item['item_id'], item['quantity'])
            logger.info(f"➕ Added item {item['item_id']} × {item['quantity']} to order for {phone_number}")
        
        # Build response message
        if language == 'arabic':
            response = "تم إضافة العناصر التالية إلى طلبك:\n\n"
            for item in processed_items:
                response += f"• {item['item_name']} × {item['quantity']} - {item['price']} دينار\n"
            
            if failed_items:
                response += f"\n⚠️ لم أتمكن من العثور على: {', '.join(failed_items)}"
            
            response += "\nهل تريد إضافة المزيد من الأصناف؟\n\n1. نعم\n2. لا"
        else:
            response = "Added the following items to your order:\n\n"
            for item in processed_items:
                response += f"• {item['item_name']} × {item['quantity']} - {item['price']} IQD\n"
            
            if failed_items:
                response += f"\n⚠️ Could not find: {', '.join(failed_items)}"
            
            response += "\nDo you want to add more items?\n\n1. Yes\n2. No"
        
        # Update session to waiting for additional items
        self.db.create_or_update_session(
            phone_number, 'waiting_for_additional', language,
            session.get('customer_name'),
            selected_main_category=session.get('selected_main_category'),
            selected_sub_category=session.get('selected_sub_category')
        )
        
        return self._create_response(response)

    def _handle_quick_order_selection(self, phone_number: str, extracted_data: Dict, session: Dict, user_context: Dict) -> Dict:
        """Handle quick order mode selection"""
        language = user_context.get('language', 'arabic')
        
        # Set quick order mode in session
        self.db.create_or_update_session(
            phone_number, 'waiting_for_quick_order', language,
            session.get('customer_name'),
            order_mode='quick'
        )
        
        # Show quick order interface
        return self._show_quick_order_interface(phone_number, language)
    
    def _handle_explore_menu_selection(self, phone_number: str, extracted_data: Dict, session: Dict, user_context: Dict) -> Dict:
        """Handle explore menu mode selection"""
        language = user_context.get('language', 'arabic')
        
        # Set explore menu mode in session
        self.db.create_or_update_session(
            phone_number, 'waiting_for_category', language,
            session.get('customer_name'),
            order_mode='explore'
        )
        
        # Show traditional category selection
        return self._show_traditional_categories(phone_number, language)

    def _match_item_from_context(self, item_name: str, user_context: Dict) -> Optional[Dict]:
        """Match item by name using context information"""
        # Get current sub-category items from context
        current_category_items = user_context.get('current_category_items', [])
        
        if not current_category_items:
            # Try to get items from database if not in context
            sub_category_id = user_context.get('selected_sub_category')
            if sub_category_id:
                current_category_items = self.db.get_sub_category_items(sub_category_id)
        
        if not current_category_items:
            logger.warning("⚠️ No items available for matching")
            return None
        
        # Use the existing matching logic
        language = user_context.get('language', 'arabic')
        return self._match_item_by_name(item_name, current_category_items, language)

    def _handle_intelligent_suggestion(self, phone_number: str, ai_result: Dict, session: Dict, user_context: Dict) -> Dict:
        """Handle intelligent suggestions from AI"""
        extracted_data = ai_result.get('extracted_data', {})
        response_message = ai_result.get('response_message', '')
        language = user_context.get('language', 'arabic')
        current_step = user_context.get('current_step')
        original_user_message = user_context.get('original_user_message', '')

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
            else:
                logger.warning(f"⚠️ Invalid main category suggestion: {suggested_main_category}, falling back to structured processing")
                # Fall back to structured processing with original message
                return self._handle_structured_message(phone_number, original_user_message, current_step, session, user_context)

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
                
            # CRITICAL VALIDATION: Check if suggested sub-category is valid for current main category
            max_sub_categories_by_main = {1: 7, 2: 3, 3: 5}  # Cold Drinks: 7, Hot Drinks: 3, Pastries & Sweets: 5
            max_allowed = max_sub_categories_by_main.get(main_category_id, 0)
            
            if suggested_sub_category > max_allowed:
                logger.error(f"🚫 CRITICAL: AI suggested invalid sub-category {suggested_sub_category} for main category {main_category_id} (max: {max_allowed})")
                logger.info(f"🔄 Falling back to structured processing for context-invalid AI suggestion with original message: '{original_user_message}'")
                return self._handle_structured_message(phone_number, original_user_message, current_step, session, user_context)
                
            sub_categories = self.db.get_sub_categories(main_category_id)
            logger.info(f"🔍 Sub-category selection: suggested={suggested_sub_category}, available={len(sub_categories)}, main_category={main_category_id}")
            
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
                # Fall back to structured processing with original message
                logger.info(f"🔄 Falling back to structured processing for invalid AI suggestion with original message: '{original_user_message}'")
                return self._handle_structured_message(phone_number, original_user_message, current_step, session, user_context)

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

    def _handle_sub_category_selection(self, phone_number: str, extracted_data: Dict, session: Dict, user_context: Dict) -> Dict:
        """Handle AI sub-category selection (e.g., user asks for mojito sub-category)"""
        sub_category_name = extracted_data.get('sub_category_name')
        sub_category_id = extracted_data.get('sub_category_id')
        language = user_context.get('language')
        
        logger.info(f"🎯 Sub-category selection: name='{sub_category_name}', id={sub_category_id}")
        
        # Get current main category
        main_category_id = session.get('selected_main_category')
        if not main_category_id:
            logger.error(f"❌ No selected_main_category in session for {phone_number}")
            return self._create_response("خطأ في النظام. الرجاء البدء من جديد")
        
        # Ensure main_category_id is an integer
        if isinstance(main_category_id, dict):
            main_category_id = main_category_id.get('id', main_category_id)
        elif not isinstance(main_category_id, int):
            try:
                main_category_id = int(main_category_id)
            except (ValueError, TypeError):
                return self._create_response("خطأ في النظام. الرجاء البدء من جديد")
        
        # Get sub-categories for current main category
        sub_categories = self.db.get_sub_categories(main_category_id)
        
        # Find the requested sub-category
        selected_sub_category = None
        
        if sub_category_id:
            # Direct ID selection
            if 1 <= sub_category_id <= len(sub_categories):
                selected_sub_category = sub_categories[sub_category_id - 1]
        
        elif sub_category_name:
            # Name-based selection
            for sub_cat in sub_categories:
                if (sub_category_name.lower() in sub_cat['name_ar'].lower() or 
                    sub_category_name.lower() in sub_cat['name_en'].lower()):
                    selected_sub_category = sub_cat
                    break
        
        if selected_sub_category:
            logger.info(f"✅ Found sub-category: '{selected_sub_category['name_ar']}' (ID: {selected_sub_category['id']})")
            
            # Update session
            self.db.create_or_update_session(
                phone_number, 'waiting_for_item', language,
                session.get('customer_name'),
                selected_main_category=main_category_id,
                selected_sub_category=selected_sub_category['id']
            )
            
            # Show sub-category items
            return self._show_sub_category_items(phone_number, selected_sub_category, language)
        else:
            logger.warning(f"❌ Sub-category not found: name='{sub_category_name}', id={sub_category_id}")
            if language == 'arabic':
                return self._create_response(f"عذراً، لم نجد الفئة الفرعية '{sub_category_name}'. الرجاء اختيار من القائمة المتاحة.")
            else:
                return self._create_response(f"Sorry, we couldn't find the sub-category '{sub_category_name}'. Please select from the available options.")

    def _handle_intelligent_item_selection(self, phone_number: str, extracted_data: Dict, session: Dict, user_context: Dict) -> Dict:
        """Handle intelligent item selection that can work across different steps"""
        item_name = extracted_data.get('item_name')
        item_id = extracted_data.get('item_id')
        language = user_context.get('language', 'arabic')
        current_step = user_context.get('current_step')
        
        logger.info(f"🧠 Intelligent item selection: '{item_name}' at step '{current_step}'")
        
        # Validate that we're at the correct step for item selection
        if current_step == 'waiting_for_sub_category':
            logger.warning(f"❌ Invalid: Attempting item selection at sub-category step")
            if language == 'arabic':
                return self._create_response("الرجاء اختيار الفئة الفرعية أولاً قبل اختيار المنتج المحدد.")
            else:
                return self._create_response("Please select a sub-category first before selecting a specific item.")
        
        # If we have a direct item ID, use it
        if item_id:
            return self._handle_ai_item_selection(phone_number, extracted_data, session, user_context)
        
        # If we have an item name, we need to find it intelligently
        if item_name:
            # First, try to find the item in the current context
            if current_step == 'waiting_for_item' and session and session.get('selected_sub_category'):
                # We're already at item selection step, try to match in current sub-category
                sub_category_id = session.get('selected_sub_category')
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
            logger.info(f"🔍 Searching across {len(main_categories)} main categories")
            
            for main_cat in main_categories:
                sub_categories = self.db.get_sub_categories(main_cat['id'])
                logger.info(f"🔍 Searching main category '{main_cat['name_ar']}' with {len(sub_categories)} sub-categories")
                
                for sub_cat in sub_categories:
                    items = self.db.get_sub_category_items(sub_cat['id'])
                    logger.info(f"🔍 Checking sub-category '{sub_cat['name_ar']}' with {len(items)} items")
                    
                    # Special handling for mojito - check if any item contains "موهيتو"
                    if item_name.lower() in ['موهيتو', 'mojito']:
                        logger.info(f"🔍 Special mojito handling for '{item_name}' in sub-category '{sub_cat['name_ar']}' (ID: {sub_cat['id']})")
                        
                        # Check if this is the mojito sub-category
                        if sub_cat['name_ar'].lower() == 'موهيتو' or sub_cat['id'] == 6:
                            logger.info(f"🎯 Found mojito sub-category! Searching for mojito items...")
                            for item in items:
                                logger.info(f"🔍 Checking item: '{item['item_name_ar']}' (ID: {item['id']})")
                                if 'موهيتو' in item['item_name_ar'].lower() or 'mojito' in item['item_name_en'].lower():
                                    logger.info(f"✅ Found mojito item: '{item['item_name_ar']}' in sub-category '{sub_cat['name_ar']}'")
                                    
                                    # Update session to reflect the found item's context
                                    self.db.create_or_update_session(
                                        phone_number, 'waiting_for_quantity', language,
                                        session.get('customer_name'),
                                        selected_main_category=main_cat['id'],
                                        selected_sub_category=sub_cat['id'],
                                        selected_item=item['id']
                                    )
                                    
                                    # Show quantity selection for the found item
                                    return self._show_quantity_selection(phone_number, item, language)
                            
                            logger.info(f"❌ No mojito items found in mojito sub-category, continuing search...")
                        else:
                            logger.info(f"🔍 Not in mojito sub-category, continuing search...")
                            continue
                    
                    # Regular matching for other items
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
            
            # Special handling for mojito - if not found, navigate to mojito sub-category
            if item_name.lower() in ['موهيتو', 'mojito']:
                logger.info(f"🔍 Mojito not found, navigating to mojito sub-category...")
                
                # Find the mojito sub-category in Cold Drinks (main category 1)
                main_categories = self.db.get_main_categories()
                cold_drinks_main = next((cat for cat in main_categories if cat['id'] == 1), None)
                
                if cold_drinks_main:
                    sub_categories = self.db.get_sub_categories(1)  # Cold Drinks
                    mojito_sub = next((sub for sub in sub_categories if sub['id'] == 6), None)
                    
                    if mojito_sub:
                        logger.info(f"✅ Found mojito sub-category, showing items...")
                        
                        # Update session to mojito sub-category
                        self.db.create_or_update_session(
                            phone_number, 'waiting_for_item', language,
                            session.get('customer_name'),
                            selected_main_category=1,
                            selected_sub_category=6
                        )
                        
                        # Show mojito items
                        return self._show_sub_category_items(phone_number, mojito_sub, language)
            
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
            item_id = session.get('selected_item') if session else None
            logger.info(f"🔧 Processing quantity: item_id={item_id}, quantity={quantity} for {phone_number}")
            
            if item_id:
                # Check if this item already exists in the order
                current_order = self.db.get_user_order(phone_number)
                existing_item = None
                
                if current_order and current_order.get('items'):
                    for item in current_order['items']:
                        if item['menu_item_id'] == item_id:
                            existing_item = item
                            break
                
                if existing_item:
                    # Update existing item quantity
                    logger.info(f"🔄 Updating existing item quantity from {existing_item['quantity']} to {quantity}")
                    success = self.db.update_item_quantity(phone_number, item_id, quantity)
                    action = "updated"
                else:
                    # Add new item to order
                    logger.info(f"➕ Adding new item to order: item_id={item_id}, quantity={quantity}")
                    success = self.db.add_item_to_order(phone_number, item_id, quantity)
                    action = "added"
                
                if success:
                    # Update session - clear selected_item to prevent re-adding
                    self.db.create_or_update_session(
                        phone_number, 'waiting_for_additional', language,
                        session.get('customer_name') if session else None,
                        selected_main_category=session.get('selected_main_category') if session else None,
                        selected_sub_category=session.get('selected_sub_category') if session else None,
                        selected_item=None  # Clear selected item
                    )
                    
                    # Get item details for confirmation
                    sub_category_id = session.get('selected_sub_category') if session else None
                    items = self.db.get_sub_category_items(sub_category_id) if sub_category_id else []
                    selected_item = next((item for item in items if item['id'] == item_id), None)
                    
                    if selected_item:
                        if language == 'arabic':
                            if action == "updated":
                                message = f"تم تحديث {selected_item['item_name_ar']} إلى × {quantity}\n\nهل تريد إضافة المزيد من الأصناف؟\n\n1. نعم\n2. لا"
                            else:
                                message = f"تم إضافة {selected_item['item_name_ar']} × {quantity} إلى طلبك\n\nهل تريد إضافة المزيد من الأصناف؟\n\n1. نعم\n2. لا"
                        else:
                            if action == "updated":
                                message = f"Updated {selected_item['item_name_en']} to × {quantity}\n\nWould you like to add more items?\n\n1. Yes\n2. No"
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
                    session.get('customer_name') if session else None
                )
                return self._show_main_categories(phone_number, language)
            
            elif current_step == 'waiting_for_confirmation':
                # Confirm order
                return self._confirm_order(phone_number, session, user_context)
            
            elif current_step == 'waiting_for_fresh_start_choice':
                # Start new order - clear everything
                self.db.cancel_order(phone_number)
                self.db.delete_session(phone_number)
                
                if language == 'arabic':
                    return self._create_response("ممتاز! اختر من القائمة الرئيسية:\n\n1. المشروبات الباردة\n2. المشروبات الحارة\n3. الحلويات والمعجنات\n\nالرجاء اختيار الفئة المطلوبة")
                else:
                    return self._create_response("Great! Choose from the main menu:\n\n1. Cold Drinks\n2. Hot Drinks\n3. Pastries & Sweets\n\nPlease select the required category")

        elif yes_no == 'no':
            if current_step == 'waiting_for_additional':
                # Proceed to service selection
                self.db.create_or_update_session(
                    phone_number, 'waiting_for_service', language,
                    session.get('customer_name') if session else None
                )
                return self._show_service_selection(phone_number, language)
            
            elif current_step == 'waiting_for_confirmation':
                # Cancel order
                return self._cancel_order(phone_number, session, user_context)
            
            elif current_step == 'waiting_for_fresh_start_choice':
                # Since the order was already completed, start a new order
                # (There's no "previous order" to keep after completion)
                self.db.create_or_update_session(
                    phone_number, 'waiting_for_category', language,
                    session.get('customer_name') if session else None
                )
                
                return self._show_main_categories(phone_number, language)

        return self._create_response(self._get_fallback_message(current_step, language))

    def _handle_ai_service_selection(self, phone_number: str, extracted_data: Dict, session: Dict, user_context: Dict) -> Dict:
        """Handle AI service selection"""
        language = user_context.get('language', 'arabic')
        
        # Convert Arabic numerals to English
        converted_text = self._convert_arabic_numerals(extracted_data.get('service_type', ''))
        text_lower = extracted_data.get('service_type', '').lower().strip()
        converted_lower = converted_text.lower().strip()
        
        service_type = None
        
        # First check for exact numeric matches (1 or 2 only)
        import re
        if re.match(r'^[12]$', converted_lower):
            if converted_lower == '1':
                service_type = 'dine-in'
                logger.info(f"✅ Dine-in service detected from exact number: '{extracted_data.get('service_type')}'")
            elif converted_lower == '2':
                service_type = 'delivery'
                logger.info(f"✅ Delivery service detected from exact number: '{extracted_data.get('service_type')}'")
        # Check for dine-in indicators (including Arabic numerals)
        elif (any(word in text_lower for word in ['داخل', 'في المقهى', 'dine', 'restaurant']) or
              any(word in converted_lower for word in ['dine', 'restaurant'])):
            service_type = 'dine-in'
            logger.info(f"✅ Dine-in service detected from text: '{extracted_data.get('service_type')}' (converted: '{converted_text}')")
        # Check for delivery indicators (including Arabic numerals)
        elif (any(word in text_lower for word in ['توصيل', 'delivery', 'home']) or
              any(word in converted_lower for word in ['delivery', 'home'])):
            service_type = 'delivery'
            logger.info(f"✅ Delivery service detected from text: '{extracted_data.get('service_type')}' (converted: '{converted_text}')")
        
        if service_type:
            # Update session step
            self.db.create_or_update_session(
                phone_number, 'waiting_for_location', language,
                session.get('customer_name') if session else None
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
        """Handle AI location input with enhanced table number validation"""
        language = user_context.get('language', 'arabic')
        location = extracted_data.get('location', '').strip()
        
        # Check for table number validation from AI processor
        table_validation = extracted_data.get('table_number_validation')
        if table_validation == 'invalid':
            invalid_number = extracted_data.get('invalid_table_number')
            if language == 'arabic':
                return self._create_response(f"رقم الطاولة {invalid_number} غير صحيح. الرجاء اختيار رقم من 1 إلى 7:")
            else:
                return self._create_response(f"Table number {invalid_number} is invalid. Please choose a number from 1 to 7:")
        
        # Clean location (remove trailing commas, etc.)
        clean_location = location.rstrip(',')
        
        # Check if this is a table number for dine-in service
        current_order = self.db.get_current_order(phone_number)
        service_type = None
        if current_order and current_order.get('details'):
            service_type = current_order['details'].get('service_type')
        
        if service_type == 'dine-in':
            # Additional validation for table number (1-7)
            try:
                # Convert Arabic numerals to English
                clean_location = self._convert_arabic_numerals(clean_location)
                table_num = int(clean_location)
                
                if table_num < 1 or table_num > 7:
                    if language == 'arabic':
                        return self._create_response("رقم الطاولة غير صحيح. الرجاء اختيار رقم من 1 إلى 7:")
                    else:
                        return self._create_response("Invalid table number. Please choose a number from 1 to 7:")
                
                clean_location = str(table_num)  # Use clean number
                
            except ValueError:
                if language == 'arabic':
                    return self._create_response("الرجاء إدخال رقم صحيح للطاولة (1-7):")
                else:
                    return self._create_response("Please enter a valid table number (1-7):")
        
        # Update session step
        self.db.create_or_update_session(
            phone_number, 'waiting_for_confirmation', language,
            session.get('customer_name') if session else None
        )
        
        # Update order details with clean location
        self.db.update_order_details(phone_number, location=clean_location)
        
        # Show order summary
        return self._show_order_summary(phone_number, session, user_context, clean_location)

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
        elif current_step == 'waiting_for_sub_category' and session:
            main_categories = self.db.get_main_categories()
            selected_category = next((cat for cat in main_categories if cat['id'] == session.get('selected_main_category')), None)
            if selected_category:
                return self._show_sub_categories(phone_number, selected_category, language)
        elif current_step == 'waiting_for_item' and session:
            main_category_id = session.get('selected_main_category')
            sub_category_id = session.get('selected_sub_category')
            if main_category_id and sub_category_id:
                sub_categories = self.db.get_sub_categories(main_category_id)
                selected_sub_category = next((cat for cat in sub_categories if cat['id'] == sub_category_id), None)
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
            'waiting_for_service': 'waiting_for_additional',  # Go back to add more items prompt
            'waiting_for_location': 'waiting_for_service',
            'waiting_for_confirmation': 'waiting_for_location'
        }
        
        previous_step = back_transitions.get(current_step)
        
        # Special case: if at waiting_for_category, check if we should go back to add more items
        if current_step == 'waiting_for_category' and not previous_step:
            # Check if there's an existing order with items (indicating we came from add more items)
            current_order = self.db.get_current_order(phone_number)
            if current_order and current_order.get('items'):
                # Go back to add more items prompt
                self.db.create_or_update_session(
                    phone_number, 'waiting_for_additional', language,
                    session.get('customer_name') if session else None
                )
                
                # Show the add more items prompt
                if language == 'arabic':
                    message = "هل تريد إضافة المزيد من الأصناف؟\n1. نعم\n2. لا"
                else:
                    message = "Do you want to add more items?\n1. Yes\n2. No"
                return self._create_response(message)
        
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
                session.get('customer_name') if session else None,
                selected_main_category=None,
                selected_sub_category=None,
                selected_item=None
            )
            return self._show_main_categories(phone_number, language)
            
        elif previous_step == 'waiting_for_sub_category':
            self.db.create_or_update_session(
                phone_number, previous_step, language,
                session.get('customer_name') if session else None,
                selected_main_category=session.get('selected_main_category') if session else None,
                selected_sub_category=None,
                selected_item=None
            )
            main_category_id = session.get('selected_main_category') if session else None
            if main_category_id:
                main_categories = self.db.get_main_categories()
                for cat in main_categories:
                    if cat['id'] == main_category_id:
                        return self._show_sub_categories(phone_number, cat, language)
            return self._show_main_categories(phone_number, language)
            
        # Default: update step and show appropriate content for the previous step
        self.db.create_or_update_session(
            phone_number, previous_step, language,
            session.get('customer_name') if session else None
        )
        
        # Show appropriate content for the previous step
        if previous_step == 'waiting_for_item':
            # Going back to item selection - show items from current sub-category
            sub_category_id = session.get('selected_sub_category') if session else None
            if sub_category_id:
                sub_categories = self.db.get_sub_categories(session.get('selected_main_category'))
                for sub_cat in sub_categories:
                    if sub_cat['id'] == sub_category_id:
                        return self._show_sub_category_items(phone_number, sub_cat, language)
        elif previous_step == 'waiting_for_additional':
            # Going back to add more items prompt
            self.db.create_or_update_session(
                phone_number, previous_step, language,
                session.get('customer_name') if session else None
            )
            
            # Show the add more items prompt
            if language == 'arabic':
                message = "هل تريد إضافة المزيد من الأصناف؟\n1. نعم\n2. لا"
            else:
                message = "Do you want to add more items?\n1. Yes\n2. No"
            return self._create_response(message)
            
        elif previous_step == 'waiting_for_quantity':
            # Going back to quantity - remove the last added item and show quantity selection again
            if current_step == 'waiting_for_additional':
                # Remove the last added item from the order
                success = self.db.remove_last_item_from_order(phone_number)
                if success:
                    logger.info(f"🔙 Removed last item when going back from {current_step} to {previous_step}")
                else:
                    logger.warning(f"⚠️ Failed to remove last item when going back from {current_step} to {previous_step}")
            
            # Update session to quantity step
            self.db.create_or_update_session(
                phone_number, previous_step, language,
                session.get('customer_name') if session else None,
                selected_main_category=session.get('selected_main_category') if session else None,
                selected_sub_category=session.get('selected_sub_category') if session else None,
                selected_item=session.get('selected_item') if session else None
            )
            
            # Show quantity selection message
            if language == 'arabic':
                message = "تم إلغاء العنصر السابق. كم الكمية المطلوبة؟"
            else:
                message = "Previous item cancelled. How many do you need?"
            return self._create_response(message)
        
        # Fallback message
        if language == 'arabic':
            message = "تم الرجوع للخطوة السابقة"
        else:
            message = "Returned to previous step"
        return self._create_response(message)

    def _handle_conversational_response(self, phone_number: str, ai_result: Dict, session: Dict, user_context: Dict) -> Dict:
        """Handle conversational responses that need acknowledgment"""
        response_message = ai_result.get('response_message', '')
        
        # If AI provided a response, use it (it should include the redirect)
        if response_message:
            return self._create_response(response_message)
        
        # Fallback: acknowledge and redirect based on current step
        current_step = user_context.get('current_step')
        language = user_context.get('language', 'arabic')
        
        if language == 'arabic':
            if current_step == 'waiting_for_confirmation':
                message = "الحمد لله، بخير! شكراً لسؤالك. الآن، هل تريد تأكيد طلبك؟\n\n1. نعم\n2. لا"
            elif current_step == 'waiting_for_sub_category':
                # If user asked "where are they?", show the sub-categories again
                main_category_id = session.get('selected_main_category') if session else None
                if main_category_id:
                    main_categories = self.db.get_main_categories()
                    for cat in main_categories:
                        if cat['id'] == main_category_id:
                            return self._show_sub_categories(phone_number, cat, language)
                message = "عذراً على عدم الوضوح. دعني أعرض لك الخيارات المتاحة مرة أخرى."
            else:
                message = "شكراً لك! دعنا نكمل طلبك."
        else:
            if current_step == 'waiting_for_confirmation':
                message = "I'm doing well, thank you for asking! Now, would you like to confirm your order?\n\n1. Yes\n2. No"
            elif current_step == 'waiting_for_sub_category':
                # If user asked "where are they?", show the sub-categories again
                main_category_id = session.get('selected_main_category')
                if main_category_id:
                    main_categories = self.db.get_main_categories()
                    for cat in main_categories:
                        if cat['id'] == main_category_id:
                            return self._show_sub_categories(phone_number, cat, language)
                message = "Sorry for the confusion. Let me show you the available options again."
            else:
                message = "Thank you! Let's continue with your order."
        
        return self._create_response(message)

    def _handle_structured_message(self, phone_number: str, text: str, current_step: str, session: Dict, user_context: Dict) -> Dict:
        """Fallback to structured message processing when AI is not available"""
        logger.info(f"🔄 Using structured processing for: '{text}' at step '{current_step}'")
        
        language = user_context.get('language', 'arabic')
        
        # Check for back navigation keywords first
        back_keywords = ['رجوع', 'back', 'السابق', 'previous', 'عودة', 'return']
        if any(keyword in text.lower() for keyword in back_keywords):
            logger.info(f"🔙 Back navigation detected in structured handler: '{text}'")
            return self._handle_back_navigation(phone_number, session, user_context)
        
        # Handle different steps with structured logic
        if current_step == 'waiting_for_language':
            return self._handle_structured_language_selection(phone_number, text, session, user_context.get('customer_name'))
            
        elif current_step == 'waiting_for_category':
            return self._handle_structured_category_selection(phone_number, text, session, user_context)
            
        elif current_step == 'waiting_for_quick_order':
            return self._handle_structured_quick_order(phone_number, text, session, user_context)
        elif current_step == 'waiting_for_quick_order_quantity':
            return self._handle_quick_order_quantity(phone_number, {'quantity': 1}, session, user_context)
        elif current_step == 'waiting_for_quick_order_service':
            return self._handle_quick_order_service(phone_number, {'service_type': 'dine-in'}, session, user_context)
            
        elif current_step == 'waiting_for_sub_category':
            return self._handle_structured_sub_category_selection(phone_number, text, session, user_context)
            
        elif current_step == 'waiting_for_item':
            return self._handle_structured_item_selection(phone_number, text, session, user_context)
            
        elif current_step == 'waiting_for_quantity':
            return self._handle_structured_quantity_selection(phone_number, text, session, user_context)
            
        elif current_step == 'waiting_for_additional':
            return self._handle_structured_additional_selection(phone_number, text, session, user_context)
            
        elif current_step == 'waiting_for_service':
            return self._handle_structured_service_selection(phone_number, text, session, user_context)
            
        elif current_step == 'waiting_for_fresh_start_choice':
            return self._handle_structured_fresh_start_choice(phone_number, text, session, user_context)
            
        elif current_step == 'waiting_for_location':
            return self._handle_structured_location_input(phone_number, text, session, user_context)
            
        elif current_step == 'waiting_for_confirmation':
            return self._handle_structured_confirmation(phone_number, text, session, user_context)
            
        else:
            return self._create_response(self._get_fallback_message(current_step, language))

    def _handle_structured_language_selection(self, phone_number: str, text: str, session: Dict, customer_name: str = None) -> Dict:
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
        
        # Use provided customer name or fallback to session
        final_customer_name = customer_name or session.get('customer_name') if session else 'Valued Customer'
        logger.info(f"👤 Using customer name: {final_customer_name}")
                
        # Update session
        self.db.create_or_update_session(
            phone_number, 'waiting_for_category', language,
            final_customer_name
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
                    session.get('customer_name') if session else None,
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
                    session.get('customer_name') if session else None,
                    selected_main_category=matched_category['id']
                )
                
                return self._show_sub_categories(phone_number, matched_category, language)
            else:
                return self._create_response("الرجاء اختيار رقم من القائمة أو كتابة اسم الفئة")

    def _handle_structured_quick_order(self, phone_number: str, text: str, session: Dict, user_context: Dict) -> Dict:
        """Handle structured quick order input"""
        language = user_context.get('language', 'arabic')
        
        # Parse the input for quantity, item name, and optional table number
        # Example: "2 موهيتو ازرق للطاولة 5" or "3 قهوة"
        text = text.strip()
        
        # Extract quantity (default to 1 if not specified)
        quantity = 1
        item_name = text
        table_number = None
        
        # Look for quantity patterns
        import re
        quantity_pattern = r'^(\d+)\s+'
        quantity_match = re.match(quantity_pattern, text)
        if quantity_match:
            quantity = int(quantity_match.group(1))
            item_name = text[quantity_match.group(0).__len__():].strip()
        
        # Look for table number patterns
        table_pattern = r'للطاولة\s+(\d+)'
        table_match = re.search(table_pattern, item_name)
        if table_match:
            table_number = table_match.group(1)
            item_name = re.sub(table_pattern, '', item_name).strip()
        
        # Search for the item across all categories
        all_items = self._get_all_items()
        matched_item = self._match_item_by_name(item_name, all_items, language)
        
        if matched_item:
            # Store the matched item in session for quantity selection
            session['quick_order_item'] = matched_item
            session['quick_order_quantity'] = quantity
            if table_number:
                session['quick_order_table'] = table_number
            
            # Update session to quantity selection step
            self.db.create_or_update_session(phone_number, 'waiting_for_quick_order_quantity', language, session.get('customer_name'), order_mode='quick')
            
            # Show quantity buttons
            return self._show_quantity_buttons(phone_number, language, matched_item['name_ar'])
        else:
            # Item not found
            if language == 'arabic':
                response = f"لم أتمكن من العثور على '{item_name}' في قائمتنا.\n\n"
                response += "المنتجات المتاحة:\n"
                for item in all_items[:5]:  # Show first 5 items as suggestions
                    response += f"• {item['name_ar']} - {item['price']} دينار\n"
                response += "\nأو اختر 'استكشاف القائمة' للتصفح الكامل."
            else:
                response = f"Could not find '{item_name}' in our menu.\n\n"
                response += "Available items:\n"
                for item in all_items[:5]:  # Show first 5 items as suggestions
                    response += f"• {item['name_en']} - {item['price']} IQD\n"
                response += "\nOr choose 'Explore Menu' for full browsing."
            
            return self._create_response(response)
    
    def _handle_quick_order_quantity(self, phone_number: str, extracted_data: Dict, session: Dict, user_context: Dict) -> Dict:
        """Handle quick order quantity selection"""
        language = user_context.get('language', 'arabic')
        
        # Get the stored item from session
        quick_order_item = session.get('quick_order_item')
        if not quick_order_item:
            return self._create_response("حدث خطأ. الرجاء المحاولة مرة أخرى.")
        
        # Extract quantity from button click
        user_message = user_context.get('original_user_message', '')
        if user_message.startswith('quantity_'):
            quantity = int(user_message.split('_')[1])
        else:
            # Fallback: try to extract quantity from AI
            quantity = extracted_data.get('quantity', 1)
        
        # Add item to order
        self.db.add_item_to_order(phone_number, quick_order_item['id'], quantity)
        
        # Update session to service selection step
        self.db.create_or_update_session(phone_number, 'waiting_for_quick_order_service', language, session.get('customer_name'), order_mode='quick')
        
        # Show service type buttons
        return self._show_service_type_buttons(phone_number, language)
    
    def _handle_quick_order_service(self, phone_number: str, extracted_data: Dict, session: Dict, user_context: Dict) -> Dict:
        """Handle quick order service type selection"""
        language = user_context.get('language', 'arabic')
        
        # Extract service type from button click
        user_message = user_context.get('original_user_message', '')
        service_type = None
        
        if user_message == 'dine_in':
            service_type = 'dine-in'
        elif user_message == 'delivery':
            service_type = 'delivery'
        else:
            # Fallback: try to extract from AI
            service_type = extracted_data.get('service_type', 'dine-in')
        
        # Update order details
        self.db.update_order_details(phone_number, {'service_type': service_type})
        
        # Update session to location step
        if service_type == 'dine-in':
            self.db.create_or_update_session(phone_number, 'waiting_for_location', language, session.get('customer_name'), order_mode='quick')
            if language == 'arabic':
                return self._create_response("اختر رقم الطاولة (1-7):")
            else:
                return self._create_response("Select table number (1-7):")
        else:
            # For delivery, go to confirmation
            self.db.create_or_update_session(phone_number, 'waiting_for_confirmation', language, session.get('customer_name'), order_mode='quick')
            return self._handle_confirmation_step(phone_number, session, user_context)
    
    def _handle_quick_order_item_selection(self, phone_number: str, extracted_data: Dict, session: Dict, user_context: Dict) -> Dict:
        """Handle quick order item selection with interactive buttons"""
        language = user_context.get('language', 'arabic')
        
        # Get the item name from AI extraction
        item_name = extracted_data.get('item_name', '')
        if not item_name:
            # Fallback: get from original message
            item_name = user_context.get('original_user_message', '').strip()
        
        if not item_name:
            return self._create_response("لم أفهم المنتج المطلوب. الرجاء المحاولة مرة أخرى.")
        
        # Search for the item across all categories
        all_items = self._get_all_items()
        matched_item = self._match_item_by_name(item_name, all_items, language)
        
        if matched_item:
            # Store the matched item in session for quantity selection
            session['quick_order_item'] = matched_item
            
            # Update session to quantity selection step
            self.db.create_or_update_session(phone_number, 'waiting_for_quick_order_quantity', language, session.get('customer_name'), order_mode='quick')
            
            # Show quantity buttons
            return self._show_quantity_buttons(phone_number, language, matched_item['name_ar'])
        else:
            # Item not found
            if language == 'arabic':
                response = f"لم أتمكن من العثور على '{item_name}' في قائمتنا.\n\n"
                response += "المنتجات المتاحة:\n"
                for item in all_items[:5]:  # Show first 5 items as suggestions
                    response += f"• {item['name_ar']} - {item['price']} دينار\n"
                response += "\nأو اختر 'استكشاف القائمة' للتصفح الكامل."
            else:
                response = f"Could not find '{item_name}' in our menu.\n\n"
                response += "Available items:\n"
                for item in all_items[:5]:  # Show first 5 items as suggestions
                    response += f"• {item['name_en']} - {item['price']} IQD\n"
                response += "\nOr choose 'Explore Menu' for full browsing."
            
            return self._create_response(response)

    def _get_all_items(self) -> List[Dict]:
        """Get all items from all categories for quick order search"""
        all_items = []
        main_categories = self.db.get_main_categories()
        
        for category in main_categories:
            sub_categories = self.db.get_sub_categories(category['id'])
            for sub_category in sub_categories:
                items = self.db.get_sub_category_items(sub_category['id'])
                all_items.extend(items)
        
        return all_items

    def _handle_structured_sub_category_selection(self, phone_number: str, text: str, session: Dict, user_context: Dict) -> Dict:
        """Handle sub-category selection with enhanced number extraction"""
        language = user_context.get('language', 'arabic')
        main_category_id = session.get('selected_main_category')
        
        if not main_category_id:
            return self._create_response("خطأ في النظام. الرجاء المحاولة مرة أخرى.")
        
        # Try to extract number from mixed input (e.g., "4 iced tea" -> "4")
        import re
        
        # First convert Arabic numerals to Western numerals
        converted_text = self._convert_arabic_numerals(text)
        number_match = re.search(r'\d+', converted_text)
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
                        session.get('customer_name') if session else None,
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
                    session.get('customer_name') if session else None,
                    selected_main_category=session.get('selected_main_category') if session else None,
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
                    session.get('customer_name') if session else None,
                    selected_main_category=session.get('selected_main_category') if session else None,
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
        
        # Also handle Arabic words for numbers (including colloquial variants)
        arabic_number_words = {
            'صفر': '0', 'واحد': '1', 'اثنين': '2', 'ثنين': '2', 'اتنين': '2', 
            'ثلاثة': '3', 'تلاتة': '3', 'اربعة': '4', 'اربع': '4',
            'خمسة': '5', 'خمس': '5', 'ستة': '6', 'ست': '6', 
            'سبعة': '7', 'سبع': '7', 'ثمانية': '8', 'ثمان': '8', 
            'تسعة': '9', 'تسع': '9', 'عشرة': '10', 'عشر': '10',
            'احدى عشر': '11', 'اثنا عشر': '12'
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
                # Check if this item already exists in the order
                current_order = self.db.get_user_order(phone_number)
                existing_item = None
                
                if current_order and current_order.get('items'):
                    for item in current_order['items']:
                        if item['menu_item_id'] == item_id:
                            existing_item = item
                            break
                
                if existing_item:
                    # Update existing item quantity
                    logger.info(f"🔄 Updating existing item quantity from {existing_item['quantity']} to {quantity}")
                    success = self.db.update_item_quantity(phone_number, item_id, quantity)
                    action = "updated"
                else:
                    # Add new item to order
                    logger.info(f"➕ Adding new item to order: item_id={item_id}, quantity={quantity}")
                    success = self.db.add_item_to_order(phone_number, item_id, quantity)
                    action = "added"
                
                if success:
                    # Update session - clear selected_item to prevent re-adding
                    self.db.create_or_update_session(
                        phone_number, 'waiting_for_additional', language,
                        session.get('customer_name') if session else None,
                        selected_main_category=session.get('selected_main_category') if session else None,
                        selected_sub_category=session.get('selected_sub_category') if session else None,
                        selected_item=None  # Clear selected item
                    )
                    
                    if language == 'arabic':
                        if action == "updated":
                            message = f"تم تحديث الكمية إلى {quantity}\n"
                        else:
                            message = f"تم إضافة المنتج إلى طلبك\n"
                        message += "هل تريد إضافة المزيد من الأصناف؟\n\n"
                        message += "1. نعم\n"
                        message += "2. لا"
                    else:
                        if action == "updated":
                            message = f"Quantity updated to {quantity}\n"
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
            # Keep current category context and go to sub-categories
            main_category_id = session.get('selected_main_category')
            if main_category_id:
                # Go back to sub-categories of current main category
                self.db.create_or_update_session(
                    phone_number, 'waiting_for_sub_category', language,
                    session.get('customer_name') if session else None,
                    selected_main_category=main_category_id,
                    selected_sub_category=None,
                    selected_item=None
                )
                
                # Get main category and show its sub-categories
                main_categories = self.db.get_main_categories()
                for cat in main_categories:
                    if cat['id'] == main_category_id:
                        return self._show_sub_categories(phone_number, cat, language)
            
            # Fallback: go to main categories if no current category
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

    def _handle_structured_service_selection(self, phone_number: str, text: str, session: Dict, user_context: Dict) -> Dict:
        """Handle service selection with structured logic"""
        language = user_context.get('language', 'arabic')
        
        # Convert Arabic numerals to English
        converted_text = self._convert_arabic_numerals(text)
        text_lower = text.lower().strip()
        converted_lower = converted_text.lower().strip()
        
        service_type = None
        
        # First check for exact numeric matches (1 or 2 only)
        import re
        if re.match(r'^[12]$', converted_lower):
            if converted_lower == '1':
                service_type = 'dine-in'
                logger.info(f"✅ Dine-in service detected from exact number: '{text}'")
            elif converted_lower == '2':
                service_type = 'delivery'
                logger.info(f"✅ Delivery service detected from exact number: '{text}'")
        # Check for dine-in indicators (including Arabic numerals)
        elif (any(word in text_lower for word in ['داخل', 'في المقهى', 'dine', 'restaurant']) or
              any(word in converted_lower for word in ['dine', 'restaurant'])):
            service_type = 'dine-in'
            logger.info(f"✅ Dine-in service detected from text: '{text}' (converted: '{converted_text}')")
        # Check for delivery indicators (including Arabic numerals)
        elif (any(word in text_lower for word in ['توصيل', 'delivery', 'home']) or
              any(word in converted_lower for word in ['delivery', 'home'])):
            service_type = 'delivery'
            logger.info(f"✅ Delivery service detected from text: '{text}' (converted: '{converted_text}')")
        
        if service_type:
            # Update order details
            success = self.db.update_order_details(phone_number, service_type=service_type)
            logger.info(f"📝 Service type update: {service_type} for {phone_number}, success: {success}")
            
            # Update session step
            self.db.create_or_update_session(
                phone_number, 'waiting_for_location', language,
                session.get('customer_name') if session else None
            )
            
            if service_type == 'dine-in':
                if language == 'arabic':
                    return self._create_response("الرجاء تحديد رقم الطاولة (1-7):")
                else:
                    return self._create_response("Please specify table number (1-7):")
            else:
                if language == 'arabic':
                    return self._create_response("الرجاء مشاركة موقعك وأي تعليمات خاصة:")
                else:
                    return self._create_response("Please share your location and any special instructions:")
        
        # Invalid input
        logger.warning(f"❌ Invalid service selection: '{text}' (converted: '{converted_text}')")
        if language == 'arabic':
            return self._create_response("الرجاء اختيار نوع الخدمة:\n\n1. تناول في المقهى\n2. توصيل")
        else:
            return self._create_response("Please select service type:\n\n1. Dine-in\n2. Delivery")

    def _handle_structured_confirmation(self, phone_number: str, text: str, session: Dict, user_context: Dict) -> Dict:
        """Handle order confirmation with structured logic"""
        language = user_context.get('language', 'arabic')
        
        text_lower = text.lower().strip()
        
        # Check for confirmation
        if any(word in text_lower for word in ['نعم', 'yes', '1', 'تأكيد', 'confirm']):
            return self._confirm_order(phone_number, session, user_context)
        # Check for cancellation
        elif any(word in text_lower for word in ['لا', 'no', '2', 'إلغاء', 'cancel']):
            return self._cancel_order(phone_number, session, user_context)
        
        # Invalid input
        if language == 'arabic':
            return self._create_response("الرجاء الرد بـ 'نعم' للتأكيد أو 'لا' للإلغاء")
        else:
            return self._create_response("Please reply with 'yes' to confirm or 'no' to cancel")

    def _handle_structured_location_input(self, phone_number: str, text: str, session: Dict, user_context: Dict) -> Dict:
        """Handle location input with structured logic"""
        language = user_context.get('language', 'arabic')
        
        # Clean location (remove trailing commas, etc.)
        clean_location = text.strip().rstrip(',')
        
        # Check if this is a table number for dine-in service
        current_order = self.db.get_current_order(phone_number)
        service_type = None
        if current_order and current_order.get('details'):
            service_type = current_order['details'].get('service_type')
        
        if service_type == 'dine-in':
            # Validate table number (1-7)
            try:
                # Convert Arabic numerals to English
                clean_location = self._convert_arabic_numerals(clean_location)
                table_num = int(clean_location)
                
                if table_num < 1 or table_num > 7:
                    if language == 'arabic':
                        return self._create_response("رقم الطاولة غير صحيح. الرجاء اختيار رقم من 1 إلى 7:")
                    else:
                        return self._create_response("Invalid table number. Please choose a number from 1 to 7:")
                
                clean_location = str(table_num)  # Use clean number
                
            except ValueError:
                if language == 'arabic':
                    return self._create_response("الرجاء إدخال رقم صحيح للطاولة (1-7):")
                else:
                    return self._create_response("Please enter a valid table number (1-7):")
        
                # Update session step
        self.db.create_or_update_session(
            phone_number, 'waiting_for_confirmation', language,
            session.get('customer_name') if session else None
        )
        
        # Update order details with clean location
        self.db.update_order_details(phone_number, location=clean_location)
        
        # Show order summary
        return self._show_order_summary(phone_number, session, user_context, clean_location)

    def _handle_structured_fresh_start_choice(self, phone_number: str, text: str, session: Dict, user_context: Dict) -> Dict:
        """Handle user's choice for fresh start after order"""
        language = user_context.get('language', 'arabic')
        
        # Extract choice from input (handle Arabic numerals and text)
        import re
        converted_text = self._convert_arabic_numerals(text)
        text_lower = text.lower().strip()
        
        choice = None
        
        # Try numeric extraction first
        number_match = re.search(r'\d+', converted_text)
        if number_match:
            choice = int(number_match.group())
        # Try text matching for Arabic phrases
        elif 'جديد' in text_lower or 'بدء' in text_lower:
            choice = 1
        elif 'احتفاظ' in text_lower or 'سابق' in text_lower or 'keep' in text_lower.lower():
            choice = 2
        
        if choice:
            if choice == 1:
                # Start new order - clear everything
                self.db.cancel_order(phone_number)
                self.db.delete_session(phone_number)
                
                if language == 'arabic':
                    return self._create_response("ممتاز! اختر من القائمة الرئيسية:\n\n1. المشروبات الباردة\n2. المشروبات الحارة\n3. الحلويات والمعجنات\n\nالرجاء اختيار الفئة المطلوبة")
                else:
                    return self._create_response("Great! Choose from the main menu:\n\n1. Cold Drinks\n2. Hot Drinks\n3. Pastries & Sweets\n\nPlease select the required category")
            
            elif choice == 2:
                # Since the order was already completed, start a new order
                # (There's no "previous order" to keep after completion)
                self.db.create_or_update_session(
                    phone_number, 'waiting_for_category', language,
                    session.get('customer_name') if session else None
                )
                
                return self._show_main_categories(phone_number, language)
        
        # Invalid choice
        if language == 'arabic':
            return self._create_response("الرجاء اختيار 1 لبدء طلب جديد أو 2 للاحتفاظ بالطلب السابق")
        else:
            return self._create_response("Please choose 1 to start new order or 2 to keep previous order")

    # Helper methods for UI generation
    def _show_main_categories(self, phone_number: str, language: str) -> Dict:
        """Show main categories with two-button interface"""
        categories = self.db.get_main_categories()
        
        if language == 'arabic':
            header_text = "مرحباً!"
            body_text = "اختر طريقة الطلب"
            footer_text = ""
            buttons = [
                {
                    "type": "reply",
                    "reply": {
                        "id": "quick_order",
                        "title": "الطلب السريع"
                    }
                },
                {
                    "type": "reply",
                    "reply": {
                        "id": "explore_menu",
                        "title": "استكشاف القائمة"
                    }
                }
            ]
        else:
            header_text = "Hello!"
            body_text = "Choose your ordering method"
            footer_text = ""
            buttons = [
                {
                    "type": "reply",
                    "reply": {
                        "id": "quick_order",
                        "title": "Quick Order"
                    }
                },
                {
                    "type": "reply",
                    "reply": {
                        "id": "explore_menu",
                        "title": "Explore Menu"
                    }
                }
            ]
        
        return self._create_interactive_response(header_text, body_text, footer_text, buttons)

    def _show_quick_order_interface(self, phone_number: str, language: str) -> Dict:
        """Show quick order interface"""
        # Get popular items and recent orders
        popular_items = self._get_popular_items()
        recent_orders = self._get_recent_orders(phone_number)
        
        if language == 'arabic':
            message = "الطلب السريع\n\n"
            message += "اكتب اسم المنتج المطلوب:\n\n"
            
            if popular_items:
                message += "المنتجات الشائعة:\n"
                for item in popular_items[:3]:
                    message += f"• {item['name_ar']} - {item['price']} دينار\n"
                message += "\n"
            
            message += "مثال: 2 موهيتو ازرق"
        else:
            message = "Quick Order\n\n"
            message += "Type the item name you want:\n\n"
            
            if popular_items:
                message += "Popular items:\n"
                for item in popular_items[:3]:
                    message += f"• {item['name_en']} - {item['price']} IQD\n"
                message += "\n"
            
            message += "Example: 2 blue mojito"
        
        return self._create_response(message)
    
    def _show_quantity_buttons(self, phone_number: str, language: str, item_name: str) -> Dict:
        """Show quantity selection buttons"""
        if language == 'arabic':
            header_text = "اختر الكمية"
            body_text = f"كم {item_name} تريد؟"
            footer_text = ""
            buttons = []
            
            for i in range(1, 11):
                buttons.append({
                    "type": "reply",
                    "reply": {
                        "id": f"quantity_{i}",
                        "title": str(i)
                    }
                })
        else:
            header_text = "Select Quantity"
            body_text = f"How many {item_name} do you want?"
            footer_text = ""
            buttons = []
            
            for i in range(1, 11):
                buttons.append({
                    "type": "reply",
                    "reply": {
                        "id": f"quantity_{i}",
                        "title": str(i)
                    }
                })
        
        return self._create_interactive_response(header_text, body_text, footer_text, buttons)
    
    def _show_service_type_buttons(self, phone_number: str, language: str) -> Dict:
        """Show service type selection buttons"""
        if language == 'arabic':
            header_text = "اختر نوع الخدمة"
            body_text = "كيف تريد استلام طلبك؟"
            footer_text = ""
            buttons = [
                {
                    "type": "reply",
                    "reply": {
                        "id": "dine_in",
                        "title": "تناول في المقهى"
                    }
                },
                {
                    "type": "reply",
                    "reply": {
                        "id": "delivery",
                        "title": "توصيل للمنزل"
                    }
                }
            ]
        else:
            header_text = "Select Service Type"
            body_text = "How would you like to receive your order?"
            footer_text = ""
            buttons = [
                {
                    "type": "reply",
                    "reply": {
                        "id": "dine_in",
                        "title": "Dine In"
                    }
                },
                {
                    "type": "reply",
                    "reply": {
                        "id": "delivery",
                        "title": "Delivery"
                    }
                }
            ]
        
        return self._create_interactive_response(header_text, body_text, footer_text, buttons)

    def _show_traditional_categories(self, phone_number: str, language: str) -> Dict:
        """Show traditional category selection for explore mode"""
        categories = self.db.get_main_categories()
        
        if language == 'arabic':
            message = "استكشاف القائمة\n\n"
            message += "اختر الفئة المطلوبة:\n\n"
            for i, cat in enumerate(categories, 1):
                message += f"{i}. {cat['name_ar']}\n"
        else:
            message = "Explore Menu\n\n"
            message += "Select the category:\n\n"
            for i, cat in enumerate(categories, 1):
                message += f"{i}. {cat['name_en']}\n"
        
        return self._create_response(message)

    def _get_popular_items(self) -> List[Dict]:
        """Get popular items for quick order suggestions"""
        # This would typically come from analytics/order history
        # For now, return some hardcoded popular items
        return [
            {'name_ar': 'موهيتو ازرق', 'name_en': 'Blue Mojito', 'price': 5000},
            {'name_ar': 'فرابتشينو شوكولاتة', 'name_en': 'Chocolate Frappuccino', 'price': 5000},
            {'name_ar': 'لاتيه فانيلا', 'name_en': 'Vanilla Latte', 'price': 4000},
            {'name_ar': 'ايس كوفي', 'name_en': 'Iced Coffee', 'price': 3000},
            {'name_ar': 'موهيتو خوخ', 'name_en': 'Peach Mojito', 'price': 5000}
        ]

    def _get_recent_orders(self, phone_number: str) -> List[str]:
        """Get recent orders for quick reorder suggestions"""
        # This would typically come from order history
        # For now, return some example orders
        return [
            "2 موهيتو ازرق",
            "1 فرابتشينو شوكولاتة",
            "3 ايس كوفي"
        ]

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
            
            # Get service type from order details and translate it
            service_type = current_order.get('details', {}).get('service_type', 'غير محدد')
            if service_type == 'dine-in':
                service_type_ar = 'تناول في المقهى'
            elif service_type == 'delivery':
                service_type_ar = 'توصيل'
            else:
                service_type_ar = 'غير محدد'
            message += f"\nالخدمة: {service_type_ar}\n"
            message += f"المكان: {location}\n"
            message += f"السعر الإجمالي: {current_order['total']} دينار\n\n"
            message += "هل تريد تأكيد هذا الطلب؟\n\n1. نعم\n2. لا"
        else:
            message = "Here is your order summary:\n\n"
            message += "Items:\n"
            for item in current_order['items']:
                message += f"• {item['item_name_en']} × {item['quantity']} - {item['subtotal']} IQD\n"
            
            # Get service type from order details
            service_type = current_order.get('details', {}).get('service_type', 'Not specified')
            message += f"\nService: {service_type.title() if service_type != 'Not specified' else service_type}\n"
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
        # Use customer name from user_context first, then fallback to session
        customer_name = user_context.get('customer_name') or session.get('customer_name') or 'Customer'
        
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
            session.get('customer_name') if session else None
        )
        
        if language == 'arabic':
            message = "مرحباً! هل تريد:\n\n1️⃣ بدء طلب جديد\n2️⃣ الاحتفاظ بالطلب السابق"
        else:
            message = "Hello! Would you like to:\n\n1️⃣ Start new order\n2️⃣ Keep previous order"
        
        return self._create_response(message)

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

    def _match_category_by_name(self, text: str, categories: list, language: str) -> Optional[Dict]:
        """Match category by name with enhanced Arabic text recognition"""
        text_lower = text.lower().strip()
        
        # Enhanced Arabic sub-category mapping for Pastries & Sweets
        if language == 'arabic':
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
                    if 1 <= sub_cat_number <= len(categories):
                        return categories[sub_cat_number - 1]
        
        # Fallback to original matching logic
        for category in categories:
            if language == 'arabic':
                if text_lower in category['name_ar'].lower():
                    return category
            else:
                if text_lower in category['name_en'].lower():
                    return category
        
        return None

    def _match_item_by_name(self, text: str, items: list, language: str) -> Optional[Dict]:
        """Match item by name with enhanced scoring mechanism and Arabic normalization."""
        import re

        def normalize_ar(s: str) -> str:
            # Basic Arabic normalization: unify alef forms and strip tatweel
            return (s.replace('أ', 'ا').replace('إ', 'ا').replace('آ', 'ا')
                     .replace('ى', 'ي').replace('ؤ', 'و').replace('ئ', 'ي').replace('ـ', ''))

        def strip_prefixes(word: str) -> str:
            # Strip common attached prefixes like و + ال and ال
            for pref in ('وال', 'بال', 'كال', 'فال'):
                if word.startswith(pref) and len(word) > len(pref) + 1:
                    return word[len(pref):]
            for pref in ('ال', 'و'):
                if word.startswith(pref) and len(word) > len(pref) + 0:
                    return word[len(pref):]
            return word

        # Clean the input - remove numbers and extra spaces
        cleaned_text = re.sub(r'\d+', '', text).strip()

        # Tokenize, remove common stop-words, and strip attached prefixes
        common_words = ['اريد', 'عايز', 'بغيت', 'بدي', 'ممكن', 'لو', 'سمحت', 'من', 'فى', 'في', 'على', 'الى', 'إلى', 'و', 'او', 'أو', 'هذا', 'هذه', 'هذا', 'ال', 'واحد', 'اثنين', 'ثلاثة', 'اربعة', 'خمسة', 'ستة', 'سبعة', 'ثمانية', 'تسعة', 'عشرة']
        raw_words = cleaned_text.split()
        normalized_words = [strip_prefixes(normalize_ar(w)) for w in raw_words if w not in common_words]
        cleaned_text = ' '.join(normalized_words)
        text_lower = normalize_ar(cleaned_text.lower().strip())
        
        logger.info(f"🔍 Matching '{text}' (cleaned: '{cleaned_text}') against {len(items)} items")
        
        # Special handling for energy drinks
        energy_terms = ['طاقة', 'مشروب طاقة', 'مشروبات طاقة', 'ريد بول', 'red bull', 'monster', 'energy drink', 'energy']
        if any(term in text_lower for term in energy_terms):
            for item in items:
                item_name_lower = normalize_ar(item['item_name_ar'].lower() if language == 'arabic' else item['item_name_en'].lower())
                if any(energy_term in item_name_lower for energy_term in ['طاقة', 'energy']):
                    logger.info(f"✅ Energy drink match: '{item_name_lower}'")
                    return item

        # Early direct flavor match for mojito when flavor is spoken
        if language == 'arabic' and 'موهيتو' in text_lower:
            flavor_terms = [
                'رمان', 'خوخ', 'توت ازرق', 'ازرق', 'روزبيري', 'دراغون', 'علكة', 'هيف', 'فانيلا', 'كراميل', 'بينا كولادا', 'فاكهة العاطفة'
            ]
            for flavor in flavor_terms:
                if flavor in text_lower:
                    for item in items:
                        name_lower = normalize_ar(item['item_name_ar'].lower())
                        if flavor in name_lower and 'موهيتو' in name_lower:
                            logger.info(f"✅ Mojito flavor direct match: '{name_lower}' for flavor '{flavor}'")
                            return item
        
        # Scoring mechanism for better accuracy
        best_match = None
        best_score = 0
        
        for item in items:
            if language == 'arabic':
                item_name_lower = normalize_ar(item['item_name_ar'].lower())
            else:
                item_name_lower = normalize_ar(item['item_name_en'].lower())
            
            score = 0
            
            # 1. Exact substring match (highest priority)
            if text_lower in item_name_lower:
                score += 100
                logger.info(f"  ✅ Exact substring match: '{text_lower}' in '{item_name_lower}' (score: {score})")
            
            # 2. Item name contains all user words (very high priority)
            user_words = set(text_lower.split())
            item_words = set(item_name_lower.split())
            common_words = user_words & item_words
            
            if len(common_words) == len(user_words) and len(user_words) > 0:
                score += 80
                logger.info(f"  ✅ All user words found: {user_words} in '{item_name_lower}' (score: {score})")
            elif len(common_words) > 0:
                # 3. Partial word match (medium priority)
                score += 20 + (len(common_words) * 10)
                logger.info(f"  📊 Partial word match: {common_words} in '{item_name_lower}' (score: {score})")
            
            # 4. Bonus for longer matches (prefer more specific items)
            if len(item_name_lower) > len(text_lower):
                score += 5
            
            # 5. Special handling for specific terms
            if language == 'arabic':
                # Handle "موهيتو" (mojito) specifically - highest priority
                if 'موهيتو' in text_lower and 'موهيتو' in item_name_lower:
                    score += 200  # Very high score to ensure mojito items are prioritized
                    logger.info(f"  🍹 Mojito match bonus: '{item_name_lower}' (score: {score})")
                
                # Handle "دجاج" (chicken) specifically
                if 'دجاج' in text_lower and 'دجاج' in item_name_lower:
                    score += 15
                    logger.info(f"  🍗 Chicken match bonus: '{item_name_lower}' (score: {score})")
                
                # Handle "جبن" (cheese) specifically
                if 'جبن' in text_lower and 'جبن' in item_name_lower:
                    score += 10
                    logger.info(f"  🧀 Cheese match bonus: '{item_name_lower}' (score: {score})")
                
                # Handle "لحم" (meat) specifically
                if 'لحم' in text_lower and 'لحم' in item_name_lower:
                    score += 15
                    logger.info(f"  🥩 Meat match bonus: '{item_name_lower}' (score: {score})")
            
            # Update best match if this score is higher
            if score > best_score:
                best_score = score
                best_match = item
                logger.info(f"  🏆 New best match: '{item_name_lower}' with score {score}")
        
        if best_match and best_score > 0:
            # Special validation for mojito requests
            if language == 'arabic' and 'موهيتو' in text_lower:
                # If user asked for mojito but best match doesn't contain mojito, reject it
                if 'موهيتو' not in best_match['item_name_ar'].lower():
                    logger.warning(f"❌ Rejecting non-mojito match '{best_match['item_name_ar']}' for mojito request")
                    return None
            
            logger.info(f"✅ Final match: '{best_match['item_name_ar' if language == 'arabic' else 'item_name_en']}' with score {best_score}")
            return best_match
        
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
        """Extract customer name from message data with proper WhatsApp structure"""
        try:
            # Check for contacts array first (WhatsApp Business API structure)
            if 'contacts' in message_data and message_data['contacts']:
                contact = message_data['contacts'][0]
                if 'profile' in contact:
                    name = contact['profile'].get('name', '').strip()
                    if name:
                        logger.info(f"✅ Extracted customer name from contacts: {name}")
                        return name
            
            # Fallback: check for profile directly
            if 'profile' in message_data:
                name = message_data['profile'].get('name', '').strip()
                if name:
                    logger.info(f"✅ Extracted customer name from profile: {name}")
                    return name
            
            # Fallback: check for from field (phone number)
            if 'from' in message_data:
                phone = message_data['from']
                # Extract last 4 digits for a friendly name
                if len(phone) >= 4:
                    last_four = phone[-4:]
                    logger.info(f"⚠️ No name found, using phone suffix: {last_four}")
                    return f"Customer {last_four}"
            
            # Final fallback
            logger.warning("⚠️ No customer name found, using default")
            return "Valued Customer"
            
        except Exception as e:
            logger.error(f"❌ Error extracting customer name: {e}")
            return "Valued Customer"

    def _create_response(self, content: str) -> Dict[str, Any]:
        """Create response structure"""
        return {
            'type': 'text',
            'content': content
        }
    
    def _create_interactive_response(self, header_text: str, body_text: str, footer_text: str, buttons: List[Dict]) -> Dict[str, Any]:
        """Create interactive button response structure"""
        return {
            'type': 'interactive_buttons',
            'header_text': header_text,
            'body_text': body_text,
            'footer_text': footer_text,
            'buttons': buttons
        } 