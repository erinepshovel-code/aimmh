#!/usr/bin/env python3
"""
Backend test for Registry enrichment backend: developer websites, lightweight verification, hub feedback message ids
"""

import asyncio
import json
import uuid
import requests
import time
from typing import Dict, Any, Optional

# Test configuration
BASE_URL = "https://aimmh-hub.preview.emergentagent.com"
API_BASE = f"{BASE_URL}/api"

class RegistryTestRunner:
    def __init__(self):
        self.session = requests.Session()
        self.auth_token = None
        self.user_id = None
        self.test_results = []
        
    def log_result(self, test_name: str, success: bool, details: str = ""):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name}")
        if details:
            print(f"   Details: {details}")
        self.test_results.append({
            "test": test_name,
            "success": success,
            "details": details
        })
        
    def register_and_login(self) -> bool:
        """Register a new user and get auth token"""
        try:
            # Generate unique test user
            test_id = str(int(time.time() * 1000))[-10:]
            username = f"regtest_{test_id}"
            password = "TestPass123!"
            
            # Register user
            register_data = {
                "username": username,
                "password": password,
                "email": f"{username}@test.com"
            }
            
            resp = self.session.post(f"{API_BASE}/auth/register", json=register_data)
            if resp.status_code != 200:
                self.log_result("User Registration", False, f"Status {resp.status_code}: {resp.text}")
                return False
                
            # Get JWT token from registration response
            register_result = resp.json()
            self.auth_token = register_result.get("access_token")
            if not self.auth_token:
                self.log_result("JWT Token Extraction", False, "No access_token in registration response")
                return False
                
            # Set Authorization header for all future requests
            self.session.headers.update({"Authorization": f"Bearer {self.auth_token}"})
                
            # Verify auth works
            resp = self.session.get(f"{API_BASE}/auth/me")
            if resp.status_code != 200:
                self.log_result("Auth Verification", False, f"Status {resp.status_code}: {resp.text}")
                return False
                
            user_data = resp.json()
            self.user_id = user_data.get("id")
            self.log_result("Authentication Flow", True, f"User: {username}, ID: {self.user_id}")
            return True
            
        except Exception as e:
            self.log_result("Authentication Flow", False, f"Exception: {str(e)}")
            return False
            
    def test_registry_get_with_websites(self) -> bool:
        """Test GET /api/v1/registry returns developer websites"""
        try:
            resp = self.session.get(f"{API_BASE}/v1/registry")
            if resp.status_code != 200:
                self.log_result("GET /api/v1/registry", False, f"Status {resp.status_code}: {resp.text}")
                return False
                
            data = resp.json()
            developers = data.get("developers", [])
            
            if not developers:
                self.log_result("GET /api/v1/registry", False, "No developers returned")
                return False
                
            # Check for website fields in default developers
            websites_found = []
            for dev in developers:
                if dev.get("website"):
                    websites_found.append(f"{dev['developer_id']}: {dev['website']}")
                    
            if not websites_found:
                self.log_result("GET /api/v1/registry - websites", False, "No websites found in default developers")
                return False
                
            self.log_result("GET /api/v1/registry - websites", True, f"Found websites: {', '.join(websites_found)}")
            return True
            
        except Exception as e:
            self.log_result("GET /api/v1/registry", False, f"Exception: {str(e)}")
            return False
            
    def test_add_developer_with_website(self) -> bool:
        """Test POST /api/v1/registry/developer with website field"""
        try:
            test_id = str(int(time.time() * 1000))[-8:]
            developer_data = {
                "developer_id": f"test_dev_{test_id}",
                "name": f"Test Developer {test_id}",
                "auth_type": "openai_compatible",
                "base_url": "https://api.example.com/v1",
                "website": "https://example.com",
                "models": [
                    {
                        "model_id": f"test-model-{test_id}",
                        "display_name": f"Test Model {test_id}",
                        "enabled": True
                    }
                ]
            }
            
            resp = self.session.post(f"{API_BASE}/v1/registry/developer", json=developer_data)
            if resp.status_code != 200:
                self.log_result("POST /api/v1/registry/developer", False, f"Status {resp.status_code}: {resp.text}")
                return False
                
            # Verify the developer was added with website
            resp = self.session.get(f"{API_BASE}/v1/registry")
            if resp.status_code != 200:
                self.log_result("POST /api/v1/registry/developer - verification", False, f"Status {resp.status_code}: {resp.text}")
                return False
                
            data = resp.json()
            developers = data.get("developers", [])
            
            added_dev = None
            for dev in developers:
                if dev["developer_id"] == developer_data["developer_id"]:
                    added_dev = dev
                    break
                    
            if not added_dev:
                self.log_result("POST /api/v1/registry/developer - verification", False, "Added developer not found in registry")
                return False
                
            if added_dev.get("website") != developer_data["website"]:
                self.log_result("POST /api/v1/registry/developer - website", False, f"Website mismatch: expected {developer_data['website']}, got {added_dev.get('website')}")
                return False
                
            self.log_result("POST /api/v1/registry/developer", True, f"Added developer with website: {added_dev['website']}")
            return True
            
        except Exception as e:
            self.log_result("POST /api/v1/registry/developer", False, f"Exception: {str(e)}")
            return False
            
    def test_verify_model_endpoint(self) -> bool:
        """Test POST /api/v1/registry/verify/model"""
        try:
            # Test with missing key scenario (should be common)
            verify_data = {
                "developer_id": "openai",
                "model_id": "gpt-4o",
                "mode": "strict"
            }
            
            resp = self.session.post(f"{API_BASE}/v1/registry/verify/model", json=verify_data)
            if resp.status_code != 200:
                self.log_result("POST /api/v1/registry/verify/model", False, f"Status {resp.status_code}: {resp.text}")
                return False
                
            data = resp.json()
            
            # Verify response structure
            required_fields = ["scope", "verification_mode", "verified_count", "total_count", "results"]
            for field in required_fields:
                if field not in data:
                    self.log_result("POST /api/v1/registry/verify/model - structure", False, f"Missing field: {field}")
                    return False
                    
            if data["scope"] != "model":
                self.log_result("POST /api/v1/registry/verify/model - scope", False, f"Expected scope 'model', got '{data['scope']}'")
                return False
                
            if data["verification_mode"] != "strict":
                self.log_result("POST /api/v1/registry/verify/model - mode", False, f"Expected mode 'strict', got '{data['verification_mode']}'")
                return False
                
            if len(data["results"]) != 1:
                self.log_result("POST /api/v1/registry/verify/model - results", False, f"Expected 1 result, got {len(data['results'])}")
                return False
                
            result = data["results"][0]
            result_fields = ["scope", "developer_id", "model_id", "status", "message", "verification_mode"]
            for field in result_fields:
                if field not in result:
                    self.log_result("POST /api/v1/registry/verify/model - result structure", False, f"Missing result field: {field}")
                    return False
                    
            self.log_result("POST /api/v1/registry/verify/model", True, f"Status: {result['status']}, Message: {result['message']}")
            return True
            
        except Exception as e:
            self.log_result("POST /api/v1/registry/verify/model", False, f"Exception: {str(e)}")
            return False
            
    def test_verify_developer_endpoint(self) -> bool:
        """Test POST /api/v1/registry/verify/developer/{developer_id}"""
        try:
            resp = self.session.post(f"{API_BASE}/v1/registry/verify/developer/openai")
            if resp.status_code != 200:
                self.log_result("POST /api/v1/registry/verify/developer", False, f"Status {resp.status_code}: {resp.text}")
                return False
                
            data = resp.json()
            
            # Verify response structure
            required_fields = ["scope", "verification_mode", "verified_count", "total_count", "results"]
            for field in required_fields:
                if field not in data:
                    self.log_result("POST /api/v1/registry/verify/developer - structure", False, f"Missing field: {field}")
                    return False
                    
            if data["scope"] != "developer":
                self.log_result("POST /api/v1/registry/verify/developer - scope", False, f"Expected scope 'developer', got '{data['scope']}'")
                return False
                
            if data["verification_mode"] != "light":
                self.log_result("POST /api/v1/registry/verify/developer - mode", False, f"Expected mode 'light', got '{data['verification_mode']}'")
                return False
                
            # Should have results for OpenAI models
            if not data["results"]:
                self.log_result("POST /api/v1/registry/verify/developer - results", False, "No results returned")
                return False
                
            # Check for free-tier semantics in messages
            free_tier_messages = []
            for result in data["results"]:
                if "free-tier" in result.get("message", "").lower() or "representative" in result.get("message", "").lower():
                    free_tier_messages.append(result["message"])
                    
            self.log_result("POST /api/v1/registry/verify/developer", True, f"Results: {len(data['results'])}, Free-tier messages: {len(free_tier_messages)}")
            return True
            
        except Exception as e:
            self.log_result("POST /api/v1/registry/verify/developer", False, f"Exception: {str(e)}")
            return False
            
    def test_verify_all_endpoint(self) -> bool:
        """Test POST /api/v1/registry/verify/all"""
        try:
            resp = self.session.post(f"{API_BASE}/v1/registry/verify/all")
            if resp.status_code != 200:
                self.log_result("POST /api/v1/registry/verify/all", False, f"Status {resp.status_code}: {resp.text}")
                return False
                
            data = resp.json()
            
            # Verify response structure
            required_fields = ["scope", "verification_mode", "verified_count", "total_count", "results"]
            for field in required_fields:
                if field not in data:
                    self.log_result("POST /api/v1/registry/verify/all - structure", False, f"Missing field: {field}")
                    return False
                    
            if data["scope"] != "registry":
                self.log_result("POST /api/v1/registry/verify/all - scope", False, f"Expected scope 'registry', got '{data['scope']}'")
                return False
                
            if data["verification_mode"] != "light":
                self.log_result("POST /api/v1/registry/verify/all - mode", False, f"Expected mode 'light', got '{data['verification_mode']}'")
                return False
                
            # Should have results for all developers
            if not data["results"]:
                self.log_result("POST /api/v1/registry/verify/all - results", False, "No results returned")
                return False
                
            # Count results by developer
            dev_counts = {}
            for result in data["results"]:
                dev_id = result.get("developer_id", "unknown")
                dev_counts[dev_id] = dev_counts.get(dev_id, 0) + 1
                
            self.log_result("POST /api/v1/registry/verify/all", True, f"Total results: {len(data['results'])}, Developers: {list(dev_counts.keys())}")
            return True
            
        except Exception as e:
            self.log_result("POST /api/v1/registry/verify/all", False, f"Exception: {str(e)}")
            return False
            
    def test_hub_run_message_id_persistence(self) -> bool:
        """Test hub run result persistence enhancement with message_id"""
        try:
            # First create a hub instance
            instance_data = {
                "name": f"Test Instance {int(time.time())}",
                "model_id": "gpt-4o",
                "archived": False
            }
            
            resp = self.session.post(f"{API_BASE}/v1/hub/instances", json=instance_data)
            if resp.status_code != 200:
                self.log_result("Hub Instance Creation", False, f"Status {resp.status_code}: {resp.text}")
                return False
                
            instance = resp.json()
            instance_id = instance["instance_id"]
            
            # Create a minimal hub run
            run_data = {
                "prompt": "Test prompt for message ID persistence",
                "label": "Message ID Test Run",
                "stages": [
                    {
                        "pattern": "fan_out",
                        "name": "Test Stage",
                        "prompt": "Respond with a brief test message",
                        "participants": [
                            {
                                "source_type": "instance",
                                "source_id": instance_id
                            }
                        ]
                    }
                ],
                "persist_instance_threads": True
            }
            
            resp = self.session.post(f"{API_BASE}/v1/hub/runs", json=run_data)
            if resp.status_code != 200:
                self.log_result("Hub Run Creation", False, f"Status {resp.status_code}: {resp.text}")
                return False
                
            run_result = resp.json()
            run_id = run_result["run_id"]
            
            # Fetch the run details
            resp = self.session.get(f"{API_BASE}/v1/hub/runs/{run_id}")
            if resp.status_code != 200:
                self.log_result("Hub Run Fetch", False, f"Status {resp.status_code}: {resp.text}")
                return False
                
            run_details = resp.json()
            
            # Check for message_id in results
            results = run_details.get("results", [])
            if not results:
                self.log_result("Hub Run Results", False, "No results found in run")
                return False
                
            message_ids_found = []
            for result in results:
                if result.get("message_id"):
                    message_ids_found.append(result["message_id"])
                    
            if not message_ids_found:
                self.log_result("Hub Run Message IDs", False, "No message_id fields found in results")
                return False
                
            self.log_result("Hub Run Message ID Persistence", True, f"Found {len(message_ids_found)} message IDs in results")
            return True
            
        except Exception as e:
            self.log_result("Hub Run Message ID Persistence", False, f"Exception: {str(e)}")
            return False
            
    def test_unauthenticated_access(self) -> bool:
        """Test that verification endpoints require authentication"""
        try:
            # Create a new session without auth
            unauth_session = requests.Session()
            
            endpoints_to_test = [
                "/v1/registry/verify/model",
                "/v1/registry/verify/developer/openai",
                "/v1/registry/verify/all"
            ]
            
            all_protected = True
            for endpoint in endpoints_to_test:
                if endpoint == "/v1/registry/verify/model":
                    resp = unauth_session.post(f"{API_BASE}{endpoint}", json={"developer_id": "openai", "model_id": "gpt-4o"})
                else:
                    resp = unauth_session.post(f"{API_BASE}{endpoint}")
                    
                if resp.status_code != 401:
                    self.log_result(f"Auth Protection {endpoint}", False, f"Expected 401, got {resp.status_code}")
                    all_protected = False
                    
            if all_protected:
                self.log_result("Authentication Protection", True, "All verification endpoints properly protected")
                return True
            else:
                return False
                
        except Exception as e:
            self.log_result("Authentication Protection", False, f"Exception: {str(e)}")
            return False
            
    def run_all_tests(self):
        """Run all registry enrichment tests"""
        print("🧪 Starting Registry Enrichment Backend Tests")
        print("=" * 60)
        
        # Authentication
        if not self.register_and_login():
            print("❌ Authentication failed - stopping tests")
            return
            
        # Test unauthenticated access first
        self.test_unauthenticated_access()
        
        # Registry tests
        self.test_registry_get_with_websites()
        self.test_add_developer_with_website()
        
        # Verification tests
        self.test_verify_model_endpoint()
        self.test_verify_developer_endpoint()
        self.test_verify_all_endpoint()
        
        # Hub message ID persistence test
        self.test_hub_run_message_id_persistence()
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for result in self.test_results if result["success"])
        total = len(self.test_results)
        
        for result in self.test_results:
            status = "✅" if result["success"] else "❌"
            print(f"{status} {result['test']}")
            
        print(f"\n🎯 Results: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All tests passed!")
        else:
            print(f"⚠️  {total - passed} tests failed")
            
        return passed == total

if __name__ == "__main__":
    runner = RegistryTestRunner()
    success = runner.run_all_tests()
    exit(0 if success else 1)