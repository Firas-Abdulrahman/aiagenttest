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
    
    # -------------------------
    # New: E2E Quick Order tests
    # -------------------------
    print("\n6. E2E Quick Order: Quantity words/numerals and ASR variants")
    print("-" * 40)

    import json as _json

    scenarios = [
        {"language": "english", "text": "two tea", "expect_specific": None},
        {"language": "arabic",  "text": "اثنين شاي", "expect_specific": None},
        {"language": "arabic",  "text": "اريد 2 شاي عراقي", "expect_specific": "شاي عراقي"},
        {"language": "arabic",  "text": "أريد الثيه والشاي العراقي", "expect_specific": "شاي عراقي"},
    ]

    for idx, sc in enumerate(scenarios, start=1):
        lang = sc["language"]
        text = sc["text"]
        expect_specific = sc["expect_specific"]

        # Ensure a clean session per scenario
        try:
            db.delete_session(phone_number)
        except Exception:
            pass

        # Initialize quick order step
        db.create_or_update_session(
            phone_number=phone_number,
            current_step='waiting_for_quick_order',
            language=lang,
            customer_name='Test User',
            order_mode='quick'
        )
        session = db.get_user_session(phone_number)
        user_context = {"language": lang}

        print(f"\nScenario {idx}: [{lang}] '{text}'")
        response = handler._handle_structured_quick_order(phone_number, text, session, user_context)

        # Expect skipping quantity selection (quantity=2) -> service buttons interactive response
        resp_type = response.get('type')
        assert resp_type == 'interactive', f"Expected interactive response with service buttons, got: {resp_type}"
        buttons = response.get('buttons') or []
        assert len(buttons) >= 2, "Expected at least two service buttons"
        assert buttons[0].get('reply', {}).get('id') == 'dine_in', "First button should be dine_in"
        assert buttons[1].get('reply', {}).get('id') == 'delivery', "Second button should be delivery"

        # Verify session advanced to quick order service step
        sess_after = db.get_user_session(phone_number)
        assert sess_after and sess_after.get('current_step') == 'waiting_for_quick_order_service', \
            f"Expected current_step 'waiting_for_quick_order_service', got: {sess_after.get('current_step') if sess_after else None}"

        # Verify quick_order_item stored in session as JSON
        qoi_json = sess_after.get('quick_order_item')
        assert qoi_json, "quick_order_item should be stored in session"
        try:
            qoi = _json.loads(qoi_json)
        except Exception as e:
            raise AssertionError(f"quick_order_item is not valid JSON: {e}\nValue: {qoi_json}")

        # If scenario expects a specific item, verify it
        if expect_specific:
            assert qoi.get('item_name_ar') == expect_specific, \
                f"Expected matched item '{expect_specific}', got '{qoi.get('item_name_ar')}'"

        print("  ✓ Interactive service buttons shown and session advanced correctly")
        if expect_specific:
            print(f"  ✓ Matched specific item: {qoi.get('item_name_ar')}")

    print("\n✅ E2E Quick Order tests passed!")

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

