"""
Database Models and Schema Definitions for Hef Cafe WhatsApp Bot
"""
from typing import Dict, List, Any
from dataclasses import dataclass
from datetime import datetime


@dataclass
class UserSession:
    """User session data model"""
    phone_number: str
    current_step: str
    language_preference: str = None
    customer_name: str = None
    selected_category: int = None
    selected_item: int = None
    conversation_context: str = None
    created_at: datetime = None
    updated_at: datetime = None


@dataclass
class MenuItem:
    """Menu item data model"""
    id: int
    category_id: int
    category_name_ar: str
    category_name_en: str
    item_name_ar: str
    item_name_en: str
    price: int
    unit: str
    available: bool = True
    created_at: datetime = None


@dataclass
class UserOrder:
    """User order item data model"""
    id: int = None
    phone_number: str = None
    menu_item_id: int = None
    quantity: int = None
    subtotal: int = None
    special_requests: str = None
    added_at: datetime = None


@dataclass
class OrderDetails:
    """Order details data model"""
    phone_number: str
    service_type: str = None
    location: str = None
    total_amount: int = 0
    customizations: str = None
    order_status: str = 'in_progress'
    created_at: datetime = None


@dataclass
class ConversationLog:
    """Conversation log data model"""
    id: int = None
    phone_number: str = None
    message_type: str = None
    content: str = None
    ai_response: str = None
    current_step: str = None
    timestamp: datetime = None


@dataclass
class CompletedOrder:
    """Completed order data model"""
    id: int = None
    phone_number: str = None
    order_id: str = None
    items_json: str = None
    total_amount: int = None
    service_type: str = None
    location: str = None
    completed_at: datetime = None


@dataclass
class StepRule:
    """Step validation rule data model"""
    current_step: str
    allowed_next_steps: str
    required_data: str = None
    description: str = None


class DatabaseSchema:
    """Database schema definitions"""

    @staticmethod
    def get_table_definitions() -> Dict[str, str]:
        """Get all table creation SQL statements"""
        return {
            'user_sessions': """
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
            """,

            'menu_items': """
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
            """,

            'user_orders': """
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
            """,

            'order_details': """
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
            """,

            'conversation_log': """
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
            """,

            'completed_orders': """
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
            """,

            'step_rules': """
                CREATE TABLE IF NOT EXISTS step_rules (
                    current_step TEXT PRIMARY KEY,
                    allowed_next_steps TEXT NOT NULL,
                    required_data TEXT,
                    description TEXT
                )
            """
        }

    @staticmethod
    def get_initial_menu_data() -> List[tuple]:
        """Get initial menu data for population"""
        return [
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

            # Sweets
            (3, "الحلويات", "Sweets", "كيك شوكولاتة", "Chocolate Cake", 4000, "slices"),
            (3, "الحلويات", "Sweets", "كيك فانيلا", "Vanilla Cake", 4000, "slices"),
            (3, "الحلويات", "Sweets", "تيراميسو", "Tiramisu", 5000, "slices"),

            # Iced Tea
            (4, "الشاي المثلج", "Iced Tea", "شاي مثلج بالليمون", "Iced Lemon Tea", 2500, "cups"),
            (4, "الشاي المثلج", "Iced Tea", "شاي مثلج بالخوخ", "Iced Peach Tea", 2500, "cups"),

            # Frappuccino
            (5, "فرابتشينو", "Frappuccino", "فرابتشينو كراميل", "Caramel Frappuccino", 6000, "cups"),
            (5, "فرابتشينو", "Frappuccino", "فرابتشينو موكا", "Mocha Frappuccino", 6000, "cups"),

            # Natural Juices
            (6, "العصائر الطبيعية", "Natural Juices", "عصير برتقال", "Orange Juice", 3000, "cups"),
            (6, "العصائر الطبيعية", "Natural Juices", "عصير تفاح", "Apple Juice", 3000, "cups"),
            (6, "العصائر الطبيعية", "Natural Juices", "عصير مانجو", "Mango Juice", 3500, "cups"),

            # Mojito
            (7, "موهيتو", "Mojito", "موهيتو كلاسيكي", "Classic Mojito", 4000, "cups"),
            (7, "موهيتو", "Mojito", "موهيتو فراولة", "Strawberry Mojito", 4500, "cups"),

            # Milkshake
            (8, "ميلك شيك", "Milkshake", "ميلك شيك فانيلا", "Vanilla Milkshake", 4000, "cups"),
            (8, "ميلك شيك", "Milkshake", "ميلك شيك شوكولاتة", "Chocolate Milkshake", 4000, "cups"),

            # Toast
            (9, "توست", "Toast", "مارتديلا لحم بالجبن", "Beef Mortadella with Cheese", 2000, "pieces"),
            (9, "توست", "Toast", "مارتديلا دجاج بالجبن", "Chicken Mortadella with Cheese", 2000, "pieces"),
            (9, "توست", "Toast", "جبن بالزعتر", "Cheese with Zaatar", 2000, "pieces"),

            # Sandwiches
            (10, "سندويشات", "Sandwiches", "سندويش دجاج", "Chicken Sandwich", 3000, "pieces"),
            (10, "سندويشات", "Sandwiches", "سندويش تونا", "Tuna Sandwich", 2500, "pieces"),

            # Cake Slices
            (11, "قطع الكيك", "Cake Slices", "فانيلا كيك", "Vanilla Cake", 4000, "slices"),
            (11, "قطع الكيك", "Cake Slices", "لوتس كيك", "Lotus Cake", 4000, "slices"),
            (11, "قطع الكيك", "Cake Slices", "شوكليت كيك", "Chocolate Cake", 4000, "slices"),

            # Croissants
            (12, "كرواسان", "Croissants", "كرواسان زبدة", "Butter Croissant", 2000, "pieces"),
            (12, "كرواسان", "Croissants", "كرواسان شوكولاتة", "Chocolate Croissant", 2500, "pieces"),

            # Savory Pies
            (13, "فطائر مالحة", "Savory Pies", "فطيرة سبانخ", "Spinach Pie", 2000, "pieces"),
            (13, "فطائر مالحة", "Savory Pies", "فطيرة جبن", "Cheese Pie", 2000, "pieces"),
        ]

    @staticmethod
    def get_initial_step_rules() -> List[tuple]:
        """Get initial step validation rules"""
        return [
            ("waiting_for_language", "waiting_for_language,waiting_for_category", "language_preference",
             "Language selection"),
            (
            "waiting_for_category", "waiting_for_category,waiting_for_item", "selected_category", "Category selection"),
            ("waiting_for_item", "waiting_for_item,waiting_for_quantity", "selected_item", "Item selection"),
            ("waiting_for_quantity", "waiting_for_quantity,waiting_for_additional", "quantity", "Quantity selection"),
            ("waiting_for_additional", "waiting_for_additional,waiting_for_category,waiting_for_service",
             "additional_choice", "Additional items choice"),
            ("waiting_for_service", "waiting_for_service,waiting_for_location", "service_type",
             "Service type selection"),
            ("waiting_for_location", "waiting_for_location,waiting_for_confirmation", "location",
             "Location/table selection"),
            ("waiting_for_confirmation", "waiting_for_confirmation,completed,waiting_for_language", "confirmation",
             "Order confirmation"),
        ]