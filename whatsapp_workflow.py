import sqlite3
import json
import datetime
import logging
import re
import os
import requests
from typing import Dict, Any, List, Optional, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import OpenAI
try:
    import openai

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI not installed. AI features will be disabled.")


class CafeDatabaseManager:
    """SQLite Database Manager for Cafe Workflow Control"""

    def __init__(self, db_path: str = "hef_cafe.db"):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Initialize SQLite database with all required tables"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")

            # User Sessions Table - Controls workflow steps
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_sessions (
                    phone_number TEXT PRIMARY KEY,
                    current_step TEXT NOT NULL,
                    language_preference TEXT,
                    customer_name TEXT,
                    selected_category INTEGER,
                    selected_item INTEGER,
                    conversation_context TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Menu Items Table - Centralized menu management
            conn.execute("""
                CREATE TABLE IF NOT EXISTS menu_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category_id INTEGER NOT NULL,
                    category_name_ar TEXT NOT NULL,
                    category_name_en TEXT NOT NULL,
                    item_name_ar TEXT NOT NULL,
                    item_name_en TEXT NOT NULL,
                    price INTEGER NOT NULL,
                    unit TEXT NOT NULL,
                    available BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # User Orders Table - Current order state
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    phone_number TEXT NOT NULL,
                    menu_item_id INTEGER NOT NULL,
                    quantity INTEGER NOT NULL,
                    subtotal INTEGER NOT NULL,
                    special_requests TEXT,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (menu_item_id) REFERENCES menu_items (id),
                    FOREIGN KEY (phone_number) REFERENCES user_sessions (phone_number)
                )
            """)

            # Order Details Table - Service type, location, etc.
            conn.execute("""
                CREATE TABLE IF NOT EXISTS order_details (
                    phone_number TEXT PRIMARY KEY,
                    service_type TEXT,
                    location TEXT,
                    total_amount INTEGER DEFAULT 0,
                    customizations TEXT,
                    order_status TEXT DEFAULT 'in_progress',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (phone_number) REFERENCES user_sessions (phone_number)
                )
            """)

            # Conversation Log Table - For analytics and debugging
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversation_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    phone_number TEXT NOT NULL,
                    message_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    ai_response TEXT,
                    current_step TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (phone_number) REFERENCES user_sessions (phone_number)
                )
            """)

            # Completed Orders Table - Order history
            conn.execute("""
                CREATE TABLE IF NOT EXISTS completed_orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    phone_number TEXT NOT NULL,
                    order_id TEXT NOT NULL UNIQUE,
                    items_json TEXT NOT NULL,
                    total_amount INTEGER NOT NULL,
                    service_type TEXT,
                    location TEXT,
                    completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Step Validation Rules Table - Workflow control
            conn.execute("""
                CREATE TABLE IF NOT EXISTS step_rules (
                    current_step TEXT PRIMARY KEY,
                    allowed_next_steps TEXT NOT NULL,
                    required_data TEXT,
                    description TEXT
                )
            """)

            # Initialize menu data if empty
            self.populate_initial_data()

        logger.info("✅ Database initialized successfully")

    def populate_initial_data(self):
        """Populate initial menu and step rules"""
        with sqlite3.connect(self.db_path) as conn:
            # Check if menu data exists
            cursor = conn.execute("SELECT COUNT(*) FROM menu_items")
            if cursor.fetchone()[0] > 0:
                return  # Data already exists

            # Insert menu items
            menu_data = [
                # Hot Beverages
                (1, "المشروبات الحارة", "Hot Beverages", "اسبريسو", "Espresso", 3000, "cups"),
                (1, "المشروبات الحارة", "Hot Beverages", "قهوة تركية", "Turkish Coffee", 3000, "cups"),
                (1, "المشروبات الحارة", "Hot Beverages", "شاي عراقي", "Iraqi Tea", 1000, "cups"),
                (1, "المشروبات الحارة", "Hot Beverages", "كابتشينو", "Cappuccino", 5000, "cups"),
                (1, "المشروبات الحارة", "Hot Beverages", "هوت شوكليت", "Hot Chocolate", 5000, "cups"),
                (1, "المشروبات الحارة", "Hot Beverages", "لاتيه كراميل", "Caramel Latte", 5000, "cups"),
                (1, "المشروبات الحارة", "Hot Beverages", "لاتيه فانيلا", "Vanilla Latte", 5000, "cups"),
                (1, "المشروبات الحارة", "Hot Beverages", "امريكانو", "Americano", 4000, "cups"),

                # Cold Beverages
                (2, "المشروبات الباردة", "Cold Beverages", "ايس كوفي", "Iced Coffee", 3000, "cups"),
                (2, "المشروبات الباردة", "Cold Beverages", "ايس لاتيه", "Iced Latte", 4000, "cups"),
                (2, "المشروبات الباردة", "Cold Beverages", "كراميل ايس لاتيه", "Caramel Iced Latte", 5000, "cups"),
                (2, "المشروبات الباردة", "Cold Beverages", "ايس امريكانو", "Iced Americano", 4000, "cups"),

                # Toast
                (9, "توست", "Toast", "مارتديلا لحم بالجبن", "Beef Mortadella with Cheese", 2000, "pieces"),
                (9, "توست", "Toast", "مارتديلا دجاج بالجبن", "Chicken Mortadella with Cheese", 2000, "pieces"),
                (9, "توست", "Toast", "جبن بالزعتر", "Cheese with Zaatar", 2000, "pieces"),

                # Cake Slices
                (11, "قطع الكيك", "Cake Slices", "فانيلا كيك", "Vanilla Cake", 4000, "slices"),
                (11, "قطع الكيك", "Cake Slices", "لوتس كيك", "Lotus Cake", 4000, "slices"),
                (11, "قطع الكيك", "Cake Slices", "شوكليت كيك", "Chocolate Cake", 4000, "slices"),
            ]

            conn.executemany("""
                INSERT INTO menu_items 
                (category_id, category_name_ar, category_name_en, item_name_ar, item_name_en, price, unit)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, menu_data)

            # Insert flexible step validation rules for AI conversations
            step_rules = [
                # Language step - can stay for clarification or move forward
                ("waiting_for_language", "waiting_for_language,waiting_for_category", "language_preference",
                 "Language selection"),

                # Category step - can stay for menu display/clarification or move forward
                ("waiting_for_category", "waiting_for_category,waiting_for_item", "selected_category",
                 "Category selection"),

                # Item step - can stay for clarification or move forward
                ("waiting_for_item", "waiting_for_item,waiting_for_quantity", "selected_item", "Item selection"),

                # Quantity step - can stay for clarification or move forward
                ("waiting_for_quantity", "waiting_for_quantity,waiting_for_additional", "quantity",
                 "Quantity selection"),

                # Additional items - can go back to categories, stay for clarification, or move to service
                ("waiting_for_additional", "waiting_for_additional,waiting_for_category,waiting_for_service",
                 "additional_choice", "Additional items choice"),

                # Service type - can stay for clarification or move forward
                ("waiting_for_service", "waiting_for_service,waiting_for_location", "service_type",
                 "Service type selection"),

                # Location - can stay for clarification or move forward
                ("waiting_for_location", "waiting_for_location,waiting_for_confirmation", "location",
                 "Location/table selection"),

                # Confirmation - can stay, complete, or restart
                ("waiting_for_confirmation", "waiting_for_confirmation,completed,waiting_for_language", "confirmation",
                 "Order confirmation"),
            ]

            conn.executemany("""
                INSERT OR REPLACE INTO step_rules 
                (current_step, allowed_next_steps, required_data, description)
                VALUES (?, ?, ?, ?)
            """, step_rules)

            conn.commit()
            logger.info("✅ Initial data populated")

    def get_user_session(self, phone_number: str) -> Optional[Dict]:
        """Get current user session state"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM user_sessions WHERE phone_number = ?
            """, (phone_number,))

            row = cursor.fetchone()
            return dict(row) if row else None

    def create_or_update_session(self, phone_number: str, current_step: str,
                                 language: str = None, customer_name: str = None,
                                 selected_category: int = None, selected_item: int = None,
                                 conversation_context: str = None) -> bool:
        """Create new session or update existing one"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Get existing session
                cursor = conn.execute("SELECT * FROM user_sessions WHERE phone_number = ?", (phone_number,))
                existing = cursor.fetchone()

                if existing:
                    # Update existing session
                    updates = ["current_step = ?", "updated_at = CURRENT_TIMESTAMP"]
                    params = [current_step]

                    if language:
                        updates.append("language_preference = ?")
                        params.append(language)
                    if customer_name:
                        updates.append("customer_name = ?")
                        params.append(customer_name)
                    if selected_category:
                        updates.append("selected_category = ?")
                        params.append(selected_category)
                    if selected_item:
                        updates.append("selected_item = ?")
                        params.append(selected_item)
                    if conversation_context:
                        updates.append("conversation_context = ?")
                        params.append(conversation_context)

                    params.append(phone_number)

                    conn.execute(f"""
                        UPDATE user_sessions 
                        SET {', '.join(updates)}
                        WHERE phone_number = ?
                    """, params)
                else:
                    # Create new session
                    conn.execute("""
                        INSERT INTO user_sessions 
                        (phone_number, current_step, language_preference, customer_name, selected_category, selected_item, conversation_context)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (phone_number, current_step, language, customer_name, selected_category, selected_item,
                          conversation_context))

                # Create order details record if doesn't exist
                conn.execute("""
                    INSERT OR IGNORE INTO order_details (phone_number)
                    VALUES (?)
                """, (phone_number,))

                conn.commit()
                return True
        except Exception as e:
            logger.error(f"❌ Error creating/updating session: {e}")
            return False

    def validate_step_transition(self, phone_number: str, next_step: str) -> bool:
        """Validate if user can move to next step"""
        session = self.get_user_session(phone_number)
        current_step = session['current_step'] if session else 'waiting_for_language'

        logger.info(f"🔄 Validating transition: {current_step} → {next_step}")

        if not session and next_step == "waiting_for_language":
            logger.info("✅ New user, allowing language selection")
            return True

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT allowed_next_steps FROM step_rules 
                WHERE current_step = ?
            """, (current_step,))

            row = cursor.fetchone()
            if not row:
                logger.warning(f"⚠️ No rules found for step: {current_step}")
                return False

            allowed_steps = row[0].split(',')
            is_allowed = next_step in allowed_steps

            logger.info(
                f"📋 Current: {current_step}, Allowed: {allowed_steps}, Requesting: {next_step}, Valid: {is_allowed}")

            return is_allowed

    def get_available_categories(self) -> List[Dict]:
        """Get all available menu categories"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT DISTINCT category_id, category_name_ar, category_name_en
                FROM menu_items 
                WHERE available = 1
                ORDER BY category_id
            """)

            return [dict(row) for row in cursor.fetchall()]

    def get_category_items(self, category_id: int) -> List[Dict]:
        """Get items for specific category"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM menu_items 
                WHERE category_id = ? AND available = 1
                ORDER BY id
            """, (category_id,))

            return [dict(row) for row in cursor.fetchall()]

    def get_item_by_id(self, item_id: int) -> Optional[Dict]:
        """Get specific menu item by ID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM menu_items WHERE id = ?
            """, (item_id,))

            row = cursor.fetchone()
            return dict(row) if row else None

    def add_item_to_order(self, phone_number: str, menu_item_id: int, quantity: int,
                          special_requests: str = None) -> bool:
        """Add item to user's current order"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Get item price
                cursor = conn.execute("SELECT price FROM menu_items WHERE id = ?", (menu_item_id,))
                price = cursor.fetchone()[0]
                subtotal = price * quantity

                # Add to order
                conn.execute("""
                    INSERT INTO user_orders 
                    (phone_number, menu_item_id, quantity, subtotal, special_requests)
                    VALUES (?, ?, ?, ?, ?)
                """, (phone_number, menu_item_id, quantity, subtotal, special_requests))

                # Update total
                cursor = conn.execute("""
                    SELECT SUM(subtotal) FROM user_orders WHERE phone_number = ?
                """, (phone_number,))
                total = cursor.fetchone()[0] or 0

                conn.execute("""
                    UPDATE order_details SET total_amount = ? WHERE phone_number = ?
                """, (total, phone_number))

                conn.commit()
                return True
        except Exception as e:
            logger.error(f"❌ Error adding item to order: {e}")
            return False

    def get_user_order(self, phone_number: str) -> Dict:
        """Get user's current order with all details"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # Get order items
            cursor = conn.execute("""
                SELECT uo.*, mi.item_name_ar, mi.item_name_en, mi.price, mi.unit
                FROM user_orders uo
                JOIN menu_items mi ON uo.menu_item_id = mi.id
                WHERE uo.phone_number = ?
                ORDER BY uo.added_at
            """, (phone_number,))

            items = [dict(row) for row in cursor.fetchall()]

            # Get order details
            cursor = conn.execute("""
                SELECT * FROM order_details WHERE phone_number = ?
            """, (phone_number,))

            details = cursor.fetchone()
            details = dict(details) if details else {}

            return {
                'items': items,
                'details': details,
                'total': details.get('total_amount', 0)
            }

    def update_order_details(self, phone_number: str, service_type: str = None,
                             location: str = None, customizations: str = None) -> bool:
        """Update order service details"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                updates = []
                params = []

                if service_type:
                    updates.append("service_type = ?")
                    params.append(service_type)
                if location:
                    updates.append("location = ?")
                    params.append(location)
                if customizations:
                    updates.append("customizations = ?")
                    params.append(customizations)

                if updates:
                    params.append(phone_number)
                    conn.execute(f"""
                        UPDATE order_details 
                        SET {', '.join(updates)}
                        WHERE phone_number = ?
                    """, params)
                    conn.commit()

                return True
        except Exception as e:
            logger.error(f"❌ Error updating order details: {e}")
            return False

    def log_conversation(self, phone_number: str, message_type: str, content: str,
                         ai_response: str = None, current_step: str = None):
        """Log conversation for analytics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO conversation_log 
                    (phone_number, message_type, content, ai_response, current_step)
                    VALUES (?, ?, ?, ?, ?)
                """, (phone_number, message_type, content, ai_response, current_step))
                conn.commit()
        except Exception as e:
            logger.error(f"❌ Error logging conversation: {e}")

    def complete_order(self, phone_number: str) -> str:
        """Complete order and generate order ID"""
        try:
            import random
            order_id = f"HEF{random.randint(1000, 9999)}"

            with sqlite3.connect(self.db_path) as conn:
                # Get order data
                order = self.get_user_order(phone_number)

                # Save to completed orders
                conn.execute("""
                    INSERT INTO completed_orders 
                    (phone_number, order_id, items_json, total_amount, service_type, location)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    phone_number,
                    order_id,
                    json.dumps(order['items']),
                    order['total'],
                    order['details'].get('service_type'),
                    order['details'].get('location')
                ))

                # Clear current order
                conn.execute("DELETE FROM user_orders WHERE phone_number = ?", (phone_number,))
                conn.execute("DELETE FROM order_details WHERE phone_number = ?", (phone_number,))
                conn.execute("DELETE FROM user_sessions WHERE phone_number = ?", (phone_number,))

                conn.commit()
                return order_id
        except Exception as e:
            logger.error(f"❌ Error completing order: {e}")
            return None


