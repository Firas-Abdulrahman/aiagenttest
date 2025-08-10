#!/usr/bin/env python3
"""
Test script for service selection validation
"""

import requests
import json

def test_service_validation():
    """Test service selection validation with invalid number '12'"""
    
    # Test data
    test_data = {
        "phone_number": "9647734973420",
        "message": "12",
        "customer_name": "Test User"
    }
    
    # First, set up the service selection step by going through the flow
    print("Setting up service selection step...")
    
    # Step 1: Start with hello
    response = requests.post("http://localhost:5000/simulate", 
                           json={"phone_number": "9647734973420", "message": "مرحبا", "customer_name": "Test User"})
    print(f"Step 1 - Hello: {response.status_code}")
    
    # Step 2: Select language (1 for Arabic)
    response = requests.post("http://localhost:5000/simulate", 
                           json={"phone_number": "9647734973420", "message": "1", "customer_name": "Test User"})
    print(f"Step 2 - Language: {response.status_code}")
    
    # Step 3: Select category (1 for Cold Drinks)
    response = requests.post("http://localhost:5000/simulate", 
                           json={"phone_number": "9647734973420", "message": "1", "customer_name": "Test User"})
    print(f"Step 3 - Category: {response.status_code}")
    
    # Step 4: Select sub-category (1 for Iced Coffee)
    response = requests.post("http://localhost:5000/simulate", 
                           json={"phone_number": "9647734973420", "message": "1", "customer_name": "Test User"})
    print(f"Step 4 - Sub-category: {response.status_code}")
    
    # Step 5: Select quantity (1)
    response = requests.post("http://localhost:5000/simulate", 
                           json={"phone_number": "9647734973420", "message": "1", "customer_name": "Test User"})
    print(f"Step 5 - Quantity: {response.status_code}")
    
    # Step 6: No more items (2)
    response = requests.post("http://localhost:5000/simulate", 
                           json={"phone_number": "9647734973420", "message": "2", "customer_name": "Test User"})
    print(f"Step 6 - No more items: {response.status_code}")
    
    # Now test the invalid service selection
    print("\nTesting invalid service selection with '12'...")
    response = requests.post("http://localhost:5000/simulate", json=test_data)
    
    if response.status_code == 200:
        result = response.json()
        content = result.get('simulation', {}).get('response', {}).get('content', '')
        print(f"Response: {content}")
        
        # Check if it's an error message
        if "غير صحيح" in content or "invalid" in content.lower():
            print("✅ SUCCESS: Invalid service number correctly rejected!")
        else:
            print("❌ FAILURE: Invalid service number was accepted!")
    else:
        print(f"❌ Error: {response.status_code}")

if __name__ == "__main__":
    test_service_validation() 