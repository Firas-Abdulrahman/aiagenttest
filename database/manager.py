import sqlite3
import json
import logging
from typing import Dict, List, Optional
from .models import DatabaseSchema, UserSession, MenuItem, UserOrder, OrderDetails

logger = logging.getLogger(__name__)


class DatabaseManager:
    """SQLite Database Manager for Cafe Workflow Control"""

    def get_available_categories(self) -> List[Dict]:
        """Get main categories for compatibility with old code"""
        try:
            with sqlite3.connect(self.db_path, timeout=30.0) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT id as category_id, name_ar as category_name_ar, name_en as category_name_en
                    FROM main_categories 
                    WHERE available = 1
                    ORDER BY display_order
                """)
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"❌ Error getting available categories: {e}")
            return []

    def get_category_items(self, main_category_id: int) -> List[Dict]:
        """Get all items for a main category (all sub-categories combined)"""
        try:
            with sqlite3.connect(self.db_path, timeout=30.0) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT mi.id, mi.sub_category_id, mi.main_category_id, 
                           mi.item_name_ar, mi.item_name_en, mi.price, mi.unit, mi.available,
                           sc.name_ar as sub_category_name_ar, sc.name_en as sub_category_name_en
                    FROM menu_items mi
                    JOIN sub_categories sc ON mi.sub_category_id = sc.id
                    WHERE mi.main_category_id = ? AND mi.available = 1
                    ORDER BY sc.display_order, mi.item_name_ar
                """, (main_category_id,))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"❌ Error getting category items: {e}")
            return []

    def get_simplified_workflow_data(self, main_category_id: int = None):
        """Get simplified data for the workflow"""
        try:
            # If no category specified, return main categories
            if not main_category_id:
                return {
                    'type': 'main_categories',
                    'data': self.get_main_categories()
                }

            # Return sub-categories for the main category
            sub_categories = self.get_sub_categories(main_category_id)

            # If only one sub-category, return items directly
            if len(sub_categories) == 1:
                items = self.get_sub_category_items(sub_categories[0]['id'])
                return {
                    'type': 'items',
                    'sub_category': sub_categories[0],
                    'data': items
                }

            # Multiple sub-categories, return them
            return {
                'type': 'sub_categories',
                'main_category_id': main_category_id,
                'data': sub_categories
            }

        except Exception as e:
            logger.error(f"❌ Error getting simplified workflow data: {e}")
            return {'type': 'error', 'data': []}

    def __init__(self, db_path: str = "hef_cafe.db"):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Initialize SQLite database with all required tables"""
        with sqlite3.connect(self.db_path, timeout=60.0) as conn:
            # Configure database for better concurrency
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA cache_size=10000")
            conn.execute("PRAGMA temp_store=MEMORY")
            conn.execute("PRAGMA mmap_size=268435456")  # 256MB
            conn.execute("PRAGMA foreign_keys = ON")

            # Check if we need to migrate from old schema
            try:
                # Try to access the old category_id column
                conn.execute("SELECT category_id FROM menu_items LIMIT 1")
                logger.info("🔄 Detected old schema, migrating to new structure...")
                self._migrate_old_schema(conn)
            except sqlite3.OperationalError:
                # New schema, create tables normally
                logger.info("✅ Using new schema, creating tables...")
                table_definitions = DatabaseSchema.get_table_definitions()
                for table_name, sql in table_definitions.items():
                    conn.execute(sql)
                    logger.info(f" Created/verified table: {table_name}")

            # Populate initial data
            self.populate_initial_data()

        logger.info("✅ Database initialized successfully")

    def _migrate_old_schema(self, conn):
        """Migrate from old schema to new schema"""
        try:
            # Backup old data
            old_menu_items = conn.execute("SELECT * FROM menu_items").fetchall()
            old_user_sessions = conn.execute("SELECT * FROM user_sessions").fetchall()
            
            # Drop old tables
            conn.execute("DROP TABLE IF EXISTS menu_items")
            conn.execute("DROP TABLE IF EXISTS user_sessions")
            
            # Create new tables
            table_definitions = DatabaseSchema.get_table_definitions()
            for table_name, sql in table_definitions.items():
                conn.execute(sql)
                logger.info(f" Created new table: {table_name}")
            
            # Populate with new data structure
            self.populate_initial_data()
            
            logger.info("✅ Schema migration completed successfully")
            
        except Exception as e:
            logger.error(f"❌ Error during schema migration: {e}")
            # If migration fails, recreate database from scratch
            conn.execute("DROP TABLE IF EXISTS menu_items")
            conn.execute("DROP TABLE IF EXISTS user_sessions")
            conn.execute("DROP TABLE IF EXISTS main_categories")
            conn.execute("DROP TABLE IF EXISTS sub_categories")
            
            # Create tables fresh
            table_definitions = DatabaseSchema.get_table_definitions()
            for table_name, sql in table_definitions.items():
                conn.execute(sql)
                logger.info(f" Created fresh table: {table_name}")
            
            # Populate data
            self.populate_initial_data()

    def populate_initial_data(self):
        """Populate database with initial data"""
        try:
            with sqlite3.connect(self.db_path, timeout=30.0) as conn:
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA busy_timeout=30000")
                
                # Check if data already exists
                main_categories_count = conn.execute("SELECT COUNT(*) FROM main_categories").fetchone()[0]
                if main_categories_count == 0:
                    # Insert main categories
                    main_categories = DatabaseSchema.get_initial_menu_data()
                    for category in main_categories:
                        conn.execute("""
                            INSERT INTO main_categories (id, name_ar, name_en, display_order)
                            VALUES (?, ?, ?, ?)
                        """, category)
                    
                    # Insert sub categories
                    sub_categories = DatabaseSchema.get_initial_sub_categories()
                    for sub_category in sub_categories:
                        conn.execute("""
                            INSERT INTO sub_categories (id, main_category_id, name_ar, name_en, display_order)
                            VALUES (?, ?, ?, ?, ?)
                        """, sub_category)
                    
                    # Insert menu items
                    menu_items = DatabaseSchema.get_initial_items()
                    for item in menu_items:
                        conn.execute("""
                            INSERT INTO menu_items (id, sub_category_id, main_category_id, item_name_ar, item_name_en, price, unit)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, item)
                    
                    # Insert step validation rules
                    step_rules = DatabaseSchema.get_initial_step_rules()
                    for rule in step_rules:
                        conn.execute("""
                            INSERT OR REPLACE INTO step_rules 
                            (current_step, allowed_next_steps, required_data, description)
                            VALUES (?, ?, ?, ?)
                        """, rule)
                    
                    conn.commit()
                    logger.info("✅ Initial data populated successfully")
                else:
                    logger.info("✅ Data already exists, skipping population")

        except Exception as e:
            logger.error(f"❌ Error populating initial data: {e}")

    # User Session Operations
    def get_user_session(self, phone_number: str) -> Optional[Dict]:
        """Get user session with new structure"""
        try:
            with sqlite3.connect(self.db_path, timeout=30.0) as conn:
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA busy_timeout=30000")
                
                cursor = conn.execute("""
                    SELECT phone_number, current_step, language_preference, customer_name,
                           selected_main_category, selected_sub_category, selected_item,
                           conversation_context, created_at, updated_at
                    FROM user_sessions 
                    WHERE phone_number = ?
                """, (phone_number,))
                
                row = cursor.fetchone()
                if row:
                    return {
                        'phone_number': row[0],
                        'current_step': row[1],
                        'language_preference': row[2],
                        'customer_name': row[3],
                        'selected_main_category': row[4],
                        'selected_sub_category': row[5],
                        'selected_item': row[6],
                        'conversation_context': row[7],
                        'created_at': row[8],
                        'updated_at': row[9]
                    }
                return None
                
        except Exception as e:
            logger.error(f"❌ Error getting user session: {e}")
            return None

    def create_or_update_session(self, phone_number: str, current_step: str, language: str = None, 
                                customer_name: str = None, selected_main_category: int = None, 
                                selected_sub_category: int = None, selected_item: int = None) -> bool:
        """Create or update user session with new structure"""
        try:
            with sqlite3.connect(self.db_path, timeout=30.0) as conn:
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA busy_timeout=30000")
                
                # Check if session exists
                cursor = conn.execute("SELECT phone_number FROM user_sessions WHERE phone_number = ?", (phone_number,))
                existing_session = cursor.fetchone()
                
                if existing_session:
                    # Update existing session
                    conn.execute("""
                        UPDATE user_sessions 
                        SET current_step = ?, 
                            language_preference = COALESCE(?, language_preference),
                            customer_name = COALESCE(?, customer_name),
                            selected_main_category = COALESCE(?, selected_main_category),
                            selected_sub_category = COALESCE(?, selected_sub_category),
                            selected_item = COALESCE(?, selected_item),
                            updated_at = CURRENT_TIMESTAMP
                        WHERE phone_number = ?
                    """, (current_step, language, customer_name, selected_main_category, 
                         selected_sub_category, selected_item, phone_number))
                else:
                    # Create new session
                    conn.execute("""
                        INSERT INTO user_sessions 
                        (phone_number, current_step, language_preference, customer_name, 
                         selected_main_category, selected_sub_category, selected_item)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (phone_number, current_step, language, customer_name, 
                         selected_main_category, selected_sub_category, selected_item))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"❌ Error creating/updating session: {e}")
            return False

    def delete_session(self, phone_number: str) -> bool:
        """Delete user session and related data with better error handling"""
        try:
            with sqlite3.connect(self.db_path, timeout=30.0) as conn:
                # Enable WAL mode for better concurrency
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA busy_timeout=30000")
                conn.execute("PRAGMA synchronous=NORMAL")
                
                # Use a single transaction for all deletions
                conn.execute("BEGIN TRANSACTION")
                try:
                    conn.execute("DELETE FROM user_orders WHERE phone_number = ?", (phone_number,))
                    conn.execute("DELETE FROM order_details WHERE phone_number = ?", (phone_number,))
                    conn.execute("DELETE FROM user_sessions WHERE phone_number = ?", (phone_number,))
                    conn.commit()
                    return True
                except Exception as e:
                    conn.rollback()
                    raise e
                    
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e):
                logger.warning(f"⚠️ Database locked, retrying delete session for {phone_number}")
                # Retry once after a short delay
                import time
                time.sleep(1)
                try:
                    with sqlite3.connect(self.db_path, timeout=60.0) as conn:
                        conn.execute("PRAGMA journal_mode=WAL")
                        conn.execute("PRAGMA busy_timeout=60000")
                        conn.execute("PRAGMA synchronous=NORMAL")
                        
                        # Use a single transaction for all deletions
                        conn.execute("BEGIN TRANSACTION")
                        try:
                            conn.execute("DELETE FROM user_orders WHERE phone_number = ?", (phone_number,))
                            conn.execute("DELETE FROM order_details WHERE phone_number = ?", (phone_number,))
                            conn.execute("DELETE FROM user_sessions WHERE phone_number = ?", (phone_number,))
                            conn.commit()
                            return True
                        except Exception as e:
                            conn.rollback()
                            raise e
                except Exception as retry_error:
                    logger.error(f"❌ Retry failed for delete session: {retry_error}")
                    return False
            else:
                logger.error(f"❌ Database error deleting session: {e}")
                return False
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
        """Get menu item by ID with new structure"""
        try:
            with sqlite3.connect(self.db_path, timeout=30.0) as conn:
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA busy_timeout=30000")
                
                cursor = conn.execute("""
                    SELECT id, sub_category_id, main_category_id, item_name_ar, item_name_en, price, unit, available
                    FROM menu_items 
                    WHERE id = ? AND available = 1
                """, (item_id,))
                
                row = cursor.fetchone()
                if row:
                    return {
                        'id': row[0],
                        'sub_category_id': row[1],
                        'main_category_id': row[2],
                        'item_name_ar': row[3],
                        'item_name_en': row[4],
                        'price': row[5],
                        'unit': row[6],
                        'available': bool(row[7])
                    }
                return None
                
        except Exception as e:
            logger.error(f"❌ Error getting item by ID: {e}")
            return None

    # Order Operations
    def add_item_to_order(self, phone_number: str, item_id: int, quantity: int, special_requests: str = None) -> bool:
        """Add item to user's order with new structure"""
        try:
            with sqlite3.connect(self.db_path, timeout=30.0) as conn:
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA busy_timeout=30000")
                
                # Get item price
                cursor = conn.execute("SELECT price FROM menu_items WHERE id = ? AND available = 1", (item_id,))
                item = cursor.fetchone()
                
                if not item:
                    logger.error(f"❌ Item {item_id} not found or not available")
                    return False
                
                price = item[0]
                subtotal = price * quantity
                
                # Add item to order
                conn.execute("""
                    INSERT INTO user_orders (phone_number, menu_item_id, quantity, subtotal, special_requests)
                    VALUES (?, ?, ?, ?, ?)
                """, (phone_number, item_id, quantity, subtotal, special_requests))
                
                # Create order details record if doesn't exist
                conn.execute("""
                    INSERT OR IGNORE INTO order_details (phone_number)
                    VALUES (?)
                """, (phone_number,))
                
                conn.commit()
                logger.info(f"✅ Added item {item_id} × {quantity} to order for {phone_number}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Error adding item to order: {e}")
            return False

    def get_user_order(self, phone_number: str) -> Optional[Dict]:
        """Get user's current order with new menu structure"""
        try:
            with sqlite3.connect(self.db_path, timeout=30.0) as conn:
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA busy_timeout=30000")
                
                # Get order items with menu item details
                cursor = conn.execute("""
                    SELECT uo.id, uo.phone_number, uo.menu_item_id, uo.quantity, uo.subtotal, uo.special_requests, uo.added_at,
                           mi.item_name_ar, mi.item_name_en, mi.price, mi.unit
                    FROM user_orders uo
                    JOIN menu_items mi ON uo.menu_item_id = mi.id
                    WHERE uo.phone_number = ?
                    ORDER BY uo.added_at
                """, (phone_number,))
                
                items = []
                total = 0
                
                for row in cursor.fetchall():
                    item = {
                        'id': row[0],
                        'phone_number': row[1],
                        'menu_item_id': row[2],
                        'quantity': row[3],
                        'subtotal': row[4],
                        'special_requests': row[5],
                        'added_at': row[6],
                        'item_name_ar': row[7],
                        'item_name_en': row[8],
                        'price': row[9],
                        'unit': row[10]
                    }
                    items.append(item)
                    total += row[4]
                
                # Get order details
                cursor = conn.execute("""
                    SELECT service_type, location, total_amount, customizations, order_status
                    FROM order_details 
                    WHERE phone_number = ?
                """, (phone_number,))
                
                details_row = cursor.fetchone()
                details = {
                    'service_type': details_row[0] if details_row else None,
                    'location': details_row[1] if details_row else None,
                    'total_amount': details_row[2] if details_row else 0,
                    'customizations': details_row[3] if details_row else None,
                    'order_status': details_row[4] if details_row else 'in_progress'
                }
                
                return {
                    'items': items,
                    'total': total,
                    'details': details
                }
                
        except Exception as e:
            logger.error(f"❌ Error getting user order: {e}")
            return None

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
        """Complete order and generate order ID with better error handling"""
        try:
            import random
            order_id = f"HEF{random.randint(1000, 9999)}"

            with sqlite3.connect(self.db_path, timeout=60.0) as conn:
                # Enable WAL mode for better concurrency
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA busy_timeout=60000")
                conn.execute("PRAGMA synchronous=NORMAL")
                
                # Get order data first
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

                # Clear current order data (but don't delete session yet)
                conn.execute("DELETE FROM user_orders WHERE phone_number = ?", (phone_number,))
                conn.execute("DELETE FROM order_details WHERE phone_number = ?", (phone_number,))

                conn.commit()
                
                # Delete session in a separate operation to avoid lock conflicts
                try:
                    self.delete_session(phone_number)
                except Exception as session_error:
                    logger.warning(f"⚠️ Could not delete session after order completion: {session_error}")
                    # Don't fail the order completion if session deletion fails
                
                return order_id
                
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e):
                logger.warning(f"⚠️ Database locked, retrying complete order for {phone_number}")
                # Retry once after a longer delay
                import time
                time.sleep(2)
                try:
                    with sqlite3.connect(self.db_path, timeout=120.0) as conn:
                        conn.execute("PRAGMA journal_mode=WAL")
                        conn.execute("PRAGMA busy_timeout=120000")
                        conn.execute("PRAGMA synchronous=NORMAL")
                        
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

                        # Clear current order data
                        conn.execute("DELETE FROM user_orders WHERE phone_number = ?", (phone_number,))
                        conn.execute("DELETE FROM order_details WHERE phone_number = ?", (phone_number,))

                        conn.commit()
                        
                        # Delete session separately
                        try:
                            self.delete_session(phone_number)
                        except Exception as session_error:
                            logger.warning(f"⚠️ Could not delete session after order completion: {session_error}")
                        
                        return order_id
                except Exception as retry_error:
                    logger.error(f"❌ Retry failed for complete order: {retry_error}")
                    return None
            else:
                logger.error(f"❌ Database error completing order: {e}")
                return None
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

    def get_main_categories(self) -> List[Dict]:
        """Get all main categories"""
        try:
            with sqlite3.connect(self.db_path, timeout=30.0) as conn:
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA busy_timeout=30000")
                
                cursor = conn.execute("""
                    SELECT id, name_ar, name_en, display_order, available
                    FROM main_categories 
                    WHERE available = 1
                    ORDER BY display_order
                """)
                
                categories = []
                for row in cursor.fetchall():
                    categories.append({
                        'id': row[0],
                        'name_ar': row[1],
                        'name_en': row[2],
                        'display_order': row[3],
                        'available': bool(row[4])
                    })
                
                return categories
        except Exception as e:
            logger.error(f"❌ Error getting main categories: {e}")
            return []

    def get_sub_categories(self, main_category_id: int) -> List[Dict]:
        """Get sub categories for a main category"""
        try:
            with sqlite3.connect(self.db_path, timeout=30.0) as conn:
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA busy_timeout=30000")
                
                cursor = conn.execute("""
                    SELECT id, main_category_id, name_ar, name_en, display_order, available
                    FROM sub_categories 
                    WHERE main_category_id = ? AND available = 1
                    ORDER BY display_order
                """, (main_category_id,))
                
                sub_categories = []
                for row in cursor.fetchall():
                    sub_categories.append({
                        'id': row[0],
                        'main_category_id': row[1],
                        'name_ar': row[2],
                        'name_en': row[3],
                        'display_order': row[4],
                        'available': bool(row[5])
                    })
                
                return sub_categories
        except Exception as e:
            logger.error(f"❌ Error getting sub categories: {e}")
            return []

    def get_sub_category_items(self, sub_category_id: int) -> List[Dict]:
        """Get items for a sub category"""
        try:
            with sqlite3.connect(self.db_path, timeout=30.0) as conn:
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA busy_timeout=30000")
                
                cursor = conn.execute("""
                    SELECT id, sub_category_id, main_category_id, item_name_ar, item_name_en, price, unit, available
                    FROM menu_items 
                    WHERE sub_category_id = ? AND available = 1
                    ORDER BY item_name_ar
                """, (sub_category_id,))
                
                items = []
                for row in cursor.fetchall():
                    items.append({
                        'id': row[0],
                        'sub_category_id': row[1],
                        'main_category_id': row[2],
                        'item_name_ar': row[3],
                        'item_name_en': row[4],
                        'price': row[5],
                        'unit': row[6],
                        'available': bool(row[7])
                    })
                
                return items
        except Exception as e:
            logger.error(f"❌ Error getting sub category items: {e}")
            return []