class TrueAIWorkflow:
    """Truly AI-Powered WhatsApp Workflow with Natural Language Understanding"""

    def __init__(self, config: Dict[str, str]):
        self.config = config
        self.db = CafeDatabaseManager()

        # Initialize OpenAI with enhanced configuration
        if OPENAI_AVAILABLE and config.get('openai_api_key'):
            try:
                self.openai_client = openai.OpenAI(api_key=config.get('openai_api_key'))
                logger.info("✅ OpenAI client initialized for True AI")
            except Exception as e:
                logger.error(f"⚠️ OpenAI initialization failed: {e}")
                self.openai_client = None
        else:
            self.openai_client = None
            logger.warning("⚠️ Running without OpenAI - AI features limited")

        # AI System Prompt for Natural Language Understanding
        self.system_prompt = """You are Hef, a friendly AI assistant for Hef Cafe in Iraq. You have natural language understanding and can handle different dialects, accents, typos, and informal language.

PERSONALITY:
- Warm, conversational, and helpful
- Understand various Arabic dialects (Iraqi, Gulf, Levantine, Egyptian, etc.)
- Handle English with different accents and typos
- Use appropriate emojis and casual language
- Be patient and clarify when unsure

CAPABILITIES:
- Understand typos and misspellings (e.g., "coffe" = "coffee", "colde" = "cold")
- Recognize numbers in any format (1, ١, "first", "واحد")
- Handle casual language ("gimme", "wanna", "اريد", "بدي")
- Understand context from conversation
- Ask clarifying questions when unclear

MENU UNDERSTANDING:
You know the complete menu. When users mention items informally, understand their intent:
- "cold stuff" = Cold Beverages
- "something sweet" = Cake Slices  
- "coffee" = could be any coffee drink
- "first one" = first item from current menu
- "١" or "1" = first item from current menu

CONVERSATION RULES:
- Always understand the user's INTENT, not just exact words
- When user says numbers/positions (1, ١, "first"), refer to the current menu context
- Handle typos gracefully without mentioning them
- If truly unclear, ask specific clarifying questions
- Be conversational, not robotic
- Maintain context throughout the conversation

RESPONSE FORMAT:
- Respond naturally in the user's preferred language
- Be helpful and understanding
- Use emojis appropriately
- Keep responses conversational and friendly"""

    def handle_whatsapp_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Main message handler with True AI Understanding"""
        try:
            if 'text' not in message_data:
                return self.create_response("أرسل لي رسالة نصية من فضلك! 😊\nPlease send me a text message! 😊")

            text = message_data.get('text', {}).get('body', '').strip()
            phone_number = message_data.get('from')
            customer_name = self.extract_customer_name(message_data)

            # Log the conversation
            self.db.log_conversation(phone_number, 'user_message', text)

            # Get current session state
            session = self.db.get_user_session(phone_number)
            current_step = session['current_step'] if session else 'waiting_for_language'

            logger.info(f"📊 User {phone_number} at step: {current_step}")

            # Process with True AI Understanding
            response = self.process_with_ai(phone_number, current_step, text, customer_name, session)

            # Log AI response
            self.db.log_conversation(phone_number, 'ai_response', response['content'])

            return response

        except Exception as e:
            logger.error(f"❌ Error handling message: {str(e)}")
            return self.create_response(
                "عذراً، حدث خطأ. من فضلك أعد المحاولة! 🙏\nSorry, something went wrong. Please try again! 🙏")

    def extract_customer_name(self, message_data: Dict) -> str:
        """Extract customer name from WhatsApp message data"""
        if 'contacts' in message_data:
            contacts = message_data.get('contacts', [])
            if contacts and len(contacts) > 0:
                profile = contacts[0].get('profile', {})
                return profile.get('name', 'Customer')
        return 'Customer'

    def process_with_ai(self, phone_number: str, current_step: str, user_message: str,
                        customer_name: str, session: Dict) -> Dict:
        """Process user message with True AI Understanding"""

        # Build context for AI
        context = self.build_conversation_context(session, current_step)

        # Get AI understanding and action
        ai_result = self.get_ai_understanding(user_message, current_step, context, session)

        if not ai_result:
            # Fallback to simple processing
            return self.fallback_processing(phone_number, current_step, user_message, customer_name)

        # Execute the AI-determined action
        return self.execute_ai_action(phone_number, ai_result, session, customer_name)

    def build_conversation_context(self, session: Dict, current_step: str) -> Dict:
        """Build rich context for AI understanding"""
        context = {
            'current_step': current_step,
            'step_description': self.get_step_description(current_step),
            'available_categories': [],
            'current_category_items': [],
            'current_order': {},
            'language': session.get('language_preference') if session else None
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

    def get_step_description(self, step: str) -> str:
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

    def get_ai_understanding(self, user_message: str, current_step: str, context: Dict, session: Dict) -> Optional[
        Dict]:
        """Get AI understanding of user intent and determine action"""
        if not self.openai_client:
            return None

        try:
            # Build AI prompt with rich context
            ai_prompt = f"""
