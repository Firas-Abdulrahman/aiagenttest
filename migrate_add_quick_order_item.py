#!/usr/bin/env python3
"""
Database Migration Script
Adds quick_order_item column to user_sessions table
"""
import sqlite3
import os
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_database():
    """Add quick_order_item column to user_sessions table"""
    
    # Database file path (adjust as needed)
    db_path = "hef_cafe.db"
    
    if not os.path.exists(db_path):
        logger.info(f"Database file {db_path} not found. Creating new database...")
        return
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if column already exists
        cursor.execute("PRAGMA table_info(user_sessions)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'quick_order_item' not in columns:
            logger.info("Adding quick_order_item column to user_sessions table...")
            
            # Add the new column
            cursor.execute("""
                ALTER TABLE user_sessions 
                ADD COLUMN quick_order_item TEXT
            """)
            
            conn.commit()
            logger.info("✅ Successfully added quick_order_item column")
        else:
            logger.info("✅ quick_order_item column already exists")
        
        # Verify the column was added
        cursor.execute("PRAGMA table_info(user_sessions)")
        columns = [column[1] for column in cursor.fetchall()]
        logger.info(f"Current columns in user_sessions: {columns}")
        
        conn.close()
        
    except Exception as e:
        logger.error(f"❌ Error during migration: {e}")
        if conn:
            conn.close()
        raise

if __name__ == "__main__":
    logger.info("🔄 Starting database migration...")
    migrate_database()
    logger.info("✅ Migration completed successfully!")
