#!/usr/bin/env python3
"""
Backend Pricing Validation Test
Tests specific pricing changes as requested in review:
- GET /api/payments/catalog should show pro_monthly amount=31.0 and pro_yearly amount=313.0
- POST /api/payments/checkout/session with package_id=supporter_custom should work with custom_amount
- POST /api/payments/checkout/session should fail with 400 when custom_amount is missing
"""

import requests
import json
import sys
import uuid

# Use the production URL from frontend/.env
BASE_URL = "https://aimmh-hub-1.preview.emergentagent.com"
API_BASE = f"{BASE_URL}/api"

def register_test_user():
    """Register a fresh test user for authentication"""
    username = f"pricing_test_{uuid.uuid4().hex[:10]}"
    password = "test_password_123"
    
    print(f"🔐 Registering test user: {username}")
    
    register_data = {
        "username": username,
        "password": password
    }
    
    response = requests.post(f"{API_BASE}/auth/register", json=register_data)
    if response.status_code != 200:
        print(f"❌ Registration failed: {response.status_code} - {response.text}")
        return None, None
    
    print(f"✅ User registered successfully")
    return username, password

def login_user(username, password):
    """Login and get session cookies"""
    print(f"🔑 Logging in user: {username}")
    
    login_data = {
        "username": username,
        "password": password
    }
    
    session = requests.Session()
    response = session.post(f"{API_BASE}/auth/login", json=login_data)
    
    if response.status_code != 200:
        print(f"❌ Login failed: {response.status_code} - {response.text}")
        return None
    
    print(f"✅ Login successful")
    return session

def test_payments_catalog(session):
    """Test GET /api/payments/catalog for specific pricing amounts"""
    print("\n📋 Testing GET /api/payments/catalog...")
    
    response = session.get(f"{API_BASE}/payments/catalog")
    
    if response.status_code != 200:
        print(f"❌ Catalog request failed: {response.status_code} - {response.text}")
        return False
    
    try:
        catalog = response.json()
        print(f"✅ Catalog retrieved successfully")
        print(f"📊 Catalog structure: {json.dumps(catalog, indent=2)}")
        
        # Look for pro_monthly and pro_yearly packages
        prices = catalog.get('prices', [])
        
        pro_monthly_found = False
        pro_yearly_found = False
        
        for price in prices:
            package_id = price.get('package_id', '')
            amount = price.get('amount', 0)
            
            if package_id == 'pro_monthly':
                pro_monthly_found = True
                if amount == 31.0:
                    print(f"✅ pro_monthly amount correct: {amount}")
                else:
                    print(f"❌ pro_monthly amount incorrect: expected 31.0, got {amount}")
                    return False
            
            elif package_id == 'pro_yearly':
                pro_yearly_found = True
                if amount == 313.0:
                    print(f"✅ pro_yearly amount correct: {amount}")
                else:
                    print(f"❌ pro_yearly amount incorrect: expected 313.0, got {amount}")
                    return False
        
        if not pro_monthly_found:
            print(f"❌ pro_monthly package not found in catalog")
            return False
        
        if not pro_yearly_found:
            print(f"❌ pro_yearly package not found in catalog")
            return False
        
        return True
        
    except json.JSONDecodeError:
        print(f"❌ Invalid JSON response from catalog")
        return False

def test_checkout_session_with_custom_amount(session):
    """Test POST /api/payments/checkout/session with supporter_custom and custom_amount"""
    print("\n💳 Testing checkout session with custom amount...")
    
    checkout_data = {
        "package_id": "supporter_custom",
        "origin_url": BASE_URL,
        "custom_amount": 12.34
    }
    
    response = session.post(f"{API_BASE}/payments/checkout/session", json=checkout_data)
    
    if response.status_code != 200:
        print(f"❌ Checkout session request failed: {response.status_code} - {response.text}")
        return False
    
    try:
        session_data = response.json()
        print(f"✅ Checkout session created successfully")
        
        # Check for required fields
        session_id = session_data.get('session_id')
        url = session_data.get('url')
        
        if not session_id:
            print(f"❌ Missing session_id in response")
            return False
        
        if not url:
            print(f"❌ Missing url in response")
            return False
        
        print(f"✅ session_id present: {session_id[:20]}...")
        print(f"✅ url present: {url[:50]}...")
        
        return True
        
    except json.JSONDecodeError:
        print(f"❌ Invalid JSON response from checkout session")
        return False

def test_checkout_session_missing_custom_amount(session):
    """Test POST /api/payments/checkout/session without custom_amount should fail with 400"""
    print("\n🚫 Testing checkout session without custom_amount (should fail)...")
    
    checkout_data = {
        "package_id": "supporter_custom",
        "origin_url": BASE_URL
        # Intentionally missing custom_amount
    }
    
    response = session.post(f"{API_BASE}/payments/checkout/session", json=checkout_data)
    
    if response.status_code == 400:
        print(f"✅ Correctly failed with 400 status code")
        print(f"✅ Error response: {response.text}")
        return True
    else:
        print(f"❌ Expected 400 status code, got {response.status_code}")
        print(f"❌ Response: {response.text}")
        return False

def main():
    """Run all pricing validation tests"""
    print("🎯 PRICING VALIDATION TEST SUITE")
    print("=" * 50)
    
    # Register and login test user
    username, password = register_test_user()
    if not username:
        print("❌ Failed to register test user")
        sys.exit(1)
    
    session = login_user(username, password)
    if not session:
        print("❌ Failed to login test user")
        sys.exit(1)
    
    # Run all tests
    tests = [
        ("Payments Catalog", test_payments_catalog),
        ("Checkout with Custom Amount", test_checkout_session_with_custom_amount),
        ("Checkout Missing Custom Amount", test_checkout_session_missing_custom_amount)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n🧪 Running: {test_name}")
        try:
            result = test_func(session)
            results.append((test_name, result))
            if result:
                print(f"✅ {test_name}: PASSED")
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {str(e)}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL PRICING BACKEND TESTS PASSED!")
        return True
    else:
        print("⚠️  Some pricing backend tests failed")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)