CURRENT SITUATION:
- User is at step: {current_step} ({context['step_description']})
- User said: "{user_message}"

CONTEXT:
{json.dumps(context, ensure_ascii=False, indent=2)}

TASK:
Understand what the user wants and determine the appropriate action. Consider:
1. Typos and misspellings
2. Different ways to express the same thing
3. Numbers in different formats (1, ١, "first", "واحد")
4. Casual language and slang
5. Context from current menu/options

RESPOND WITH JSON:
{{
    "understood_intent": "clear description of what user wants",
    "confidence": "high/medium/low",
    "action": "language_selection/category_selection/item_selection/quantity_selection/yes_no/service_selection/location_input/confirmation/show_menu/help_request/stay_current_step",
    "extracted_data": {{
        "language": "arabic/english/null",
        "category_id": "number or null",
        "category_name": "string or null",
        "item_id": "number or null",
        "item_name": "string or null",
        "quantity": "number or null",
        "yes_no": "yes/no/null",
        "service_type": "dine-in/delivery/null",
        "location": "string or null"
    }},
    "clarification_needed": "true/false",
    "clarification_question": "question to ask if clarification needed",
    "response_message": "natural response to user in their preferred language"
}}

IMPORTANT ACTIONS:
- Use "show_menu" when user asks for menu, منيو, قائمة
- Use "help_request" when user needs help or explanation
- Use "stay_current_step" when providing clarification without step change
- Always prioritize staying at current step for natural conversation
- Only move to next step when user clearly selects something

