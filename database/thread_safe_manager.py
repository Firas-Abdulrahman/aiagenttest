# database/thread_safe_manager.py - NEW FILE
"""
Thread-safe database operations with proper user isolation
"""
import sqlite3
import json
import logging
import threading
import time
from typing import Dict, List, Optional, Any
from contextlib import contextmanager
from .models import DatabaseSchema
from utils.thread_safe_session import session_manager, UserWorkflowState

logger = logging.getLogger(__name__)


class ThreadSafeDatabaseManager:
    """Thread-safe database manager with user isolation"""

    def __init__(self, db_path: str = "hef_cafe.db"):
        self.db_path = db_path
        self._db_lock = threading.RLock()
        self._connection_pool = {}
        self._pool_lock = threading.Lock()
        self._max_connections = 10
        self._connection_timeout = 30.0
        self._pool_cleanup_interval = 300  # 5 minutes
        self._last_pool_cleanup = time.time()

        # Initialize database
        self.init_database()

        logger.info("✅ Thread-safe database manager initialized with connection pooling")

    @contextmanager
    def get_db_connection(self, timeout: float = None):
        """Get database connection with improved connection pooling and timeout handling"""
        if timeout is None:
            timeout = self._connection_timeout
            
        conn = None
        connection_id = None
        
        try:
            # Try to get connection from pool first
            with self._pool_lock:
                if self._connection_pool:
                    connection_id, conn = self._connection_pool.popitem()
                    logger.debug(f"🔌 Reusing connection {connection_id}")
                else:
                    # Create new connection
                    connection_id = f"conn_{int(time.time() * 1000)}_{threading.get_ident()}"
                    conn = sqlite3.connect(
                        self.db_path,
                        timeout=timeout,
                        check_same_thread=False
                    )
                    logger.debug(f"🔌 Created new connection {connection_id}")

            # Configure connection for better performance
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA cache_size=10000")
            conn.execute("PRAGMA temp_store=MEMORY")
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA busy_timeout=30000")
            conn.execute("PRAGMA optimize")

            yield conn

        except sqlite3.OperationalError as e:
            if "database is locked" in str(e):
                logger.warning(f"⚠️ Database locked, retrying...")
                time.sleep(0.1)
                raise
            else:
                logger.error(f"❌ Database operational error: {e}")
                raise
        except Exception as e:
            logger.error(f"❌ Database error: {e}")
            if conn:
                try:
                    conn.rollback()
                except:
                    pass
            raise
        finally:
            if conn:
                try:
                    # Return connection to pool if it's still valid
                    if conn and not conn.closed:
                        with self._pool_lock:
                            if len(self._connection_pool) < self._max_connections:
                                self._connection_pool[connection_id] = conn
                                logger.debug(f"🔌 Returned connection {connection_id} to pool")
                            else:
                                conn.close()
                                logger.debug(f"🔌 Closed connection {connection_id} (pool full)")
                except Exception as e:
                    logger.warning(f"⚠️ Error returning connection to pool: {e}")
                    try:
                        conn.close()
                    except:
                        pass

    def _cleanup_connection_pool(self):
        """Clean up stale connections from the pool"""
        current_time = time.time()
        if current_time - self._last_pool_cleanup > self._pool_cleanup_interval:
            with self._pool_lock:
                stale_connections = []
                for conn_id, conn in self._connection_pool.items():
                    try:
                        # Test if connection is still valid
                        conn.execute("SELECT 1")
                    except:
                        stale_connections.append(conn_id)
                
                # Remove stale connections
                for conn_id in stale_connections:
                    try:
                        conn = self._connection_pool.pop(conn_id)
                        conn.close()
                        logger.debug(f"🧹 Cleaned up stale connection {conn_id}")
                    except:
                        pass
                
                self._last_pool_cleanup = current_time
                logger.debug(f"🧹 Connection pool cleanup completed. Active connections: {len(self._connection_pool)}")

    def init_database(self):
        """Initialize database with thread safety"""
        with self._db_lock:
            with self.get_db_connection(timeout=60.0) as conn:
                # Create tables
                table_definitions = DatabaseSchema.get_table_definitions()
                for table_name, sql in table_definitions.items():
                    conn.execute(sql)
                    logger.debug(f"✅ Created/verified table: {table_name}")

                conn.commit()

                # Populate initial data if needed
                self._populate_initial_data(conn)

    def _populate_initial_data(self, conn):
        """Populate initial data (thread-safe)"""
        try:
            # Check if data already exists
            cursor = conn.execute("SELECT COUNT(*) FROM main_categories")
            count = cursor.fetchone()[0]

            if count == 0:
                logger.info("📝 Populating initial menu data...")

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

                # Insert step rules
                step_rules = DatabaseSchema.get_initial_step_rules()
                for rule in step_rules:
                    conn.execute("""
                        INSERT OR REPLACE INTO step_rules 
                        (current_step, allowed_next_steps, required_data, description)
                        VALUES (?, ?, ?, ?)
                    """, rule)

                conn.commit()
                logger.info("✅ Initial data populated successfully")

        except Exception as e:
            logger.error(f"❌ Error populating initial data: {e}")
            conn.rollback()
            raise

    # User Session Operations (Thread-Safe)
    def get_user_session(self, phone_number: str) -> Optional[Dict]:
        """Get user session with improved performance and caching"""
        try:
            # Clean up connection pool periodically
            self._cleanup_connection_pool()
            
            with self.get_db_connection() as conn:
                cursor = conn.execute("""
                    SELECT s.*, 
                           o.id as order_id,
                           o.total as order_total,
                           o.status as order_status,
                           o.created_at as order_created,
                           o.updated_at as order_updated
                    FROM user_sessions s
                    LEFT JOIN orders o ON s.phone_number = o.phone_number AND o.status = 'pending'
                    WHERE s.phone_number = ?
                """, (phone_number,))
                
                row = cursor.fetchone()
                if row:
                    # Convert row to dict with proper column names
                    columns = [description[0] for description in cursor.description]
                    session_data = dict(zip(columns, row))
                    
                    # Parse JSON fields
                    for field in ['conversation_context', 'order_items']:
                        if field in session_data and session_data[field]:
                            try:
                                if isinstance(session_data[field], str):
                                    session_data[field] = json.loads(session_data[field])
                            except json.JSONDecodeError:
                                logger.warning(f"⚠️ Failed to parse JSON for {field}: {session_data[field]}")
                                session_data[field] = {}
                    
                    logger.debug(f"✅ Retrieved session for {phone_number}")
                    return session_data
                else:
                    logger.debug(f"📋 No session found for {phone_number}")
                    return None
                    
        except Exception as e:
            logger.error(f"❌ Error getting user session for {phone_number}: {e}")
            return None

    def create_or_update_session(self, phone_number: str, current_step: str,
                                 language: str = None, customer_name: str = None,
                                 selected_main_category: int = None,
                                 selected_sub_category: int = None,
                                 selected_item: int = None) -> bool:
        """Create or update user session with thread safety"""

        # Use the session manager's user lock
        with session_manager.user_session_lock(phone_number):
            try:
                # Update in-memory state first
                session_manager.create_or_update_user_state(
                    phone_number=phone_number,
                    current_step=current_step,
                    language_preference=language,
                    customer_name=customer_name,
                    selected_main_category=selected_main_category,
                    selected_sub_category=selected_sub_category,
                    selected_item=selected_item
                )

                # Persist to database
                with self.get_db_connection() as conn:
                    # Use INSERT OR REPLACE for atomic operation
                    conn.execute("""
                        INSERT OR REPLACE INTO user_sessions 
                        (phone_number, current_step, language_preference, customer_name, 
                         selected_main_category, selected_sub_category, selected_item, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """, (phone_number, current_step, language, customer_name,
                          selected_main_category, selected_sub_category, selected_item))

                    conn.commit()

                logger.debug(f"✅ Session updated for {phone_number}: {current_step}")
                return True

            except Exception as e:
                logger.error(f"❌ Error updating session for {phone_number}: {e}")
                return False

    def delete_session(self, phone_number: str, only_session: bool = False) -> bool:
        """Delete user session with thread safety"""
        with session_manager.user_session_lock(phone_number):
            try:
                # Remove from in-memory cache
                session_manager.delete_user_state(phone_number)

                # Remove from database
                with self.get_db_connection() as conn:
                    conn.execute("BEGIN IMMEDIATE TRANSACTION")

                    if only_session:
                        # Only delete session record and conversation log (for when orders already cleaned up)
                        conn.execute("DELETE FROM conversation_log WHERE phone_number = ?", (phone_number,))
                        conn.execute("DELETE FROM user_sessions WHERE phone_number = ?", (phone_number,))
                    else:
                        # Delete all related data in proper order to avoid foreign key constraints
                        conn.execute("DELETE FROM user_orders WHERE phone_number = ?", (phone_number,))
                        conn.execute("DELETE FROM order_details WHERE phone_number = ?", (phone_number,))
                        conn.execute("DELETE FROM conversation_log WHERE phone_number = ?", (phone_number,))
                        conn.execute("DELETE FROM user_sessions WHERE phone_number = ?", (phone_number,))

                    conn.commit()

                logger.info(f"🗑️ Session deleted for {phone_number}")
                return True

            except Exception as e:
                logger.error(f"❌ Error deleting session for {phone_number}: {e}")
                return False

    # Order Operations (Thread-Safe)
    def add_item_to_order(self, phone_number: str, item_id: int, quantity: int,
                          special_requests: str = None) -> bool:
        """Add item to order with thread safety"""
        with session_manager.user_session_lock(phone_number):
            try:
                with self.get_db_connection() as conn:
                    conn.execute("BEGIN IMMEDIATE TRANSACTION")

                    # Get item price atomically
                    cursor = conn.execute(
                        "SELECT price FROM menu_items WHERE id = ? AND available = 1",
                        (item_id,)
                    )
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
        """Get user order with thread safety"""
        try:
            with self.get_db_connection() as conn:
                # Get order items
                cursor = conn.execute("""
                    SELECT uo.id, uo.phone_number, uo.menu_item_id, uo.quantity, 
                           uo.subtotal, uo.special_requests, uo.added_at,
                           COALESCE(mi.item_name_ar, 'Unknown Item') as item_name_ar, 
                           COALESCE(mi.item_name_en, 'Unknown Item') as item_name_en, 
                           COALESCE(mi.price, 0) as price, 
                           COALESCE(mi.unit, 'piece') as unit
                    FROM user_orders uo
                    LEFT JOIN menu_items mi ON uo.menu_item_id = mi.id
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

    def complete_order(self, phone_number: str) -> str:
        """Complete order with thread safety"""
        with session_manager.user_session_lock(phone_number):
            try:
                import random
                order_id = f"HEF{random.randint(1000, 9999)}"

                with self.get_db_connection() as conn:
                    conn.execute("BEGIN IMMEDIATE TRANSACTION")

                    # Get order data
                    order = self.get_user_order(phone_number)

                    if not order or not order['items']:
                        logger.error(f"❌ No order found for {phone_number}")
                        return None

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

                    # Clear current order data and conversation log
                    conn.execute("DELETE FROM user_orders WHERE phone_number = ?", (phone_number,))
                    conn.execute("DELETE FROM order_details WHERE phone_number = ?", (phone_number,))
                    conn.execute("DELETE FROM conversation_log WHERE phone_number = ?", (phone_number,))

                    conn.commit()

                # Clear session (orders already deleted above)
                self.delete_session(phone_number, only_session=True)

                logger.info(f"✅ Order {order_id} completed for {phone_number}")
                return order_id

            except Exception as e:
                logger.error(f"❌ Error completing order: {e}")
                return None

    # Menu Operations (Read-only, thread-safe by nature)
    def get_main_categories(self) -> List[Dict]:
        """Get main categories"""
        try:
            with self.get_db_connection() as conn:
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

    def get_category_items(self, main_category_id: int) -> List[Dict]:
        """Get all items for a main category"""
        try:
            with self.get_db_connection() as conn:
                cursor = conn.execute("""
                    SELECT mi.id, mi.sub_category_id, mi.main_category_id, 
                           mi.item_name_ar, mi.item_name_en, mi.price, mi.unit, mi.available
                    FROM menu_items mi
                    WHERE mi.main_category_id = ? AND mi.available = 1
                    ORDER BY mi.item_name_ar
                """, (main_category_id,))

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
            logger.error(f"❌ Error getting category items: {e}")
            return []

    def get_sub_categories(self, main_category_id: int) -> List[Dict]:
        """Get sub-categories for a main category"""
        try:
            with self.get_db_connection() as conn:
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
            logger.error(f"❌ Error getting sub-categories: {e}")
            return []

    def get_sub_category_items(self, sub_category_id: int) -> List[Dict]:
        """Get items for a specific sub-category"""
        try:
            with self.get_db_connection() as conn:
                cursor = conn.execute("""
                    SELECT mi.id, mi.sub_category_id, mi.main_category_id, 
                           mi.item_name_ar, mi.item_name_en, mi.price, mi.unit, mi.available
                    FROM menu_items mi
                    WHERE mi.sub_category_id = ? AND mi.available = 1
                    ORDER BY mi.item_name_ar
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
            logger.error(f"❌ Error getting sub-category items: {e}")
            return []

    def get_item_by_id(self, item_id: int) -> Optional[Dict]:
        """Get item by ID"""
        try:
            with self.get_db_connection() as conn:
                cursor = conn.execute("""
                    SELECT id, sub_category_id, main_category_id, item_name_ar, 
                           item_name_en, price, unit, available
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

    def update_session_field(self, phone_number: str, field_name: str, value: Any) -> bool:
        """Update a specific field in user session with thread safety"""
        try:
            with self.get_db_connection() as conn:
                # Build dynamic update query
                query = f"""
                    UPDATE user_sessions 
                    SET {field_name} = ?, updated_at = datetime('now')
                    WHERE phone_number = ?
                """
                conn.execute(query, (value, phone_number))
                conn.commit()
                logger.info(f"✅ Updated session field '{field_name}' for {phone_number}")
                return True
        except Exception as e:
            logger.error(f"❌ Error updating session field: {e}")
            return False

    def update_order_details(self, phone_number: str, **kwargs) -> bool:
        """Update order details with thread safety"""
        try:
            with self.get_db_connection() as conn:
                # First, ensure the order_details record exists
                conn.execute("""
                    INSERT OR IGNORE INTO order_details (phone_number)
                    VALUES (?)
                """, (phone_number,))
                
                # Build the UPDATE query for order_details table
                update_fields = []
                values = []
                for field, value in kwargs.items():
                    if value is not None:
                        update_fields.append(f"{field} = ?")
                        values.append(value)
                
                if update_fields:
                    values.append(phone_number)
                    query = f"""
                        UPDATE order_details 
                        SET {', '.join(update_fields)}
                        WHERE phone_number = ?
                    """
                    conn.execute(query, values)
                    conn.commit()
                    logger.info(f"✅ Updated order details for {phone_number}: {kwargs}")
                    return True
                
                return True
                    
        except Exception as e:
            logger.error(f"❌ Error updating order details: {e}")
            return False

    def remove_last_item_from_order(self, phone_number: str) -> bool:
        """Remove the last added item from user's order with thread safety"""
        try:
            with self.get_db_connection() as conn:
                # Get the last added item
                cursor = conn.execute("""
                    SELECT id, menu_item_id, quantity 
                    FROM user_orders 
                    WHERE phone_number = ? 
                    ORDER BY added_at DESC 
                    LIMIT 1
                """, (phone_number,))
                
                last_item = cursor.fetchone()
                
                if last_item:
                    # Remove the last item
                    conn.execute("""
                        DELETE FROM user_orders 
                        WHERE id = ?
                    """, (last_item[0],))
                    
                    conn.commit()
                    logger.info(f"✅ Removed last item {last_item[1]} × {last_item[2]} from order for {phone_number}")
                    return True
                else:
                    logger.warning(f"⚠️ No items found in order for {phone_number}")
                    return False
                
        except Exception as e:
            logger.error(f"❌ Error removing last item from order: {e}")
            return False

    def update_item_quantity(self, phone_number: str, item_id: int, new_quantity: int) -> bool:
        """Update quantity of existing item in user's order (thread-safe)"""
        try:
            with self.get_db_connection() as conn:
                # Update the quantity of the existing item
                cursor = conn.execute("""
                    UPDATE user_orders 
                    SET quantity = ?, subtotal = ? * (SELECT price FROM menu_items WHERE id = ?)
                    WHERE phone_number = ? AND menu_item_id = ?
                """, (new_quantity, new_quantity, item_id, phone_number, item_id))
                
                conn.commit()
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"❌ Error updating item quantity: {e}")
            return False

    def delete_menu_item(self, item_id: int) -> bool:
        """Delete a menu item by setting it as unavailable (thread-safe)"""
        try:
            with self.get_db_connection() as conn:
                # Set the item as unavailable instead of actually deleting it
                cursor = conn.execute("""
                    UPDATE menu_items 
                    SET available = 0
                    WHERE id = ?
                """, (item_id,))
                
                conn.commit()
                success = cursor.rowcount > 0
                
                if success:
                    logger.info(f"✅ Successfully deleted menu item with ID: {item_id}")
                else:
                    logger.warning(f"⚠️ Menu item with ID {item_id} not found or already deleted")
                
                return success
                
        except Exception as e:
            logger.error(f"❌ Error deleting menu item {item_id}: {e}")
            return False

    # Utility Methods
    def cleanup_expired_sessions(self, days_old: int = 7) -> int:
        """Clean up old sessions"""
        try:
            # Clean in-memory sessions first
            memory_cleaned = session_manager.cleanup_expired_sessions()

            # Clean database sessions
            with self.get_db_connection() as conn:
                cursor = conn.execute("""
                    DELETE FROM user_sessions 
                    WHERE created_at < datetime('now', '-{} days')
                """.format(days_old))

                db_cleaned = cursor.rowcount
                conn.commit()

            total_cleaned = memory_cleaned + db_cleaned
            logger.info(f"🧹 Cleaned up {total_cleaned} old sessions")
            return total_cleaned

        except Exception as e:
            logger.error(f"❌ Error cleaning up sessions: {e}")
            return 0

    def get_database_stats(self) -> Dict:
        """Get database statistics"""
        try:
            with self.get_db_connection() as conn:
                stats = {}

                # Count records in each table
                tables = ['user_sessions', 'menu_items', 'user_orders', 'order_details',
                          'completed_orders', 'step_rules']

                for table in tables:
                    cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
                    stats[f"{table}_count"] = cursor.fetchone()[0]

                # Additional stats
                cursor = conn.execute("SELECT COUNT(DISTINCT phone_number) FROM user_sessions")
                stats['active_users'] = cursor.fetchone()[0]

                cursor = conn.execute("SELECT SUM(total_amount) FROM completed_orders")
                total_revenue = cursor.fetchone()[0]
                stats['total_revenue'] = total_revenue or 0

                # Add session manager stats
                session_stats = session_manager.get_session_stats()
                stats.update(session_stats)

                return stats

        except Exception as e:
            logger.error(f"❌ Error getting database stats: {e}")
            return {}

    def log_conversation(self, phone_number: str, message_type: str, content: str,
                         ai_response: str = None, current_step: str = None):
        """Log conversation for analytics (non-blocking) - FIXED"""
        try:
            with self.get_db_connection() as conn:
                # First ensure user session exists to avoid foreign key constraint
                conn.execute("""
                    INSERT OR IGNORE INTO user_sessions 
                    (phone_number, current_step, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                """, (phone_number, current_step or 'waiting_for_language'))
                
                # Now log the conversation
                conn.execute("""
                    INSERT INTO conversation_log 
                    (phone_number, message_type, content, ai_response, current_step)
                    VALUES (?, ?, ?, ?, ?)
                """, (phone_number, message_type, content, ai_response, current_step))
                conn.commit()
        except Exception as e:
            logger.error(f"❌ Error logging conversation: {e}")
            # Don't fail the main operation if logging fails

    def validate_step_transition(self, phone_number: str, next_step: str) -> bool:
        """Validate step transition"""
        state = session_manager.get_user_state(phone_number)
        current_step = state.current_step if state else 'waiting_for_language'

        # Allow transitions from any step to language (restart)
        if next_step == 'waiting_for_language':
            return True

        # Define allowed transitions
        allowed_transitions = {
            'waiting_for_language': ['waiting_for_category'],
            'waiting_for_category': ['waiting_for_item'],
            'waiting_for_item': ['waiting_for_quantity'],
            'waiting_for_quantity': ['waiting_for_additional'],
            'waiting_for_additional': ['waiting_for_category', 'waiting_for_service'],
            'waiting_for_service': ['waiting_for_location'],
            'waiting_for_location': ['waiting_for_confirmation'],
            'waiting_for_confirmation': ['completed', 'waiting_for_language']
        }

        return next_step in allowed_transitions.get(current_step, [])

    def get_current_order(self, phone_number: str) -> Optional[Dict]:
        """Get current order for a user (alias for get_user_order)"""
        return self.get_user_order(phone_number)

    def get_order_history(self, phone_number: str = None, limit: int = 50) -> List[Dict]:
        """Get order history with thread safety"""
        try:
            with self.get_db_connection() as conn:
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
        except Exception as e:
            logger.error(f"❌ Error getting order history: {e}")
            return []

    def cancel_order(self, phone_number: str) -> bool:
        """Cancel order for a user with thread safety"""
        try:
            with self.get_db_connection() as conn:
                # Delete current order
                conn.execute("""
                    DELETE FROM user_orders WHERE phone_number = ?
                """, (phone_number,))
                
                # Delete order details
                conn.execute("""
                    DELETE FROM order_details WHERE phone_number = ?
                """, (phone_number,))
                
                # Reset session to initial state
                conn.execute("""
                    UPDATE user_sessions 
                    SET current_step = 'waiting_for_language',
                        selected_main_category = NULL,
                        selected_sub_category = NULL,
                        selected_item = NULL,
                        updated_at = datetime('now')
                    WHERE phone_number = ?
                """, (phone_number,))
                
                conn.commit()
                logger.info(f"✅ Order cancelled for {phone_number}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Error cancelling order: {e}")
            return False