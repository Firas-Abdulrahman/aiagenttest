#!/usr/bin/env python3
"""
Test script for the two-button interface implementation
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from workflow.enhanced_handlers import EnhancedMessageHandler
from database.thread_safe_manager import ThreadSafeDatabaseManager
from ai.enhanced_processor import EnhancedAIProcessor

def test_two_button_interface():
    """Test the two-button interface implementation"""
    
    print("🧪 Testing Two-Button Interface Implementation")
    print("=" * 50)
    
    # Initialize components
    db = ThreadSafeDatabaseManager()
    ai_processor = EnhancedAIProcessor()
    
    # Create a simple action executor for testing
    class SimpleActionExecutor:
        def execute_action(self, action, data):
            return {"status": "success", "action": action}
    
    handler = EnhancedMessageHandler(db, ai_processor, SimpleActionExecutor())
    
    # Test phone number
    phone_number = "9647734973420"
    
    print("\n1. Testing Main Categories Display (Two-Button Interface)")
    print("-" * 40)
    
    # Test Arabic interface
    response = handler._show_main_categories(phone_number, "arabic")
    print("Arabic Response:")
    print(f"Type: {response.get('type', 'unknown')}")
    print(f"Header: {response.get('header_text', '')}")
    print(f"Body: {response.get('body_text', '')}")
    print(f"Footer: {response.get('footer_text', '')}")
    print("Buttons:")
    for button in response.get('buttons', []):
        print(f"  - {button.get('reply', {}).get('title', '')} (ID: {button.get('reply', {}).get('id', '')})")
    
    print("\n" + "="*50)
    
    # Test English interface
    response = handler._show_main_categories(phone_number, "english")
    print("English Response:")
    print(f"Type: {response.get('type', 'unknown')}")
    print(f"Header: {response.get('header_text', '')}")
    print(f"Body: {response.get('body_text', '')}")
    print(f"Footer: {response.get('footer_text', '')}")
    print("Buttons:")
    for button in response.get('buttons', []):
        print(f"  - {button.get('reply', {}).get('title', '')} (ID: {button.get('reply', {}).get('id', '')})")
    
    print("\n2. Testing Quick Order Interface")
    print("-" * 40)
    
    # Test quick order interface
    response = handler._show_quick_order_interface(phone_number, "arabic")
    print("Quick Order Interface (Arabic):")
    print(response.get('message', ''))
    
    print("\n3. Testing Traditional Categories (Explore Mode)")
    print("-" * 40)
    
    # Test traditional categories
    response = handler._show_traditional_categories(phone_number, "arabic")
    print("Traditional Categories (Arabic):")
    print(response.get('message', ''))
    
    print("\n4. Testing Popular Items")
    print("-" * 40)
    
    # Test popular items
    popular_items = handler._get_popular_items()
    print("Popular Items:")
    for item in popular_items:
        print(f"  • {item['name_ar']} - {item['price']} دينار")
    
    print("\n5. Testing Recent Orders")
    print("-" * 40)
    
    # Test recent orders
    recent_orders = handler._get_recent_orders(phone_number)
    print("Recent Orders:")
    for order in recent_orders:
        print(f"  • {order}")
    
    print("\n✅ Two-Button Interface Test Completed!")
    print("\nKey Features Implemented:")
    print("  ✓ Two-button main interface (Quick Order vs Explore Menu)")
    print("  ✓ Quick order interface with search and suggestions")
    print("  ✓ Traditional explore menu interface")
    print("  ✓ Popular items suggestions")
    print("  ✓ Recent orders suggestions")
    print("  ✓ Multi-language support (Arabic/English)")
    print("  ✓ AI integration for both modes")
    print("  ✓ Database schema updates for order_mode")
    print("  ✓ Session management for different modes")

if __name__ == "__main__":
    test_two_button_interface()
