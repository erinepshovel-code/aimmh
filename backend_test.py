#!/usr/bin/env python3
"""
Backend API Test for AIMMH Hub Registry
Tests fresh auth flow and registry model validation
"""

import asyncio
import httpx
import json
import uuid
from datetime import datetime

# Test configuration
BASE_URL = "https://aimmh-hub-1.preview.emergentagent.com"
TIMEOUT = 30.0

# Expected model IDs from the review request
EXPECTED_ANTHROPIC_MODELS = {
    "claude-sonnet-4-5-20250929",
    "claude-haiku-4-5-20251001", 
    "claude-opus-4-5-20251101"
}

EXPECTED_GOOGLE_MODELS = {
    "gemini-2.0-flash",
    "gemini-2.5-pro", 
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite"
}

# Old model IDs that should be absent
OLD_ANTHROPIC_MODELS = {
    "claude-3-5-sonnet",
    "claude-3-5-haiku"
}

OLD_GOOGLE_MODELS = {
    "gemini-1.5-pro",
    "gemini-1.5-flash"
}

class RegistryTestResult:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.details = []
        
    def add_pass(self, test_name: str, details: str = ""):
        self.passed += 1
        self.details.append(f"✅ {test_name}: {details}")
        
    def add_fail(self, test_name: str, details: str = ""):
        self.failed += 1
        self.details.append(f"❌ {test_name}: {details}")
        
    def summary(self):
        total = self.passed + self.failed
        status = "PASS" if self.failed == 0 else "FAIL"
        return f"{status} ({self.passed}/{total} tests passed)"

async def test_registry_api():
    """Main test function for registry API validation"""
    result = RegistryTestResult()
    
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            # Step 1: Register fresh user
            username = f"registry_test_{int(datetime.now().timestamp())}"
            password = "test_password_123"
            
            register_data = {
                "username": username,
                "password": password
            }
            
            print(f"🔄 Registering user: {username}")
            register_response = await client.post(
                f"{BASE_URL}/api/auth/register",
                json=register_data
            )
            
            if register_response.status_code != 200:
                result.add_fail("User Registration", f"Status {register_response.status_code}: {register_response.text}")
                return result
                
            register_json = register_response.json()
            access_token = register_json.get("access_token")
            
            if not access_token:
                result.add_fail("User Registration", "No access token in response")
                return result
                
            result.add_pass("User Registration", f"User {username} registered successfully")
            
            # Step 2: Test authentication with /api/auth/me
            print("🔄 Testing authentication...")
            auth_headers = {"Authorization": f"Bearer {access_token}"}
            
            me_response = await client.get(
                f"{BASE_URL}/api/auth/me",
                headers=auth_headers
            )
            
            if me_response.status_code != 200:
                result.add_fail("Authentication Test", f"Status {me_response.status_code}: {me_response.text}")
                return result
                
            result.add_pass("Authentication Test", "Bearer token authentication working")
            
            # Step 3: Call GET /api/v1/registry with auth token
            print("🔄 Fetching registry...")
            registry_response = await client.get(
                f"{BASE_URL}/api/v1/registry",
                headers=auth_headers
            )
            
            if registry_response.status_code != 200:
                result.add_fail("Registry API Call", f"Status {registry_response.status_code}: {registry_response.text}")
                return result
                
            registry_data = registry_response.json()
            result.add_pass("Registry API Call", "Successfully fetched registry")
            
            # Step 4: Validate registry structure
            if "developers" not in registry_data:
                result.add_fail("Registry Structure", "Missing 'developers' field")
                return result
                
            developers = registry_data["developers"]
            if not isinstance(developers, list):
                result.add_fail("Registry Structure", "'developers' is not a list")
                return result
                
            result.add_pass("Registry Structure", f"Found {len(developers)} developers")
            
            # Step 5: Find and validate Anthropic models
            anthropic_dev = None
            google_dev = None
            
            for dev in developers:
                if dev.get("developer_id") == "anthropic":
                    anthropic_dev = dev
                elif dev.get("developer_id") == "google":
                    google_dev = dev
                    
            # Test Anthropic models
            if not anthropic_dev:
                result.add_fail("Anthropic Developer", "Anthropic developer not found")
            else:
                anthropic_models = {model.get("model_id") for model in anthropic_dev.get("models", [])}
                
                # Check expected models are present
                missing_anthropic = EXPECTED_ANTHROPIC_MODELS - anthropic_models
                if missing_anthropic:
                    result.add_fail("Anthropic Expected Models", f"Missing: {missing_anthropic}")
                else:
                    result.add_pass("Anthropic Expected Models", f"All expected models present: {EXPECTED_ANTHROPIC_MODELS}")
                
                # Check old models are absent
                present_old_anthropic = OLD_ANTHROPIC_MODELS & anthropic_models
                if present_old_anthropic:
                    result.add_fail("Anthropic Old Models Absent", f"Old models still present: {present_old_anthropic}")
                else:
                    result.add_pass("Anthropic Old Models Absent", f"Old models correctly absent: {OLD_ANTHROPIC_MODELS}")
                    
            # Test Google models
            if not google_dev:
                result.add_fail("Google Developer", "Google developer not found")
            else:
                google_models = {model.get("model_id") for model in google_dev.get("models", [])}
                
                # Check expected models are present
                missing_google = EXPECTED_GOOGLE_MODELS - google_models
                if missing_google:
                    result.add_fail("Google Expected Models", f"Missing: {missing_google}")
                else:
                    result.add_pass("Google Expected Models", f"All expected models present: {EXPECTED_GOOGLE_MODELS}")
                
                # Check old models are absent
                present_old_google = OLD_GOOGLE_MODELS & google_models
                if present_old_google:
                    result.add_fail("Google Old Models Absent", f"Old models still present: {present_old_google}")
                else:
                    result.add_pass("Google Old Models Absent", f"Old models correctly absent: {OLD_GOOGLE_MODELS}")
            
            # Step 6: Print registry response snippet for verification
            print("\n📋 Registry Response Snippet:")
            print("=" * 50)
            
            for dev in developers:
                if dev.get("developer_id") in ["anthropic", "google"]:
                    print(f"\n{dev.get('name', dev.get('developer_id'))} ({dev.get('developer_id')}):")
                    for model in dev.get("models", []):
                        print(f"  - {model.get('model_id')} ({model.get('display_name', 'N/A')})")
                        
            print("=" * 50)
            
        except httpx.TimeoutException:
            result.add_fail("Network", "Request timeout")
        except httpx.RequestError as e:
            result.add_fail("Network", f"Request error: {e}")
        except Exception as e:
            result.add_fail("Unexpected Error", f"Exception: {e}")
            
    return result

async def main():
    """Main entry point"""
    print("🚀 Starting AIMMH Hub Registry API Test")
    print(f"📍 Base URL: {BASE_URL}")
    print("=" * 60)
    
    result = await test_registry_api()
    
    print("\n📊 Test Results:")
    print("=" * 60)
    for detail in result.details:
        print(detail)
        
    print("=" * 60)
    print(f"🏁 Final Result: {result.summary()}")
    
    if result.failed > 0:
        exit(1)
    else:
        print("🎉 All tests passed!")

if __name__ == "__main__":
    asyncio.run(main())