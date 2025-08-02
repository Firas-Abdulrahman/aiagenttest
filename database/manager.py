import sqlite3
import json
import logging
from typing import Dict, List, Optional
from .models import DatabaseSchema, UserSession, MenuItem, UserOrder, OrderDetails

logger = logging.getLogger(__name__)


class DatabaseManager:
    """SQLite Database Manager for Cafe Workflow Control"""

    def __init__(self, db_path: str = "hef_cafe.db"):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Initialize SQLite database with all required tables"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")

            # Create all tables
            table_definitions = DatabaseSchema.get_table_definitions()
            for table_name, sql in table_definitions.items():
                conn.execute(sql)
                logger.info(f"✅ Created/verified table: {table_name}")

            # Populate initial data
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
            menu_data = DatabaseSchema.get_initial_menu_data()
            conn.executemany("""
                INSERT INTO menu_items 
                (category_id, category_name_ar, category_name_en, item_name_ar, item_name_en, price, unit)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, menu_data)

            # Insert step validation rules
            step_rules = DatabaseSchema.get_initial_step_rules()
            conn.executemany("""
                INSERT OR REPLACE INTO step_rules 
                (current_step, allowed_next_steps, required_data, description)
                VALUES (?, ?, ?, ?)
            """, step_rules)

            conn.commit()
            logger.info("✅ Initial data populated")

    # User Session Operations
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
                # Check if session exists
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
                        (phone_number, current_step, language_preference, customer_name, 
                         selected_category, selected_item, conversation_context)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (phone_number, current_step, language, customer_name,
                          selected_category, selected_item, conversation_context))

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

    def delete_session(self, phone_number: str) -> bool:
        """Delete user session and related data"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM user_orders WHERE phone_number = ?", (phone_number,))
                conn.execute("DELETE FROM order_details WHERE phone_number = ?", (phone_number,))
                conn.execute("DELETE FROM user_sessions WHERE phone_number = ?", (phone_number,))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"❌ Error deleting session: {e}")
            return False

    # Step Validation Operations
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

    # Menu Operations
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

    # Order Operations
    def add_item_to_order(self, phone_number: str, menu_item_id: int, quantity: int,
                          special_requests: str = None) -> bool:
        """Add item to user's current order"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Get item price
                cursor = conn.execute("SELECT price FROM menu_items WHERE id = ?", (menu_item_id,))
                price_row = cursor.fetchone()
                if not price_row:
                    logger.error(f"❌ Item {menu_item_id} not found")
                    return False

                price = price_row[0]
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
                self.delete_session(phone_number)

                conn.commit()
                return order_id
        except Exception as e:
            logger.error(f"❌ Error completing order: {e}")
            return None

    # Conversation Logging
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

    # Analytics and Reporting
    def get_order_history(self, phone_number: str = None, limit: int = 50) -> List[Dict]:
        """Get order history"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            if phone_number:
                cursor = conn.execute("""
                    SELECT * FROM completed_orders 
                    WHERE phone_number = ?
                    ORDER BY completed_at DESC
                    LIMIT ?
                """, (phone_number, limit))
            else:
                cursor = conn.execute("""
                    SELECT * FROM completed_orders 
                    ORDER BY completed_at DESC
                    LIMIT ?
                """, (limit,))

            return [dict(row) for row in cursor.fetchall()]

    def get_conversation_history(self, phone_number: str, limit: int = 100) -> List[Dict]:
        """Get conversation history for a user"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM conversation_log 
                WHERE phone_number = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (phone_number, limit))

            return [dict(row) for row in cursor.fetchall()]

    def get_popular_items(self, limit: int = 10) -> List[Dict]:
        """Get most popular menu items"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT 
                    co.items_json,
                    COUNT(*) as order_count,
                    SUM(co.total_amount) as total_revenue
                FROM completed_orders co
                GROUP BY co.items_json
                ORDER BY order_count DESC
                LIMIT ?
            """, (limit,))

            return [dict(row) for row in cursor.fetchall()]

    # Database Maintenance
    def cleanup_old_sessions(self, days_old: int = 7) -> int:
        """Clean up old user sessions"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    DELETE FROM user_sessions 
                    WHERE created_at < datetime('now', '-{} days')
                """.format(days_old))

                deleted_count = cursor.rowcount
                conn.commit()

                logger.info(f"🧹 Cleaned up {deleted_count} old sessions")
                return deleted_count
        except Exception as e:
            logger.error(f"❌ Error cleaning up sessions: {e}")
            return 0

    def get_database_stats(self) -> Dict:
        """Get database statistics"""
        with sqlite3.connect(self.db_path) as conn:
            stats = {}

            # Count records in each table
            tables = ['user_sessions', 'menu_items', 'user_orders', 'order_details',
                      'conversation_log', 'completed_orders', 'step_rules']

            for table in tables:
                cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
                stats[f"{table}_count"] = cursor.fetchone()[0]

            # Additional stats
            cursor = conn.execute("SELECT COUNT(DISTINCT phone_number) FROM user_sessions")
            stats['active_users'] = cursor.fetchone()[0]

            cursor = conn.execute("SELECT SUM(total_amount) FROM completed_orders")
            total_revenue = cursor.fetchone()[0]
            stats['total_revenue'] = total_revenue or 0

            return stats