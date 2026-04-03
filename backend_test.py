#!/usr/bin/env python3
"""
Backend regression test for cookie-based auth changes
Testing on: https://aimmh-hub-1.preview.emergentagent.com

Test scenarios:
1) Register fresh user via /api/auth/register and verify Set-Cookie includes access_token
2) Call /api/auth/me using cookies only (no Authorization header) and expect 200
3) Call a protected API (/api/v1/registry) with cookies only and expect 200
4) Call /api/auth/logout and verify subsequent /api/auth/me returns 401
5) Confirm Google session endpoint still responds correctly for missing X-Session-ID (400)
"""

import requests
import json
import random
import string
from datetime import datetime

# Base URL from frontend .env
BASE_URL = "https://aimmh-hub-1.preview.emergentagent.com"

def generate_test_user():
    """Generate a unique test username"""
    timestamp = int(datetime.now().timestamp())
    random_suffix = ''.join(random.choices(string.digits, k=6))
    return f"authtest_{timestamp}_{random_suffix}"

def test_cookie_auth_regression():
    """Main test function for cookie-based auth regression"""
    print("🔍 BACKEND REGRESSION TEST: Cookie-based Auth Changes")
    print(f"🌐 Testing on: {BASE_URL}")
    print("=" * 80)
    
    # Generate fresh test user
    test_username = generate_test_user()
    test_password = "testpass123"
    
    print(f"👤 Test user: {test_username}")
    print()
    
    # Test results tracking
    results = {
        "register_with_cookie": False,
        "me_with_cookies_only": False,
        "protected_api_with_cookies": False,
        "logout_and_verify": False,
        "google_session_400": False
    }
    
    # Session to maintain cookies
    session = requests.Session()
    
    try:
        # Test 1: Register fresh user and verify Set-Cookie includes access_token
        print("1️⃣ Testing user registration with Set-Cookie access_token...")
        register_data = {
            "username": test_username,
            "password": test_password
        }
        
        register_response = session.post(
            f"{BASE_URL}/api/auth/register",
            json=register_data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"   📤 POST /api/auth/register")
        print(f"   📊 Status: {register_response.status_code}")
        
        if register_response.status_code == 200:
            # Check for Set-Cookie header with access_token
            set_cookie_header = register_response.headers.get('Set-Cookie', '')
            if 'access_token' in set_cookie_header:
                print(f"   ✅ Set-Cookie contains access_token")
                print(f"   🍪 Cookie: {set_cookie_header[:100]}...")
                results["register_with_cookie"] = True
            else:
                print(f"   ❌ Set-Cookie missing access_token")
                print(f"   🍪 Cookie: {set_cookie_header}")
        else:
            print(f"   ❌ Registration failed: {register_response.text}")
        
        print()
        
        # Test 2: Call /api/auth/me using cookies only (no Authorization header)
        print("2️⃣ Testing /api/auth/me with cookies only...")
        
        me_response = session.get(f"{BASE_URL}/api/auth/me")
        
        print(f"   📤 GET /api/auth/me (cookies only)")
        print(f"   📊 Status: {me_response.status_code}")
        
        if me_response.status_code == 200:
            me_data = me_response.json()
            # For username/password auth, the username is stored in 'email' field
            if me_data.get('email') == test_username:
                print(f"   ✅ Cookie auth successful - user: {me_data.get('email')}")
                results["me_with_cookies_only"] = True
            else:
                print(f"   ❌ Wrong user returned: {me_data}")
        else:
            print(f"   ❌ Cookie auth failed: {me_response.text}")
        
        print()
        
        # Test 3: Call protected API (/api/v1/registry) with cookies only
        print("3️⃣ Testing protected API /api/v1/registry with cookies only...")
        
        registry_response = session.get(f"{BASE_URL}/api/v1/registry")
        
        print(f"   📤 GET /api/v1/registry (cookies only)")
        print(f"   📊 Status: {registry_response.status_code}")
        
        if registry_response.status_code == 200:
            registry_data = registry_response.json()
            if 'developers' in registry_data:
                print(f"   ✅ Protected API accessible with cookies")
                print(f"   📋 Found {len(registry_data['developers'])} developers")
                results["protected_api_with_cookies"] = True
            else:
                print(f"   ❌ Unexpected registry response: {registry_data}")
        else:
            print(f"   ❌ Protected API failed: {registry_response.text}")
        
        print()
        
        # Test 4: Call /api/auth/logout and verify subsequent /api/auth/me returns 401
        print("4️⃣ Testing logout and session invalidation...")
        
        logout_response = session.post(f"{BASE_URL}/api/auth/logout")
        
        print(f"   📤 POST /api/auth/logout")
        print(f"   📊 Status: {logout_response.status_code}")
        
        if logout_response.status_code == 200:
            print(f"   ✅ Logout successful")
            
            # Now test that /api/auth/me returns 401
            me_after_logout = session.get(f"{BASE_URL}/api/auth/me")
            print(f"   📤 GET /api/auth/me (after logout)")
            print(f"   📊 Status: {me_after_logout.status_code}")
            
            if me_after_logout.status_code == 401:
                print(f"   ✅ Session properly invalidated - 401 as expected")
                results["logout_and_verify"] = True
            else:
                print(f"   ❌ Session not invalidated - got {me_after_logout.status_code}")
        else:
            print(f"   ❌ Logout failed: {logout_response.text}")
        
        print()
        
        # Test 5: Confirm Google session endpoint responds correctly for missing X-Session-ID (400)
        print("5️⃣ Testing Google session endpoint without X-Session-ID...")
        
        # Create new session for this test (no cookies needed)
        google_session = requests.Session()
        google_response = google_session.post(f"{BASE_URL}/api/auth/google/session")
        
        print(f"   📤 POST /api/auth/google/session (no X-Session-ID header)")
        print(f"   📊 Status: {google_response.status_code}")
        
        if google_response.status_code == 400:
            print(f"   ✅ Google session endpoint correctly returns 400 for missing X-Session-ID")
            results["google_session_400"] = True
        else:
            print(f"   ❌ Expected 400, got {google_response.status_code}: {google_response.text}")
        
        print()
        
    except Exception as e:
        print(f"❌ Test execution error: {str(e)}")
    
    # Summary
    print("=" * 80)
    print("📋 TEST SUMMARY")
    print("=" * 80)
    
    passed_tests = sum(results.values())
    total_tests = len(results)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print()
    print(f"🎯 OVERALL: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 ALL COOKIE-BASED AUTH REGRESSION TESTS PASSED!")
        return True
    else:
        print("⚠️  SOME TESTS FAILED - REGRESSION DETECTED")
        return False

if __name__ == "__main__":
    success = test_cookie_auth_regression()
    exit(0 if success else 1)