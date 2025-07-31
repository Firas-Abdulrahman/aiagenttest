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

            # Insert step validation rules
            step_rules = [
                ("waiting_for_language", "waiting_for_category", "language_preference", "Language selection"),
                ("waiting_for_category", "waiting_for_item", "selected_category", "Category selection"),
                ("waiting_for_item", "waiting_for_quantity", "selected_item", "Item selection"),
                ("waiting_for_quantity", "waiting_for_additional", "quantity", "Quantity selection"),
                ("waiting_for_additional", "waiting_for_category,waiting_for_service", "additional_choice",
                 "Additional items choice"),
                ("waiting_for_service", "waiting_for_location", "service_type", "Service type selection"),
                ("waiting_for_location", "waiting_for_confirmation", "location", "Location/table selection"),
                ("waiting_for_confirmation", "completed,waiting_for_language", "confirmation", "Order confirmation"),
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
                                 selected_category: int = None, selected_item: int = None) -> bool:
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
                        (phone_number, current_step, language_preference, customer_name, selected_category, selected_item)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (phone_number, current_step, language, customer_name, selected_category, selected_item))

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


class SmartAIWorkflow:
    """AI-Powered WhatsApp Workflow with SQLite Control"""

    def __init__(self, config: Dict[str, str]):
        self.config = config
        self.db = CafeDatabaseManager()

        # Initialize OpenAI
        if OPENAI_AVAILABLE and config.get('openai_api_key'):
            try:
                self.openai_client = openai.OpenAI(api_key=config.get('openai_api_key'))
                logger.info("✅ OpenAI client initialized")
            except Exception as e:
                logger.error(f"⚠️ OpenAI initialization failed: {e}")
                self.openai_client = None
        else:
            self.openai_client = None

    def handle_whatsapp_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Main message handler with strict workflow control"""
        try:
            if 'text' not in message_data:
                return self.create_response("أرسل لي رسالة نصية من فضلك! 😊")

            text = message_data.get('text', {}).get('body', '').strip()
            phone_number = message_data.get('from')
            customer_name = self.extract_customer_name(message_data)

            # Log the conversation
            self.db.log_conversation(phone_number, 'user_message', text)

            # Get current session state
            session = self.db.get_user_session(phone_number)
            current_step = session['current_step'] if session else 'waiting_for_language'

            logger.info(f"📊 User {phone_number} at step: {current_step}")

            # Process based on current step (DATABASE CONTROLS THE FLOW)
            response = self.process_step(phone_number, current_step, text, customer_name)

            # Log AI response
            self.db.log_conversation(phone_number, 'ai_response', response['content'])

            return response

        except Exception as e:
            logger.error(f"❌ Error handling message: {str(e)}")
            return self.create_response("عذراً، حدث خطأ. من فضلك أعد المحاولة! 🙏")

    def extract_customer_name(self, message_data: Dict) -> str:
        """Extract customer name from WhatsApp message data"""
        if 'contacts' in message_data:
            contacts = message_data.get('contacts', [])
            if contacts and len(contacts) > 0:
                profile = contacts[0].get('profile', {})
                return profile.get('name', 'Customer')
        return 'Customer'

    def process_step(self, phone_number: str, current_step: str, user_message: str, customer_name: str) -> Dict:
        """Process user message based on current workflow step"""

        if current_step == 'waiting_for_language':
            return self.handle_language_selection(phone_number, user_message, customer_name)

        elif current_step == 'waiting_for_category':
            return self.handle_category_selection(phone_number, user_message)

        elif current_step == 'waiting_for_item':
            return self.handle_item_selection(phone_number, user_message)

        elif current_step == 'waiting_for_quantity':
            return self.handle_quantity_selection(phone_number, user_message)

        elif current_step == 'waiting_for_additional':
            return self.handle_additional_items(phone_number, user_message)

        elif current_step == 'waiting_for_service':
            return self.handle_service_type(phone_number, user_message)

        elif current_step == 'waiting_for_location':
            return self.handle_location(phone_number, user_message)

        elif current_step == 'waiting_for_confirmation':
            return self.handle_confirmation(phone_number, user_message)

        else:
            # Reset to beginning if unknown step
            self.db.create_or_update_session(phone_number, 'waiting_for_language')
            return self.handle_language_selection(phone_number, user_message, customer_name)

    def handle_language_selection(self, phone_number: str, user_message: str, customer_name: str) -> Dict:
        """Step 1: Language Selection - AI interprets, DB controls"""
        logger.info(f"🔍 Processing language selection: '{user_message}'")

        # Use AI to understand language preference
        language = self.ai_detect_language_preference(user_message)
        logger.info(f"🎯 Detected language: {language}")

        if language:
            # Database allows transition to next step
            if self.db.validate_step_transition(phone_number, 'waiting_for_category'):
                success = self.db.create_or_update_session(phone_number, 'waiting_for_category', language,
                                                           customer_name)
                logger.info(f"📊 Database update success: {success}")

                if success:
                    categories = self.db.get_available_categories()
                    logger.info(f"📋 Retrieved {len(categories)} categories")

                    if language == 'arabic':
                        response_text = f"أهلاً {customer_name}! 😊\n\nاختر فئة من قائمتنا:\n"
                        for cat in categories:
                            response_text += f"🔸 {cat['category_name_ar']}\n"
                        response_text += "\nيمكنك كتابة اسم الفئة أو رقمها 👆"
                    else:
                        response_text = f"Welcome {customer_name}! 😊\n\nSelect a category from our menu:\n"
                        for cat in categories:
                            response_text += f"🔸 {cat['category_name_en']}\n"
                        response_text += "\nYou can type the category name or number 👆"

                    return self.create_response(response_text)
                else:
                    logger.error("❌ Failed to update database session")

        # If language not detected or database update failed, ask again
        logger.warning(f"⚠️ Language detection failed for: '{user_message}'")
        return self.create_response(
            f"أهلاً {customer_name}! مرحباً بك في مقهى هيف ☕\n\n"
            f"أي لغة تفضل؟\n1️⃣ العربية\n2️⃣ English\n\n"
            f"Welcome to Hef Cafe! Which language do you prefer?"
        )

    def handle_category_selection(self, phone_number: str, user_message: str) -> Dict:
        """Step 2: Category Selection - AI interprets, DB validates"""
        session = self.db.get_user_session(phone_number)
        language = session['language_preference']

        # Get available categories from database
        categories = self.db.get_available_categories()

        # Use AI to identify selected category
        selected_category = self.ai_identify_category(user_message, categories)

        if selected_category and self.db.validate_step_transition(phone_number, 'waiting_for_item'):
            # Store selected category in session
            self.db.create_or_update_session(phone_number, 'waiting_for_item', language,
                                             selected_category=selected_category['category_id'])

            # Get items for selected category
            items = self.db.get_category_items(selected_category['category_id'])

            # Show items naturally
            if language == 'arabic':
                response_text = f"ممتاز! إليك خيارات {selected_category['category_name_ar']}:\n\n"
                for item in items:
                    response_text += f"🔸 {item['item_name_ar']} - {item['price']} دينار\n"
                response_text += "\nاختر ما تريده من القائمة أعلاه 👆"
            else:
                response_text = f"Great! Here are our {selected_category['category_name_en']} options:\n\n"
                for item in items:
                    response_text += f"🔸 {item['item_name_en']} - {item['price']} IQD\n"
                response_text += "\nChoose what you'd like from the menu above 👆"

            return self.create_response(response_text)

        # Category not recognized, ask again
        if language == 'arabic':
            response_text = "من فضلك اختر فئة من القائمة:\n"
            for cat in categories:
                response_text += f"🔸 {cat['category_name_ar']}\n"
        else:
            response_text = "Please select a category from the menu:\n"
            for cat in categories:
                response_text += f"🔸 {cat['category_name_en']}\n"

        return self.create_response(response_text)

    def handle_item_selection(self, phone_number: str, user_message: str) -> Dict:
        """Step 3: Item Selection - AI interprets, DB validates"""
        session = self.db.get_user_session(phone_number)
        language = session['language_preference']
        selected_category = session['selected_category']

        # Get items for the selected category
        items = self.db.get_category_items(selected_category)

        # Use AI to identify selected item
        selected_item = self.ai_identify_item(user_message, items)

        if selected_item and self.db.validate_step_transition(phone_number, 'waiting_for_quantity'):
            # Store selected item in session
            self.db.create_or_update_session(phone_number, 'waiting_for_quantity', language,
                                             selected_item=selected_item['id'])

            # Ask for quantity with correct unit
            unit = selected_item['unit']

            if language == 'arabic':
                if unit == 'cups':
                    question = f"كم كوب من {selected_item['item_name_ar']} تريد؟ ☕"
                elif unit == 'slices':
                    question = f"كم شريحة من {selected_item['item_name_ar']} تريد؟ 🍰"
                else:
                    question = f"كم قطعة من {selected_item['item_name_ar']} تريد؟ 🍞"
            else:
                if unit == 'cups':
                    question = f"How many cups of {selected_item['item_name_en']} would you like? ☕"
                elif unit == 'slices':
                    question = f"How many slices of {selected_item['item_name_en']} would you like? 🍰"
                else:
                    question = f"How many pieces of {selected_item['item_name_en']} would you like? 🍞"

            return self.create_response(question)

        # Item not recognized
        if language == 'arabic':
            response_text = "من فضلك اختر عنصر من القائمة أعلاه 👆"
        else:
            response_text = "Please select an item from the menu above 👆"

        return self.create_response(response_text)

    def handle_quantity_selection(self, phone_number: str, user_message: str) -> Dict:
        """Step 4: Quantity Selection - AI extracts quantity, DB validates"""
        session = self.db.get_user_session(phone_number)
        language = session['language_preference']
        selected_item_id = session['selected_item']

        # Use AI to extract quantity (with Arabic numeral support)
        quantity = self.ai_extract_quantity(user_message)

        if quantity and quantity > 0 and self.db.validate_step_transition(phone_number, 'waiting_for_additional'):
            # Add item to order
            success = self.db.add_item_to_order(phone_number, selected_item_id, quantity)

            if success:
                # Get item details for confirmation
                item = self.db.get_item_by_id(selected_item_id)

                self.db.create_or_update_session(phone_number, 'waiting_for_additional', language)

                if language == 'arabic':
                    unit_ar = "أكواب" if item['unit'] == 'cups' else ("شرائح" if item['unit'] == 'slices' else "قطع")
                    response_text = f"ممتاز! أضفت {quantity} {unit_ar} من {item['item_name_ar']} إلى طلبك ✅\n\n"
                    response_text += "هل تريد إضافة المزيد من العناصر؟\n"
                    response_text += "🔸 نعم - لإضافة المزيد\n"
                    response_text += "🔸 لا - للانتقال للخطوة التالية"
                else:
                    response_text = f"Great! Added {quantity} {item['unit']} of {item['item_name_en']} to your order ✅\n\n"
                    response_text += "Would you like to add more items?\n"
                    response_text += "🔸 Yes - to add more\n"
                    response_text += "🔸 No - to proceed"

                return self.create_response(response_text)

        # Invalid quantity
        if language == 'arabic':
            response_text = "من فضلك أدخل كمية صحيحة (رقم أكبر من صفر) 🔢\n"
            response_text += "يمكنك استخدام الأرقام العربية أو الإنكليزية"
        else:
            response_text = "Please enter a valid quantity (number greater than zero) 🔢"

        return self.create_response(response_text)

    def handle_additional_items(self, phone_number: str, user_message: str) -> Dict:
        """Step 5: Additional Items - AI understands yes/no, DB controls flow"""
        session = self.db.get_user_session(phone_number)
        language = session['language_preference']

        # Use AI to understand if user wants more items
        wants_more = self.ai_understand_yes_no(user_message, language)

        if wants_more == 'yes':
            if self.db.validate_step_transition(phone_number, 'waiting_for_category'):
                self.db.create_or_update_session(phone_number, 'waiting_for_category', language)

                categories = self.db.get_available_categories()

                if language == 'arabic':
                    response_text = "ممتاز! اختر فئة أخرى:\n\n"
                    for cat in categories:
                        response_text += f"🔸 {cat['category_name_ar']}\n"
                else:
                    response_text = "Great! Select another category:\n\n"
                    for cat in categories:
                        response_text += f"🔸 {cat['category_name_en']}\n"

                return self.create_response(response_text)

        elif wants_more == 'no':
            if self.db.validate_step_transition(phone_number, 'waiting_for_service'):
                self.db.create_or_update_session(phone_number, 'waiting_for_service', language)

                if language == 'arabic':
                    response_text = "ممتاز! الآن دعنا نرتب التوصيل 🚀\n\n"
                    response_text += "كيف تريد استلام طلبك؟\n"
                    response_text += "🔸 في المقهى (للتناول داخل المقهى)\n"
                    response_text += "🔸 توصيل (للتوصيل إلى منزلك)"
                else:
                    response_text = "Great! Now let's arrange delivery 🚀\n\n"
                    response_text += "How would you like to receive your order?\n"
                    response_text += "🔸 Dine-in (eat at the cafe)\n"
                    response_text += "🔸 Delivery (deliver to your home)"

                return self.create_response(response_text)

        # Unclear response
        if language == 'arabic':
            response_text = "من فضلك أجب بـ 'نعم' أو 'لا':\n"
            response_text += "🔸 نعم - لإضافة المزيد من العناصر\n"
            response_text += "🔸 لا - للانتقال للخطوة التالية"
        else:
            response_text = "Please answer with 'Yes' or 'No':\n"
            response_text += "🔸 Yes - to add more items\n"
            response_text += "🔸 No - to proceed to next step"

        return self.create_response(response_text)

    def handle_service_type(self, phone_number: str, user_message: str) -> Dict:
        """Step 6: Service Type Selection - Fixed to prevent loops"""
        session = self.db.get_user_session(phone_number)
        language = session['language_preference']

        logger.info(f"🍽️ Processing service type selection: '{user_message}'")

        # Use AI to identify service type
        service_type = self.ai_identify_service_type(user_message, language)
        logger.info(f"🎯 Detected service type: {service_type}")

        if service_type and self.db.validate_step_transition(phone_number, 'waiting_for_location'):
            # Update database with service type
            success = self.db.update_order_details(phone_number, service_type=service_type)
            logger.info(f"📊 Database update success: {success}")

            # Move to next step
            self.db.create_or_update_session(phone_number, 'waiting_for_location', language)

            if service_type == 'dine-in':
                if language == 'arabic':
                    response_text = "ممتاز! تناول في المقهى 🪑\n\n"
                    response_text += "من فضلك أخبرني برقم طaولتك (1-7) 📍"
                else:
                    response_text = "Great! Dine-in service 🪑\n\n"
                    response_text += "Please tell me your table number (1-7) 📍"
            else:  # delivery
                if language == 'arabic':
                    response_text = "ممتاز! خدمة التوصيل 🚗\n\n"
                    response_text += "من فضلك أرسل عنوانك أو موقعك للتوصيل 📍"
                else:
                    response_text = "Great! Delivery service 🚗\n\n"
                    response_text += "Please send your address or location for delivery 📍"

            return self.create_response(response_text)

        # Service type not recognized - ask clearly
        logger.warning(f"⚠️ Service type not recognized from: '{user_message}'")

        if language == 'arabic':
            response_text = "من فضلك اختر نوع الخدمة:\n\n"
            response_text += "🔸 في المقهى (للتناول داخل المقهى)\n"
            response_text += "🔸 توصيل (للتوصيل إلى منزلك)\n\n"
            response_text += "يمكنك كتابة: 'في المقهى' أو 'توصيل'"
        else:
            response_text = "Please choose your service type:\n\n"
            response_text += "🔸 Dine-in (eat at the cafe)\n"
            response_text += "🔸 Delivery (deliver to your home)\n\n"
            response_text += "You can type: 'dine-in' or 'delivery'"

        return self.create_response(response_text)

    def handle_location(self, phone_number: str, user_message: str) -> Dict:
        """Step 7: Location/Table Input"""
        session = self.db.get_user_session(phone_number)
        language = session['language_preference']

        # Store location
        self.db.update_order_details(phone_number, location=user_message)

        if self.db.validate_step_transition(phone_number, 'waiting_for_confirmation'):
            self.db.create_or_update_session(phone_number, 'waiting_for_confirmation', language)

            # Get complete order for confirmation
            order = self.db.get_user_order(phone_number)

            if language == 'arabic':
                response_text = "ممتاز! إليك ملخص طلبك:\n\n"
                response_text += "📋 **طلبك:**\n"
                for item in order['items']:
                    unit_ar = "أكواب" if item['unit'] == 'cups' else ("شرائح" if item['unit'] == 'slices' else "قطع")
                    response_text += f"• {item['item_name_ar']} x{item['quantity']} {unit_ar} - {item['subtotal']} دينار\n"

                response_text += f"\n💰 **المجموع:** {order['total']} دينار عراقي\n"
                response_text += f"📍 **الخدمة:** {order['details'].get('service_type', '')}\n"
                response_text += f"🏠 **الموقع:** {user_message}\n\n"
                response_text += "هل تريد تأكيد هذا الطلب؟\n"
                response_text += "🔸 نعم - لتأكيد الطلب\n"
                response_text += "🔸 لا - لإلغاء الطلب"
            else:
                response_text = "Perfect! Here's your order summary:\n\n"
                response_text += "📋 **Your Order:**\n"
                for item in order['items']:
                    response_text += f"• {item['item_name_en']} x{item['quantity']} {item['unit']} - {item['subtotal']} IQD\n"

                response_text += f"\n💰 **Total:** {order['total']} IQD\n"
                response_text += f"📍 **Service:** {order['details'].get('service_type', '')}\n"
                response_text += f"🏠 **Location:** {user_message}\n\n"
                response_text += "Would you like to confirm this order?\n"
                response_text += "🔸 Yes - to confirm order\n"
                response_text += "🔸 No - to cancel order"

            return self.create_response(response_text)

        # This shouldn't happen with proper validation
        return self.create_response("حدث خطأ. من فضلك أعد المحاولة.")

    def handle_confirmation(self, phone_number: str, user_message: str) -> Dict:
        """Step 8: Final Order Confirmation"""
        session = self.db.get_user_session(phone_number)
        language = session['language_preference']

        # Use AI to understand confirmation
        confirmed = self.ai_understand_yes_no(user_message, language)

        if confirmed == 'yes':
            # Complete the order
            order_id = self.db.complete_order(phone_number)

            if order_id:
                if language == 'arabic':
                    response_text = f"🎉 **تم تأكيد طلبك بنجاح!**\n\n"
                    response_text += f"📄 **رقم الطلب:** {order_id}\n"
                    response_text += f"⏰ **الوقت المتوقع:** 10-15 دقيقة\n\n"
                    response_text += "شكراً لاختيارك مقهى هيف! ☕\n"
                    response_text += "سنقوم بإشعارك عندما يكون طلبك جاهزاً 🔔"
                else:
                    response_text = f"🎉 **Order Confirmed Successfully!**\n\n"
                    response_text += f"📄 **Order ID:** {order_id}\n"
                    response_text += f"⏰ **Estimated Time:** 10-15 minutes\n\n"
                    response_text += "Thank you for choosing Hef Cafe! ☕\n"
                    response_text += "We'll notify you when your order is ready 🔔"

                return self.create_response(response_text)

        elif confirmed == 'no':
            # Clear order and reset
            with sqlite3.connect(self.db.db_path) as conn:
                conn.execute("DELETE FROM user_orders WHERE phone_number = ?", (phone_number,))
                conn.execute("DELETE FROM order_details WHERE phone_number = ?", (phone_number,))
                conn.execute("DELETE FROM user_sessions WHERE phone_number = ?", (phone_number,))
                conn.commit()

            if language == 'arabic':
                response_text = "تم إلغاء طلبك ❌\n\n"
                response_text += "هل تريد البدء من جديد؟\n"
                response_text += "أرسل أي رسالة للبدء مرة أخرى 😊"
            else:
                response_text = "Your order has been cancelled ❌\n\n"
                response_text += "Would you like to start over?\n"
                response_text += "Send any message to start again 😊"

            return self.create_response(response_text)

        # Unclear confirmation
        if language == 'arabic':
            response_text = "من فضلك أجب بوضوح:\n"
            response_text += "🔸 نعم - لتأكيد الطلب\n"
            response_text += "🔸 لا - لإلغاء الطلب"
        else:
            response_text = "Please answer clearly:\n"
            response_text += "🔸 Yes - to confirm order\n"
            response_text += "🔸 No - to cancel order"

        return self.create_response(response_text)

    # AI Helper Methods
    def ai_detect_language_preference(self, message: str) -> Optional[str]:
        """AI detects language preference from user message"""
        message_lower = message.lower().strip()

        # Enhanced pattern matching for Arabic
        arabic_patterns = [
            'عربي', 'العربية', 'عربية', 'arabic', '1',
            'مرحبا', 'السلام', 'اهلا', 'أهلا'
        ]

        english_patterns = [
            'english', 'انكليزي', 'إنكليزي', '2',
            'hello', 'hi', 'hey'
        ]

        # Check for Arabic patterns
        for pattern in arabic_patterns:
            if pattern in message_lower:
                logger.info(f"✅ Detected Arabic from pattern: {pattern}")
                return 'arabic'

        # Check for English patterns
        for pattern in english_patterns:
            if pattern in message_lower:
                logger.info(f"✅ Detected English from pattern: {pattern}")
                return 'english'

        # Default to Arabic for Arabic characters
        if any(char in message for char in 'ابتثجحخدذرزسشصضطظعغفقكلمنهوي'):
            logger.info("✅ Detected Arabic from Arabic characters")
            return 'arabic'

        logger.warning(f"❌ Could not detect language from: {message}")
        return None

    def ai_identify_category(self, message: str, categories: List[Dict]) -> Optional[Dict]:
        """AI identifies which category user selected"""
        message_lower = message.lower().strip()

        # Direct matching with typo tolerance
        for cat in categories:
            # Check category ID
            if str(cat['category_id']) in message:
                return cat

            # Check Arabic name (with basic typo tolerance)
            ar_name = cat['category_name_ar'].lower()
            if ar_name in message_lower:
                return cat

            # Check English name
            en_name = cat['category_name_en'].lower()
            if en_name in message_lower:
                return cat

            # Partial matching for common variations
            if 'مشروبات' in message_lower and 'حارة' in message_lower and cat['category_id'] == 1:
                return cat
            if 'مشروبات' in message_lower and 'باردة' in message_lower and cat['category_id'] == 2:
                return cat
            if ('توست' in message_lower or 'toast' in message_lower) and cat['category_id'] == 9:
                return cat
            if ('كيك' in message_lower or 'cake' in message_lower) and cat['category_id'] == 11:
                return cat

        return None

    def ai_identify_item(self, message: str, items: List[Dict]) -> Optional[Dict]:
        """AI identifies which menu item user selected"""
        message_lower = message.lower().strip()

        for item in items:
            # Check Arabic name
            if item['item_name_ar'].lower() in message_lower:
                return item
            # Check English name
            if item['item_name_en'].lower() in message_lower:
                return item
            # Check partial matches for common items
            if 'اسبريسو' in message_lower and 'اسبريسو' in item['item_name_ar']:
                return item
            if 'كابتشينو' in message_lower and 'كابتشينو' in item['item_name_ar']:
                return item

        return None

    def ai_extract_quantity(self, message: str) -> Optional[int]:
        """AI extracts quantity from user message with Arabic numeral support"""
        # First, normalize Arabic numerals to Western
        arabic_to_western = {
            '٠': '0', '١': '1', '٢': '2', '٣': '3', '٤': '4',
            '٥': '5', '٦': '6', '٧': '7', '٨': '8', '٩': '9'
        }

        normalized_message = message
        for arabic, western in arabic_to_western.items():
            normalized_message = normalized_message.replace(arabic, western)

        logger.info(f"🔢 Extracting quantity from: '{message}' (normalized: '{normalized_message}')")

        # Look for numbers in normalized message
        numbers = re.findall(r'\d+', normalized_message)
        if numbers:
            quantity = int(numbers[0])
            logger.info(f"✅ Found quantity: {quantity}")
            return quantity

        logger.warning(f"❌ Could not extract quantity from: '{message}'")
        return None

    def ai_understand_yes_no(self, message: str, language: str) -> Optional[str]:
        """AI understands yes/no responses in any language"""
        message_lower = message.lower().strip()
        yes_words = ['yes', 'y', 'نعم', 'اي', 'طبعا', 'اكيد', '1', 'اه', 'ايوه']
        no_words = ['no', 'n', 'لا', 'كلا', 'ما اريد', '2', 'لأ']

        if any(word in message_lower for word in yes_words):
            return 'yes'
        elif any(word in message_lower for word in no_words):
            return 'no'
        return None

    def ai_identify_service_type(self, message: str, language: str) -> Optional[str]:
        """AI identifies service type (dine-in or delivery) with better Arabic support"""
        message_lower = message.lower().strip()

        # Enhanced patterns for Arabic dine-in
        dine_patterns = [
            'dine', 'table', 'here', 'تناول', 'طاولة', 'هنا',
            'في المقهى', 'بالمقهى', 'داخل', 'مقهى', 'cafe',
            'sit', 'stay', 'inside', 'المطعم', 'بالمطعم', 'في المطعم'
        ]

        # Enhanced patterns for delivery
        delivery_patterns = [
            'delivery', 'deliver', 'توصيل', 'بيت', 'منزل',
            'home', 'house', 'address', 'location'
        ]

        logger.info(f"🔍 Analyzing service type from: '{message}'")

        # Check for dine-in patterns
        for pattern in dine_patterns:
            if pattern in message_lower:
                logger.info(f"✅ Detected dine-in from pattern: {pattern}")
                return 'dine-in'

        # Check for delivery patterns
        for pattern in delivery_patterns:
            if pattern in message_lower:
                logger.info(f"✅ Detected delivery from pattern: {pattern}")
                return 'delivery'

        logger.warning(f"❌ Could not detect service type from: '{message}'")
        return None

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
WhatsAppWorkflow = SmartAIWorkflow