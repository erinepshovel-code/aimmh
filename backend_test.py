#!/usr/bin/env python3
"""
Backend API Testing Script for AIMMH Hub
Tests the new /api/payments/stripe/mode endpoint
"""

import requests
import json
import random
import string
from datetime import datetime

# Configuration
BASE_URL = "https://aimmh-hub-1.preview.emergentagent.com"
API_BASE = f"{BASE_URL}/api"

def generate_test_username():
    """Generate a unique test username"""
    timestamp = str(int(datetime.now().timestamp()))
    random_suffix = ''.join(random.choices(string.digits, k=6))
    return f"stripe_mode_test_{timestamp}_{random_suffix}"

def register_and_login():
    """Register a fresh user and get bearer token"""
    print("=== STEP 1: User Registration & Authentication ===")
    
    username = generate_test_username()
    password = "testpass123"
    
    # Register user
    register_data = {
        "username": username,
        "password": password
    }
    
    print(f"Registering user: {username}")
    register_response = requests.post(f"{API_BASE}/auth/register", json=register_data)
    print(f"Register response: {register_response.status_code}")
    
    if register_response.status_code != 200:
        print(f"Registration failed: {register_response.text}")
        return None, None
    
    # Login to get token
    login_data = {
        "username": username,
        "password": password
    }
    
    print(f"Logging in user: {username}")
    login_response = requests.post(f"{API_BASE}/auth/login", json=login_data)
    print(f"Login response: {login_response.status_code}")
    
    if login_response.status_code != 200:
        print(f"Login failed: {login_response.text}")
        return None, None
    
    login_data = login_response.json()
    access_token = login_data.get("access_token")
    
    if not access_token:
        print("No access token in login response")
        return None, None
    
    print(f"✅ Successfully authenticated user: {username}")
    print(f"✅ Bearer token obtained: {access_token[:20]}...")
    
    return username, access_token

def test_stripe_mode_authenticated(token):
    """Test GET /api/payments/stripe/mode with authentication"""
    print("\n=== STEP 2: Test Authenticated Stripe Mode Endpoint ===")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    print(f"Calling GET {API_BASE}/payments/stripe/mode with Bearer token")
    response = requests.get(f"{API_BASE}/payments/stripe/mode", headers=headers)
    
    print(f"Response status: {response.status_code}")
    print(f"Response headers: {dict(response.headers)}")
    
    if response.status_code != 200:
        print(f"❌ Expected 200, got {response.status_code}")
        print(f"Response body: {response.text}")
        return False
    
    # Check if response is JSON
    try:
        response_data = response.json()
        print(f"✅ Response is valid JSON")
        print(f"Response data: {json.dumps(response_data, indent=2)}")
    except json.JSONDecodeError:
        print(f"❌ Response is not valid JSON: {response.text}")
        return False
    
    # Check required keys
    required_keys = ["stripe_mode", "key_present"]
    missing_keys = []
    
    for key in required_keys:
        if key not in response_data:
            missing_keys.append(key)
    
    if missing_keys:
        print(f"❌ Missing required keys: {missing_keys}")
        return False
    
    print(f"✅ All required keys present: {required_keys}")
    
    # Check that actual key material is NOT leaked
    response_str = json.dumps(response_data).lower()
    suspicious_patterns = [
        "sk_test_", "sk_live_", "pk_test_", "pk_live_",  # Stripe key prefixes
        "rk_test_", "rk_live_",  # Restricted key prefixes
        "whsec_",  # Webhook secret prefix
    ]
    
    leaked_patterns = []
    for pattern in suspicious_patterns:
        if pattern in response_str:
            leaked_patterns.append(pattern)
    
    if leaked_patterns:
        print(f"❌ SECURITY ISSUE: Potential key material leaked - found patterns: {leaked_patterns}")
        return False
    
    print(f"✅ No key material leaked - response does not contain sensitive patterns")
    
    # Validate response structure
    stripe_mode = response_data.get("stripe_mode")
    key_present = response_data.get("key_present")
    
    print(f"stripe_mode: {stripe_mode}")
    print(f"key_present: {key_present}")
    
    # Basic validation
    if stripe_mode not in ["test", "live", None]:
        print(f"⚠️  Unexpected stripe_mode value: {stripe_mode}")
    
    if not isinstance(key_present, bool):
        print(f"⚠️  key_present should be boolean, got: {type(key_present)}")
    
    print(f"✅ Authenticated endpoint test PASSED")
    return True

def test_stripe_mode_unauthenticated():
    """Test GET /api/payments/stripe/mode without authentication"""
    print("\n=== STEP 3: Test Unauthenticated Access ===")
    
    print(f"Calling GET {API_BASE}/payments/stripe/mode without Bearer token")
    response = requests.get(f"{API_BASE}/payments/stripe/mode")
    
    print(f"Response status: {response.status_code}")
    
    if response.status_code != 401:
        print(f"❌ Expected 401 Unauthorized, got {response.status_code}")
        print(f"Response body: {response.text}")
        return False
    
    print(f"✅ Unauthenticated access correctly returns 401 Unauthorized")
    return True

def main():
    """Main test execution"""
    print("🧪 STRIPE MODE ENDPOINT VALIDATION TEST")
    print("=" * 50)
    
    # Step 1: Register and login
    username, token = register_and_login()
    if not token:
        print("❌ Failed to obtain authentication token")
        return False
    
    # Step 2: Test authenticated endpoint
    auth_test_passed = test_stripe_mode_authenticated(token)
    
    # Step 3: Test unauthenticated endpoint
    unauth_test_passed = test_stripe_mode_unauthenticated()
    
    # Summary
    print("\n" + "=" * 50)
    print("🏁 TEST SUMMARY")
    print("=" * 50)
    
    if auth_test_passed and unauth_test_passed:
        print("✅ ALL TESTS PASSED")
        print("✅ Endpoint returns correct JSON structure with stripe_mode and key_present")
        print("✅ No key material leaked in response")
        print("✅ Unauthenticated access properly blocked with 401")
        return True
    else:
        print("❌ SOME TESTS FAILED")
        print(f"   Authenticated test: {'PASS' if auth_test_passed else 'FAIL'}")
        print(f"   Unauthenticated test: {'PASS' if unauth_test_passed else 'FAIL'}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)