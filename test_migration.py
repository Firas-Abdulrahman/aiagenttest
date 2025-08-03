#!/usr/bin/env python3
"""
Test database migration from old schema to new schema
"""

import sys
import os
import sqlite3
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_database_migration():
    """Test database migration from old schema to new schema"""
    from database.manager import DatabaseManager
    
    print("🧪 Testing Database Migration:")
    
    # Create a test database with old schema first
    db_path = "test_migration.db"
    
    # Create old schema tables
    with sqlite3.connect(db_path) as conn:
        # Old user_sessions table
        conn.execute("""
            CREATE TABLE user_sessions (
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
        
        # Old menu_items table
        conn.execute("""
            CREATE TABLE menu_items (
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
        
        # Insert some old data
        conn.execute("""
            INSERT INTO user_sessions (phone_number, current_step, language_preference, customer_name)
            VALUES ('1234567890', 'waiting_for_language', 'arabic', 'Test User')
        """)
        
        conn.execute("""
            INSERT INTO menu_items (category_id, category_name_ar, category_name_en, item_name_ar, item_name_en, price, unit)
            VALUES (1, 'المشروبات الحارة', 'Hot Beverages', 'اسبريسو', 'Espresso', 3000, 'cups')
        """)
        
        conn.commit()
    
    print("✅ Created old schema database")
    
    # Now test migration
    db = DatabaseManager(db_path)
    
    # Test that new structure works
    main_categories = db.get_main_categories()
    print(f"✅ Retrieved {len(main_categories)} main categories")
    
    if main_categories:
        sub_categories = db.get_sub_categories(main_categories[0]['id'])
        print(f"✅ Retrieved {len(sub_categories)} sub categories")
    
    # Clean up
    if os.path.exists(db_path):
        os.remove(db_path)
    
    print("✅ Database migration test completed!")

if __name__ == "__main__":
    test_database_migration() 