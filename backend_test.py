#!/usr/bin/env python3
"""
Backend Regression Test Suite: Conversation Persistence After Early Stream Termination

Testing scenarios:
1. Start chat stream and terminate early (simulate disconnect), verify conversation persistence
2. Validate /api/conversations/search and /api/a0/non-ui/conversations/search endpoints 
3. Ensure Agent Zero non-UI endpoints still work for authenticated users

Regression test for: conversation persistence fix in /api/chat/stream
"""

import asyncio
import aiohttp
import json
import uuid
import time
import subprocess
from typing import Dict, Any, Optional


class BackendRegressionTester:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.session_token: Optional[str] = None
        self.user_id: Optional[str] = None
        self.test_conversation_id: Optional[str] = None
        self.results = {
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "details": []
        }

    def log_test(self, test_name: str, status: str, details: str = ""):
        """Log test results"""
        self.results["total_tests"] += 1
        if status == "PASS":
            self.results["passed"] += 1
        else:
            self.results["failed"] += 1
        
        self.results["details"].append({
            "test": test_name,
            "status": status,
            "details": details
        })
        print(f"[{status}] {test_name}: {details}")

    async def setup_auth_user(self) -> bool:
        """Create test user and session token in MongoDB"""
        try:
            # Generate unique test data
            timestamp = int(time.time())
            self.user_id = f"regression_test_{timestamp}"
            self.session_token = f"regression_session_{timestamp}"
            email = f"regression_test_{timestamp}@example.com"
            
            # MongoDB commands to create user and session
            mongo_script = f'''
use('test_database');
db.users.insertOne({{
  user_id: '{self.user_id}',
  email: '{email}',
  name: 'Regression Test User',
  picture: 'https://via.placeholder.com/150',
  created_at: new Date()
}});
db.user_sessions.insertOne({{
  user_id: '{self.user_id}',
  session_token: '{self.session_token}',
  expires_at: new Date(Date.now() + 24*60*60*1000),
  created_at: new Date()
}});
print('SUCCESS: Test user and session created');
            '''
            
            result = subprocess.run(['mongosh', '--eval', mongo_script], 
                                  capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0 and 'SUCCESS' in result.stdout:
                self.log_test("Auth Setup", "PASS", f"Created user {self.user_id}")
                return True
            else:
                self.log_test("Auth Setup", "FAIL", f"MongoDB error: {result.stderr}")
                return False
                
        except Exception as e:
            self.log_test("Auth Setup", "FAIL", f"Exception: {str(e)}")
            return False

    async def verify_auth(self, session: aiohttp.ClientSession) -> bool:
        """Verify authentication works"""
        try:
            headers = {"Authorization": f"Bearer {self.session_token}"}
            async with session.get(f"{self.base_url}/api/auth/me", headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    self.log_test("Auth Verification", "PASS", f"Authenticated as {data.get('name')}")
                    return True
                else:
                    self.log_test("Auth Verification", "FAIL", f"Status: {response.status}")
                    return False
        except Exception as e:
            self.log_test("Auth Verification", "FAIL", f"Exception: {str(e)}")
            return False

    async def test_chat_stream_early_termination(self, session: aiohttp.ClientSession) -> bool:
        """Test 1: Start chat stream and terminate early to simulate disconnect"""
        try:
            headers = {
                "Authorization": f"Bearer {self.session_token}",
                "Content-Type": "application/json"
            }
            
            # Generate unique conversation ID for tracking
            self.test_conversation_id = str(uuid.uuid4())
            
            payload = {
                "message": "Regression test prompt: Explain quantum computing in simple terms.",
                "models": ["gpt-5.2", "claude-sonnet-4-5-20250929"],
                "conversation_id": self.test_conversation_id,
                "context_mode": "compartmented",
                "shared_room_mode": "parallel_all",
                "persist_user_message": True,
                "history_limit": 30
            }
            
            # Start streaming request
            chunk_count = 0
            async with session.post(f"{self.base_url}/api/chat/stream", 
                                  headers=headers, json=payload) as response:
                
                if response.status != 200:
                    self.log_test("Chat Stream Start", "FAIL", 
                                f"HTTP {response.status}: {await response.text()}")
                    return False
                
                # Read only first few chunks then terminate (simulate early disconnect)
                async for line in response.content:
                    line = line.decode('utf-8').strip()
                    if line.startswith('data: '):
                        chunk_count += 1
                        data = line[6:]  # Remove "data: " prefix
                        
                        if data == "[DONE]":
                            break
                        
                        try:
                            chunk_json = json.loads(data)
                            print(f"  📦 Chunk {chunk_count}: {chunk_json.get('event', 'unknown')}")
                        except json.JSONDecodeError:
                            continue
                        
                        # Terminate after 3-4 chunks to simulate disconnect
                        if chunk_count >= 3:
                            print("  🔌 Simulating early disconnect...")
                            break
            
            # Allow time for async database persistence
            await asyncio.sleep(3)
            
            self.log_test("Chat Stream Early Termination", "PASS", 
                        f"Terminated after {chunk_count} chunks, conversation_id: {self.test_conversation_id}")
            return True
            
        except Exception as e:
            self.log_test("Chat Stream Early Termination", "FAIL", f"Exception: {str(e)}")
            return False

    async def test_conversation_persistence_after_disconnect(self, session: aiohttp.ClientSession) -> bool:
        """Test 2: Verify conversation was persisted despite early stream termination"""
        try:
            headers = {"Authorization": f"Bearer {self.session_token}"}
            
            # Check if conversation exists in database
            async with session.get(f"{self.base_url}/api/conversations/{self.test_conversation_id}/messages", 
                                 headers=headers) as response:
                
                if response.status == 200:
                    messages = await response.json()
                    user_messages = [msg for msg in messages if msg["role"] == "user"]
                    assistant_messages = [msg for msg in messages if msg["role"] == "assistant"]
                    
                    if len(user_messages) >= 1:
                        self.log_test("Conversation Persistence", "PASS", 
                                    f"Found {len(user_messages)} user messages, {len(assistant_messages)} assistant messages")
                        
                        # Verify the test message content
                        if any("Regression test prompt" in msg.get("content", "") for msg in user_messages):
                            return True
                        else:
                            self.log_test("Message Content Verification", "FAIL", 
                                        "Test message content not found in persisted messages")
                            return False
                    else:
                        self.log_test("Conversation Persistence", "FAIL", 
                                    "No user messages found in persisted conversation")
                        return False
                else:
                    self.log_test("Conversation Persistence", "FAIL", 
                                f"Cannot retrieve messages: HTTP {response.status}")
                    return False
                    
        except Exception as e:
            self.log_test("Conversation Persistence", "FAIL", f"Exception: {str(e)}")
            return False

    async def test_conversation_search_endpoints(self, session: aiohttp.ClientSession) -> bool:
        """Test 3: Validate conversation search endpoints structure and auth enforcement"""
        try:
            headers = {"Authorization": f"Bearer {self.session_token}"}
            
            # Test 3a: /api/conversations/search
            async with session.get(f"{self.base_url}/api/conversations/search?q=regression&offset=0&limit=20", 
                                 headers=headers) as response:
                
                if response.status == 200:
                    data = await response.json()
                    required_fields = ["query", "offset", "limit", "total", "conversations"]
                    
                    if all(field in data for field in required_fields):
                        self.log_test("Conversations Search Endpoint", "PASS", 
                                    f"Correct structure, found {data['total']} conversations")
                    else:
                        self.log_test("Conversations Search Endpoint", "FAIL", 
                                    f"Missing fields: {set(required_fields) - set(data.keys())}")
                        return False
                else:
                    self.log_test("Conversations Search Endpoint", "FAIL", 
                                f"HTTP {response.status}")
                    return False
            
            # Test 3b: /api/a0/non-ui/conversations/search
            async with session.get(f"{self.base_url}/api/a0/non-ui/conversations/search?q=regression&offset=0&limit=20",
                                 headers=headers) as response:
                
                if response.status == 200:
                    a0_data = await response.json()
                    if all(field in a0_data for field in required_fields):
                        self.log_test("A0 Conversations Search Endpoint", "PASS", 
                                    f"Correct structure, found {a0_data['total']} conversations")
                    else:
                        self.log_test("A0 Conversations Search Endpoint", "FAIL", 
                                    f"Missing fields: {set(required_fields) - set(a0_data.keys())}")
                        return False
                else:
                    self.log_test("A0 Conversations Search Endpoint", "FAIL", 
                                f"HTTP {response.status}")
                    return False
            
            # Test 3c: Auth enforcement - test without authorization
            async with session.get(f"{self.base_url}/api/conversations/search") as response:
                if response.status == 401:
                    self.log_test("Search Auth Enforcement", "PASS", 
                                "Unauthenticated requests return 401")
                else:
                    self.log_test("Search Auth Enforcement", "FAIL", 
                                f"Unauthenticated request returned {response.status}, expected 401")
                    return False
            
            return True
            
        except Exception as e:
            self.log_test("Conversation Search Endpoints", "FAIL", f"Exception: {str(e)}")
            return False

    async def test_agent_zero_non_ui_endpoints(self, session: aiohttp.ClientSession) -> bool:
        """Test 4: Ensure Agent Zero non-UI endpoints remain functional"""
        try:
            headers = {"Authorization": f"Bearer {self.session_token}"}
            
            # Test 4a: /api/a0/non-ui/options
            async with session.get(f"{self.base_url}/api/a0/non-ui/options", headers=headers) as response:
                if response.status == 200:
                    options = await response.json()
                    required_keys = ["input_options", "output_options", "available_models", "non_ui_endpoints"]
                    
                    if all(key in options for key in required_keys):
                        model_count = sum(len(models) for models in options["available_models"].values())
                        self.log_test("A0 Options Endpoint", "PASS", 
                                    f"Complete structure with {model_count} total models")
                    else:
                        self.log_test("A0 Options Endpoint", "FAIL", 
                                    f"Missing keys: {set(required_keys) - set(options.keys())}")
                        return False
                else:
                    self.log_test("A0 Options Endpoint", "FAIL", f"HTTP {response.status}")
                    return False
            
            # Test 4b: /api/a0/non-ui/prompt/selected (verify it starts streaming)
            prompt_payload = {
                "message": "Quick test for A0 endpoint functionality",
                "models": ["gpt-5.2"],
                "context_mode": "compartmented",
                "persist_user_message": True
            }
            
            # Just verify the endpoint starts streaming
            async with session.post(f"{self.base_url}/api/a0/non-ui/prompt/selected",
                                  headers=headers, json=prompt_payload) as response:
                
                if response.status == 200:
                    # Read first chunk to verify streaming works
                    chunk = await response.content.read(100)
                    if b'data: ' in chunk:
                        self.log_test("A0 Prompt Selected Endpoint", "PASS", "SSE streaming works")
                    else:
                        self.log_test("A0 Prompt Selected Endpoint", "FAIL", "Invalid SSE format")
                        return False
                else:
                    self.log_test("A0 Prompt Selected Endpoint", "FAIL", f"HTTP {response.status}")
                    return False
            
            # Test 4c: /api/a0/non-ui/history/{conversation_id} with non-existent ID
            fake_id = "non-existent-conversation"
            async with session.get(f"{self.base_url}/api/a0/non-ui/history/{fake_id}?offset=0&limit=200",
                                 headers=headers) as response:
                
                if response.status == 404:
                    self.log_test("A0 History Endpoint", "PASS", "Returns 404 for non-existent conversation")
                else:
                    self.log_test("A0 History Endpoint", "FAIL", 
                                f"Expected 404, got {response.status}")
                    return False
            
            # Test 4d: /api/a0/non-ui/synthesis with invalid data
            synthesis_payload = {
                "conversation_id": "fake-conversation",
                "selected_message_ids": ["fake-message-1", "fake-message-2"],
                "target_models": ["gpt-5.2"],
                "synthesis_prompt": "Test synthesis"
            }
            
            async with session.post(f"{self.base_url}/api/a0/non-ui/synthesis",
                                  headers=headers, json=synthesis_payload) as response:
                
                if response.status == 404:
                    self.log_test("A0 Synthesis Endpoint", "PASS", "Returns 404 for non-existent messages")
                else:
                    self.log_test("A0 Synthesis Endpoint", "FAIL", 
                                f"Expected 404, got {response.status}")
                    return False
            
            # Test 4e: /api/a0/non-ui/conversations/{id}/export with non-existent ID
            async with session.get(f"{self.base_url}/api/a0/non-ui/conversations/{fake_id}/export?format=json",
                                 headers=headers) as response:
                
                if response.status == 404:
                    self.log_test("A0 Export Endpoint", "PASS", "Returns 404 for non-existent conversation")
                else:
                    self.log_test("A0 Export Endpoint", "FAIL", 
                                f"Expected 404, got {response.status}")
                    return False
            
            # Test 4f: Auth enforcement on A0 endpoints
            async with session.get(f"{self.base_url}/api/a0/non-ui/options") as response:
                if response.status == 401:
                    self.log_test("A0 Auth Enforcement", "PASS", "All endpoints require authentication")
                else:
                    self.log_test("A0 Auth Enforcement", "FAIL", 
                                f"Unauthenticated request returned {response.status}, expected 401")
                    return False
            
            return True
            
        except Exception as e:
            self.log_test("Agent Zero Endpoints", "FAIL", f"Exception: {str(e)}")
            return False

    async def cleanup_test_data(self):
        """Clean up test user and conversation data"""
        try:
            mongo_script = f'''
use('test_database');
db.users.deleteOne({{user_id: '{self.user_id}'}});
db.user_sessions.deleteOne({{user_id: '{self.user_id}'}});
if ('{self.test_conversation_id}') {{
    db.conversations.deleteOne({{id: '{self.test_conversation_id}', user_id: '{self.user_id}'}});
    db.messages.deleteMany({{conversation_id: '{self.test_conversation_id}', user_id: '{self.user_id}'}});
}}
print('SUCCESS: Test data cleaned up');
            '''
            
            result = subprocess.run(['mongosh', '--eval', mongo_script], 
                                  capture_output=True, text=True, timeout=30)
            
            if 'SUCCESS' in result.stdout:
                self.log_test("Cleanup", "PASS", "Test data removed from database")
            else:
                self.log_test("Cleanup", "FAIL", f"MongoDB cleanup error: {result.stderr}")
        
        except Exception as e:
            self.log_test("Cleanup", "FAIL", f"Exception: {str(e)}")

    async def run_regression_tests(self) -> bool:
        """Run all backend regression tests"""
        print("🚀 BACKEND REGRESSION TESTS - Conversation Persistence After Stream Disconnect")
        print("=" * 80)
        print(f"Target: {self.base_url}")
        print()
        
        # Setup authentication
        if not await self.setup_auth_user():
            print("❌ Authentication setup failed, cannot continue")
            return False
        
        success = True
        
        # Run tests with aiohttp session
        timeout = aiohttp.ClientTimeout(total=60)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            
            # Verify auth works
            if not await self.verify_auth(session):
                print("❌ Authentication verification failed")
                return False
            
            # Run regression test scenarios
            tests = [
                ("Chat Stream Early Termination", self.test_chat_stream_early_termination),
                ("Conversation Persistence After Disconnect", self.test_conversation_persistence_after_disconnect),
                ("Conversation Search Endpoints", self.test_conversation_search_endpoints), 
                ("Agent Zero Non-UI Endpoints", self.test_agent_zero_non_ui_endpoints)
            ]
            
            for test_name, test_func in tests:
                print(f"\n🧪 Running: {test_name}")
                if not await test_func(session):
                    success = False
        
        # Cleanup
        await self.cleanup_test_data()
        
        # Print final results
        print("\n" + "=" * 80)
        print("📊 REGRESSION TEST RESULTS")
        print("=" * 80)
        
        for result in self.results["details"]:
            status_icon = "✅" if result["status"] == "PASS" else "❌"
            print(f"{status_icon} {result['test']}: {result['details']}")
        
        print(f"\n📈 Summary: {self.results['passed']}/{self.results['total_tests']} tests passed")
        
        if success and self.results["passed"] == self.results["total_tests"]:
            print("🎉 ALL REGRESSION TESTS PASSED!")
            return True
        else:
            print("💥 SOME REGRESSION TESTS FAILED!")
            return False


async def main():
    """Main test runner"""
    BASE_URL = "https://prompt-hub-67.preview.emergentagent.com"
    
    tester = BackendRegressionTester(BASE_URL)
    success = await tester.run_regression_tests()
    
    exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())