EXAMPLES:
- "منيو" at category step → show_menu action, stay at waiting_for_category
- "Cold" → category_selection, category_name: "Cold Beverages"
- "Iced coffe" → item_selection, item_name: "Iced Coffee"  
- "١" in item context → item_selection, item_id: first item from context
- "first one" → item_selection, item_id: first item from context
- "Dine in" → service_selection, service_type: "dine-in"
"""

            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": ai_prompt}
                ],
                max_tokens=800,
                temperature=0.3,  # Lower temperature for more consistent parsing
            )

            ai_response = response.choices[0].message.content.strip()

            # Parse JSON response
            try:
                # Clean the response if it has markdown formatting
                if ai_response.startswith('```json'):
                    ai_response = ai_response.replace('```json', '').replace('```', '').strip()

                result = json.loads(ai_response)
                logger.info(f"✅ AI Understanding: {result['understood_intent']} (confidence: {result['confidence']})")
                return result

            except json.JSONDecodeError as e:
                logger.error(f"❌ Failed to parse AI JSON response: {e}")
                logger.error(f"AI Response was: {ai_response}")
                return None

        except Exception as e:
            logger.error(f"❌ AI understanding error: {str(e)}")
            return None

    def execute_ai_action(self, phone_number: str, ai_result: Dict, session: Dict, customer_name: str) -> Dict:
        """Execute the action determined by AI with flexible workflow support"""
        action = ai_result.get('action')
        extracted_data = ai_result.get('extracted_data', {})
        response_message = ai_result.get('response_message', '')
        clarification_needed = ai_result.get('clarification_needed', False)
        current_step = session.get('current_step') if session else 'waiting_for_language'

        # If AI needs clarification, return clarification question
        if clarification_needed:
            clarification_question = ai_result.get('clarification_question', 'Could you please clarify?')
            return self.create_response(clarification_question)

        try:
            # Handle staying at current step for clarification/help
            if action == 'stay_current_step':
                return self.create_response(response_message)

            # Handle specific actions based on AI understanding
            if action == 'language_selection':
                return self.execute_language_selection(phone_number, extracted_data, customer_name, response_message)

            elif action == 'category_selection':
                return self.execute_category_selection(phone_number, extracted_data, response_message, session)

            elif action == 'item_selection':
                return self.execute_item_selection(phone_number, extracted_data, response_message, session)

            elif action == 'quantity_selection':
                return self.execute_quantity_selection(phone_number, extracted_data, response_message, session)

            elif action == 'yes_no':
                return self.execute_yes_no_action(phone_number, extracted_data, response_message, session)

            elif action == 'service_selection':
                return self.execute_service_selection(phone_number, extracted_data, response_message, session)

            elif action == 'location_input':
                return self.execute_location_input(phone_number, extracted_data, response_message, session)

            elif action == 'confirmation':
                return self.execute_confirmation(phone_number, extracted_data, response_message, session)

            elif action == 'show_menu':
                return self.execute_show_menu(phone_number, current_step, response_message, session)

            elif action == 'help_request':
                return self.execute_help_request(phone_number, current_step, response_message, session)

            else:
                # AI provided a natural response without specific action - allow staying at current step
                return self.create_response(response_message)

        except Exception as e:
            logger.error(f"❌ Error executing AI action {action}: {e}")
            return self.create_response(
                "عذراً، حدث خطأ. هل يمكنك المحاولة مرة أخرى؟\nSorry, something went wrong. Can you try again?")

    def execute_language_selection(self, phone_number: str, extracted_data: Dict, customer_name: str,
                                   response_message: str) -> Dict:
        """Execute language selection with AI understanding"""
        language = extracted_data.get('language')

        if language and self.db.validate_step_transition(phone_number, 'waiting_for_category'):
            success = self.db.create_or_update_session(phone_number, 'waiting_for_category', language, customer_name)

            if success:
                categories = self.db.get_available_categories()

                # Generate natural response showing categories
                if language == 'arabic':
                    if not response_message:
                        response_message = f"أهلاً {customer_name}! 😊\n\nشو تحب تطلب اليوم؟ عندنا:\n"
                        for cat in categories:
                            response_message += f"🔸 {cat['category_name_ar']}\n"
                        response_message += "\nقلي شو تريد! 👆"
                else:
                    if not response_message:
                        response_message = f"Welcome {customer_name}! 😊\n\nWhat would you like today? We have:\n"
                        for cat in categories:
                            response_message += f"🔸 {cat['category_name_en']}\n"
                        response_message += "\nTell me what you'd like! 👆"

                return self.create_response(response_message)

        # Language not detected, ask again naturally
        return self.create_response(
            f"مرحباً {customer_name}! أهلاً بك في مقهى هيف ☕\n"
            f"تحب نحكي عربي ولا إنكليزي؟\n\n"
            f"Hello {customer_name}! Welcome to Hef Cafe ☕\n"
            f"Would you prefer Arabic or English?"
        )

    def execute_category_selection(self, phone_number: str, extracted_data: Dict, response_message: str,
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

            # Use AI response or generate natural one
            if not response_message:
                if language == 'arabic':
                    response_message = f"ممتاز! عندنا من {selected_category['category_name_ar']}:\n\n"
                    for i, item in enumerate(items, 1):
                        response_message += f"{i}. {item['item_name_ar']} - {item['price']} دينار\n"
                    response_message += "\nشو تختار؟ 😊"
                else:
                    response_message = f"Great choice! Our {selected_category['category_name_en']} options:\n\n"
                    for i, item in enumerate(items, 1):
                        response_message += f"{i}. {item['item_name_en']} - {item['price']} IQD\n"
                    response_message += "\nWhat would you like? 😊"

            return self.create_response(response_message)

        # Category not found, ask again naturally
        if language == 'arabic':
            response_message = "ما فهمت شو تريد بالضبط 🤔 عندنا هاي الأنواع:\n"
            for cat in categories:
                response_message += f"🔸 {cat['category_name_ar']}\n"
            response_message += "\nإيش تفضل؟"
        else:
            response_message = "I'm not sure what you're looking for 🤔 We have these categories:\n"
            for cat in categories:
                response_message += f"🔸 {cat['category_name_en']}\n"
            response_message += "\nWhat would you prefer?"

        return self.create_response(response_message)

    def execute_item_selection(self, phone_number: str, extracted_data: Dict, response_message: str,
                               session: Dict) -> Dict:
        """Execute item selection with AI understanding"""
        language = session['language_preference'] if session else 'arabic'
        selected_category_id = session.get('selected_category') if session else None

        if not selected_category_id:
            return self.create_response(
                "عذراً، حدث خطأ. من فضلك ابدأ من جديد.\nSorry, something went wrong. Please start over.")

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

            # Ask for quantity naturally
            if not response_message:
                unit = selected_item['unit']
                if language == 'arabic':
                    if unit == 'cups':
                        response_message = f"حلو! كم كوب من {selected_item['item_name_ar']} تريد؟ ☕"
                    elif unit == 'slices':
                        response_message = f"ممتاز! كم شريحة من {selected_item['item_name_ar']} تريد؟ 🍰"
                    else:
                        response_message = f"تمام! كم قطعة من {selected_item['item_name_ar']} تريد؟ 🍞"
                else:
                    response_message = f"Perfect! How many {selected_item['item_name_en']} would you like? 😊"

            return self.create_response(response_message)

        # Item not found, ask again naturally
        if language == 'arabic':
            response_message = "ما لقيت هاي! 🤔 وين بالقائمة؟ قلي الرقم أو الاسم:"
        else:
            response_message = "I couldn't find that! 🤔 Which one from the menu? Tell me the number or name:"

        return self.create_response(response_message)

    def execute_quantity_selection(self, phone_number: str, extracted_data: Dict, response_message: str,
                                   session: Dict) -> Dict:
        """Execute quantity selection with AI understanding"""
        language = session['language_preference'] if session else 'arabic'
        selected_item_id = session.get('selected_item') if session else None
        quantity = extracted_data.get('quantity')

        if not selected_item_id:
            return self.create_response(
                "عذراً، حدث خطأ. من فضلك ابدأ من جديد.\nSorry, something went wrong. Please start over.")

        if quantity and quantity > 0 and self.db.validate_step_transition(phone_number, 'waiting_for_additional'):
            # Add item to order
            success = self.db.add_item_to_order(phone_number, selected_item_id, quantity)

            if success:
                item = self.db.get_item_by_id(selected_item_id)
                self.db.create_or_update_session(phone_number, 'waiting_for_additional', language)

                # Natural confirmation
                if not response_message:
                    if language == 'arabic':
                        unit_ar = "أكواب" if item['unit'] == 'cups' else (
                            "شرائح" if item['unit'] == 'slices' else "قطع")
                        response_message = f"تمام! أضفت {quantity} {unit_ar} {item['item_name_ar']} لطلبك ✅\n\n"
                        response_message += "تريد تضيف شي ثاني؟ 😊"
                    else:
                        response_message = f"Great! Added {quantity} {item['item_name_en']} to your order ✅\n\n"
                        response_message += "Want to add anything else? 😊"

                return self.create_response(response_message)

        # Invalid quantity
        if language == 'arabic':
            response_message = "كم واحد بالضبط تريد؟ قلي رقم 🔢"
        else:
            response_message = "How many exactly would you like? Tell me a number 🔢"

        return self.create_response(response_message)

    def execute_yes_no_action(self, phone_number: str, extracted_data: Dict, response_message: str,
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
                    if language == 'arabic':
                        response_message = "ممتاز! شو كمان تريد؟\n"
                        for cat in categories:
                            response_message += f"🔸 {cat['category_name_ar']}\n"
                    else:
                        response_message = "Great! What else would you like?\n"
                        for cat in categories:
                            response_message += f"🔸 {cat['category_name_en']}\n"

                    return self.create_response(response_message)

            elif yes_no == 'no':
                if self.db.validate_step_transition(phone_number, 'waiting_for_service'):
                    self.db.create_or_update_session(phone_number, 'waiting_for_service', language)

                    if language == 'arabic':
                        response_message = "تمام! تريد تاكل هنا في المقهى أو توصيل للبيت؟ 🚀"
                    else:
                        response_message = "Perfect! Would you like to eat here at the cafe or delivery to your place? 🚀"

                    return self.create_response(response_message)

        elif current_step == 'waiting_for_confirmation':
            if yes_no == 'yes':
                # Complete order
                order_id = self.db.complete_order(phone_number)
                if order_id:
                    if language == 'arabic':
                        response_message = f"🎉 هاي! تم تأكيد طلبك!\n\n📄 رقم الطلب: {order_id}\n⏰ خلاص 10-15 دقيقة وجاهز!\n\nشكراً إلك! ☕✨"
                    else:
                        response_message = f"🎉 Awesome! Your order is confirmed!\n\n📄 Order ID: {order_id}\n⏰ Ready in 10-15 minutes!\n\nThank you! ☕✨"

                    return self.create_response(response_message)

            elif yes_no == 'no':
                # Cancel order
                with sqlite3.connect(self.db.db_path) as conn:
                    conn.execute("DELETE FROM user_orders WHERE phone_number = ?", (phone_number,))
                    conn.execute("DELETE FROM order_details WHERE phone_number = ?", (phone_number,))
                    conn.execute("DELETE FROM user_sessions WHERE phone_number = ?", (phone_number,))
                    conn.commit()

                if language == 'arabic':
                    response_message = "ماشي، ألغيت الطلب ❌\nإذا بدك تطلب شي تاني، بس اكتبلي! 😊"
                else:
                    response_message = "Okay, cancelled the order ❌\nIf you want to order something else, just message me! 😊"

                return self.create_response(response_message)

        # Default response if unclear
        return self.create_response(response_message or "هل تقصد نعم أو لا؟\nDo you mean yes or no?")

    def execute_service_selection(self, phone_number: str, extracted_data: Dict, response_message: str,
                                  session: Dict) -> Dict:
        """Execute service type selection with AI understanding"""
        language = session['language_preference'] if session else 'arabic'
        service_type = extracted_data.get('service_type')

        if service_type and self.db.validate_step_transition(phone_number, 'waiting_for_location'):
            # Update service type
            self.db.update_order_details(phone_number, service_type=service_type)
            self.db.create_or_update_session(phone_number, 'waiting_for_location', language)

            if not response_message:
                if service_type == 'dine-in':
                    if language == 'arabic':
                        response_message = "حلو! رقم الطاولة كم؟ (1-7) 🪑"
                    else:
                        response_message = "Great! What's your table number? (1-7) 🪑"
                else:  # delivery
                    if language == 'arabic':
                        response_message = "ممتاز! وين عنوانك للتوصيل؟ 📍"
                    else:
                        response_message = "Perfect! What's your address for delivery? 📍"

            return self.create_response(response_message)

        # Service type not clear
        if language == 'arabic':
            response_message = "هنا في الكافيه ولا توصيل للبيت؟ 🤔"
        else:
            response_message = "Dine-in at the cafe or delivery to your place? 🤔"

        return self.create_response(response_message)

    def execute_location_input(self, phone_number: str, extracted_data: Dict, response_message: str,
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
                    if language == 'arabic':
                        response_message = f"تمام! هاي طلبك:\n\n📋 **طلبك:**\n"
                        for item in order['items']:
                            unit_ar = "أكواب" if item['unit'] == 'cups' else (
                                "شرائح" if item['unit'] == 'slices' else "قطع")
                            response_message += f"• {item['item_name_ar']} x{item['quantity']} {unit_ar} - {item['subtotal']} دينار\n"

                        response_message += f"\n💰 **المجموع:** {order['total']} دينار\n"
                        response_message += f"📍 **مكان:** {location}\n\n"
                        response_message += "تأكد الطلب؟ ✅"
                    else:
                        response_message = f"Perfect! Here's your order:\n\n📋 **Your Order:**\n"
                        for item in order['items']:
                            response_message += f"• {item['item_name_en']} x{item['quantity']} {item['unit']} - {item['subtotal']} IQD\n"

                        response_message += f"\n💰 **Total:** {order['total']} IQD\n"
                        response_message += f"📍 **Location:** {location}\n\n"
                        response_message += "Confirm this order? ✅"

                return self.create_response(response_message)

        # Location not clear
        if language == 'arabic':
            response_message = "وين بالضبط؟ 📍"
        else:
            response_message = "Where exactly? 📍"

        return self.create_response(response_message)

    def execute_confirmation(self, phone_number: str, extracted_data: Dict, response_message: str,
                             session: Dict) -> Dict:
        """Execute order confirmation"""
        # This is handled by yes_no_action, so just return the AI response
        return self.create_response(response_message or "تأكد الطلب؟\nConfirm the order?")

    def execute_show_menu(self, phone_number: str, current_step: str, response_message: str, session: Dict) -> Dict:
        """Show menu based on current step"""
        language = session['language_preference'] if session else 'arabic'

        if current_step == 'waiting_for_category':
            # Stay at category step, show categories
            if self.db.validate_step_transition(phone_number, 'waiting_for_category'):
                categories = self.db.get_available_categories()

                if language == 'arabic':
                    response_message = "هاي قائمتنا! 📋\n\n"
                    for cat in categories:
                        response_message += f"🔸 {cat['category_name_ar']}\n"
                    response_message += "\nشو تحب تجرب؟ 😊"
                else:
                    response_message = "Here's our menu! 📋\n\n"
                    for cat in categories:
                        response_message += f"🔸 {cat['category_name_en']}\n"
                    response_message += "\nWhat would you like to try? 😊"

                return self.create_response(response_message)

        elif current_step == 'waiting_for_item' and session and session.get('selected_category'):
            # Stay at item step, show items for current category
            if self.db.validate_step_transition(phone_number, 'waiting_for_item'):
                items = self.db.get_category_items(session['selected_category'])
                categories = self.db.get_available_categories()
                current_category = next(
                    (cat for cat in categories if cat['category_id'] == session['selected_category']), None)

                if current_category:
                    if language == 'arabic':
                        response_message = f"إليك قائمة {current_category['category_name_ar']}:\n\n"
                        for i, item in enumerate(items, 1):
                            response_message += f"{i}. {item['item_name_ar']} - {item['price']} دينار\n"
                        response_message += "\nاختر اللي تحبه! 😊"
                    else:
                        response_message = f"Here's our {current_category['category_name_en']} menu:\n\n"
                        for i, item in enumerate(items, 1):
                            response_message += f"{i}. {item['item_name_en']} - {item['price']} IQD\n"
                        response_message += "\nChoose what you like! 😊"

                return self.create_response(response_message)

        # Default menu response
        return self.create_response(
            response_message or "قائمتنا جاهزة! إيش تحب تشوف؟\nOur menu is ready! What would you like to see?")

    def execute_help_request(self, phone_number: str, current_step: str, response_message: str, session: Dict) -> Dict:
        """Handle help requests based on current step"""
        language = session['language_preference'] if session else 'arabic'

        if current_step == 'waiting_for_category':
            if language == 'arabic':
                response_message = "أكيد بساعدك! 😊\nعندنا أربع أنواع رئيسية:\n🔸 مشروبات حارة (قهوة، شاي)\n🔸 مشروبات باردة (آيس كوفي)\n🔸 توست (فطار)\n🔸 كيك (حلويات)\n\nشو يهمك؟"
            else:
                response_message = "Happy to help! 😊\nWe have four main types:\n🔸 Hot drinks (coffee, tea)\n🔸 Cold drinks (iced coffee)\n🔸 Toast (breakfast)\n🔸 Cake (desserts)\n\nWhat interests you?"

        elif current_step == 'waiting_for_item':
            if language == 'arabic':
                response_message = "اختر رقم أو اسم اللي تحبه من القائمة فوق! 👆\nأو قل 'رجوع' إذا تريد تغير الفئة 😊"
            else:
                response_message = "Choose a number or name from the menu above! 👆\nOr say 'back' if you want to change category 😊"

        else:
            if language == 'arabic':
                response_message = "أنا هنا أساعدك! قلي شو تحتاج 😊"
            else:
                response_message = "I'm here to help! Tell me what you need 😊"

        return self.create_response(response_message)

    def fallback_processing(self, phone_number: str, current_step: str, user_message: str, customer_name: str) -> Dict:
        """Fallback processing when AI is unavailable"""
        if current_step == 'waiting_for_language':
            # Simple language detection
            if any(word in user_message.lower() for word in ['عربي', 'arabic', '1', 'العربية', 'مرحبا']):
                if self.db.validate_step_transition(phone_number, 'waiting_for_category'):
                    self.db.create_or_update_session(phone_number, 'waiting_for_category', 'arabic', customer_name)
                    return self.create_response(f"أهلاً {customer_name}! شو تحب تطلب؟")
            elif any(word in user_message.lower() for word in ['english', '2', 'hello', 'hi']):
                if self.db.validate_step_transition(phone_number, 'waiting_for_category'):
                    self.db.create_or_update_session(phone_number, 'waiting_for_category', 'english', customer_name)
                    return self.create_response(f"Welcome {customer_name}! What would you like to order?")

        # Generic fallback
        return self.create_response(
            "عذراً، لم أفهم. هل يمكنك إعادة المحاولة؟\n"
            "Sorry, I didn't understand. Can you try again?"
        )

    def create_response(self, text: str) -> Dict[str, Any]:
        """Create response with proper formatting"""
        # Ensure message doesn't exceed WhatsApp limits
        if len(text) > 4000:
            text = text[:3900] + "... (تم اختصار الرسالة)"

        return {
            'type': 'text',
            'content': text,
            'timestamp': datetime.datetime.now().isoformat()
        }

    def send_whatsapp_message(self, phone_number: str, response_data: Dict[str, Any]) -> bool:
        """Send response back to WhatsApp"""
        try:
            url = f"https://graph.facebook.com/v18.0/{self.config.get('phone_number_id')}/messages"
            headers = {
                'Authorization': f'Bearer {self.config.get("whatsapp_token")}',
                'Content-Type': 'application/json'
            }

            payload = {
                'messaging_product': 'whatsapp',
                'to': phone_number,
                'text': {'body': response_data['content']}
            }

            logger.info(f"📤 Sending message to {phone_number}")

            response = requests.post(url, headers=headers, json=payload)

            if response.status_code == 200:
                logger.info(f"✅ Message sent successfully")
                return True
            else:
                logger.error(f"❌ Failed to send message: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return False

        except Exception as e:
            logger.error(f"❌ Error sending WhatsApp message: {str(e)}")
            return False


# For backward compatibility - create alias
WhatsAppWorkflow = TrueAIWorkflow