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
    selected_main_category: int = None
    selected_sub_category: int = None
    selected_item: int = None
    order_mode: str = None
    quick_order_item: str = None  # JSON string to store item data
    conversation_context: str = None
    created_at: datetime = None
    updated_at: datetime = None


@dataclass
class MainCategory:
    """Main category data model"""
    id: int
    name_ar: str
    name_en: str
    display_order: int
    available: bool = True
    created_at: datetime = None


@dataclass
class SubCategory:
    """Sub category data model"""
    id: int
    main_category_id: int
    name_ar: str
    name_en: str
    display_order: int
    available: bool = True
    created_at: datetime = None


@dataclass
class MenuItem:
    """Menu item data model"""
    id: int
    sub_category_id: int
    main_category_id: int
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
                    selected_main_category INTEGER,
                    selected_sub_category INTEGER,
                    selected_item INTEGER,
                    order_mode TEXT,
                    quick_order_item TEXT,
                    conversation_context TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """,

            'main_categories': """
                CREATE TABLE IF NOT EXISTS main_categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name_ar TEXT NOT NULL,
                    name_en TEXT NOT NULL,
                    display_order INTEGER NOT NULL,
                    available BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """,

            'sub_categories': """
                CREATE TABLE IF NOT EXISTS sub_categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    main_category_id INTEGER NOT NULL,
                    name_ar TEXT NOT NULL,
                    name_en TEXT NOT NULL,
                    display_order INTEGER NOT NULL,
                    available BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (main_category_id) REFERENCES main_categories (id)
                )
            """,

            'menu_items': """
                CREATE TABLE IF NOT EXISTS menu_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sub_category_id INTEGER NOT NULL,
                    main_category_id INTEGER NOT NULL,
                    item_name_ar TEXT NOT NULL,
                    item_name_en TEXT NOT NULL,
                    price INTEGER NOT NULL,
                    unit TEXT NOT NULL,
                    available BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (sub_category_id) REFERENCES sub_categories (id),
                    FOREIGN KEY (main_category_id) REFERENCES main_categories (id)
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
        """Get initial menu data for population - Main Categories, Sub Categories, and Items"""
        return [
            # Main Categories
            # 1. Cold Drinks
            (1, "المشروبات الباردة", "Cold Drinks", 1),
            
            # 2. Hot Drinks  
            (2, "المشروبات الحارة", "Hot Drinks", 2),
            
            # 3. Pastries & Sweets
            (3, "الحلويات والمعجنات", "Pastries & Sweets", 3),
        ]

    @staticmethod
    def get_initial_sub_categories() -> List[tuple]:
        """Get initial sub-categories data"""
        return [
            # Cold Drinks Sub-categories
            (1, 1, "ايس كوفي", "Iced Coffee Drinks", 1),
            (2, 1, "فرابتشينو", "Frappuccino", 2),
            (3, 1, "ميلك شيك", "Milkshakes", 3),
            (4, 1, "شاي مثلج", "Iced Tea", 4),
            (5, 1, "عصائر طازجة", "Fresh Juices", 5),
            (6, 1, "موهيتو", "Mojito", 6),
            (7, 1, "مشروبات الطاقة", "Energy & Soft Drinks", 7),
            
            # Hot Drinks Sub-categories
            (8, 2, "قهوة واسبرسو", "Coffee & Espresso", 1),
            (9, 2, "لاتيه ومشروبات خاصة", "Lattes & Specialties", 2),
            (10, 2, "مشروبات ساخنة أخرى", "Other Hot Drinks", 3),
            
            # Pastries & Sweets Sub-categories
            (11, 3, "توست", "Toast", 1),
            (12, 3, "سندويشات", "Sandwiches", 2),
            (13, 3, "كرواسان", "Croissants", 3),
            (14, 3, "فطائر", "Pies", 4),
            (15, 3, "قطع كيك", "Cake Slices", 5),
        ]

    @staticmethod
    def get_initial_items() -> List[tuple]:
        """Get initial menu items data"""
        return [
            # Iced Coffee Drinks
            (1, 1, 1, "ايس كوفي", "Iced Coffee", 3000, "cups"),
            (2, 1, 1, "ايس امريكانو", "Iced Americano", 4000, "cups"),
            (3, 1, 1, "لاتيه مثلج عادي", "Plain Iced Latte", 4000, "cups"),
            (4, 1, 1, "لاتيه مثلج كراميل", "Caramel Iced Latte", 5000, "cups"),
            (5, 1, 1, "لاتيه مثلج فانيلا", "Vanilla Iced Latte", 5000, "cups"),
            (6, 1, 1, "لاتيه مثلج بندق", "Hazelnut Iced Latte", 5000, "cups"),
            (7, 1, 1, "ايس موكا", "Iced Mocha", 5000, "cups"),
            (8, 1, 1, "لاتيه اسباني مثلج", "Spanish Latte (Iced)", 6000, "cups"),
            
            # Frappuccino
            (9, 2, 1, "فرابتشينو كراميل", "Caramel Frappuccino", 5000, "cups"),
            (10, 2, 1, "فرابتشينو فانيلا", "Vanilla Frappuccino", 5000, "cups"),
            (11, 2, 1, "فرابتشينو بندق", "Hazelnut Frappuccino", 5000, "cups"),
            (12, 2, 1, "فرابتشينو شوكولاتة", "Chocolate Frappuccino", 5000, "cups"),
            
            # Milkshakes
            (13, 3, 1, "ميلك شيك فانيلا", "Vanilla Milkshake", 6000, "cups"),
            (14, 3, 1, "ميلك شيك شوكولاتة", "Chocolate Milkshake", 6000, "cups"),
            (15, 3, 1, "ميلك شيك اوريو", "Oreo Milkshake", 6000, "cups"),
            (16, 3, 1, "ميلك شيك فراولة", "Strawberry Milkshake", 6000, "cups"),
            
            # Iced Tea
            (17, 4, 1, "شاي مثلج بالخوخ", "Peach Iced Tea", 5000, "cups"),
            (18, 4, 1, "شاي مثلج بفاكهة العاطفة", "Passion Fruit Iced Tea", 5000, "cups"),
            
            # Fresh Juices
            (19, 5, 1, "عصير برتقال", "Orange Juice", 4000, "cups"),
            (20, 5, 1, "عصير ليمون", "Lemon Juice", 4000, "cups"),
            (21, 5, 1, "عصير ليمون ونعناع", "Lemon & Mint Juice", 5000, "cups"),
            (22, 5, 1, "عصير بطيخ", "Watermelon Juice", 5000, "cups"),
            (23, 5, 1, "عصير كيوي", "Kiwi Juice", 5000, "cups"),
            (24, 5, 1, "عصير اناناس", "Pineapple Juice", 5000, "cups"),
            (25, 5, 1, "موز وحليب", "Banana & Milk", 5000, "cups"),
            (26, 5, 1, "موز وفراولة", "Banana & Strawberry", 6000, "cups"),
            (27, 5, 1, "موز وشوكولاتة", "Banana & Chocolate", 6000, "cups"),
            (28, 5, 1, "عصير فراولة", "Strawberry Juice", 5000, "cups"),
            
            # Mojito
            (29, 6, 1, "موهيتو ازرق", "Blue Mojito", 5000, "cups"),
            (30, 6, 1, "موهيتو فاكهة العاطفة", "Passion Fruit Mojito", 5000, "cups"),
            (31, 6, 1, "موهيتو توت ازرق", "Blueberry Mojito", 5000, "cups"),
            (32, 6, 1, "موهيتو روزبيري", "Roseberry Mojito", 5000, "cups"),
            (33, 6, 1, "موهيتو فراولة", "Strawberry Mojito", 5000, "cups"),
            (34, 6, 1, "موهيتو بينا كولادا", "Pina Colada Mojito", 5000, "cups"),
            (35, 6, 1, "موهيتو علكة", "Bubble Gum Mojito", 5000, "cups"),
            (36, 6, 1, "موهيتو دراغون", "Dragon Mojito", 5000, "cups"),
            (37, 6, 1, "موهيتو هيف", "Hef Mojito", 5000, "cups"),
            (38, 6, 1, "موهيتو رمان", "Pomegranate Mojito", 5000, "cups"),
            (39, 6, 1, "موهيتو خوخ", "Peach Mojito", 5000, "cups"),
            
            # Energy & Soft Drinks
            (40, 7, 1, "مزيج الطاقة", "Energy Mix", 6000, "cups"),
            (41, 7, 1, "ريد بول عادي", "Regular Red Bull", 3000, "cups"),
            (42, 7, 1, "صودا عادية", "Plain Soda", 1000, "cups"),
            (43, 7, 1, "ماء", "Water", 1000, "cups"),
            
            # Coffee & Espresso
            (44, 8, 2, "اسبرسو", "Espresso", 3000, "cups"),
            (45, 8, 2, "قهوة تركية", "Turkish Coffee", 3000, "cups"),
            (46, 8, 2, "امريكانو", "Americano", 4000, "cups"),
            
            # Lattes & Specialties
            (47, 9, 2, "كابتشينو", "Cappuccino", 5000, "cups"),
            (48, 9, 2, "لاتيه اسباني ساخن", "Spanish Latte (Hot)", 6000, "cups"),
            (49, 9, 2, "لاتيه كراميل", "Caramel Latte", 5000, "cups"),
            (50, 9, 2, "لاتيه فانيلا", "Vanilla Latte", 5000, "cups"),
            (51, 9, 2, "لاتيه بندق", "Hazelnut Latte", 5000, "cups"),
            (52, 9, 2, "لاتيه هيف", "Hef Latte", 6000, "cups"),
            
            # Other Hot Drinks
            (53, 10, 2, "هوت شوكليت", "Hot Chocolate", 5000, "cups"),
            (54, 10, 2, "شاي عراقي", "Iraqi Tea", 1000, "cups"),
            
            # Toast
            (55, 11, 3, "توست مارتديلا لحم وجبن", "Beef Mortadella & Cheese Toast", 2000, "pieces"),
            (56, 11, 3, "توست مارتديلا دجاج وجبن", "Chicken Mortadella & Cheese Toast", 2000, "pieces"),
            (57, 11, 3, "توست جبن وزعتر", "Cheese & Thyme Toast", 2000, "pieces"),
            
            # Sandwiches
            (58, 12, 3, "سندويش لحم مشوي", "Roast Beef Sandwich", 3000, "pieces"),
            (59, 12, 3, "سندويش مارتديلا دجاج", "Chicken Mortadella Sandwich", 3000, "pieces"),
            (60, 12, 3, "سندويش جبن حلومي", "Halloumi Cheese Sandwich", 3000, "pieces"),
            (61, 12, 3, "سندويش دجاج وخضار دايت", "Diet Chicken & Veggies Sandwich", 3000, "pieces"),
            (62, 12, 3, "سندويش ديك رومي", "Turkey Sandwich", 3000, "pieces"),
            (63, 12, 3, "سندويش دجاج فاجيتا", "Chicken Fajita Sandwich", 3000, "pieces"),
            
            # Croissants
            (64, 13, 3, "كرواسان عادي", "Plain Croissant", 2000, "pieces"),
            (65, 13, 3, "كرواسان جبن", "Cheese Croissant", 2000, "pieces"),
            (66, 13, 3, "كرواسان شوكولاتة", "Chocolate Croissant", 2000, "pieces"),
            
            # Pies
            (67, 14, 3, "فطيرة دجاج", "Chicken Pie", 2000, "pieces"),
            (68, 14, 3, "فطيرة جبن", "Cheese Pie", 2000, "pieces"),
            (69, 14, 3, "فطيرة زعتر", "Thyme Pie", 2000, "pieces"),
            
            # Cake Slices
            (70, 15, 3, "كيك فانيلا", "Vanilla Cake", 4000, "slices"),
            (71, 15, 3, "كيك لوتس", "Lotus Cake", 4000, "slices"),
            (72, 15, 3, "كيك فستق", "Pistachio Cake", 4000, "slices"),
            (73, 15, 3, "كيك اوريو", "Oreo Cake", 4000, "slices"),
            (74, 15, 3, "سان سيباستيان", "San Sebastian", 4000, "slices"),
            (75, 15, 3, "كيك كراميل", "Caramel Cake", 4000, "slices"),
            (76, 15, 3, "كيك شوكولاتة", "Chocolate Cake", 4000, "slices"),
        ]

    @staticmethod
    def get_initial_step_rules() -> List[tuple]:
        """Get initial step validation rules"""
        return [
            ("waiting_for_language", "waiting_for_language,waiting_for_main_category", "language_preference",
             "Language selection"),
            ("waiting_for_main_category", "waiting_for_main_category,waiting_for_sub_category", "selected_main_category", 
             "Main category selection"),
            ("waiting_for_sub_category", "waiting_for_sub_category,waiting_for_item", "selected_sub_category", 
             "Sub category selection"),
            ("waiting_for_item", "waiting_for_item,waiting_for_quantity", "selected_item", "Item selection"),
            ("waiting_for_quantity", "waiting_for_quantity,waiting_for_additional", "quantity", "Quantity selection"),
            ("waiting_for_additional", "waiting_for_additional,waiting_for_main_category,waiting_for_service",
             "additional_choice", "Additional items choice"),
            ("waiting_for_service", "waiting_for_service,waiting_for_location", "service_type",
             "Service type selection"),
            ("waiting_for_location", "waiting_for_location,waiting_for_confirmation", "location",
             "Location/table selection"),
            ("waiting_for_confirmation", "waiting_for_confirmation,completed,waiting_for_language", "confirmation",
             "Order confirmation"),
        ]