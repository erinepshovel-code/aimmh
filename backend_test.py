#!/usr/bin/env python3
"""
Registry API Universal Key Compatibility Test
Tests the registry API cleanup and protection rules after universal-key compatibility changes.
"""

import asyncio
import json
import uuid
import httpx
from typing import Dict, Any, Optional

# Test configuration
BASE_URL = "https://aimmh-hub-1.preview.emergentagent.com"
API_BASE = f"{BASE_URL}/api"

class RegistryAPITest:
    def __init__(self):
        self.session_token: Optional[str] = None
        self.user_email: Optional[str] = None
        self.test_results = []
        
    async def log_result(self, test_name: str, success: bool, details: str = "", data: Any = None):
        """Log test result"""
        result = {
            "test": test_name,
            "success": success,
            "details": details,
            "data": data
        }
        self.test_results.append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name}")
        if details:
            print(f"   Details: {details}")
        if not success and data:
            print(f"   Data: {json.dumps(data, indent=2)}")
        print()

    async def register_fresh_user(self) -> bool:
        """Register a fresh user for testing"""
        test_id = str(uuid.uuid4())[:8]
        self.user_email = f"registry_test_{test_id}"
        password = "TestPass123!"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                # Register user
                register_data = {
                    "username": self.user_email,
                    "password": password
                }
                
                response = await client.post(f"{API_BASE}/auth/register", json=register_data)
                
                if response.status_code != 200:
                    await self.log_result(
                        "Register Fresh User", 
                        False, 
                        f"Registration failed with status {response.status_code}",
                        response.text
                    )
                    return False
                
                # Login to get session token
                login_data = {
                    "username": self.user_email,
                    "password": password
                }
                
                response = await client.post(f"{API_BASE}/auth/login", json=login_data)
                
                if response.status_code != 200:
                    await self.log_result(
                        "Register Fresh User", 
                        False, 
                        f"Login failed with status {response.status_code}",
                        response.text
                    )
                    return False
                
                login_result = response.json()
                self.session_token = login_result.get("access_token")
                
                if not self.session_token:
                    await self.log_result(
                        "Register Fresh User", 
                        False, 
                        "No access token in login response",
                        login_result
                    )
                    return False
                
                await self.log_result(
                    "Register Fresh User", 
                    True, 
                    f"Successfully registered and logged in user: {self.user_email}"
                )
                return True
                
            except Exception as e:
                await self.log_result(
                    "Register Fresh User", 
                    False, 
                    f"Exception during registration: {str(e)}"
                )
                return False

    def get_auth_headers(self) -> Dict[str, str]:
        """Get authorization headers"""
        if not self.session_token:
            raise ValueError("No session token available")
        return {
            "Authorization": f"Bearer {self.session_token}",
            "Content-Type": "application/json"
        }

    async def test_get_registry_structure(self) -> bool:
        """Test GET /api/v1/registry and verify curated universal-key-compatible model sets"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    f"{API_BASE}/v1/registry",
                    headers=self.get_auth_headers()
                )
                
                if response.status_code != 200:
                    await self.log_result(
                        "GET Registry Structure", 
                        False, 
                        f"Registry GET failed with status {response.status_code}",
                        response.text
                    )
                    return False
                
                registry_data = response.json()
                developers = registry_data.get("developers", [])
                
                # Convert to dict for easier lookup
                dev_dict = {dev["developer_id"]: dev for dev in developers}
                
                # Expected universal-key-compatible model sets
                expected_models = {
                    "openai": {"gpt-4o", "gpt-4o-mini", "o1"},
                    "anthropic": {"claude-3-5-sonnet", "claude-3-5-haiku"},
                    "google": {"gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"}
                }
                
                # Check each universal-key developer
                all_checks_passed = True
                details = []
                
                for dev_id, expected_model_set in expected_models.items():
                    if dev_id not in dev_dict:
                        details.append(f"Missing developer: {dev_id}")
                        all_checks_passed = False
                        continue
                    
                    developer = dev_dict[dev_id]
                    actual_models = {model["model_id"] for model in developer.get("models", [])}
                    
                    # Check if expected models are present
                    missing_models = expected_model_set - actual_models
                    if missing_models:
                        details.append(f"{dev_id}: Missing models {missing_models}")
                        all_checks_passed = False
                    
                    # Check if only expected models are present (no extra models)
                    extra_models = actual_models - expected_model_set
                    if extra_models:
                        details.append(f"{dev_id}: Extra models {extra_models}")
                        all_checks_passed = False
                    
                    # Verify auth_type is emergent for universal-key developers
                    if developer.get("auth_type") != "emergent":
                        details.append(f"{dev_id}: Expected auth_type 'emergent', got '{developer.get('auth_type')}'")
                        all_checks_passed = False
                
                # Check that xAI, DeepSeek, Perplexity are still available as separate providers
                expected_other_providers = {"xai", "deepseek", "perplexity"}
                actual_other_providers = {dev_id for dev_id in dev_dict.keys() if dev_id not in expected_models}
                
                missing_providers = expected_other_providers - actual_other_providers
                if missing_providers:
                    details.append(f"Missing other providers: {missing_providers}")
                    all_checks_passed = False
                
                # Verify these providers have openai_compatible auth_type
                for provider in expected_other_providers:
                    if provider in dev_dict:
                        if dev_dict[provider].get("auth_type") != "openai_compatible":
                            details.append(f"{provider}: Expected auth_type 'openai_compatible', got '{dev_dict[provider].get('auth_type')}'")
                            all_checks_passed = False
                
                await self.log_result(
                    "GET Registry Structure", 
                    all_checks_passed, 
                    "; ".join(details) if details else "All expected model sets and providers verified correctly",
                    {"developers_found": list(dev_dict.keys()), "total_developers": len(developers)}
                )
                return all_checks_passed
                
            except Exception as e:
                await self.log_result(
                    "GET Registry Structure", 
                    False, 
                    f"Exception during registry GET: {str(e)}"
                )
                return False

    async def test_post_unsupported_model(self) -> bool:
        """Test POST /api/v1/registry/developer/openai/model with unsupported model and verify rejection"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                # Try to add an unsupported model like 'o3'
                model_data = {
                    "model_id": "o3",
                    "display_name": "o3"
                }
                
                response = await client.post(
                    f"{API_BASE}/v1/registry/developer/openai/model",
                    headers=self.get_auth_headers(),
                    json=model_data
                )
                
                # Should be rejected with 400 status
                if response.status_code == 400:
                    response_data = response.json()
                    detail = response_data.get("detail", "")
                    
                    # Check if rejection message mentions universal-key curation
                    if "universal-key" in detail.lower() and "curated" in detail.lower():
                        await self.log_result(
                            "POST Unsupported Model Rejection", 
                            True, 
                            f"Correctly rejected unsupported model with message: {detail}"
                        )
                        return True
                    else:
                        await self.log_result(
                            "POST Unsupported Model Rejection", 
                            False, 
                            f"Rejected but with unexpected message: {detail}"
                        )
                        return False
                else:
                    await self.log_result(
                        "POST Unsupported Model Rejection", 
                        False, 
                        f"Expected 400 rejection, got status {response.status_code}",
                        response.text
                    )
                    return False
                
            except Exception as e:
                await self.log_result(
                    "POST Unsupported Model Rejection", 
                    False, 
                    f"Exception during unsupported model POST: {str(e)}"
                )
                return False

    async def test_delete_curated_model(self) -> bool:
        """Test DELETE /api/v1/registry/developer/openai/model/gpt-4o and verify rejection"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.delete(
                    f"{API_BASE}/v1/registry/developer/openai/model/gpt-4o",
                    headers=self.get_auth_headers()
                )
                
                # Should be rejected with 400 status
                if response.status_code == 400:
                    response_data = response.json()
                    detail = response_data.get("detail", "")
                    
                    # Check if rejection message mentions universal-key management
                    if "universal-key" in detail.lower() and ("managed" in detail.lower() or "cannot be removed" in detail.lower()):
                        await self.log_result(
                            "DELETE Curated Model Rejection", 
                            True, 
                            f"Correctly rejected curated model deletion with message: {detail}"
                        )
                        return True
                    else:
                        await self.log_result(
                            "DELETE Curated Model Rejection", 
                            False, 
                            f"Rejected but with unexpected message: {detail}"
                        )
                        return False
                else:
                    await self.log_result(
                        "DELETE Curated Model Rejection", 
                        False, 
                        f"Expected 400 rejection, got status {response.status_code}",
                        response.text
                    )
                    return False
                
            except Exception as e:
                await self.log_result(
                    "DELETE Curated Model Rejection", 
                    False, 
                    f"Exception during curated model DELETE: {str(e)}"
                )
                return False

    async def test_delete_universal_developer(self) -> bool:
        """Test DELETE /api/v1/registry/developer/openai and verify rejection"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.delete(
                    f"{API_BASE}/v1/registry/developer/openai",
                    headers=self.get_auth_headers()
                )
                
                # Should be rejected with 400 status
                if response.status_code == 400:
                    response_data = response.json()
                    detail = response_data.get("detail", "")
                    
                    # Check if rejection message mentions universal-key management
                    if "universal-key" in detail.lower() and ("managed" in detail.lower() or "cannot be removed" in detail.lower()):
                        await self.log_result(
                            "DELETE Universal Developer Rejection", 
                            True, 
                            f"Correctly rejected universal developer deletion with message: {detail}"
                        )
                        return True
                    else:
                        await self.log_result(
                            "DELETE Universal Developer Rejection", 
                            False, 
                            f"Rejected but with unexpected message: {detail}"
                        )
                        return False
                else:
                    await self.log_result(
                        "DELETE Universal Developer Rejection", 
                        False, 
                        f"Expected 400 rejection, got status {response.status_code}",
                        response.text
                    )
                    return False
                
            except Exception as e:
                await self.log_result(
                    "DELETE Universal Developer Rejection", 
                    False, 
                    f"Exception during universal developer DELETE: {str(e)}"
                )
                return False

    async def test_registry_response_structure(self) -> bool:
        """Test that normal registry response structure is valid and no regression affects auth-protected access"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                # Test authenticated access
                response = await client.get(
                    f"{API_BASE}/v1/registry",
                    headers=self.get_auth_headers()
                )
                
                if response.status_code != 200:
                    await self.log_result(
                        "Registry Response Structure", 
                        False, 
                        f"Authenticated registry access failed with status {response.status_code}",
                        response.text
                    )
                    return False
                
                registry_data = response.json()
                
                # Validate response structure
                if "developers" not in registry_data:
                    await self.log_result(
                        "Registry Response Structure", 
                        False, 
                        "Missing 'developers' field in registry response",
                        registry_data
                    )
                    return False
                
                developers = registry_data["developers"]
                if not isinstance(developers, list):
                    await self.log_result(
                        "Registry Response Structure", 
                        False, 
                        "Developers field is not a list",
                        {"developers_type": type(developers).__name__}
                    )
                    return False
                
                # Validate developer structure
                for dev in developers:
                    required_fields = ["developer_id", "name", "auth_type", "models"]
                    for field in required_fields:
                        if field not in dev:
                            await self.log_result(
                                "Registry Response Structure", 
                                False, 
                                f"Missing required field '{field}' in developer",
                                dev
                            )
                            return False
                    
                    # Validate models structure
                    models = dev["models"]
                    if not isinstance(models, list):
                        await self.log_result(
                            "Registry Response Structure", 
                            False, 
                            f"Models field is not a list for developer {dev['developer_id']}",
                            dev
                        )
                        return False
                    
                    for model in models:
                        if "model_id" not in model:
                            await self.log_result(
                                "Registry Response Structure", 
                                False, 
                                f"Missing model_id in model for developer {dev['developer_id']}",
                                model
                            )
                            return False
                
                # Test unauthenticated access should fail
                response_unauth = await client.get(f"{API_BASE}/v1/registry")
                
                if response_unauth.status_code != 401:
                    await self.log_result(
                        "Registry Response Structure", 
                        False, 
                        f"Unauthenticated access should return 401, got {response_unauth.status_code}",
                        response_unauth.text
                    )
                    return False
                
                await self.log_result(
                    "Registry Response Structure", 
                    True, 
                    f"Registry response structure valid, auth protection working. Found {len(developers)} developers."
                )
                return True
                
            except Exception as e:
                await self.log_result(
                    "Registry Response Structure", 
                    False, 
                    f"Exception during registry structure test: {str(e)}"
                )
                return False

    async def run_all_tests(self):
        """Run all registry API tests"""
        print("🧪 Starting Registry API Universal Key Compatibility Tests")
        print("=" * 70)
        print()
        
        # Step 1: Register fresh user
        if not await self.register_fresh_user():
            print("❌ Cannot proceed without user registration")
            return
        
        # Step 2: Test registry structure and curated models
        await self.test_get_registry_structure()
        
        # Step 3: Test unsupported model rejection
        await self.test_post_unsupported_model()
        
        # Step 4: Test curated model deletion rejection
        await self.test_delete_curated_model()
        
        # Step 5: Test universal developer deletion rejection
        await self.test_delete_universal_developer()
        
        # Step 6: Test registry response structure and auth
        await self.test_registry_response_structure()
        
        # Summary
        print("=" * 70)
        print("📊 TEST SUMMARY")
        print("=" * 70)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests} ✅")
        print(f"Failed: {failed_tests} ❌")
        print()
        
        if failed_tests > 0:
            print("❌ FAILED TESTS:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  - {result['test']}: {result['details']}")
            print()
        
        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        print(f"Success Rate: {success_rate:.1f}%")
        
        if success_rate == 100:
            print("🎉 ALL TESTS PASSED! Registry API cleanup and protection rules are working correctly.")
        elif success_rate >= 80:
            print("⚠️  Most tests passed, but some issues need attention.")
        else:
            print("🚨 Multiple test failures detected. Registry API needs investigation.")

async def main():
    """Main test runner"""
    test_runner = RegistryAPITest()
    await test_runner.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())