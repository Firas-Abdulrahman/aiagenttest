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
            
            # Defensive programming: ensure session is a dictionary
            if session is not None and not isinstance(session, dict):
                logger.error(f"❌ Session is not a dictionary: {type(session)} = {session}")
                # Clear corrupted session and start fresh
                self.db.delete_session(phone_number)
                session = None
            
            # Build initial user context (may be updated after session reset)
            current_step = session.get('current_step') if session else 'waiting_for_language'
            user_context = self._build_user_context(phone_number, session, current_step, text)
            
            # Update user context with extracted customer name
            user_context['customer_name'] = customer_name
            
            # Check for session reset (fresh start intent or timeout)
            should_reset = self._should_reset_session(session, text)
            if should_reset:
                logger.info(f"🔄 Resetting session for {phone_number} due to fresh start intent or timeout")
                
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

            # Check for button clicks first - these should always use structured handling
            button_clicks = [
                'confirm_order', 'cancel_order', 'edit_order',
                'add_item_to_order', 'edit_item_quantity', 'remove_item_from_order',
                'quick_order_add', 'explore_menu_add', 'dine_in', 'delivery'
            ]
            
            # Check for edit/remove/quantity button patterns
            is_button_click = (
                text in button_clicks or
                text.startswith('edit_qty_') or
                text.startswith('remove_') or
                text.startswith('quantity_')
            )
            
            if is_button_click:
                logger.info(f"🔘 Button click detected: '{text}' - using structured handling")
                return self._handle_structured_message(phone_number, text, current_step, session, user_context)

            # Hybrid AI + Structured Processing
            logger.info(f"🔍 AI Status: ai={self.ai is not None}, available={self.ai.is_available() if self.ai else False}")
            ai_result = None
            
            if self.ai and self.ai.is_available():
                logger.info(f"🧠 Using enhanced AI for message: '{text}' at step '{current_step}'")
                # Determine language safely
                language = 'arabic'  # Default
                if session:
                    language = session.get('language_preference', 'arabic')
                
                # CRITICAL FIX: Convert Arabic numerals before AI processing
                processed_text = self._convert_arabic_numerals(text)
                if processed_text != text:
                    logger.info(f"🔢 Converted Arabic numerals: '{text}' → '{processed_text}'")
                
                ai_result = self.ai.understand_natural_language(
                    user_message=processed_text,
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
        
        elif current_step == 'waiting_for_sub_category':
            # AI might have extracted sub-category information
            sub_category_id = extracted_data.get('sub_category_id')
            if sub_category_id:
                logger.info(f"🔧 Using AI-extracted sub-category: {sub_category_id}")
                return self._handle_sub_category_selection(phone_number, extracted_data, session, user_context)
        
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
            'selected_main_category': session.get('selected_main_category') if session else None,
            'selected_sub_category': session.get('selected_sub_category') if session else None,
            'selected_item': session.get('selected_item') if session else None,
            'order_mode': session.get('order_mode') if session else None,  # Add order mode to context
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
        
        # Refresh session from database to get latest state
        session = self.db.get_user_session(phone_number)
        logger.info(f"🔍 Refreshed session: order_mode={session.get('order_mode') if session else 'None'}")

        # CRITICAL FIX: Override intelligent_suggestion in quick order mode
        if action == 'intelligent_suggestion' and current_step == 'waiting_for_quick_order':
            logger.info(f"🔄 Overriding intelligent_suggestion to item_selection for quick order mode")
            # Convert intelligent suggestion to item selection for quick order
            ai_result['action'] = 'item_selection'
            action = 'item_selection'
            
            # Extract item name from the user message
            user_message = user_context.get('original_user_message', '')
            if user_message:
                extracted_data['item_name'] = user_message.strip()
                extracted_data['quantity'] = 1  # Default quantity
                ai_result['extracted_data'] = extracted_data
                ai_result['understood_intent'] = f"User wants to order {user_message.strip()} (quick order mode)"
                logger.info(f"✅ Converted to item_selection: {extracted_data}")

        # Handle intelligent suggestions (items/categories) that can work across steps
        if action == 'intelligent_suggestion':
            return self._handle_intelligent_suggestion(phone_number, ai_result, session, user_context)

        # Handle specific step-based actions
        if action == 'language_selection':
            return self._handle_ai_language_selection(phone_number, extracted_data, session)
        elif action == 'show_menu':
            # Handle show menu request
            return self._handle_ai_show_menu(phone_number, session, user_context)
        elif action == 'category_selection':
            return self._handle_ai_category_selection(phone_number, extracted_data, session, user_context)
        elif action == 'sub_category_selection':
            # Handle sub-category selection (e.g., user asks for "موهيتو" sub-category)
            return self._handle_sub_category_selection(phone_number, extracted_data, session, user_context)
        elif action == 'item_selection':
            # Check if we're in quick order mode
            logger.info(f"🔍 Debug: order_mode={session.get('order_mode')}, current_step={user_context.get('current_step')}")
            if session.get('order_mode') == 'quick':
                logger.info(f"✅ Quick order mode detected, using interactive button flow")
                return self._handle_quick_order_item_selection(phone_number, extracted_data, session, user_context)
            else:
                logger.info(f"⚠️ Not in quick order mode, using traditional flow")
            
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
            # Pass direct_order flag to user context if present
            if ai_result.get('direct_order'):
                user_context['direct_order'] = True
            return self._handle_quick_order_selection(phone_number, extracted_data, session, user_context)
        elif action == 'explore_menu_selection':
            # Handle explore menu mode selection
            return self._handle_explore_menu_selection(phone_number, extracted_data, session, user_context)
        elif action == 'quantity_selection':
            # Check if we're editing an existing item quantity first
            current_step = user_context.get('current_step', '')
            if current_step == 'waiting_for_new_quantity':
                # User is editing quantity of existing item
                return self._handle_new_quantity_input(phone_number, str(extracted_data.get('quantity', '')), session, user_context)
            elif session.get('order_mode') == 'quick':
                # Handle quick order quantity selection (only if not editing existing quantity)
                return self._handle_quick_order_quantity(phone_number, extracted_data, session, user_context)
            else:
                # User is selecting quantity for new item
                return self._handle_ai_quantity_selection(phone_number, extracted_data, session, user_context)
        elif action == 'service_selection' and session.get('order_mode') == 'quick':
            # Handle quick order service selection
            return self._handle_quick_order_service(phone_number, extracted_data, session, user_context)
        elif action == 'confirmation':
            # Check for yes_no in extracted_data first
            yes_no = extracted_data.get('yes_no')
            if yes_no in ['yes', 'no']:
                # Route to yes_no handler for proper confirmation/cancellation
                return self._handle_ai_yes_no(phone_number, extracted_data, session, user_context)
            
            # Check for button clicks
            user_message = user_context.get('original_user_message', '')
            if user_message == 'confirm_order':
                return self._confirm_order(phone_number, session, user_context)
            elif user_message == 'cancel_order':
                return self._cancel_order(phone_number, session, user_context)
            else:
                return self._handle_ai_confirmation(phone_number, extracted_data, session, user_context)
        elif action == 'yes_no':
            return self._handle_ai_yes_no(phone_number, extracted_data, session, user_context)
        elif action == 'service_selection':
            return self._handle_ai_service_selection(phone_number, extracted_data, session, user_context)
        elif action == 'location_input':
            return self._handle_ai_location_input(phone_number, extracted_data, session, user_context)
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
        # Check if we have valid AI-extracted multi-item data first
        current_step = user_context.get('current_step', '')
        order_mode = session.get('order_mode') if session else None
        
        # First try to get multi_items from AI extracted data
        multi_items = extracted_data.get('multi_items', [])
        
        # If AI provided good multi-item data, use it regardless of mode
        if multi_items and len(multi_items) > 0:
            logger.info(f"✅ Using AI-extracted multi-items data: {len(multi_items)} items")
        elif current_step == 'waiting_for_quick_order' or order_mode == 'quick':
            logger.info("🎯 Multi-item selection in quick order mode but no AI data, falling back to structured processing")
            original_message = user_context.get('original_user_message', '')
            return self._handle_structured_quick_order(phone_number, original_message, session, user_context)
        
        # Continue with multi-item processing if no fallback needed
        
        # If not found, check if AI provided item_name array (which is the correct format from AI)
        if not multi_items and 'item_name' in extracted_data:
            ai_items = extracted_data.get('item_name', [])
            if isinstance(ai_items, list):
                multi_items = [{'item_name': item.get('name', ''), 'quantity': item.get('quantity', 1)} for item in ai_items]
                logger.info(f"🤖 Using AI-extracted items: {multi_items}")
        
        language = user_context.get('language', 'arabic')
        
        # Only fall back to manual extraction if AI completely failed
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
        
        # Check if service type and location were detected by AI first
        detected_service_type = extracted_data.get('service_type')
        detected_location = extracted_data.get('location')
        detected_table_number = None
        
        # Extract table number from location if it's in "Table X" format
        if detected_location and detected_location.startswith('Table '):
            detected_table_number = detected_location.replace('Table ', '')
        
        # If not found at top level, look for service type and table number in any of the multi_items
        if not detected_service_type:
            for item_data in multi_items:
                if item_data.get('service_type') and not detected_service_type:
                    detected_service_type = item_data.get('service_type')
                if item_data.get('table_number') and not detected_table_number:
                    detected_table_number = item_data.get('table_number')
        
        # If service type detected, handle appropriately
        if detected_service_type:
            logger.info(f"✅ Multi-item order with service type: {detected_service_type}, location: {detected_location or detected_table_number}")
            
            # Update order details
            self.db.update_order_details(phone_number, service_type=detected_service_type)
            
            order_mode = session.get('order_mode') if session else None
            if order_mode == 'quick':
                # Handle dine-in with table number or location
                if detected_service_type == 'dine-in' and (detected_table_number or detected_location):
                    # Use the AI-provided location if available, otherwise format table number
                    location_to_save = detected_location if detected_location else f"Table {detected_table_number}"
                    self.db.update_order_details(phone_number, location=location_to_save)
                    
                    # Go directly to confirmation
                    self.db.create_or_update_session(
                        phone_number, 'waiting_for_confirmation', language,
                        session.get('customer_name'),
                        order_mode='quick'
                    )
                    return self._show_quick_order_confirmation(phone_number, session, user_context)
                
                # Handle dine-in without table number or location (ask for table)
                elif detected_service_type == 'dine-in' and not detected_table_number and not detected_location:
                    self.db.create_or_update_session(
                        phone_number, 'waiting_for_location', language,
                        session.get('customer_name'),
                        order_mode='quick'
                    )
                    if language == 'arabic':
                        return self._create_response("اختر رقم الطاولة (1-7):")
                    else:
                        return self._create_response("Select table number (1-7):")
                
                # Handle delivery (ask for address)
                elif detected_service_type == 'delivery':
                    self.db.create_or_update_session(
                        phone_number, 'waiting_for_location', language,
                        session.get('customer_name'),
                        order_mode='quick'
                    )
                    if language == 'arabic':
                        return self._create_response("الرجاء مشاركة عنوانك أو موقعك للتوصيل:")
                    else:
                        return self._create_response("Please share your address or location for delivery:")
        
        # Regular flow: Build response message and ask for additional items
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
        original_user_message = user_context.get('original_user_message', '')
        
        # Check if this is a direct order (user provided item name directly)
        if extracted_data.get('item_name') or 'direct_order' in user_context:
            logger.info(f"🎯 Direct order detected: {original_user_message}")
            
            # Set quick order mode in session
            self.db.create_or_update_session(
                phone_number, 'waiting_for_quick_order', language,
                session.get('customer_name'),
                order_mode='quick'
            )
            
            # Update the session object in memory
            session['order_mode'] = 'quick'
            session['current_step'] = 'waiting_for_quick_order'
            
            # Process the direct order immediately
            return self._handle_structured_quick_order(phone_number, original_user_message, session, user_context)
        
        # Regular quick order selection (user clicked button or typed "quick_order")
        # Set quick order mode in session
        self.db.create_or_update_session(
            phone_number, 'waiting_for_quick_order', language,
            session.get('customer_name'),
            order_mode='quick'
        )
        
        # Update the session object in memory
        session['order_mode'] = 'quick'
        session['current_step'] = 'waiting_for_quick_order'
        
        logger.info(f"✅ Quick order mode set: order_mode={session.get('order_mode')}, current_step={session.get('current_step')}")
        
        # Show quick order interface
        return self._show_quick_order_interface(phone_number, language)
    
    def _handle_explore_menu_selection(self, phone_number: str, extracted_data: Dict, session: Dict, user_context: Dict) -> Dict:
        """Handle explore menu mode selection"""
        language = user_context.get('language', 'arabic')
        
        # Check if already in explore mode to prevent loops
        current_order_mode = session.get('order_mode')
        if current_order_mode == 'explore':
            # Already in explore mode, just show categories again
            if language == 'arabic':
                return self._create_response("ممتاز! إليك الفئات الرئيسية:\n\n1. المشروبات الباردة\n2. المشروبات الحارة\n3. الحلويات والمعجنات\n\nاختر رقم الفئة التي تفضلها!")
            else:
                return self._create_response("Great! Here are the main categories:\n\n1. Cold Drinks\n2. Hot Drinks\n3. Pastries & Sweets\n\nPlease select the category number you prefer!")
        
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
        
        language = user_context.get('language', 'arabic')
        
        # If still empty, fallback to matching across all items
        if not current_category_items:
            try:
                all_items = self._get_all_items()
            except Exception as e:
                logger.exception(f"⚠️ Failed to fetch all items for global matching fallback: {e}")
                all_items = []
            if not all_items:
                logger.warning("⚠️ No items available for matching")
                return None
            return self._match_item_by_name(item_name, all_items, language)
        
        # Use the existing matching logic
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
                
            # Get available sub-categories for this main category
            sub_categories = self.db.get_sub_categories(main_category_id)
            logger.info(f"🔍 Sub-category selection: suggested={suggested_sub_category}, available={len(sub_categories)}, main_category={main_category_id}")
            
            # Try to find the sub-category by both display order and actual database ID
            selected_sub_category = None
            
            # First try by display order (1-based index)
            if 1 <= suggested_sub_category <= len(sub_categories):
                selected_sub_category = sub_categories[suggested_sub_category - 1]
                logger.info(f"✅ Found sub-category by display order: {selected_sub_category['name_en']} (ID: {selected_sub_category['id']})")
            
            # If not found by display order, try by actual database ID
            if not selected_sub_category:
                for sub_cat in sub_categories:
                    if sub_cat['id'] == suggested_sub_category:
                        selected_sub_category = sub_cat
                        logger.info(f"✅ Found sub-category by database ID: {selected_sub_category['name_en']} (ID: {selected_sub_category['id']})")
                        break
            
            # If still not found, check if it's a valid sub-category ID for this main category
            if not selected_sub_category:
                # Get the valid sub-category IDs for this main category
                valid_sub_category_ids = [sub_cat['id'] for sub_cat in sub_categories]
                if suggested_sub_category in valid_sub_category_ids:
                    # This is a valid ID but not in our list (shouldn't happen, but just in case)
                    logger.warning(f"⚠️ Sub-category ID {suggested_sub_category} is valid but not found in sub_categories list")
                    return self._handle_structured_message(phone_number, original_user_message, current_step, session, user_context)
                else:
                    logger.error(f"🚫 CRITICAL: AI suggested invalid sub-category {suggested_sub_category} for main category {main_category_id}")
                    logger.info(f"🔄 Falling back to structured processing for context-invalid AI suggestion with original message: '{original_user_message}'")
                    return self._handle_structured_message(phone_number, original_user_message, current_step, session, user_context)
            
            # If we found a valid sub-category, proceed with it
            if selected_sub_category:
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

        # ENHANCED FIX: Context-aware intelligent suggestions for item selection
        if current_step == 'waiting_for_item':
            # User is in item selection step - provide context-aware suggestions
            sub_category_id = session.get('selected_sub_category')
            if sub_category_id:
                # Ensure sub_category_id is an integer
                if isinstance(sub_category_id, dict):
                    sub_category_id = sub_category_id.get('id', sub_category_id)
                elif not isinstance(sub_category_id, int):
                    try:
                        sub_category_id = int(sub_category_id)
                    except (ValueError, TypeError):
                        logger.error(f"❌ Cannot convert sub_category_id to int: {sub_category_id}")
                        return self._create_response("خطأ في النظام. الرجاء المحاولة مرة أخرى")
                
                # Get items from current sub-category only
                items = self.db.get_sub_category_items(sub_category_id)
                if items:
                    # Build context-aware suggestions based on user's request
                    user_message = original_user_message.lower()
                    suggestions = []
                    
                    # Filter items based on user's request
                    for item in items:
                        item_name = item['item_name_ar'].lower() if language == 'arabic' else item['item_name_en'].lower()
                        
                        # Check if item matches user's request
                        if any(keyword in item_name for keyword in user_message.split()):
                            suggestions.append(item)
                    
                    # If no specific matches, show all items in current category
                    if not suggestions:
                        suggestions = items[:3]  # Show first 3 items
                    
                    # Build response with current category items only
                    if language == 'arabic':
                        response = f"إليك خياراتنا من {items[0]['sub_category_name_ar'] if 'sub_category_name_ar' in items[0] else 'هذه الفئة'}:\n\n"
                        for i, item in enumerate(suggestions, 1):
                            response += f"{i}. {item['item_name_ar']} - {item['price']} دينار\n"
                        response += f"\nاختر الرقم من 1 إلى {len(items)} أو اكتب اسم المنتج المطلوب"
                    else:
                        response = f"Here are our {items[0]['sub_category_name_en'] if 'sub_category_name_en' in items[0] else 'category'} options:\n\n"
                        for i, item in enumerate(suggestions, 1):
                            response += f"{i}. {item['item_name_en']} - {item['price']} IQD\n"
                        response += f"\nChoose a number from 1 to {len(items)} or type the item name"
                    
                    return self._create_response(response)
        
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
            # Direct ID selection - check both display order and actual ID
            # First try by display order (1-based index)
            if 1 <= sub_category_id <= len(sub_categories):
                selected_sub_category = sub_categories[sub_category_id - 1]
            else:
                # Try by actual database ID
                for sub_cat in sub_categories:
                    if sub_cat['id'] == sub_category_id:
                        selected_sub_category = sub_cat
                        break
        
        elif sub_category_name:
            # Name-based selection with enhanced matching for voice input
            sub_category_name_lower = sub_category_name.lower().strip()
            
            # Enhanced matching for common voice input variations
            for sub_cat in sub_categories:
                # Check exact matches first
                if (sub_category_name_lower == sub_cat['name_ar'].lower() or 
                    sub_category_name_lower == sub_cat['name_en'].lower()):
                    selected_sub_category = sub_cat
                    logger.info(f"✅ Exact match found for '{sub_category_name}' -> '{sub_cat['name_en']}'")
                    break
                
                # Check partial matches
                if (sub_category_name_lower in sub_cat['name_ar'].lower() or 
                    sub_category_name_lower in sub_cat['name_en'].lower()):
                    selected_sub_category = sub_cat
                    logger.info(f"✅ Partial match found for '{sub_category_name}' -> '{sub_cat['name_en']}'")
                    break
            
            # If no match found, try fuzzy matching for common voice input variations
            if not selected_sub_category:
                # Common voice input variations for sub-categories
                voice_variations = {
                    'latte': ['لاتيه', 'latte', 'lattes', 'لاتيه ومشروبات خاصة', 'lattes & specialties'],
                    'coffee': ['قهوة', 'coffee', 'espresso', 'اسبرسو', 'قهوة واسبرسو', 'coffee & espresso'],
                    'tea': ['شاي', 'tea', 'teas', 'مشروبات ساخنة أخرى', 'other hot drinks'],
                    'espresso': ['اسبرسو', 'espresso', 'قهوة واسبرسو', 'coffee & espresso'],
                    'cappuccino': ['كابتشينو', 'cappuccino', 'لاتيه ومشروبات خاصة', 'lattes & specialties'],
                    'sandwich': ['ساندويت', 'سندويش', 'سندويشة', 'سندويشات', 'sandwich', 'sandwiches'],
                    'toast': ['توست', 'toast'],
                    'croissant': ['كرواسان', 'كرواسون', 'croissant', 'croissants'],
                    'pastry': ['فطائر', 'فطيرة', 'فطاير', 'pastry', 'pastries'],
                    'cake': ['كيك', 'كيكة', 'قطع كيك', 'cake', 'cakes']
                }
                
                for variation_key, variations in voice_variations.items():
                    if sub_category_name_lower in variations:
                        # Find the matching sub-category
                        for sub_cat in sub_categories:
                            if any(var in sub_cat['name_en'].lower() or var in sub_cat['name_ar'].lower() 
                                   for var in variations):
                                selected_sub_category = sub_cat
                                logger.info(f"✅ Voice variation match found: '{sub_category_name}' -> '{sub_cat['name_en']}'")
                                break
                        if selected_sub_category:
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
            
            # Get available sub-categories to show options
            available_sub_categories = self.db.get_sub_categories(main_category_id)
            
            if language == 'arabic':
                response = f"عذراً، لم نجد الفئة الفرعية '{sub_category_name}'. الفئات الفرعية المتاحة:\n\n"
                for i, sub_cat in enumerate(available_sub_categories, 1):
                    response += f"{i}. {sub_cat['name_ar']}\n"
                response += "\nالرجاء اختيار رقم الفئة الفرعية المطلوبة."
            else:
                response = f"Sorry, we couldn't find the sub-category '{sub_category_name}'. Available sub-categories:\n\n"
                for i, sub_cat in enumerate(available_sub_categories, 1):
                    response += f"{i}. {sub_cat['name_en']}\n"
                response += "\nPlease select the sub-category number you prefer."
            
            return self._create_response(response)

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

        # Defensive programming: ensure session is a dictionary
        if not isinstance(session, dict):
            logger.error(f"❌ Session is not a dictionary: {type(session)} = {session}")
            return self._create_response("خطأ في النظام. الرجاء البدء من جديد\nSystem error. Please restart")

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
                        # Update session to waiting for additional items
                        self.db.create_or_update_session(
                            phone_number, 'waiting_for_additional', language,
                            session.get('customer_name') if session else None,
                            order_mode=session.get('order_mode') if session else None
                        )
                        
                        # Show interactive buttons for additional items selection
                        return self._show_additional_items_selection(phone_number, language)
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

        # Defensive programming: ensure session is a dictionary
        if not isinstance(session, dict):
            logger.error(f"❌ Session is not a dictionary in _handle_ai_yes_no: {type(session)} = {session}")
            return self._create_response("خطأ في النظام. الرجاء البدء من جديد\nSystem error. Please restart")

        if yes_no == 'yes':
            if current_step == 'waiting_for_quick_order':
                # User is confirming in quick order mode - show quick order interface again
                if language == 'arabic':
                    response = "ممتاز! ما الذي تود طلبه اليوم؟\n\n"
                    response += "اكتب اسم المنتج المطلوب:\n"
                    response += "مثال: موهيتو ازرق"
                else:
                    response = "Great! What would you like to order today?\n\n"
                    response += "Type the item name you want:\n"
                    response += "Example: blue mojito"
                
                return self._create_response(response)
            
            elif current_step == 'waiting_for_additional':
                # Check if user is in explore mode
                order_mode = session.get('order_mode') if session else None
                
                if order_mode == 'explore':
                    # Continue with explore menu - show traditional categories
                    self.db.create_or_update_session(
                        phone_number, 'waiting_for_category', language,
                        session.get('customer_name') if session else None,
                        order_mode='explore'  # Maintain explore mode
                    )
                    return self._show_traditional_categories(phone_number, language)
                else:
                    # Show two-button interface for new orders
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
                # Check if we're in edit mode and should return to confirmation
                order_mode = session.get('order_mode') if session else None
                
                if order_mode in ['edit_add_quick', 'edit_add_explore']:
                    # Return to confirmation with updated order
                    self.db.create_or_update_session(
                        phone_number, 'waiting_for_confirmation', language,
                        session.get('customer_name') if session else None,
                        order_mode='quick'  # Restore to quick mode for confirmation
                    )
                    # Get refreshed session and user context for confirmation
                    refreshed_session = self.db.get_user_session(phone_number)
                    refreshed_user_context = self._build_user_context(phone_number, refreshed_session, 'waiting_for_confirmation', '')
                    return self._show_quick_order_confirmation(phone_number, refreshed_session, refreshed_user_context)
                else:
                    # Normal flow: Proceed to service selection
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
                # Extract table number from AI's location format or direct input
                table_num = None
                
                # Check if AI provided "Table X" format
                if clean_location.startswith('Table '):
                    table_num_str = clean_location.replace('Table ', '').strip()
                else:
                    # Direct number input, convert Arabic numerals to English
                    table_num_str = self._convert_arabic_numerals(clean_location)
                
                table_num = int(table_num_str)
                
                if table_num < 1 or table_num > 7:
                    if language == 'arabic':
                        return self._create_response("رقم الطاولة غير صحيح. الرجاء اختيار رقم من 1 إلى 7:")
                    else:
                        return self._create_response("Invalid table number. Please choose a number from 1 to 7:")
                
                # Store in consistent format for database
                clean_location = f"Table {table_num}"
                
            except ValueError:
                if language == 'arabic':
                    return self._create_response("الرجاء إدخال رقم صحيح للطاولة (1-7):")
                else:
                    return self._create_response("Please enter a valid table number (1-7):")
        
        # Update session step (preserve order_mode for quick orders)
        order_mode = session.get('order_mode') if session else None
        self.db.create_or_update_session(
            phone_number, 'waiting_for_confirmation', language,
            session.get('customer_name') if session else None,
            order_mode=order_mode
        )
        
        # Update order details with clean location
        self.db.update_order_details(phone_number, location=clean_location)
        
        # Check if this is a quick order (including edit modes) and route appropriately
        if order_mode in ['quick', 'edit_add_quick', 'edit_add_explore']:
            logger.info(f"🎯 Quick order detected, showing quick order confirmation")
            return self._show_quick_order_confirmation(phone_number, session, user_context)
        else:
            logger.info(f"📋 Regular order, showing order summary")
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
            # If user is at waiting_for_category and wants to explore menu,
            # set order_mode to 'explore' and show traditional categories
            if not session or session.get('order_mode') is None:
                # Update session to set order_mode to 'explore'
                self.db.create_or_update_session(
                    phone_number=phone_number,
                    current_step='waiting_for_category',
                    language=language,
                    order_mode='explore'
                )
                logger.info(f"🔍 Set order_mode to 'explore' for {phone_number}")
            
            return self._show_traditional_categories(phone_number, language)
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
        
        # Check if we should show interactive buttons
        if ai_result.get('show_interactive_buttons'):
            logger.info(f"🎯 Showing interactive buttons for conversational response")
            current_step = user_context.get('current_step')
            
            # Show appropriate interactive buttons based on step
            if current_step == 'waiting_for_category':
                return self._show_main_categories(phone_number, user_context.get('language', 'arabic'))
            else:
                # Fallback to text response
                return self._create_response(response_message)
        
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
            # Check for direct explore menu request to bypass language selection
            text_lower = text.lower().strip()
            if text_lower in ['explore_menu', 'استكشاف القائمة', 'explore menu', 'explore']:
                logger.info(f"🚀 Direct explore menu request detected at language step, bypassing language selection")
                # Set language to Arabic by default and go directly to explore menu
                self.db.create_or_update_session(
                    phone_number, 'waiting_for_category', 'arabic',
                    session.get('customer_name') if session else None,
                    order_mode='explore'
                )
                return self._show_traditional_categories(phone_number, 'arabic')
            
            return self._handle_structured_language_selection(phone_number, text, session, user_context.get('customer_name'))
            
        elif current_step == 'waiting_for_category':
            return self._handle_structured_category_selection(phone_number, text, session, user_context)
            
        elif current_step == 'waiting_for_quick_order':
            return self._handle_structured_quick_order(phone_number, text, session, user_context)
        elif current_step == 'waiting_for_quick_order_quantity':
            # Handle quantity selection from buttons or text input
            user_message = user_context.get('original_user_message', '')
            if user_message.startswith('quantity_'):
                # Button click - extract quantity
                try:
                    quantity = int(user_message.split('_')[1])
                    return self._handle_quick_order_quantity(phone_number, {'quantity': quantity}, session, user_context)
                except (ValueError, IndexError):
                    pass
            
            # Text input - try to extract quantity
            try:
                quantity = int(text.strip())
                if 1 <= quantity <= 10:
                    return self._handle_quick_order_quantity(phone_number, {'quantity': quantity}, session, user_context)
            except ValueError:
                pass
            
            # Invalid input - show quantity buttons again
            quick_order_item = session.get('quick_order_item')
            if quick_order_item:
                return self._show_quantity_buttons(phone_number, user_context.get('language', 'arabic'), quick_order_item['item_name_ar'])
            else:
                return self._create_response("حدث خطأ. الرجاء المحاولة مرة أخرى.")
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
            # Always handle structured confirmation first (for button clicks)
            return self._handle_structured_confirmation(phone_number, text, session, user_context)
        
        elif current_step == 'waiting_for_edit_choice':
            return self._handle_edit_choice(phone_number, text, session, user_context)
        
        elif current_step == 'waiting_for_add_item_choice':
            return self._handle_add_item_choice(phone_number, text, session, user_context)
        
        elif current_step == 'waiting_for_quantity_item_selection':
            return self._handle_quantity_item_selection(phone_number, text, session, user_context)
        
        elif current_step == 'waiting_for_remove_item_selection':
            return self._handle_remove_item_selection(phone_number, text, session, user_context)
        
        elif current_step == 'waiting_for_new_quantity':
            return self._handle_new_quantity_input(phone_number, text, session, user_context)
            
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
        
        # Convert Arabic numerals to English first
        converted_text = self._convert_arabic_numerals(text.strip())
        
        # Try to extract number
        try:
            category_num = int(converted_text)
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
        
        # Check for confirmations first
        text_lower = text.lower().strip()
        confirmations = ['نعم', 'اي', 'yes', 'ok', 'حسنا', 'تمام']
        
        if any(confirmation in text_lower for confirmation in confirmations):
            # User is confirming - show quick order interface again
            if language == 'arabic':
                response = "ممتاز! ما الذي تود طلبه اليوم؟\n\n"
                response += "اكتب اسم المنتج المطلوب:\n"
                response += "مثال: موهيتو ازرق"
            else:
                response = "Great! What would you like to order today?\n\n"
                response += "Type the item name you want:\n"
                response += "Example: 2 blue mojito"
            
            return self._create_response(response)
        
        # Parse the input for quantity, item name, service type, and optional table number
        # Example: "2 موهيتو ازرق للطاولة 5" or "٣ قهوة توصيل" or "٢ موهيتو ازرق في المقهى"
        text = text.strip()
        
        # Extract quantity (default to 1 if not specified)
        quantity = 1
        item_name = text
        table_number = None
        service_type = None
        
        # Look for quantity patterns - support both English and Arabic numerals and words
        import re
        
        # Remove common leading intent verbs (Arabic dialects and English)
        verb_leading_pattern = r'^(?:أ?ريد|بدي|ابي|ابغى|عايز|حاب|ارغب|i\s*w(?:ant|anna)|give\s*me)\s+'
        text_wo_verbs = re.sub(verb_leading_pattern, '', text, flags=re.IGNORECASE).strip()
        
        # Convert Arabic numerals to English for processing using existing method
        processed_text = self._convert_arabic_numerals(text_wo_verbs)
        logger.info(f"🔍 Quick order processing: original='{text}', no_verbs='{text_wo_verbs}', processed='{processed_text}'")
        
        # Try leading quantity WORDS first (Arabic/English + common ASR variants)
        quantity_words_map = {
            'واحد': 1, 'واحدة': 1, 'one': 1,
            'اثنين': 2, 'إثنين': 2, 'اتنين': 2, 'ثنين': 2, 'two': 2,
            'الاثنين': 2, 'الأثنين': 2, 'الثنين': 2, 'الثين': 2,
            'الثيه': 2, 'ثيه': 2  # common ASR mis-hearings
        }
        qw_pattern = r'^(?:' + '|'.join(map(re.escape, quantity_words_map.keys())) + r')\s+'
        qw_match = re.match(qw_pattern, text_wo_verbs, flags=re.IGNORECASE)
        if qw_match:
            matched_word = qw_match.group(0).strip()
            key = matched_word.lower()
            qty = quantity_words_map.get(matched_word, quantity_words_map.get(key))
            if qty:
                quantity = int(qty)
                item_name = text_wo_verbs[qw_match.end():].strip()
                logger.info(f"✅ Extracted leading word quantity: {matched_word} -> {quantity}, item_name: '{item_name}'")
        else:
            # Look for quantity patterns (now handles both Arabic and English numerals)
            quantity_pattern = r'^(\d+)\s+'
            quantity_match = re.match(quantity_pattern, processed_text)
            if quantity_match:
                quantity = int(quantity_match.group(1))
                # Find the position of the quantity in the original (verb-stripped) text
                original_quantity = text_wo_verbs[:len(quantity_match.group(0))]
                item_name = text_wo_verbs[len(original_quantity):].strip()
                logger.info(f"✅ Extracted numeric quantity: {quantity}, item_name: '{item_name}'")
            else:
                logger.info(f"🔍 No leading quantity found, defaulting to quantity=1")
                quantity = 1
                item_name = text_wo_verbs.strip()
        
        # Look for table number patterns first (which implies dine-in service)
        table_patterns = [
            r'طاولة\s*رقم\s*(\d+)',  # طاولة رقم 6
            r'للطاولة\s+(\d+)',      # للطاولة 5  
            r'طاولة\s+(\d+)',        # طاولة 3
            r'table\s*(\d+)',        # table 4
            r'table\s*number\s*(\d+)', # table number 5
            r'رقم\s*الطاولة\s*(\d+)', # رقم الطاولة 2
        ]
        
        for pattern in table_patterns:
            table_match = re.search(pattern, item_name, re.IGNORECASE)
            if table_match:
                table_number = table_match.group(1)
                service_type = 'dine-in'  # Table number implies dine-in
                # Remove table pattern from item name
                item_name = re.sub(pattern, '', item_name, flags=re.IGNORECASE).strip()
                logger.info(f"✅ Extracted table number: {table_number} and service type: dine-in from pattern: {pattern}")
                break
        
        # If no table number found, look for other service type patterns
        if not service_type:
            service_patterns = {
                'dine-in': [
                    r'في\s*المقهى', r'في\s*الكافيه', r'بالكهوة', r'بالكافيه', r'تناول', 
                    r'عندكم', r'عندك', r'dine.?in', r'restaurant', r'في\s*المطعم',
                    r'بالمقهى', r'بالكافيه', r'في\s*الكافي', r'داخل\s*المقهى'
                ],
                'delivery': [
                    r'توصيل', r'للبيت', r'للمنزل', r'delivery', r'deliver', 
                    r'وصل', r'وصلي', r'وصله', r'للمنطقة', r'للعنوان',
                    r'للعنواني', r'للموقع', r'deliver\s*to', r'take\s*away'
                ]
        }
        
        for service, patterns in service_patterns.items():
            for pattern in patterns:
                if re.search(pattern, item_name, re.IGNORECASE):
                    service_type = service
                    # Remove service type from item name
                    item_name = re.sub(pattern, '', item_name, flags=re.IGNORECASE).strip()
                    logger.info(f"✅ Extracted service type: {service_type} from pattern: {pattern}")
                    break
            if service_type:
                break
        
        # Search for the item across all categories
        all_items = self._get_all_items()
        matched_item = self._match_item_by_name(item_name, all_items, language)
        
        if matched_item:
            # Store the matched item in session for quantity selection (as JSON string)
            import json
            quick_order_item_json = json.dumps(matched_item, ensure_ascii=False)
            
            # If quantity was specified in the input, skip quantity selection
            logger.info(f"🔍 Quantity decision: extracted_quantity={quantity}, should_skip_quantity={quantity > 1}")
            if quantity > 1:
                logger.info(f"✅ Quantity {quantity} already specified, skipping quantity selection")
                
                # Add item to order immediately since quantity is specified
                success = self.db.add_item_to_order(
                    phone_number=phone_number,
                    item_id=matched_item['id'],
                    quantity=quantity
                )
                
                if success:
                    logger.info(f"✅ Added {quantity}x {matched_item['item_name_ar']} to order for {phone_number}")
                else:
                    logger.error(f"❌ Failed to add item to order for {phone_number}")
                    return self._create_response("حدث خطأ في إضافة المنتج. يرجى المحاولة مرة أخرى." if language == 'arabic' else "Error adding item. Please try again.")
                
                # Also update the in-memory session
                session['quick_order_item'] = matched_item
                session['quick_order_quantity'] = quantity
                if table_number:
                    session['quick_order_table'] = table_number
                
                # Check if service type was provided in the message
                if service_type:
                    logger.info(f"✅ Service type {service_type} already specified, skipping service selection")
                    
                    # Update order details with service type
                    self.db.update_order_details(phone_number, service_type=service_type)
                    
                    # If dine-in and table number provided, skip location step too
                    if service_type == 'dine-in' and table_number:
                        logger.info(f"✅ Table number {table_number} already specified for dine-in, going to confirmation")
                        
                        # Update location with table number
                        self.db.update_order_details(phone_number, location=f"Table {table_number}")
                        
                        # Go directly to confirmation
                        self.db.create_or_update_session(phone_number, 'waiting_for_confirmation', language, session.get('customer_name'), order_mode='quick', quick_order_item=quick_order_item_json)
                        return self._show_quick_order_confirmation(phone_number, session, user_context)
                    
                    elif service_type == 'dine-in':
                        # Ask for table number
                        self.db.create_or_update_session(phone_number, 'waiting_for_location', language, session.get('customer_name'), order_mode='quick', quick_order_item=quick_order_item_json)
                        if language == 'arabic':
                            return self._create_response("اختر رقم الطاولة (1-7):")
                        else:
                            return self._create_response("Select table number (1-7):")
                    
                    elif service_type == 'delivery':
                        # Ask for delivery address
                        self.db.create_or_update_session(phone_number, 'waiting_for_location', language, session.get('customer_name'), order_mode='quick', quick_order_item=quick_order_item_json)
                        if language == 'arabic':
                            return self._create_response("الرجاء مشاركة عنوانك أو موقعك للتوصيل:")
                        else:
                            return self._create_response("Please share your address or location for delivery:")
                else:
                    # No service type specified, show service selection
                    self.db.create_or_update_session(phone_number, 'waiting_for_quick_order_service', language, session.get('customer_name'), order_mode='quick', quick_order_item=quick_order_item_json)
                    return self._show_service_type_buttons(phone_number, language)
            else:
                # Quantity not specified, but check if service type was provided
                logger.info(f"✅ No quantity specified, checking for service type")
                
                # Also update the in-memory session to ensure consistency
                session['quick_order_item'] = matched_item
                session['quick_order_quantity'] = quantity
                if table_number:
                    session['quick_order_table'] = table_number
                
                # If service type was provided, store it in session for later use
                if service_type:
                    logger.info(f"✅ Service type {service_type} provided with item, storing for later")
                    session['quick_order_service'] = service_type
                    if table_number and service_type == 'dine-in':
                        session['quick_order_location'] = f"Table {table_number}"
                
                # Update session to quantity selection step with item data
                self.db.create_or_update_session(phone_number, 'waiting_for_quick_order_quantity', language, session.get('customer_name'), order_mode='quick', quick_order_item=quick_order_item_json)
                
                # Show quantity buttons
                return self._show_quantity_buttons(phone_number, language, matched_item['item_name_ar'])
        else:
            # Item not found
            if language == 'arabic':
                response = f"لم أتمكن من العثور على '{item_name}' في قائمتنا.\n\n"
                response += "المنتجات المتاحة:\n"
                for item in all_items[:5]:  # Show first 5 items as suggestions
                    response += f"• {item['item_name_ar']} - {item['price']} دينار\n"
                response += "\nأو اختر 'استكشاف القائمة' للتصفح الكامل."
            else:
                response = f"Could not find '{item_name}' in our menu.\n\n"
                response += "Available items:\n"
                for item in all_items[:5]:  # Show first 5 items as suggestions
                    response += f"• {item['item_name_en']} - {item['price']} IQD\n"
                response += "\nOr choose 'Explore Menu' for full browsing."
            
            return self._create_response(response)
    
    def _handle_quick_order_quantity(self, phone_number: str, extracted_data: Dict, session: Dict, user_context: Dict) -> Dict:
        """Handle quick order quantity selection"""
        language = user_context.get('language', 'arabic')
        
        # Get the stored item from session
        quick_order_item = session.get('quick_order_item')
        logger.info(f"🔍 Debug: quick_order_item from session: {quick_order_item}")
        
        # Parse JSON string to dictionary if needed
        if isinstance(quick_order_item, str):
            import json
            try:
                quick_order_item = json.loads(quick_order_item)
                logger.info(f"✅ Parsed quick_order_item from JSON string: {quick_order_item}")
            except (json.JSONDecodeError, TypeError) as e:
                logger.error(f"❌ Error parsing quick_order_item JSON: {e}")
                quick_order_item = None
        
        if not quick_order_item:
            logger.error(f"❌ No quick_order_item found in session for {phone_number}")
            return self._create_response("حدث خطأ. الرجاء المحاولة مرة أخرى.")
        
        # Extract quantity from button click
        user_message = user_context.get('original_user_message', '')
        logger.info(f"🔍 Debug: user_message='{user_message}', extracted_data={extracted_data}")
        
        if user_message.startswith('quantity_'):
            try:
                quantity = int(user_message.split('_')[1])
                logger.info(f"✅ Extracted quantity from button: {quantity}")
            except (ValueError, IndexError) as e:
                logger.error(f"❌ Error extracting quantity from button: {e}")
                quantity = 1
        else:
            # Fallback: try to extract quantity from AI
            quantity = extracted_data.get('quantity', 1)
            logger.info(f"✅ Using quantity from AI: {quantity}")
        
        # Add item to order
        item_id = quick_order_item.get('id')
        if not item_id:
            logger.error(f"❌ No item_id found in quick_order_item: {quick_order_item}")
            return self._create_response("حدث خطأ. الرجاء المحاولة مرة أخرى.")
        
        logger.info(f"🔧 Adding item to order: item_id={item_id}, quantity={quantity}")
        success = self.db.add_item_to_order(
            phone_number=phone_number,
            item_id=item_id,
            quantity=quantity
        )
        
        if not success:
            logger.error(f"❌ Failed to add item to order: item_id={item_id}, quantity={quantity}")
            return self._create_response("حدث خطأ في إضافة المنتج. الرجاء المحاولة مرة أخرى.")
        
        # Check if service type was already provided in the original message
        quick_order_service = session.get('quick_order_service')
        quick_order_location = session.get('quick_order_location')
        
        if quick_order_service:
            logger.info(f"✅ Service type {quick_order_service} already provided, skipping service selection")
            
            # Update order details with service type
            self.db.update_order_details(phone_number, service_type=quick_order_service)
            
            # If location was also provided (dine-in with table), go directly to confirmation
            if quick_order_location:
                logger.info(f"✅ Location {quick_order_location} already provided, going to confirmation")
                
                # Update location
                self.db.update_order_details(phone_number, location=quick_order_location)
                
                # Go directly to confirmation
                self.db.create_or_update_session(phone_number, 'waiting_for_confirmation', language, session.get('customer_name'), order_mode='quick')
                return self._show_quick_order_confirmation(phone_number, session, user_context)
            
            elif quick_order_service == 'dine-in':
                # Ask for table number
                self.db.create_or_update_session(phone_number, 'waiting_for_location', language, session.get('customer_name'), order_mode='quick')
                if language == 'arabic':
                    return self._create_response("اختر رقم الطاولة (1-7):")
                else:
                    return self._create_response("Select table number (1-7):")
            
            elif quick_order_service == 'delivery':
                # Ask for delivery address
                self.db.create_or_update_session(phone_number, 'waiting_for_location', language, session.get('customer_name'), order_mode='quick')
                if language == 'arabic':
                    return self._create_response("الرجاء مشاركة عنوانك أو موقعك للتوصيل:")
                else:
                    return self._create_response("Please share your address or location for delivery:")
        else:
            # No service type provided, show service selection
            self.db.create_or_update_session(phone_number, 'waiting_for_quick_order_service', language, session.get('customer_name'), order_mode='quick')
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
        self.db.update_order_details(phone_number, service_type=service_type)
        
        # Update session to location step for both service types
        self.db.create_or_update_session(phone_number, 'waiting_for_location', language, session.get('customer_name'), order_mode='quick')
        
        if service_type == 'dine-in':
            if language == 'arabic':
                return self._create_response("اختر رقم الطاولة (1-7):")
            else:
                return self._create_response("Select table number (1-7):")
        else:  # delivery
            if language == 'arabic':
                return self._create_response("الرجاء مشاركة عنوانك أو موقعك للتوصيل:")
            else:
                return self._create_response("Please share your address or location for delivery:")
    
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
        
        # Get quantity from AI extraction
        quantity = extracted_data.get('quantity', 1)
        logger.info(f"🔍 AI extracted quantity: {quantity}")
        
        # Search for the item across all categories
        all_items = self._get_all_items()
        matched_item = self._match_item_by_name(item_name, all_items, language)
        
        if matched_item:
            # Store the matched item in session for quantity selection (as JSON string)
            import json
            quick_order_item_json = json.dumps(matched_item, ensure_ascii=False)
            
            # CRITICAL FIX: Check if quantity was already specified
            if quantity > 1:
                logger.info(f"✅ Quantity {quantity} already specified, skipping quantity selection")
                
                # Add item to order immediately since quantity is specified
                success = self.db.add_item_to_order(
                    phone_number=phone_number,
                    item_id=matched_item['id'],
                    quantity=quantity
                )
                
                if success:
                    logger.info(f"✅ Added {quantity}x {matched_item['item_name_ar']} to order for {phone_number}")
                else:
                    logger.error(f"❌ Failed to add item to order for {phone_number}")
                    return self._create_response("حدث خطأ في إضافة المنتج. يرجى المحاولة مرة أخرى." if language == 'arabic' else "Error adding item. Please try again.")
                
                # Update session to service selection step
                self.db.create_or_update_session(phone_number, 'waiting_for_quick_order_service', language, session.get('customer_name'), order_mode='quick', quick_order_item=quick_order_item_json)
                
                # Also update the in-memory session
                session['current_step'] = 'waiting_for_quick_order_service'
                session['quick_order_item'] = matched_item
                session['quick_order_quantity'] = quantity
                
                # Show service type selection
                return self._show_service_type_buttons(phone_number, language)
            else:
                logger.info(f"✅ No quantity specified, proceeding to quantity selection")
                # Update session to quantity selection step with item data
                self.db.create_or_update_session(phone_number, 'waiting_for_quick_order_quantity', language, session.get('customer_name'), order_mode='quick', quick_order_item=quick_order_item_json)
                
                # Also update the in-memory session to ensure consistency
                session['current_step'] = 'waiting_for_quick_order_quantity'
                session['quick_order_item'] = matched_item
                
                # Show quantity buttons
                return self._show_quantity_buttons(phone_number, language, matched_item['item_name_ar'])
        else:
            # Item not found
            if language == 'arabic':
                response = f"لم أتمكن من العثور على '{item_name}' في قائمتنا.\n\n"
                response += "المنتجات المتاحة:\n"
                for item in all_items[:5]:  # Show first 5 items as suggestions
                    response += f"• {item['item_name_ar']} - {item['price']} دينار\n"
                response += "\nأو اختر 'استكشاف القائمة' للتصفح الكامل."
            else:
                response = f"Could not find '{item_name}' in our menu.\n\n"
                response += "Available items:\n"
                for item in all_items[:5]:  # Show first 5 items as suggestions
                    response += f"• {item['item_name_en']} - {item['price']} IQD\n"
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
                    # Enhanced error message with available options
                    if language == 'arabic':
                        response = f"الرقم {sub_category_num} غير صحيح. الفئات الفرعية المتاحة:\n\n"
                        for i, sub_cat in enumerate(sub_categories, 1):
                            response += f"{i}. {sub_cat['name_ar']}\n"
                        response += f"\nالرجاء اختيار رقم من 1 إلى {len(sub_categories)}"
                    else:
                        response = f"Number {sub_category_num} is invalid. Available sub-categories:\n\n"
                        for i, sub_cat in enumerate(sub_categories, 1):
                            response += f"{i}. {sub_cat['name_en']}\n"
                        response += f"\nPlease choose a number from 1 to {len(sub_categories)}"
                    
                    return self._create_response(response)
                    
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
            # Check if we're in edit mode and should return to confirmation
            order_mode = session.get('order_mode') if session else None
            
            if order_mode in ['edit_add_quick', 'edit_add_explore']:
                # Return to confirmation with updated order
                self.db.create_or_update_session(
                    phone_number, 'waiting_for_confirmation', language,
                    session.get('customer_name') if session else None,
                    order_mode='quick'  # Restore to quick mode for confirmation
                )
                # Get refreshed session and user context for confirmation
                refreshed_session = self.db.get_user_session(phone_number)
                refreshed_user_context = self._build_user_context(phone_number, refreshed_session, 'waiting_for_confirmation', '')
                return self._show_quick_order_confirmation(phone_number, refreshed_session, refreshed_user_context)
            else:
                # Normal flow: Move to service selection
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
        
        # Check for button clicks first
        if text == 'confirm_order':
            return self._confirm_order(phone_number, session, user_context)
        elif text == 'cancel_order':
            return self._cancel_order(phone_number, session, user_context)
        elif text == 'edit_order':
            return self._show_edit_order_menu(phone_number, session, user_context)
        
        # Check for text confirmation
        if any(word in text_lower for word in ['نعم', 'yes', '1', 'تأكيد', 'confirm']):
            return self._confirm_order(phone_number, session, user_context)
        # Check for cancellation
        elif any(word in text_lower for word in ['لا', 'no', '2', 'إلغاء', 'cancel']):
            return self._cancel_order(phone_number, session, user_context)
        
        # If it's a quick order and not a recognized command, show confirmation again
        if session and session.get('order_mode') == 'quick':
            return self._show_quick_order_confirmation(phone_number, session, user_context)
        
        # Invalid input for regular orders
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
                
                # Store in consistent format for database
                clean_location = f"Table {table_num}"
                
            except ValueError:
                if language == 'arabic':
                    return self._create_response("الرجاء إدخال رقم صحيح للطاولة (1-7):")
                else:
                    return self._create_response("Please enter a valid table number (1-7):")
        
        # Update session step
        self.db.create_or_update_session(
            phone_number, 'waiting_for_confirmation', language,
            session.get('customer_name') if session else None,
            order_mode=session.get('order_mode')
        )
        
        # Update order details with clean location
        self.db.update_order_details(phone_number, location=clean_location)
        
        # Check order mode and route accordingly
        order_mode = session.get('order_mode')
        logger.info(f"🔄 Structured location input: order_mode={order_mode}")
        
        if order_mode in ['quick', 'edit_add_quick', 'edit_add_explore']:
            logger.info("📋 Routing to quick order confirmation")
            return self._show_quick_order_confirmation(phone_number, session, user_context)
        else:
            logger.info("📋 Routing to regular order summary")
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
            message = "🚀 الطلب السريع\n"
            message += "ماذا تريد أن تطلب؟ أعطني اسم المنتج:\n\n"
            
            if popular_items:
                message += "💡 المنتجات الاكثر طلبا:\n"
                for item in popular_items[:5]:  # Show up to 5 items
                    message += f"• {item['item_name_ar']} - {item['price']} دينار\n"
                message += "\n"
            
            if popular_items:
                message += "📝 أمثلة على الطلب:\n"
                # Example 1: Single item
                example1 = popular_items[0]['item_name_ar']
                message += f"• {example1}\n"
                
                # Example 2: With quantity
                if len(popular_items) > 1:
                    example2 = popular_items[1]['item_name_ar']
                    message += f"• 2 {example2}\n"
                
                # Example 3: Another item
                if len(popular_items) > 2:
                    example3 = popular_items[2]['item_name_ar']
                    message += f"• 3 {example3}\n"
                message += "\n"
            
            message += "💡 نصائح للطلب السريع:\n"
            message += "• اكتب اسم المنتج فقط (مثل: موهيتو رمان)\n"
            message += "• اكتب الكمية مع الاسم وطريقة الخدمة (مثل: 2 موهيتو رمان ومع 2 شاي عراقي طاولة رقم 4)\n"
            message += "• يمكنك طلب أكثر من صنف في رسالة واحدة\n\n"
            message += "اكتب اسم المنتج المطلوب الآن! 🍽️"
        else:
            message = "🚀 Quick Order\n"
            message += "What do you want to order? Give me the item name:\n\n"
            
            if popular_items:
                message += "💡 Most popular items:\n"
                for item in popular_items[:5]:  # Show up to 5 items
                    message += f"• {item['item_name_en']} - {item['price']} IQD\n"
                message += "\n"
            
            if popular_items:
                message += "📝 Order examples:\n"
                # Example 1: Single item
                example1 = popular_items[0]['item_name_en']
                message += f"• {example1}\n"
                
                # Example 2: With quantity
                if len(popular_items) > 1:
                    example2 = popular_items[1]['item_name_en']
                    message += f"• 2 {example2}\n"
                
                # Example 3: Another item
                if len(popular_items) > 2:
                    example3 = popular_items[2]['item_name_en']
                    message += f"• 3 {example3}\n"
                message += "\n"
            
            message += "💡 Quick order tips:\n"
            message += "• Just type the item name (e.g., Pomegranate Mojito)\n"
            message += "• Include quantity with name and service method (e.g., 2 Pomegranate Mojito with 2 Iraqi Tea table 4)\n"
            message += "• You can order multiple items in one message\n\n"
            message += "Type the item name you want now! 🍽️"
        
        return self._create_response(message)
    
    def _show_quantity_buttons(self, phone_number: str, language: str, item_name: str) -> Dict:
        """Show quantity selection buttons"""
        if language == 'arabic':
            header_text = "اختر الكمية"
            body_text = f"كم {item_name} تريد؟\n\nاكتب رقم من 1 إلى 10 أو اختر من الأزرار أدناه"
            footer_text = ""
            buttons = [
                {
                    "type": "reply",
                    "reply": {
                        "id": "quantity_1",
                        "title": "1"
                    }
                },
                {
                    "type": "reply",
                    "reply": {
                        "id": "quantity_2",
                        "title": "2"
                    }
                },
                {
                    "type": "reply",
                    "reply": {
                        "id": "quantity_3",
                        "title": "3"
                    }
                }
            ]
        else:
            header_text = "Select Quantity"
            body_text = f"How many {item_name} do you want?\n\nType a number from 1 to 10 or select from buttons below"
            footer_text = ""
            buttons = [
                {
                    "type": "reply",
                    "reply": {
                        "id": "quantity_1",
                        "title": "1"
                    }
                },
                {
                    "type": "reply",
                    "reply": {
                        "id": "quantity_2",
                        "title": "2"
                    }
                },
                {
                    "type": "reply",
                    "reply": {
                        "id": "quantity_3",
                        "title": "3"
                    }
                }
            ]
        
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
        """Show traditional category selection for explore mode with interactive buttons"""
        categories = self.db.get_main_categories()
        
        if language == 'arabic':
            header_text = "استكشاف القائمة"
            body_text = "اختر الفئة المطلوبة:"
            footer_text = "اضغط على الفئة المطلوبة"
            
            buttons = []
            for i, cat in enumerate(categories, 1):
                # Shorten category names to fit WhatsApp's 20 character limit
                if i == 1:
                    title = "1. المشروبات الباردة"
                elif i == 2:
                    title = "2. المشروبات الحارة"
                elif i == 3:
                    title = "3. الحلويات"
                else:
                    title = f"{i}. {cat['name_ar'][:15]}"  # Fallback shortening
                
                button = {
                    "type": "reply",
                    "reply": {
                        "id": f"category_{cat['id']}",
                        "title": title
                    }
                }
                buttons.append(button)
                logger.debug(f"🔍 Created button {i}: {button}")
        else:
            header_text = "Explore Menu"
            body_text = "Select the category:"
            footer_text = "Press the required category"
            
            buttons = []
            for i, cat in enumerate(categories, 1):
                # Shorten category names to fit WhatsApp's 20 character limit
                if i == 1:
                    title = "1. Cold Drinks"
                elif i == 2:
                    title = "2. Hot Drinks"
                elif i == 3:
                    title = "3. Pastries"
                else:
                    title = f"{i}. {cat['name_en'][:15]}"  # Fallback shortening
                
                button = {
                    "type": "reply",
                    "reply": {
                        "id": f"category_{cat['id']}",
                        "title": title
                    }
                }
                buttons.append(button)
                logger.debug(f"🔍 Created button {i}: {button}")
        
        logger.info(f"🔍 Created {len(buttons)} buttons for traditional categories")
        
        # Validate buttons for WhatsApp requirements
        if len(buttons) > 3:
            logger.warning(f"⚠️ Too many buttons ({len(buttons)}), WhatsApp only allows 3")
            buttons = buttons[:3]
        
        # Validate each button structure
        for i, button in enumerate(buttons):
            if 'type' not in button or button['type'] != 'reply':
                logger.error(f"❌ Invalid button {i}: missing or wrong type")
            if 'reply' not in button:
                logger.error(f"❌ Invalid button {i}: missing reply wrapper")
            if 'id' not in button.get('reply', {}):
                logger.error(f"❌ Invalid button {i}: missing id")
            if 'title' not in button.get('reply', {}):
                logger.error(f"❌ Invalid button {i}: missing title")
            
            # Check button title length (WhatsApp limit is 20 characters)
            title = button.get('reply', {}).get('title', '')
            if len(title) > 20:
                logger.warning(f"⚠️ Button {i} title too long ({len(title)} chars): {title}")
        
        response = self._create_interactive_response(header_text, body_text, footer_text, buttons)
        logger.debug(f"🔍 Interactive response: {response}")
        return response

    def _get_popular_items(self) -> List[Dict]:
        """Get popular items for quick order suggestions from database"""
        try:
            # Get items from all categories to show variety
            all_items = []
            
            # Get main categories
            main_categories = self.db.get_main_categories()
            for main_cat in main_categories:
                sub_categories = self.db.get_sub_categories(main_cat['id'])
                for sub_cat in sub_categories:
                    items = self.db.get_sub_category_items(sub_cat['id'])
                    all_items.extend(items)
            
            # Sort by price and take top 5-8 items for variety
            all_items.sort(key=lambda x: x.get('price', 0))
            
            # Return a mix of items from different categories
            popular_items = []
            if all_items:
                # Take first 2-3 items from each price range for variety
                price_ranges = [(0, 3000), (3000, 5000), (5000, 10000)]
                for min_price, max_price in price_ranges:
                    range_items = [item for item in all_items if min_price <= item.get('price', 0) <= max_price]
                    popular_items.extend(range_items[:2])  # Take max 2 from each range
            
            # If we don't have enough items, just return what we have
            if not popular_items and all_items:
                popular_items = all_items[:5]
            
            return popular_items
            
        except Exception as e:
            logger.warning(f"⚠️ Error getting popular items from database: {e}")
            # Return empty list if database fails - no hardcoded items
            return []

    def _get_recent_orders(self, phone_number: str) -> List[str]:
        """Get recent orders for quick reorder suggestions from database"""
        try:
            # Get recent orders from database using order history
            recent_orders = self.db.get_order_history(phone_number, limit=3)
            
            if recent_orders:
                formatted_orders = []
                for order in recent_orders:
                    try:
                        # Parse items from the order
                        items_json = order.get('items_json', '[]')
                        if isinstance(items_json, str):
                            import json
                            items_data = json.loads(items_json)
                        else:
                            items_data = items_json
                        
                        # Get the first item from the order for display
                        if items_data and len(items_data) > 0:
                            first_item = items_data[0]
                            quantity = first_item.get('quantity', 1)
                            item_name = first_item.get('item_name_ar', first_item.get('item_name_en', 'Unknown'))
                            formatted_orders.append(f"{quantity} {item_name}")
                    except Exception as e:
                        logger.warning(f"⚠️ Error parsing order item: {e}")
                        continue
                
                return formatted_orders
            
            # If no recent orders, return empty list
            return []
            
        except Exception as e:
            logger.warning(f"⚠️ Error getting recent orders from database: {e}")
            # Return empty list if database fails
            return []

    def _show_sub_categories(self, phone_number: str, main_category, language: str) -> Dict:
        """Show sub-categories for selected main category as numbered text list"""
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
            message = f"قائمة {category_name_ar}\n"
            message += "الرجاء اختيار الفئة الفرعية المطلوبة:\n\n"
            
            for i, sub_cat in enumerate(sub_categories, 1):
                message += f"{i}. {sub_cat['name_ar']}\n"
            
            message += "\n🔙 اكتب 'رجوع' للعودة للخطوة السابقة\n"
            message += "اكتب رقم الفئة الفرعية المطلوبة"
        else:
            message = f"{category_name_en} Menu\n"
            message += "Please select the required sub-category:\n\n"
            
            for i, sub_cat in enumerate(sub_categories, 1):
                message += f"{i}. {sub_cat['name_en']}\n"
            
            message += "\n🔙 Type 'back' to go to previous step\n"
            message += "Type the number of the required sub-category"
        
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
            message = f"قائمة {sub_category['name_ar']}\n"
            message += "اختر المنتج الذي تريده:\n\n"
            
            for i, item in enumerate(items, 1):
                message += f"{i}. {item['item_name_ar']} - {item['price']} دينار\n"
            
            message += "\nاكتب رقم المنتج المطلوب"
        else:
            message = f"{sub_category['name_en']} Menu\n"
            message += "Choose the item you want:\n\n"
            
            for i, item in enumerate(items, 1):
                message += f"{i}. {item['item_name_en']} - {item['price']} IQD\n"
            
            message += "\nType the number of the required item"
        
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

    def _show_additional_items_selection(self, phone_number: str, language: str) -> Dict:
        """Show additional items selection with interactive buttons"""
        if language == 'arabic':
            header_text = "إضافة أصناف"
            body_text = "هل تريد إضافة المزيد من الأصناف؟"
            footer_text = "اختر من الأزرار أدناه"
            buttons = [
                {
                    "type": "reply",
                    "reply": {
                        "id": "add_more_yes",
                        "title": "نعم"
                    }
                },
                {
                    "type": "reply",
                    "reply": {
                        "id": "add_more_no",
                        "title": "لا"
                    }
                }
            ]
        else:
            header_text = "Add More Items"
            body_text = "Do you want to add more items?"
            footer_text = "Select from buttons below"
            buttons = [
                {
                    "type": "reply",
                    "reply": {
                        "id": "add_more_yes",
                        "title": "Yes"
                    }
                },
                {
                    "type": "reply",
                    "reply": {
                        "id": "add_more_no",
                        "title": "No"
                    }
                }
                ]
        
        return self._create_interactive_response(header_text, body_text, footer_text, buttons)

    def _handle_structured_additional_selection(self, phone_number: str, text: str, session: Dict, user_context: Dict) -> Dict:
        """Handle additional items selection with button IDs or text"""
        language = user_context.get('language', 'arabic')
        
        # Handle button clicks
        if text == 'add_more_yes':
            # Check if user is in explore mode
            order_mode = session.get('order_mode') if session else None
            
            if order_mode == 'explore':
                # Continue with explore menu - show traditional categories
                self.db.create_or_update_session(
                    phone_number, 'waiting_for_category', language,
                    session.get('customer_name') if session else None,
                    order_mode='explore'  # Maintain explore mode
                )
                return self._show_traditional_categories(phone_number, language)
            else:
                # Show two-button interface for new orders
                self.db.create_or_update_session(
                    phone_number, 'waiting_for_category', language,
                    session.get('customer_name') if session else None
                )
                return self._show_main_categories(phone_number, language)
        
        elif text == 'add_more_no':
            # Check if we're in edit mode and should return to confirmation
            order_mode = session.get('order_mode') if session else None
            
            if order_mode in ['edit_add_quick', 'edit_add_explore']:
                # Return to confirmation with updated order
                self.db.create_or_update_session(
                    phone_number, 'waiting_for_confirmation', language,
                    session.get('customer_name') if session else None,
                    order_mode='quick'  # Restore to quick mode for confirmation
                )
                # Get refreshed session and user context for confirmation
                refreshed_session = self.db.get_user_session(phone_number)
                refreshed_user_context = self._build_user_context(phone_number, refreshed_session, 'waiting_for_confirmation', '')
                return self._show_quick_order_confirmation(phone_number, refreshed_session, refreshed_user_context)
            else:
                # Normal flow: Proceed to service selection
                self.db.create_or_update_session(
                    phone_number, 'waiting_for_service', language,
                    session.get('customer_name') if session else None
                )
                return self._show_service_selection(phone_number, language)
        
        # Handle text input (fallback)
        text_lower = text.lower().strip()
        if text_lower in ['نعم', 'yes', 'y', '1']:
            # Same logic as add_more_yes button
            order_mode = session.get('order_mode') if session else None
            
            if order_mode == 'explore':
                self.db.create_or_update_session(
                    phone_number, 'waiting_for_category', language,
                    session.get('customer_name') if session else None,
                    order_mode='explore'
                )
                return self._show_traditional_categories(phone_number, language)
            else:
                self.db.create_or_update_session(
                    phone_number, 'waiting_for_category', language,
                    session.get('customer_name') if session else None
                )
                return self._show_main_categories(phone_number, language)
        
        elif text_lower in ['لا', 'no', 'n', '2']:
            # Same logic as add_more_no button
            order_mode = session.get('order_mode') if session else None
            
            if order_mode in ['edit_add_quick', 'edit_add_explore']:
                self.db.create_or_update_session(
                    phone_number, 'waiting_for_confirmation', language,
                    session.get('customer_name') if session else None,
                    order_mode='quick'
                )
                refreshed_session = self.db.get_user_session(phone_number)
                refreshed_user_context = self._build_user_context(phone_number, refreshed_session, 'waiting_for_confirmation', '')
                return self._show_quick_order_confirmation(phone_number, refreshed_session, refreshed_user_context)
            else:
                self.db.create_or_update_session(
                    phone_number, 'waiting_for_service', language,
                    session.get('customer_name') if session else None
                )
                return self._show_service_selection(phone_number, language)
        
        # Invalid input - show the question again
        return self._show_additional_items_selection(phone_number, language)

    def _handle_structured_service_selection(self, phone_number: str, text: str, session: Dict, user_context: Dict) -> Dict:
        """Handle service selection with button IDs or text"""
        language = user_context.get('language', 'arabic')
        
        # Handle button clicks
        if text == 'service_dine_in':
            service_type = 'dine-in'
        elif text == 'service_delivery':
            service_type = 'delivery'
        else:
            # Handle text input (fallback)
            text_lower = text.lower().strip()
            if text_lower in ['1', 'تناول', 'داخل', 'في المقهى', 'dine', 'restaurant']:
                service_type = 'dine-in'
            elif text_lower in ['2', 'توصيل', 'delivery', 'home']:
                service_type = 'delivery'
            else:
                # Invalid input - show the question again
                return self._show_service_selection(phone_number, language)
        
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

    def _show_service_selection(self, phone_number: str, language: str) -> Dict:
        """Show service selection with interactive buttons"""
        if language == 'arabic':
            header_text = "نوع الخدمة"
            body_text = "هل تريد طلبك للتناول في المقهى أم للتوصيل؟"
            footer_text = "اختر نوع الخدمة المطلوبة"
            buttons = [
                {
                    "type": "reply",
                    "reply": {
                        "id": "service_dine_in",
                        "title": "تناول في المقهى"
                    }
                },
                {
                    "type": "reply",
                    "reply": {
                        "id": "service_delivery",
                        "title": "توصيل"
                    }
                }
            ]
        else:
            header_text = "Service Type"
            body_text = "Do you want your order for dine-in or delivery?"
            footer_text = "Select the required service type"
            buttons = [
                {
                    "type": "reply",
                    "reply": {
                        "id": "service_dine_in",
                        "title": "Dine-in"
                    }
                },
                {
                    "type": "reply",
                    "reply": {
                        "id": "service_delivery",
                        "title": "Delivery"
                    }
                }
            ]
        
        return self._create_interactive_response(header_text, body_text, footer_text, buttons)

    def _show_order_summary(self, phone_number: str, session: Dict, user_context: Dict, location: str) -> Dict:
        """Show order summary"""
        # Check if this is a quick order and show interactive confirmation
        if session.get('order_mode') == 'quick':
            return self._show_quick_order_confirmation(phone_number, session, user_context)
        
        # For explore menu orders, show interactive confirmation
        if session.get('order_mode') == 'explore':
            return self._show_explore_menu_confirmation(phone_number, session, user_context, location)
        
        # For regular orders, show text-based confirmation
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

    def _show_quick_order_confirmation(self, phone_number: str, session: Dict, user_context: Dict) -> Dict:
        """Show quick order confirmation with interactive buttons"""
        language = user_context.get('language', 'arabic')
        
        # Add detailed debugging before getting order
        logger.info(f"🔍 Quick order confirmation called for {phone_number}")
        logger.info(f"🔍 Session state: {session}")
        logger.info(f"🔍 User context: {user_context}")
        
        # Get current order details
        current_order = self.db.get_current_order(phone_number)
        logger.info(f"🔍 Quick order confirmation - Retrieved order: {current_order}")
        
        # Additional debugging for database state
        if current_order:
            logger.info(f"🔍 Order items count: {len(current_order.get('items', []))}")
            logger.info(f"🔍 Order details: {current_order.get('details', {})}")
            logger.info(f"🔍 Order total: {current_order.get('total', 0)}")
        
        if not current_order:
            logger.warning(f"❌ No current order found for {phone_number}")
            return self._create_response("لا توجد أصناف في الطلب. الرجاء المحاولة مرة أخرى.")
        
        if not current_order.get('items'):
            logger.warning(f"❌ Order exists but no items found: {current_order}")
            return self._create_response("لا توجد أصناف في الطلب. الرجاء المحاولة مرة أخرى.")
        
        # Calculate total
        total_amount = current_order.get('total', 0)
        
        if language == 'arabic':
            header_text = "تأكيد الطلب السريع"
            body_text = "إليك ملخص طلبك:\n\n"
            body_text += "الأصناف:\n"
            
            for item in current_order['items']:
                body_text += f"• {item['item_name_ar']} × {item['quantity']} - {item['subtotal']} دينار\n"
            
            body_text += f"\nالخدمة: {current_order['details'].get('service_type', 'غير محدد')}"
            if current_order['details'].get('location'):
                body_text += f"\nالمكان: {current_order['details']['location']}"
            body_text += f"\nالسعر الإجمالي: {total_amount} دينار"
            
            footer_text = "اختر من الأزرار أدناه"
            buttons = [
                {
                    "type": "reply",
                    "reply": {
                        "id": "confirm_order",
                        "title": "تأكيد الطلب"
                    }
                },
                {
                    "type": "reply",
                    "reply": {
                        "id": "edit_order",
                        "title": "تعديل الطلب"
                    }
                },
                {
                    "type": "reply",
                    "reply": {
                        "id": "cancel_order",
                        "title": "إلغاء الطلب"
                    }
                }
            ]
        else:
            header_text = "Quick Order Confirmation"
            body_text = "Here's your order summary:\n\n"
            body_text += "Items:\n"
            
            for item in current_order['items']:
                body_text += f"• {item['item_name_en']} × {item['quantity']} - {item['subtotal']} IQD\n"
            
            body_text += f"\nService: {current_order['details'].get('service_type', 'Not specified')}"
            if current_order['details'].get('location'):
                body_text += f"\nLocation: {current_order['details']['location']}"
            body_text += f"\nTotal Amount: {total_amount} IQD"
            
            footer_text = "Select from buttons below"
            buttons = [
                {
                    "type": "reply",
                    "reply": {
                        "id": "confirm_order",
                        "title": "Confirm Order"
                    }
                },
                {
                    "type": "reply",
                    "reply": {
                        "id": "edit_order",
                        "title": "Edit Order"
                    }
                },
                {
                    "type": "reply",
                    "reply": {
                        "id": "cancel_order",
                        "title": "Cancel Order"
                    }
                }
            ]
        
        return self._create_interactive_response(header_text, body_text, footer_text, buttons)

    def _show_explore_menu_confirmation(self, phone_number: str, session: Dict, user_context: Dict, location: str) -> Dict:
        """Show explore menu order confirmation with interactive buttons"""
        language = user_context.get('language', 'arabic')
        
        # Get current order details
        current_order = self.db.get_current_order(phone_number)
        
        if not current_order or not current_order.get('items'):
            return self._create_response("لا توجد أصناف في الطلب. الرجاء المحاولة مرة أخرى.")
        
        # Calculate total
        total_amount = current_order.get('total', 0)
        
        if language == 'arabic':
            header_text = "تأكيد الطلب"
            body_text = "إليك ملخص طلبك:\n\n"
            body_text += "الأصناف:\n"
            
            for item in current_order['items']:
                body_text += f"• {item['item_name_ar']} × {item['quantity']} - {item['subtotal']} دينار\n"
            
            body_text += f"\nالخدمة: {current_order['details'].get('service_type', 'غير محدد')}"
            if location:
                body_text += f"\nالمكان: {location}"
            body_text += f"\nالسعر الإجمالي: {total_amount} دينار"
            
            footer_text = "اختر من الأزرار أدناه"
            buttons = [
                {
                    "type": "reply",
                    "reply": {
                        "id": "confirm_order",
                        "title": "تأكيد الطلب"
                    }
                },
                {
                    "type": "reply",
                    "reply": {
                        "id": "edit_order",
                        "title": "تعديل الطلب"
                    }
                },
                {
                    "type": "reply",
                    "reply": {
                        "id": "cancel_order",
                        "title": "إلغاء الطلب"
                    }
                }
            ]
        else:
            header_text = "Order Confirmation"
            body_text = "Here's your order summary:\n\n"
            body_text += "Items:\n"
            
            for item in current_order['items']:
                body_text += f"• {item['item_name_en']} × {item['quantity']} - {item['subtotal']} IQD\n"
            
            body_text += f"\nService: {current_order['details'].get('service_type', 'Not specified')}"
            if location:
                body_text += f"\nLocation: {location}"
            body_text += f"\nTotal Amount: {total_amount} IQD"
            
            footer_text = "Select from buttons below"
            buttons = [
                {
                    "type": "reply",
                    "reply": {
                        "id": "confirm_order",
                        "title": "Confirm Order"
                    }
                },
                {
                    "type": "reply",
                    "reply": {
                        "id": "edit_order",
                        "title": "Edit Order"
                    }
                },
                {
                    "type": "reply",
                    "reply": {
                        "id": "cancel_order",
                        "title": "Cancel Order"
                    }
                }
            ]
        
        return self._create_interactive_response(header_text, body_text, footer_text, buttons)

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
        """Cancel order and properly clean up session"""
        self.db.cancel_order(phone_number)
        
        # CRITICAL FIX: Clear the session completely after cancellation
        # This prevents the session from remaining in 'waiting_for_confirmation' state
        self.db.delete_session(phone_number)
        
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

    def _show_edit_order_menu(self, phone_number: str, session: Dict, user_context: Dict) -> Dict:
        """Show edit order menu with 3 options"""
        language = user_context.get('language', 'arabic')
        
        # Update session to edit mode
        self.db.create_or_update_session(
            phone_number, 'waiting_for_edit_choice', language,
            session.get('customer_name') if session else None,
            order_mode=session.get('order_mode') if session else None
        )
        
        if language == 'arabic':
            header_text = "تعديل الطلب"
            body_text = "ماذا تريد أن تفعل؟"
            footer_text = "اختر من الخيارات أدناه"
            buttons = [
                {
                    "type": "reply",
                    "reply": {
                        "id": "add_item_to_order",
                        "title": "إضافة صنف آخر"
                    }
                },
                {
                    "type": "reply",
                    "reply": {
                        "id": "edit_item_quantity",
                        "title": "تعديل الكمية"
                    }
                },
                {
                    "type": "reply",
                    "reply": {
                        "id": "remove_item_from_order",
                        "title": "حذف صنف"
                    }
                }
            ]
        else:
            header_text = "Edit Order"
            body_text = "What would you like to do?"
            footer_text = "Choose from the options below"
            buttons = [
                {
                    "type": "reply",
                    "reply": {
                        "id": "add_item_to_order",
                        "title": "Add Another Item"
                    }
                },
                {
                    "type": "reply",
                    "reply": {
                        "id": "edit_item_quantity",
                        "title": "Edit Quantity"
                    }
                },
                {
                    "type": "reply",
                    "reply": {
                        "id": "remove_item_from_order",
                        "title": "Remove Item"
                    }
                }
            ]
        
        return self._create_interactive_response(header_text, body_text, footer_text, buttons)

    def _handle_edit_choice(self, phone_number: str, text: str, session: Dict, user_context: Dict) -> Dict:
        """Handle edit choice selection"""
        language = user_context.get('language', 'arabic')
        
        # Check for button clicks
        if text == 'add_item_to_order':
            return self._show_add_item_choice(phone_number, session, user_context)
        elif text == 'edit_item_quantity':
            return self._show_quantity_edit_menu(phone_number, session, user_context)
        elif text == 'remove_item_from_order':
            return self._show_remove_item_menu(phone_number, session, user_context)
        
        # Handle text input (1, 2, 3)
        text_lower = text.lower().strip()
        if text_lower in ['1', '١']:
            return self._show_add_item_choice(phone_number, session, user_context)
        elif text_lower in ['2', '٢']:
            return self._show_quantity_edit_menu(phone_number, session, user_context)
        elif text_lower in ['3', '٣']:
            return self._show_remove_item_menu(phone_number, session, user_context)
        
        # Invalid input
        if language == 'arabic':
            return self._create_response("الرجاء اختيار أحد الخيارات:\n1. إضافة صنف آخر\n2. تعديل الكمية\n3. حذف صنف")
        else:
            return self._create_response("Please choose one of the options:\n1. Add Another Item\n2. Edit Quantity\n3. Remove Item")

    def _show_add_item_choice(self, phone_number: str, session: Dict, user_context: Dict) -> Dict:
        """Show choice between quick order and explore menu for adding items"""
        language = user_context.get('language', 'arabic')
        
        # Update session to add item choice
        self.db.create_or_update_session(
            phone_number, 'waiting_for_add_item_choice', language,
            session.get('customer_name') if session else None,
            order_mode=session.get('order_mode') if session else None
        )
        
        if language == 'arabic':
            header_text = "إضافة صنف جديد"
            body_text = "كيف تريد أن تضيف صنف جديد؟"
            footer_text = "اختر من الخيارات أدناه"
            buttons = [
                {
                    "type": "reply",
                    "reply": {
                        "id": "quick_order_add",
                        "title": "طلب سريع"
                    }
                },
                {
                    "type": "reply",
                    "reply": {
                        "id": "explore_menu_add",
                        "title": "استكشف القائمة"
                    }
                }
            ]
        else:
            header_text = "Add New Item"
            body_text = "How would you like to add a new item?"
            footer_text = "Choose from the options below"
            buttons = [
                {
                    "type": "reply",
                    "reply": {
                        "id": "quick_order_add",
                        "title": "Quick Order"
                    }
                },
                {
                    "type": "reply",
                    "reply": {
                        "id": "explore_menu_add",
                        "title": "Explore Menu"
                    }
                }
            ]
        
        return self._create_interactive_response(header_text, body_text, footer_text, buttons)

    def _show_quantity_edit_menu(self, phone_number: str, session: Dict, user_context: Dict) -> Dict:
        """Show menu of items to edit quantity"""
        language = user_context.get('language', 'arabic')
        
        # Get current order items
        current_order = self.db.get_current_order(phone_number)
        if not current_order or not current_order.get('items'):
            if language == 'arabic':
                return self._create_response("لا توجد أصناف في الطلب لتعديل كميتها.")
            else:
                return self._create_response("No items in the order to edit quantity.")
        
        # Update session
        self.db.create_or_update_session(
            phone_number, 'waiting_for_quantity_item_selection', language,
            session.get('customer_name') if session else None,
            order_mode=session.get('order_mode') if session else None
        )
        
        if language == 'arabic':
            header_text = "تعديل الكمية"
            body_text = "أي صنف تريد تعديل كميته؟"
            footer_text = "اختر الصنف"
        else:
            header_text = "Edit Quantity"
            body_text = "Which item would you like to edit the quantity for?"
            footer_text = "Select the item"
        
        buttons = []
        for i, item in enumerate(current_order['items']):
            buttons.append({
                "type": "reply",
                "reply": {
                    "id": f"edit_qty_{item['menu_item_id']}",
                    "title": f"{item['item_name_ar']} × {item['quantity']}"
                }
            })
        
        return self._create_interactive_response(header_text, body_text, footer_text, buttons)

    def _show_remove_item_menu(self, phone_number: str, session: Dict, user_context: Dict) -> Dict:
        """Show menu of items to remove"""
        language = user_context.get('language', 'arabic')
        
        # Get current order items
        current_order = self.db.get_current_order(phone_number)
        if not current_order or not current_order.get('items'):
            if language == 'arabic':
                return self._create_response("لا توجد أصناف في الطلب لحذفها.")
            else:
                return self._create_response("No items in the order to remove.")
        
        # Update session
        self.db.create_or_update_session(
            phone_number, 'waiting_for_remove_item_selection', language,
            session.get('customer_name') if session else None,
            order_mode=session.get('order_mode') if session else None
        )
        
        if language == 'arabic':
            header_text = "حذف صنف"
            body_text = "أي صنف تريد حذفه؟"
            footer_text = "اختر الصنف للحذف"
        else:
            header_text = "Remove Item"
            body_text = "Which item would you like to remove?"
            footer_text = "Select the item to remove"
        
        buttons = []
        for i, item in enumerate(current_order['items']):
            buttons.append({
                "type": "reply",
                "reply": {
                    "id": f"remove_{item['menu_item_id']}",
                    "title": f"{item['item_name_ar']} × {item['quantity']}"
                }
            })
        
        return self._create_interactive_response(header_text, body_text, footer_text, buttons)

    def _handle_add_item_choice(self, phone_number: str, text: str, session: Dict, user_context: Dict) -> Dict:
        """Handle add item choice - quick order or explore menu"""
        language = user_context.get('language', 'arabic')
        
        if text == 'quick_order_add':
            # Set session to quick order mode for adding items
            self.db.create_or_update_session(
                phone_number, 'waiting_for_quick_order', language,
                session.get('customer_name') if session else None,
                order_mode='edit_add_quick'  # Special mode to return to confirmation after adding
            )
            
            # Use the same quick order interface for consistency
            return self._show_quick_order_interface(phone_number, language)
            
        elif text == 'explore_menu_add':
            # Set session to explore mode for adding items
            self.db.create_or_update_session(
                phone_number, 'waiting_for_category', language,
                session.get('customer_name') if session else None,
                order_mode='edit_add_explore'  # Special mode to return to confirmation after adding
            )
            return self._show_main_categories(phone_number, language)
        
        # Handle text input (1, 2)
        text_lower = text.lower().strip()
        if text_lower in ['1', '١']:
            return self._handle_add_item_choice(phone_number, 'quick_order_add', session, user_context)
        elif text_lower in ['2', '٢']:
            return self._handle_add_item_choice(phone_number, 'explore_menu_add', session, user_context)
        
        # Invalid input
        if language == 'arabic':
            return self._create_response("الرجاء اختيار أحد الخيارات:\n1. طلب سريع\n2. استكشف القائمة")
        else:
            return self._create_response("Please choose one of the options:\n1. Quick Order\n2. Explore Menu")

    def _handle_quantity_item_selection(self, phone_number: str, text: str, session: Dict, user_context: Dict) -> Dict:
        """Handle item selection for quantity editing"""
        language = user_context.get('language', 'arabic')
        
        # Check if it's a button click with edit_qty_ prefix
        if text.startswith('edit_qty_'):
            item_id = text.replace('edit_qty_', '')
            
            # Get the item details
            current_order = self.db.get_current_order(phone_number)
            selected_item = None
            for item in current_order.get('items', []):
                if str(item['menu_item_id']) == item_id:
                    selected_item = item
                    break
            
            if not selected_item:
                if language == 'arabic':
                    return self._create_response("لم يتم العثور على الصنف المحدد.")
                else:
                    return self._create_response("Selected item not found.")
            
            # Store selected item in session and ask for new quantity
            self.db.create_or_update_session(
                phone_number, 'waiting_for_new_quantity', language,
                session.get('customer_name') if session else None,
                order_mode=session.get('order_mode') if session else None,
                selected_item=int(item_id)
            )
            
            if language == 'arabic':
                response = f"كم تريد من {selected_item['item_name_ar']}؟\n\n"
                response += f"الكمية الحالية: {selected_item['quantity']}\n"
                response += "أدخل الكمية الجديدة:"
            else:
                response = f"How many {selected_item['item_name_en']} do you want?\n\n"
                response += f"Current quantity: {selected_item['quantity']}\n"
                response += "Enter new quantity:"
            
            return self._create_response(response)
        
        # Invalid input
        if language == 'arabic':
            return self._create_response("الرجاء اختيار أحد الأصناف من القائمة أعلاه.")
        else:
            return self._create_response("Please select one of the items from the list above.")

    def _handle_remove_item_selection(self, phone_number: str, text: str, session: Dict, user_context: Dict) -> Dict:
        """Handle item selection for removal"""
        language = user_context.get('language', 'arabic')
        
        # Check if it's a button click with remove_ prefix
        if text.startswith('remove_'):
            item_id = text.replace('remove_', '')
            
            # Get the item details
            current_order = self.db.get_current_order(phone_number)
            selected_item = None
            for item in current_order.get('items', []):
                if str(item['menu_item_id']) == item_id:
                    selected_item = item
                    break
            
            if not selected_item:
                if language == 'arabic':
                    return self._create_response("لم يتم العثور على الصنف المحدد.")
                else:
                    return self._create_response("Selected item not found.")
            
            # Remove the item from order
            success = self.db.remove_item_from_order(phone_number, int(item_id))
            
            if success:
                if language == 'arabic':
                    message = f"تم حذف {selected_item['item_name_ar']} من طلبك.\n\n"
                    message += "سيتم عرض الطلب المحدث:"
                else:
                    message = f"{selected_item['item_name_en']} has been removed from your order.\n\n"
                    message += "Updated order will be displayed:"
                
                # Return to confirmation with updated order
                order_mode = session.get('order_mode') if session else None
                self.db.create_or_update_session(
                    phone_number, 'waiting_for_confirmation', language,
                    session.get('customer_name') if session else None,
                    order_mode=order_mode
                )
                
                # Send removal confirmation and then show updated confirmation
                self._create_response(message)
                return self._show_quick_order_confirmation(phone_number, session, user_context)
            else:
                if language == 'arabic':
                    return self._create_response("فشل في حذف الصنف. الرجاء المحاولة مرة أخرى.")
                else:
                    return self._create_response("Failed to remove item. Please try again.")
        
        # Invalid input
        if language == 'arabic':
            return self._create_response("الرجاء اختيار أحد الأصناف من القائمة أعلاه.")
        else:
            return self._create_response("Please select one of the items from the list above.")

    def _handle_new_quantity_input(self, phone_number: str, text: str, session: Dict, user_context: Dict) -> Dict:
        """Handle new quantity input for editing"""
        language = user_context.get('language', 'arabic')
        
        # Convert Arabic numerals to English
        converted_text = self._convert_arabic_numerals(text.strip())
        
        try:
            new_quantity = int(converted_text)
            if new_quantity <= 0:
                raise ValueError("Quantity must be positive")
            
            # Get the item ID being edited
            edit_item_id = session.get('selected_item')
            if not edit_item_id:
                if language == 'arabic':
                    return self._create_response("خطأ: لم يتم العثور على الصنف المراد تعديله.")
                else:
                    return self._create_response("Error: Item to edit not found.")
            
            # Update the quantity in database
            success = self.db.update_item_quantity(phone_number, int(edit_item_id), new_quantity)
            
            if success:
                # Get updated item details
                current_order = self.db.get_current_order(phone_number)
                updated_item = None
                for item in current_order.get('items', []):
                    if item['menu_item_id'] == int(edit_item_id):
                        updated_item = item
                        break
                
                if language == 'arabic':
                    if updated_item:
                        message = f"تم تحديث {updated_item['item_name_ar']} إلى {new_quantity} قطعة.\n\n"
                    else:
                        message = f"تم تحديث الكمية إلى {new_quantity} قطعة.\n\n"
                    message += "سيتم عرض الطلب المحدث:"
                else:
                    if updated_item:
                        message = f"Updated {updated_item['item_name_en']} to {new_quantity} pieces.\n\n"
                    else:
                        message = f"Updated quantity to {new_quantity} pieces.\n\n"
                    message += "Updated order will be displayed:"
                
                # Return to confirmation with updated order
                order_mode = session.get('order_mode') if session else None
                self.db.create_or_update_session(
                    phone_number, 'waiting_for_confirmation', language,
                    session.get('customer_name') if session else None,
                    order_mode=order_mode
                )
                
                # Send update confirmation and then show updated confirmation
                self._create_response(message)
                return self._show_quick_order_confirmation(phone_number, session, user_context)
            else:
                if language == 'arabic':
                    return self._create_response("فشل في تحديث الكمية. الرجاء المحاولة مرة أخرى.")
                else:
                    return self._create_response("Failed to update quantity. Please try again.")
                    
        except ValueError:
            if language == 'arabic':
                return self._create_response("الرجاء إدخال رقم صحيح للكمية.")
            else:
                return self._create_response("Please enter a valid number for quantity.")

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
        """AI-driven item matching with flexible scoring mechanism."""
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
        
        logger.info(f"🔍 AI-driven matching '{text}' (cleaned: '{cleaned_text}') against {len(items)} items")
        
        # AI-driven scoring mechanism - let the AI handle the complex understanding
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
            
            # 5. Character-level similarity for misspellings (lower priority)
            if len(text_lower) > 2:  # Only for meaningful words
                char_similarity = len(set(text_lower) & set(item_name_lower)) / len(set(text_lower) | set(item_name_lower))
                if char_similarity > 0.7:  # 70% character similarity
                    score += char_similarity * 10
                    logger.info(f"  🔤 Character similarity: {char_similarity:.2f} for '{item_name_lower}' (score: {score})")
            
            # Update best match if this score is higher
            if score > best_score:
                best_score = score
                best_match = item
                logger.info(f"  🏆 New best match: '{item_name_lower}' with score {score}")
        
        if best_match and best_score > 10:  # Minimum threshold to avoid false matches
            logger.info(f"✅ AI-driven final match: '{best_match['item_name_ar' if language == 'arabic' else 'item_name_en']}' with score {best_score}")
            return best_match
        
        logger.info(f"❌ No confident match found for '{text}' (cleaned: '{cleaned_text}')")
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

        # Get current step and order mode
        current_step = session.get('current_step')
        order_mode = session.get('order_mode')
        
        logger.debug(f"🔍 Session reset check: message='{user_message}', current_step='{current_step}', order_mode='{order_mode}'")

        # CRITICAL FIX: Never reset session during quick order flow
        if order_mode == 'quick':
            logger.debug(f"🎯 Quick order mode detected - preventing session reset")
            return False

        # CRITICAL FIX: Never reset during active order steps
        active_order_steps = [
            'waiting_for_location', 'waiting_for_confirmation', 'waiting_for_service_type',
            'waiting_for_quick_order_service', 'waiting_for_quantity', 'waiting_for_additional'
        ]
        if current_step in active_order_steps:
            logger.debug(f"🛡️ Active order step '{current_step}' - preventing session reset")
            return False

        # Check for greeting words that might indicate a fresh start
        greeting_words = ['مرحبا', 'السلام عليكم', 'أهلا', 'hello', 'hi', 'hey']
        user_lower = user_message.lower().strip()
        
        # Convert Arabic numerals to check if message is numeric
        converted_message = self._convert_arabic_numerals(user_message)
        
        # Only reset if it's clearly a greeting and not at language selection step
        # Also, don't reset if we're in confirmation step and user says yes/no
        if (any(greeting in user_lower for greeting in greeting_words) and
                len(user_message.strip()) <= 15 and  # Allow slightly longer greetings
                current_step not in ['waiting_for_language', 'waiting_for_category', 'waiting_for_confirmation'] and
                # Make sure it's not just a number (including Arabic numerals)
                not user_message.strip().isdigit() and
                not converted_message.strip().isdigit() and
                not any(char.isdigit() for char in user_message) and
                not any(char.isdigit() for char in converted_message)):
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