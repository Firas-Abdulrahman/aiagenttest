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
                (
                "waiting_for_quantity", "waiting_for_additional,waiting_for_service", "quantity", "Quantity selection"),
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
                                 language: str = None, customer_name: str = None) -> bool:
        """Create new session or update existing one"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO user_sessions 
                    (phone_number, current_step, language_preference, customer_name, updated_at)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (phone_number, current_step, language, customer_name))

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
            # Store selected category in session (you might want to add this field)
            self.db.create_or_update_session(phone_number, 'waiting_for_item', language)

            # Get items for selected category
            items = self.db.get_category_items(selected_category['category_id'])

            # AI generates natural response showing items
            if language == 'arabic':
                prompt = f"المستخدم اختار فئة {selected_category['category_name_ar']}. اعرض العناصر المتاحة بطريقة طبيعية."
            else:
                prompt = f"User selected {selected_category['category_name_en']} category. Show available items naturally."

            response = self.ai_generate_response(prompt, context={
                'step': 'item_selection',
                'category': selected_category,
                'items': items,
                'language': language
            })

            return self.create_response(response)

        # Category not recognized, ask again with AI help
        if language == 'arabic':
            prompt = f"المستخدم لم يختر فئة صحيحة. اعرض عليه الفئات المتاحة مرة أخرى بطريقة ودودة."
        else:
            prompt = f"User didn't select a valid category. Show available categories again in a friendly way."

        response = self.ai_generate_response(prompt, context={
            'step': 'category_selection_retry',
            'categories': categories,
            'language': language
        })

        return self.create_response(response)

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

        # If OpenAI is available, use it as backup
        if self.openai_client:
            try:
                response = self.openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system",
                         "content": "User wants to select Arabic or English language. If message contains Arabic words or suggests Arabic preference, reply 'arabic'. If English preference, reply 'english'. Otherwise reply 'unknown'."},
                        {"role": "user", "content": message}
                    ],
                    max_tokens=10
                )

                result = response.choices[0].message.content.strip().lower()
                if result in ['arabic', 'english']:
                    logger.info(f"✅ AI detected language: {result}")
                    return result

            except Exception as e:
                logger.error(f"❌ AI language detection error: {e}")

        # Default to Arabic for Arabic greetings
        if any(char in message for char in 'ابتثجحخدذرزسشصضطظعغفقكلمنهوي'):
            logger.info("✅ Detected Arabic from Arabic characters")
            return 'arabic'

        logger.warning(f"❌ Could not detect language from: {message}")
        return None

    def ai_identify_category(self, message: str, categories: List[Dict]) -> Optional[Dict]:
        """AI identifies which category user selected"""
        if not self.openai_client:
            # Simple fallback
            for cat in categories:
                if (cat['category_name_ar'].lower() in message.lower() or
                        cat['category_name_en'].lower() in message.lower() or
                        str(cat['category_id']) in message):
                    return cat
            return None

        try:
            categories_text = "\n".join([
                f"{cat['category_id']}: {cat['category_name_ar']} / {cat['category_name_en']}"
                for cat in categories
            ])

            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system",
                     "content": f"User message refers to one of these categories:\n{categories_text}\n\nReply only with the category_id number, or 'none' if unclear."},
                    {"role": "user", "content": message}
                ],
                max_tokens=10
            )

            result = response.choices[0].message.content.strip()

            try:
                category_id = int(result)
                return next((cat for cat in categories if cat['category_id'] == category_id), None)
            except:
                return None

        except Exception as e:
            logger.error(f"❌ AI category identification error: {e}")
            return None

    def ai_generate_response(self, prompt: str, context: Dict) -> str:
        """Generate natural AI response based on context"""
        if not self.openai_client:
            return self.fallback_response(context)

        try:
            system_prompt = """You are a friendly AI assistant for Hef Cafe in Iraq. 
            Generate natural, conversational responses in the user's preferred language.
            Be warm, helpful, and use appropriate emojis.
            Keep responses under 4000 characters to avoid WhatsApp limits."""

            full_prompt = f"{prompt}\n\nContext: {json.dumps(context, ensure_ascii=False)}"

            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": full_prompt}
                ],
                max_tokens=800,
                temperature=0.7
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"❌ AI response generation error: {e}")
            return self.fallback_response(context)

    def fallback_response(self, context: Dict) -> str:
        """Fallback response when AI is unavailable"""
        step = context.get('step', 'unknown')
        language = context.get('language', 'arabic')

        if step == 'category_selection':
            if language == 'arabic':
                return "اختر فئة من القائمة:\n1: المشروبات الحارة ☕\n2: المشروبات الباردة 🧊\n9: توست 🍞\n11: قطع الكيك 🍰"
            else:
                return "Select a category:\n1: Hot Beverages ☕\n2: Cold Beverages 🧊\n9: Toast 🍞\n11: Cake Slices 🍰"

        return "مرحباً بك في مقهى هيف! 😊"

    def extract_customer_name(self, message_data: Dict) -> str:
        """Extract customer name from WhatsApp message data"""
        if 'contacts' in message_data:
            contacts = message_data.get('contacts', [])
            if contacts and len(contacts) > 0:
                profile = contacts[0].get('profile', {})
                return profile.get('name', 'Customer')
        return 'Customer'

    def handle_item_selection(self, phone_number: str, user_message: str) -> Dict:
        """Step 3: Item Selection - AI interprets, DB validates"""
        session = self.db.get_user_session(phone_number)
        language = session['language_preference']

        # Get the current category items (you'll need to store selected category)
        # For now, let's get all items and let AI figure it out
        categories = self.db.get_available_categories()
        all_items = []
        for cat in categories:
            items = self.db.get_category_items(cat['category_id'])
            all_items.extend(items)

        # Use AI to identify selected item
        selected_item = self.ai_identify_item(user_message, all_items)

        if selected_item and self.db.validate_step_transition(phone_number, 'waiting_for_quantity'):
            self.db.create_or_update_session(phone_number, 'waiting_for_quantity', language)

            # Store selected item temporarily (you might want to add this to session)
            # For now, we'll pass it in the AI context

            if language == 'arabic':
                prompt = f"المستخدم اختار {selected_item['item_name_ar']}. اسأله عن الكمية المطلوبة بطريقة طبيعية."
            else:
                prompt = f"User selected {selected_item['item_name_en']}. Ask for quantity naturally."

            response = self.ai_generate_response(prompt, context={
                'step': 'quantity_selection',
                'selected_item': selected_item,
                'language': language
            })

            return self.create_response(response)

        # Item not recognized
        if language == 'arabic':
            prompt = "المستخدم لم يختر عنصر صحيح. اطلب منه اختيار عنصر من القائمة بطريقة ودودة."
        else:
            prompt = "User didn't select a valid item. Ask them to choose from the menu in a friendly way."

        response = self.ai_generate_response(prompt, context={
            'step': 'item_selection_retry',
            'language': language
        })

        return self.create_response(response)

    def handle_quantity_selection(self, phone_number: str, user_message: str) -> Dict:
        """Step 4: Quantity Selection - AI extracts quantity, DB validates"""
        session = self.db.get_user_session(phone_number)
        language = session['language_preference']

        # Use AI to extract quantity
        quantity = self.ai_extract_quantity(user_message)

        if quantity and quantity > 0 and self.db.validate_step_transition(phone_number, 'waiting_for_additional'):
            # TODO: Add the item to order (you'll need to store selected item somewhere)
            # For now, simulate adding item
            # self.db.add_item_to_order(phone_number, item_id, quantity)

            self.db.create_or_update_session(phone_number, 'waiting_for_additional', language)

            if language == 'arabic':
                prompt = f"المستخدم طلب {quantity} قطعة. اسأله إذا كان يريد إضافة المزيد من العناصر."
            else:
                prompt = f"User ordered {quantity} items. Ask if they want to add more items."

            response = self.ai_generate_response(prompt, context={
                'step': 'additional_items',
                'quantity': quantity,
                'language': language
            })

            return self.create_response(response)

        # Invalid quantity
        if language == 'arabic':
            prompt = "الكمية غير صحيحة. اطلب من المستخدم إدخال رقم صحيح للكمية."
        else:
            prompt = "Invalid quantity. Ask user to enter a valid number for quantity."

        response = self.ai_generate_response(prompt, context={
            'step': 'quantity_retry',
            'language': language
        })

        return self.create_response(response)

    def handle_additional_items(self, phone_number: str, user_message: str) -> Dict:
        """Step 5: Additional Items - AI understands yes/no, DB controls flow"""
        session = self.db.get_user_session(phone_number)
        language = session['language_preference']

        # Use AI to understand if user wants more items
        wants_more = self.ai_understand_yes_no(user_message, language)

        if wants_more == 'yes':
            if self.db.validate_step_transition(phone_number, 'waiting_for_category'):
                self.db.create_or_update_session(phone_number, 'waiting_for_category', language)

                if language == 'arabic':
                    prompt = "المستخدم يريد إضافة المزيد. اعرض عليه الفئات مرة أخرى."
                else:
                    prompt = "User wants to add more items. Show categories again."

                categories = self.db.get_available_categories()
                response = self.ai_generate_response(prompt, context={
                    'step': 'category_selection',
                    'categories': categories,
                    'language': language
                })

                return self.create_response(response)

        elif wants_more == 'no':
            if self.db.validate_step_transition(phone_number, 'waiting_for_service'):
                self.db.create_or_update_session(phone_number, 'waiting_for_service', language)

                if language == 'arabic':
                    prompt = "المستخدم لا يريد إضافة المزيد. اسأله عن نوع الخدمة (تناول هنا أم توصيل)."
                else:
                    prompt = "User doesn't want more items. Ask about service type (dine-in or delivery)."

                response = self.ai_generate_response(prompt, context={
                    'step': 'service_type',
                    'language': language
                })

                return self.create_response(response)

        # Unclear response
        if language == 'arabic':
            prompt = "إجابة المستخدم غير واضحة. اسأله مرة أخرى بوضوح إذا كان يريد إضافة المزيد."
        else:
            prompt = "User response unclear. Ask again clearly if they want to add more items."

        response = self.ai_generate_response(prompt, context={
            'step': 'additional_retry',
            'language': language
        })

        return self.create_response(response)

    def handle_service_type(self, phone_number: str, user_message: str) -> Dict:
        """Step 6: Service Type Selection"""
        session = self.db.get_user_session(phone_number)
        language = session['language_preference']

        # Use AI to identify service type
        service_type = self.ai_identify_service_type(user_message, language)

        if service_type and self.db.validate_step_transition(phone_number, 'waiting_for_location'):
            self.db.update_order_details(phone_number, service_type=service_type)
            self.db.create_or_update_session(phone_number, 'waiting_for_location', language)

            if service_type == 'dine-in':
                if language == 'arabic':
                    prompt = "المستخدم اختار التناول في المطعم. اطلب منه رقم طاولته."
                else:
                    prompt = "User chose dine-in. Ask for their table number."
            else:  # delivery
                if language == 'arabic':
                    prompt = "المستخدم اختار التوصيل. اطلب منه عنوانه أو موقعه."
                else:
                    prompt = "User chose delivery. Ask for their address or location."

            response = self.ai_generate_response(prompt, context={
                'step': 'location_input',
                'service_type': service_type,
                'language': language
            })

            return self.create_response(response)

        # Service type not recognized
        if language == 'arabic':
            prompt = "نوع الخدمة غير واضح. اسأل المستخدم: تناول في المطعم أم توصيل؟"
        else:
            prompt = "Service type unclear. Ask user: dine-in or delivery?"

        response = self.ai_generate_response(prompt, context={
            'step': 'service_type_retry',
            'language': language
        })

        return self.create_response(response)

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
                prompt = "اعرض على المستخدم ملخص طلبه الكامل واطلب منه التأكيد."
            else:
                prompt = "Show user their complete order summary and ask for confirmation."

            response = self.ai_generate_response(prompt, context={
                'step': 'order_confirmation',
                'order': order,
                'location': user_message,
                'language': language
            })

            return self.create_response(response)

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
                    prompt = f"تم تأكيد الطلب برقم {order_id}. اشكر المستخدم وأعطه تفاصيل الطلب."
                else:
                    prompt = f"Order confirmed with ID {order_id}. Thank user and give order details."

                response = self.ai_generate_response(prompt, context={
                    'step': 'order_completed',
                    'order_id': order_id,
                    'language': language
                })

                return self.create_response(response)

        elif confirmed == 'no':
            # Reset to beginning
            self.db.create_or_update_session(phone_number, 'waiting_for_language')

            if language == 'arabic':
                prompt = "المستخدم ألغى الطلب. اسأله إذا كان يريد البدء من جديد."
            else:
                prompt = "User cancelled order. Ask if they want to start over."

            response = self.ai_generate_response(prompt, context={
                'step': 'order_cancelled',
                'language': language
            })

            return self.create_response(response)

        # Unclear confirmation
        if language == 'arabic':
            prompt = "إجابة المستخدم غير واضحة. اسأله مرة أخرى: هل تريد تأكيد الطلب؟"
        else:
            prompt = "User response unclear. Ask again: do you want to confirm the order?"

        response = self.ai_generate_response(prompt, context={
            'step': 'confirmation_retry',
            'language': language
        })

        return self.create_response(response)

    def ai_identify_item(self, message: str, items: List[Dict]) -> Optional[Dict]:
        """AI identifies which menu item user selected"""
        if not self.openai_client:
            # Simple fallback
            for item in items:
                if (item['item_name_ar'].lower() in message.lower() or
                        item['item_name_en'].lower() in message.lower()):
                    return item
            return None

        try:
            items_text = "\n".join([
                f"{item['id']}: {item['item_name_ar']} / {item['item_name_en']}"
                for item in items
            ])

            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system",
                     "content": f"User message refers to one of these menu items:\n{items_text}\n\nReply only with the item id number, or 'none' if unclear."},
                    {"role": "user", "content": message}
                ],
                max_tokens=10
            )

            result = response.choices[0].message.content.strip()

            try:
                item_id = int(result)
                return next((item for item in items if item['id'] == item_id), None)
            except:
                return None

        except Exception as e:
            logger.error(f"❌ AI item identification error: {e}")
            return None

    def ai_extract_quantity(self, message: str) -> Optional[int]:
        """AI extracts quantity from user message"""
        if not self.openai_client:
            # Simple fallback - look for numbers
            numbers = re.findall(r'\d+', message)
            return int(numbers[0]) if numbers else None

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system",
                     "content": "Extract the quantity/number from user message. Reply only with the number, or 'none' if unclear."},
                    {"role": "user", "content": message}
                ],
                max_tokens=10
            )

            result = response.choices[0].message.content.strip()

            try:
                return int(result)
            except:
                return None

        except Exception as e:
            logger.error(f"❌ AI quantity extraction error: {e}")
            return None

    def ai_understand_yes_no(self, message: str, language: str) -> Optional[str]:
        """AI understands yes/no responses in any language"""
        if not self.openai_client:
            # Simple fallback
            message_lower = message.lower()
            yes_words = ['yes', 'y', 'نعم', 'اي', 'طبعا', 'اكيد', '1']
            no_words = ['no', 'n', 'لا', 'كلا', 'ما اريد', '2']

            if any(word in message_lower for word in yes_words):
                return 'yes'
            elif any(word in message_lower for word in no_words):
                return 'no'
            return None

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system",
                     "content": "Determine if user message means 'yes' or 'no'. Reply only: 'yes', 'no', or 'unclear'."},
                    {"role": "user", "content": message}
                ],
                max_tokens=10
            )

            result = response.choices[0].message.content.strip().lower()
            return result if result in ['yes', 'no'] else None

        except Exception as e:
            logger.error(f"❌ AI yes/no understanding error: {e}")
            return None

    def ai_identify_service_type(self, message: str, language: str) -> Optional[str]:
        """AI identifies service type (dine-in or delivery)"""
        if not self.openai_client:
            # Simple fallback
            message_lower = message.lower()
            dine_words = ['dine', 'table', 'here', 'تناول', 'طاولة', 'هنا']
            delivery_words = ['delivery', 'deliver', 'توصيل', 'بيت', 'منزل']

            if any(word in message_lower for word in dine_words):
                return 'dine-in'
            elif any(word in message_lower for word in delivery_words):
                return 'delivery'
            return None

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system",
                     "content": "Determine if user wants 'dine-in' or 'delivery' service. Reply only: 'dine-in', 'delivery', or 'unclear'."},
                    {"role": "user", "content": message}
                ],
                max_tokens=10
            )

            result = response.choices[0].message.content.strip().lower()
            return result if result in ['dine-in', 'delivery'] else None

        except Exception as e:
            logger.error(f"❌ AI service type identification error: {e}")
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