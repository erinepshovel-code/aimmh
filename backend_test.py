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
                use('test_database');
                var userId = 'convtest-user-' + Date.now();
                var sessionToken = 'convtest_session_' + Date.now();
                db.users.insertOne({
                  user_id: userId,
                  email: 'convtest.user.' + Date.now() + '@example.com',
                  name: 'Conversation Search Test User',
                  picture: 'https://via.placeholder.com/150',
                  created_at: new Date()
                });
                db.user_sessions.insertOne({
                  user_id: userId,
                  session_token: sessionToken,
                  expires_at: new Date(Date.now() + 7*24*60*60*1000),
                  created_at: new Date()
                });
                print('SESSION_TOKEN:' + sessionToken);
                """
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"MongoDB session creation failed: {result.stderr}")
                return False
            
            # Extract session token from output
            lines = result.stdout.split('\n')
            session_token = None
            for line in lines:
                if line.startswith('SESSION_TOKEN:'):
                    session_token = line.split('SESSION_TOKEN:')[1].strip()
                    break
            
            if not session_token:
                print("Failed to extract session token from MongoDB output")
                return False
            
            # Set the session token as a cookie
            self.session_token = session_token
            
            # Test authentication
            cookies = {'session_token': session_token}
            async with session.get(f"{self.base_url}/api/auth/me", cookies=cookies) as resp:
                if resp.status == 200:
                    # Update session with cookies for subsequent requests
                    session.cookie_jar.update_cookies({'session_token': session_token})
                    return True
                else:
                    print(f"Auth test failed with status {resp.status}")
                    return False
                    
        except Exception as e:
            print(f"Authentication setup error: {e}")
            return False

    async def create_test_conversations(self, session: aiohttp.ClientSession) -> bool:
        """Create test conversations with different titles for searching"""
        try:
            # Create conversations with different titles
            test_titles = [
                "Machine Learning Tutorial",
                "Python Programming Guide", 
                "JavaScript Development",
                "API Design Best Practices",
                "Database Optimization Tips"
            ]
            
            for title in test_titles:
                # Create conversation by sending a chat message
                chat_data = {
                    "message": f"Tell me about {title}",
                    "models": ["gpt-5.2"],
                    "conversation_id": str(uuid.uuid4()),
                    "context_mode": "compartmented",
                    "shared_room_mode": "parallel_all",
                    "global_context": "",
                    "model_roles": {},
                    "per_model_messages": {},
                    "persist_user_message": True,
                    "history_limit": 10,
                    "attachments": []
                }
                
                async with session.post(f"{self.base_url}/api/chat/stream", json=chat_data) as resp:
                    if resp.status == 200:
                        # Store the first conversation ID for reference
                        if not self.test_conversation_id:
                            self.test_conversation_id = chat_data["conversation_id"]
                        
                        # Read the SSE stream to completion (just to ensure the conversation is created)
                        async for line in resp.content:
                            if b'event: complete' in line:
                                break
                    
            return True
            
        except Exception as e:
            print(f"Error creating test conversations: {e}")
            return False

    async def test_unauthenticated_access(self, session: aiohttp.ClientSession):
        """Test that unauthenticated requests return 401"""
        # Create new session without auth
        async with aiohttp.ClientSession() as unauth_session:
            # Test regular search endpoint
            async with unauth_session.get(f"{self.base_url}/api/conversations/search") as resp:
                if resp.status == 401:
                    self.log_test("Unauthenticated access to /api/conversations/search", "PASS", "Returns 401 as expected")
                else:
                    self.log_test("Unauthenticated access to /api/conversations/search", "FAIL", f"Expected 401, got {resp.status}")
            
            # Test a0 non-ui search endpoint
            async with unauth_session.get(f"{self.base_url}/api/a0/non-ui/conversations/search") as resp:
                if resp.status == 401:
                    self.log_test("Unauthenticated access to /api/a0/non-ui/conversations/search", "PASS", "Returns 401 as expected")
                else:
                    self.log_test("Unauthenticated access to /api/a0/non-ui/conversations/search", "FAIL", f"Expected 401, got {resp.status}")

    async def test_search_endpoint(self, session: aiohttp.ClientSession, endpoint: str, endpoint_name: str):
        """Test a specific search endpoint"""
        
        # Test 1: Basic search without query (should return all conversations)
        async with session.get(f"{self.base_url}{endpoint}") as resp:
            if resp.status == 200:
                data = await resp.json()
                required_fields = ["query", "offset", "limit", "total", "conversations"]
                if all(field in data for field in required_fields):
                    self.log_test(f"{endpoint_name}: Basic search structure", "PASS", 
                                f"Returns all required fields: {required_fields}")
                    
                    # Verify default values
                    if data["query"] == "" and data["offset"] == 0 and data["limit"] == 20:
                        self.log_test(f"{endpoint_name}: Default parameters", "PASS", 
                                    "Query='', offset=0, limit=20 as expected")
                    else:
                        self.log_test(f"{endpoint_name}: Default parameters", "FAIL", 
                                    f"Unexpected defaults: query='{data['query']}', offset={data['offset']}, limit={data['limit']}")
                else:
                    missing = [f for f in required_fields if f not in data]
                    self.log_test(f"{endpoint_name}: Basic search structure", "FAIL", 
                                f"Missing fields: {missing}")
            else:
                self.log_test(f"{endpoint_name}: Basic search", "FAIL", f"Status {resp.status}")

        # Test 2: Search with query parameter - case insensitive
        search_queries = [
            ("python", "Should find Python Programming Guide"),
            ("MACHINE", "Should find Machine Learning Tutorial (case insensitive)"),
            ("javascript", "Should find JavaScript Development"),
            ("nonexistent", "Should return empty results")
        ]
        
        for query, description in search_queries:
            async with session.get(f"{self.base_url}{endpoint}?q={query}") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data["query"] == query:
                        if query == "nonexistent":
                            if data["total"] == 0 and len(data["conversations"]) == 0:
                                self.log_test(f"{endpoint_name}: Search '{query}'", "PASS", 
                                            "Returns empty results for non-existent query")
                            else:
                                self.log_test(f"{endpoint_name}: Search '{query}'", "FAIL", 
                                            f"Expected 0 results, got {data['total']}")
                        else:
                            # Should find conversations based on case-insensitive regex
                            found_titles = [conv.get("title", "") for conv in data["conversations"]]
                            query_lower = query.lower()
                            matching_titles = [title for title in found_titles 
                                             if query_lower in title.lower()]
                            
                            if len(matching_titles) > 0:
                                self.log_test(f"{endpoint_name}: Search '{query}'", "PASS", 
                                            f"Found {len(matching_titles)} matching conversations")
                            else:
                                self.log_test(f"{endpoint_name}: Search '{query}'", "FAIL", 
                                            f"No matching conversations found for '{query}'")
                    else:
                        self.log_test(f"{endpoint_name}: Search '{query}'", "FAIL", 
                                    f"Query field mismatch: expected '{query}', got '{data['query']}'")
                else:
                    self.log_test(f"{endpoint_name}: Search '{query}'", "FAIL", f"Status {resp.status}")

        # Test 3: Pagination
        async with session.get(f"{self.base_url}{endpoint}?offset=0&limit=2") as resp:
            if resp.status == 200:
                data = await resp.json()
                if data["offset"] == 0 and data["limit"] == 2:
                    if len(data["conversations"]) <= 2:
                        self.log_test(f"{endpoint_name}: Pagination limit", "PASS", 
                                    f"Respects limit parameter (requested 2, got {len(data['conversations'])})")
                    else:
                        self.log_test(f"{endpoint_name}: Pagination limit", "FAIL", 
                                    f"Limit not respected: requested 2, got {len(data['conversations'])}")
                else:
                    self.log_test(f"{endpoint_name}: Pagination parameters", "FAIL", 
                                f"Pagination params not reflected correctly")
            else:
                self.log_test(f"{endpoint_name}: Pagination", "FAIL", f"Status {resp.status}")

        # Test 4: Offset pagination
        if data.get("total", 0) > 2:  # Only test if we have enough conversations
            async with session.get(f"{self.base_url}{endpoint}?offset=2&limit=2") as resp:
                if resp.status == 200:
                    offset_data = await resp.json()
                    if offset_data["offset"] == 2:
                        self.log_test(f"{endpoint_name}: Offset pagination", "PASS", 
                                    "Offset parameter working correctly")
                    else:
                        self.log_test(f"{endpoint_name}: Offset pagination", "FAIL", 
                                    f"Offset not reflected: expected 2, got {offset_data['offset']}")
                else:
                    self.log_test(f"{endpoint_name}: Offset pagination", "FAIL", f"Status {resp.status}")

    async def run_tests(self):
        """Run all conversation search tests"""
        print("=== CONVERSATION SEARCH ENDPOINTS TEST ===")
        print(f"Testing against: {self.base_url}")
        
        async with aiohttp.ClientSession() as session:
            # Test unauthenticated access first
            await self.test_unauthenticated_access(session)
            
            # Authenticate
            print("\n--- Authenticating ---")
            if not await self.setup_auth_session(session):
                print("❌ Authentication failed - cannot proceed with authenticated tests")
                return False
            
            print("✅ Authentication successful")
            
            # Create test conversations
            print("\n--- Creating Test Conversations ---")
            if not await self.create_test_conversations(session):
                print("⚠️ Failed to create test conversations - search tests may have limited data")
            else:
                print("✅ Test conversations created")
            
            # Wait a moment for conversations to be indexed
            await asyncio.sleep(2)
            
            # Test both search endpoints
            print("\n--- Testing Search Endpoints ---")
            await self.test_search_endpoint(session, "/api/conversations/search", "Regular Search API")
            await self.test_search_endpoint(session, "/api/a0/non-ui/conversations/search", "A0 Non-UI Search API")
            
            return True

    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*60)
        print("CONVERSATION SEARCH ENDPOINTS TEST SUMMARY")
        print("="*60)
        print(f"Total Tests: {self.results['total_tests']}")
        print(f"Passed: {self.results['passed']}")
        print(f"Failed: {self.results['failed']}")
        print(f"Success Rate: {(self.results['passed']/self.results['total_tests']*100):.1f}%" if self.results['total_tests'] > 0 else "No tests run")
        
        if self.results['failed'] > 0:
            print(f"\n❌ FAILED TESTS ({self.results['failed']}):")
            for detail in self.results['details']:
                if detail['status'] == 'FAIL':
                    print(f"  • {detail['test']}: {detail['details']}")
        
        if self.results['passed'] > 0:
            print(f"\n✅ PASSED TESTS ({self.results['passed']}):")
            for detail in self.results['details']:
                if detail['status'] == 'PASS':
                    print(f"  • {detail['test']}: {detail['details']}")


async def main():
    """Main test function"""
    backend_url = "https://prompt-hub-67.preview.emergentagent.com"
    
    tester = ConversationSearchTester(backend_url)
    
    try:
        success = await tester.run_tests()
        tester.print_summary()
        
        # Return appropriate exit code
        return 0 if tester.results['failed'] == 0 else 1
        
    except Exception as e:
        print(f"❌ Test suite failed with error: {e}")
        return 1


if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code)