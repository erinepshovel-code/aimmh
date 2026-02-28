#!/usr/bin/env python3
"""
Backend API Test Suite for Conversation Search Endpoints
Tests both regular and a0 non-ui conversation search endpoints
"""

import asyncio
import aiohttp
import json
import uuid
from typing import Dict, Any, Optional


class ConversationSearchTester:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.session_token: Optional[str] = None
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

    async def login(self, session: aiohttp.ClientSession) -> bool:
        """Authenticate with test user"""
        try:
            # First check if we can get existing test users
            async with session.get(f"{self.base_url}/api/auth/me") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.session_token = "existing_session"
                    return True
                    
            # Try to register/login with test user
            test_user = f"convtestuser_{uuid.uuid4().hex[:8]}"
            test_pass = "ConvTestPass123!"
            
            # Register
            register_data = {
                "email": f"{test_user}@testdomain.com",
                "password": test_pass,
                "confirm_password": test_pass
            }
            
            async with session.post(f"{self.base_url}/api/auth/register", json=register_data) as resp:
                if resp.status not in [200, 409]:  # 409 = already exists
                    print(f"Registration failed with status {resp.status}")
                    return False
            
            # Login
            login_data = {
                "email": f"{test_user}@testdomain.com",
                "password": test_pass
            }
            
            async with session.post(f"{self.base_url}/api/auth/login", json=login_data) as resp:
                if resp.status == 200:
                    self.session_token = "authenticated"
                    return True
                else:
                    print(f"Login failed with status {resp.status}")
                    return False
                    
        except Exception as e:
            print(f"Authentication error: {e}")
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
            if not await self.login(session):
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