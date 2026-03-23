#!/usr/bin/env python3
"""
AIMMH Hub Backend Test Suite
Tests run archival + direct multi-instance chat backend functionality
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional

import aiohttp
import pymongo
from pymongo import MongoClient

# Configuration
BACKEND_URL = "https://aimmh-hub.preview.emergentagent.com/api"
MONGO_URL = "mongodb://localhost:27017"
DB_NAME = "test_database"

class TestRunner:
    def __init__(self):
        self.session_token: Optional[str] = None
        self.user_id: Optional[str] = None
        self.test_instances: List[Dict] = []
        self.test_run_id: Optional[str] = None
        self.test_prompt_id: Optional[str] = None
        self.mongo_client = MongoClient(MONGO_URL)
        self.db = self.mongo_client[DB_NAME]
        
    async def setup_auth(self) -> bool:
        """Create test user and session for authentication"""
        try:
            # Generate unique test identifiers
            timestamp = int(time.time())
            self.user_id = f"test-user-{timestamp}"
            self.session_token = f"test_session_{timestamp}"
            
            # Create test user
            user_doc = {
                "user_id": self.user_id,
                "email": f"test.user.{timestamp}@example.com",
                "name": "AIMMH Test User",
                "picture": "https://via.placeholder.com/150",
                "created_at": datetime.fromtimestamp(time.time(), tz=timezone.utc).isoformat()
            }
            self.db.users.insert_one(user_doc)
            
            # Create session
            session_doc = {
                "user_id": self.user_id,
                "session_token": self.session_token,
                "expires_at": datetime.fromtimestamp(time.time() + (7 * 24 * 60 * 60), tz=timezone.utc).isoformat(),
                "created_at": datetime.fromtimestamp(time.time(), tz=timezone.utc).isoformat()
            }
            self.db.user_sessions.insert_one(session_doc)
            
            print(f"✅ Created test user: {self.user_id}")
            print(f"✅ Created session token: {self.session_token}")
            return True
            
        except Exception as e:
            print(f"❌ Auth setup failed: {e}")
            return False
    
    async def cleanup_auth(self):
        """Clean up test user and session"""
        try:
            self.db.users.delete_many({"user_id": self.user_id})
            self.db.user_sessions.delete_many({"session_token": self.session_token})
            print(f"✅ Cleaned up test user and session")
        except Exception as e:
            print(f"⚠️ Cleanup warning: {e}")
    
    async def make_request(self, method: str, endpoint: str, data: Optional[Dict] = None, params: Optional[Dict] = None) -> Dict:
        """Make authenticated HTTP request"""
        headers = {
            "Content-Type": "application/json"
        }
        
        # Use session token as cookie for authentication
        cookies = {
            "session_token": self.session_token
        }
        
        url = f"{BACKEND_URL}{endpoint}"
        
        async with aiohttp.ClientSession() as session:
            if method.upper() == "GET":
                async with session.get(url, headers=headers, cookies=cookies, params=params) as response:
                    try:
                        result = await response.json()
                    except:
                        result = {"error": await response.text()}
                    return {"status": response.status, "data": result}
            elif method.upper() == "POST":
                async with session.post(url, headers=headers, cookies=cookies, json=data) as response:
                    try:
                        result = await response.json()
                    except:
                        result = {"error": await response.text()}
                    return {"status": response.status, "data": result}
            elif method.upper() == "PATCH":
                async with session.patch(url, headers=headers, cookies=cookies, json=data) as response:
                    try:
                        result = await response.json()
                    except:
                        result = {"error": await response.text()}
                    return {"status": response.status, "data": result}
            elif method.upper() == "DELETE":
                async with session.delete(url, headers=headers, cookies=cookies) as response:
                    if response.status == 200:
                        try:
                            result = await response.json()
                        except:
                            result = {"message": "deleted"}
                        return {"status": response.status, "data": result}
                    else:
                        return {"status": response.status, "data": {}}
    
    async def test_auth_protection(self) -> bool:
        """Test that endpoints require authentication"""
        print("\n🔒 Testing authentication protection...")
        
        # Test without auth token
        headers = {"Content-Type": "application/json"}
        
        endpoints_to_test = [
            "/v1/hub/options",
            "/v1/hub/instances",
            "/v1/hub/runs",
            "/v1/hub/chat/prompts"
        ]
        
        async with aiohttp.ClientSession() as session:
            for endpoint in endpoints_to_test:
                url = f"{BACKEND_URL}{endpoint}"
                async with session.get(url, headers=headers) as response:
                    if response.status != 401:
                        print(f"❌ {endpoint} should return 401 without auth, got {response.status}")
                        return False
                    print(f"✅ {endpoint} correctly returns 401 without auth")
        
        return True
    
    async def test_hub_options(self) -> bool:
        """Test hub options endpoint"""
        print("\n📋 Testing hub options...")
        
        result = await self.make_request("GET", "/v1/hub/options")
        if result["status"] != 200:
            print(f"❌ Hub options failed: {result}")
            return False
        
        data = result["data"]
        required_keys = ["fastapi_connections", "patterns", "supports"]
        for key in required_keys:
            if key not in data:
                print(f"❌ Missing key in hub options: {key}")
                return False
        
        # Check for run archival support
        if not data["supports"].get("run_archival"):
            print("❌ Run archival support not enabled")
            return False
        
        # Check for multi-instance chat support
        if not data["supports"].get("same_prompt_multi_instance_chat"):
            print("❌ Multi-instance chat support not enabled")
            return False
        
        print("✅ Hub options endpoint working with required features")
        return True
    
    async def create_test_instances(self) -> bool:
        """Create test instances for testing"""
        print("\n🏗️ Creating test instances...")
        
        # Create 2 test instances with the same model
        instance_requests = [
            {
                "name": "Test Instance Alpha",
                "model_id": "gpt-4o",
                "role_preset": "assistant",
                "context": {
                    "role": "helpful assistant",
                    "prompt_modifier": "Be concise and helpful"
                },
                "instance_prompt": "You are a test assistant for AIMMH hub testing",
                "history_window_messages": 10,
                "archived": False
            },
            {
                "name": "Test Instance Beta", 
                "model_id": "gpt-4o",
                "role_preset": "assistant",
                "context": {
                    "role": "helpful assistant",
                    "prompt_modifier": "Be detailed and thorough"
                },
                "instance_prompt": "You are another test assistant for AIMMH hub testing",
                "history_window_messages": 10,
                "archived": False
            }
        ]
        
        for i, instance_req in enumerate(instance_requests):
            result = await self.make_request("POST", "/v1/hub/instances", instance_req)
            if result["status"] != 200:
                print(f"❌ Failed to create instance {i+1}: {result}")
                return False
            
            instance = result["data"]
            self.test_instances.append(instance)
            print(f"✅ Created instance: {instance['name']} ({instance['instance_id']})")
        
        return True
    
    async def test_run_archival_flow(self) -> bool:
        """Test complete run archival flow"""
        print("\n📦 Testing run archival flow...")
        
        # Step 1: Create a minimal hub run
        run_request = {
            "prompt": "Test prompt for archival testing",
            "label": "Archival Test Run",
            "stages": [
                {
                    "pattern": "fan_out",
                    "name": "Test Stage",
                    "participants": [
                        {"source_type": "instance", "source_id": self.test_instances[0]["instance_id"]},
                        {"source_type": "instance", "source_id": self.test_instances[1]["instance_id"]}
                    ],
                    "rounds": 1
                }
            ],
            "persist_instance_threads": True
        }
        
        print("Creating test run...")
        result = await self.make_request("POST", "/v1/hub/runs", run_request)
        if result["status"] != 200:
            print(f"❌ Failed to create run: {result}")
            return False
        
        run_data = result["data"]
        self.test_run_id = run_data["run_id"]
        print(f"✅ Created run: {self.test_run_id}")
        
        # Step 2: Verify run appears in default list (not archived)
        print("Checking run appears in default list...")
        result = await self.make_request("GET", "/v1/hub/runs")
        if result["status"] != 200:
            print(f"❌ Failed to list runs: {result}")
            return False
        
        runs = result["data"]["runs"]
        run_found = any(run["run_id"] == self.test_run_id for run in runs)
        if not run_found:
            print(f"❌ Run {self.test_run_id} not found in default list")
            return False
        print("✅ Run appears in default list")
        
        # Step 3: Archive the run
        print("Archiving run...")
        result = await self.make_request("POST", f"/v1/hub/runs/{self.test_run_id}/archive")
        if result["status"] != 200:
            print(f"❌ Failed to archive run: {result}")
            return False
        
        archived_run = result["data"]
        if not archived_run["archived"]:
            print("❌ Run not marked as archived")
            return False
        print("✅ Run archived successfully")
        
        # Step 4: Verify run is hidden from default list
        print("Checking run is hidden from default list...")
        result = await self.make_request("GET", "/v1/hub/runs")
        if result["status"] != 200:
            print(f"❌ Failed to list runs: {result}")
            return False
        
        runs = result["data"]["runs"]
        run_found = any(run["run_id"] == self.test_run_id for run in runs)
        if run_found:
            print(f"❌ Archived run {self.test_run_id} still appears in default list")
            return False
        print("✅ Archived run hidden from default list")
        
        # Step 5: Verify run appears when include_archived=true
        print("Checking run appears with include_archived=true...")
        result = await self.make_request("GET", "/v1/hub/runs", params={"include_archived": "true"})
        if result["status"] != 200:
            print(f"❌ Failed to list runs with archived: {result}")
            return False
        
        runs = result["data"]["runs"]
        run_found = any(run["run_id"] == self.test_run_id and run["archived"] for run in runs)
        if not run_found:
            print(f"❌ Archived run {self.test_run_id} not found with include_archived=true")
            return False
        print("✅ Archived run appears with include_archived=true")
        
        # Step 6: Unarchive the run
        print("Unarchiving run...")
        result = await self.make_request("POST", f"/v1/hub/runs/{self.test_run_id}/unarchive")
        if result["status"] != 200:
            print(f"❌ Failed to unarchive run: {result}")
            return False
        
        unarchived_run = result["data"]
        if unarchived_run["archived"]:
            print("❌ Run still marked as archived after unarchive")
            return False
        print("✅ Run unarchived successfully")
        
        # Step 7: Verify run appears in default list again
        print("Checking run appears in default list after unarchive...")
        result = await self.make_request("GET", "/v1/hub/runs")
        if result["status"] != 200:
            print(f"❌ Failed to list runs: {result}")
            return False
        
        runs = result["data"]["runs"]
        run_found = any(run["run_id"] == self.test_run_id and not run["archived"] for run in runs)
        if not run_found:
            print(f"❌ Unarchived run {self.test_run_id} not found in default list")
            return False
        print("✅ Unarchived run appears in default list")
        
        # Step 8: Archive again for delete test
        print("Re-archiving run for delete test...")
        result = await self.make_request("POST", f"/v1/hub/runs/{self.test_run_id}/archive")
        if result["status"] != 200:
            print(f"❌ Failed to re-archive run: {result}")
            return False
        print("✅ Run re-archived")
        
        # Step 9: Delete archived run
        print("Deleting archived run...")
        result = await self.make_request("DELETE", f"/v1/hub/runs/{self.test_run_id}")
        if result["status"] != 200:
            print(f"❌ Failed to delete archived run: {result}")
            return False
        print("✅ Archived run deleted successfully")
        
        # Step 10: Verify run no longer exists
        print("Verifying run no longer exists...")
        result = await self.make_request("GET", f"/v1/hub/runs/{self.test_run_id}")
        if result["status"] != 404:
            print(f"❌ Deleted run still accessible: {result}")
            return False
        print("✅ Deleted run no longer accessible")
        
        return True
    
    async def test_multi_instance_chat(self) -> bool:
        """Test direct multi-instance chat functionality"""
        print("\n💬 Testing multi-instance chat...")
        
        # Step 1: Send prompt to multiple instances
        chat_request = {
            "prompt": "What is the capital of France? Please respond with just the city name.",
            "instance_ids": [inst["instance_id"] for inst in self.test_instances],
            "label": "Multi-Instance Test"
        }
        
        print("Sending chat prompt to multiple instances...")
        result = await self.make_request("POST", "/v1/hub/chat/prompts", chat_request)
        if result["status"] != 200:
            print(f"❌ Failed to send chat prompt: {result}")
            return False
        
        prompt_data = result["data"]
        self.test_prompt_id = prompt_data["prompt_id"]
        
        # Verify response structure
        required_keys = ["prompt_id", "prompt", "instance_ids", "instance_names", "responses"]
        for key in required_keys:
            if key not in prompt_data:
                print(f"❌ Missing key in chat prompt response: {key}")
                return False
        
        # Verify we got responses from all instances
        if len(prompt_data["responses"]) != len(self.test_instances):
            print(f"❌ Expected {len(self.test_instances)} responses, got {len(prompt_data['responses'])}")
            return False
        
        # Verify each response has required fields
        for i, response in enumerate(prompt_data["responses"]):
            required_response_keys = ["prompt_id", "instance_id", "instance_name", "thread_id", "model", "content", "message_id"]
            for key in required_response_keys:
                if key not in response:
                    print(f"❌ Missing key in response {i}: {key}")
                    return False
            
            # Verify response belongs to one of our instances
            if response["instance_id"] not in [inst["instance_id"] for inst in self.test_instances]:
                print(f"❌ Response from unknown instance: {response['instance_id']}")
                return False
        
        print(f"✅ Multi-instance chat successful: {len(prompt_data['responses'])} responses received")
        
        return True
    
    async def test_prompt_history_persistence(self) -> bool:
        """Test that prompts are persisted to instance thread histories"""
        print("\n📚 Testing prompt history persistence...")
        
        # Check each instance's history for the chat prompt
        for instance in self.test_instances:
            print(f"Checking history for instance {instance['name']}...")
            
            result = await self.make_request("GET", f"/v1/hub/instances/{instance['instance_id']}/history")
            if result["status"] != 200:
                print(f"❌ Failed to get instance history: {result}")
                return False
            
            history = result["data"]
            messages = history["messages"]
            
            print(f"Found {len(messages)} messages in {instance['name']} history")
            
            # Look for our test prompt in the history
            user_message_found = False
            assistant_message_found = False
            
            for i, message in enumerate(messages):
                if (message.get("role") == "user" and 
                    "capital of France" in message.get("content", "") and
                    message.get("hub_role") == "input"):
                    user_message_found = True
                    print(f"✅ Found user message in {instance['name']} history (hub_role=input)")
                
                if (message.get("role") == "assistant" and 
                    message.get("hub_role") == "response"):
                    assistant_message_found = True
                    print(f"✅ Found assistant message in {instance['name']} history (hub_role=response)")
            
            if not user_message_found:
                print(f"❌ User message not found in {instance['name']} history")
                print(f"Looking for prompt_id: {self.test_prompt_id}")
                return False
            
            if not assistant_message_found:
                print(f"❌ Assistant message not found in {instance['name']} history")
                print(f"Looking for prompt_id: {self.test_prompt_id}")
                return False
        
        print("✅ Prompt history persistence verified for all instances")
        return True
    
    async def test_chat_prompt_retrieval(self) -> bool:
        """Test chat prompt retrieval endpoints"""
        print("\n🔍 Testing chat prompt retrieval...")
        
        # Test list chat prompts
        print("Testing list chat prompts...")
        result = await self.make_request("GET", "/v1/hub/chat/prompts")
        if result["status"] != 200:
            print(f"❌ Failed to list chat prompts: {result}")
            return False
        
        prompts_data = result["data"]
        if "prompts" not in prompts_data or "total" not in prompts_data:
            print("❌ Invalid chat prompts list response structure")
            return False
        
        # Find our test prompt
        test_prompt_found = False
        for prompt in prompts_data["prompts"]:
            if prompt["prompt_id"] == self.test_prompt_id:
                test_prompt_found = True
                break
        
        if not test_prompt_found:
            print(f"❌ Test prompt {self.test_prompt_id} not found in list")
            return False
        
        print("✅ Chat prompts list working")
        
        # Test get specific chat prompt
        print("Testing get specific chat prompt...")
        result = await self.make_request("GET", f"/v1/hub/chat/prompts/{self.test_prompt_id}")
        if result["status"] != 200:
            print(f"❌ Failed to get chat prompt detail: {result}")
            return False
        
        prompt_detail = result["data"]
        if prompt_detail["prompt_id"] != self.test_prompt_id:
            print(f"❌ Wrong prompt returned: expected {self.test_prompt_id}, got {prompt_detail['prompt_id']}")
            return False
        
        # Verify all responses are included
        if len(prompt_detail["responses"]) != len(self.test_instances):
            print(f"❌ Expected {len(self.test_instances)} responses in detail, got {len(prompt_detail['responses'])}")
            return False
        
        print("✅ Chat prompt detail retrieval working")
        return True
    
    async def cleanup_test_data(self):
        """Clean up test instances and data"""
        print("\n🧹 Cleaning up test data...")
        
        # Delete test instances
        for instance in self.test_instances:
            try:
                result = await self.make_request("DELETE", f"/v1/hub/instances/{instance['instance_id']}")
                print(f"✅ Cleaned up instance {instance['name']}")
            except Exception as e:
                print(f"⚠️ Failed to cleanup instance {instance['name']}: {e}")
        
        # Clean up MongoDB test data
        try:
            self.db.hub_instances.delete_many({"user_id": self.user_id})
            self.db.hub_runs.delete_many({"user_id": self.user_id})
            self.db.hub_run_steps.delete_many({"user_id": self.user_id})
            self.db.hub_chat_prompts.delete_many({"user_id": self.user_id})
            self.db.threads.delete_many({"user_id": self.user_id})
            self.db.messages.delete_many({"user_id": self.user_id})
            print("✅ Cleaned up MongoDB test data")
        except Exception as e:
            print(f"⚠️ MongoDB cleanup warning: {e}")
    
    async def run_all_tests(self) -> bool:
        """Run all tests in sequence"""
        print("🚀 Starting AIMMH Hub Backend Tests")
        print("=" * 50)
        
        try:
            # Setup
            if not await self.setup_auth():
                return False
            
            # Test sequence
            tests = [
                ("Authentication Protection", self.test_auth_protection),
                ("Hub Options", self.test_hub_options),
                ("Create Test Instances", self.create_test_instances),
                ("Run Archival Flow", self.test_run_archival_flow),
                ("Multi-Instance Chat", self.test_multi_instance_chat),
                ("Prompt History Persistence", self.test_prompt_history_persistence),
                ("Chat Prompt Retrieval", self.test_chat_prompt_retrieval),
            ]
            
            for test_name, test_func in tests:
                print(f"\n{'='*20} {test_name} {'='*20}")
                if not await test_func():
                    print(f"❌ {test_name} FAILED")
                    return False
                print(f"✅ {test_name} PASSED")
            
            return True
            
        finally:
            # Always cleanup
            await self.cleanup_test_data()
            await self.cleanup_auth()
    
    def close(self):
        """Close MongoDB connection"""
        self.mongo_client.close()

async def main():
    """Main test runner"""
    runner = TestRunner()
    
    try:
        success = await runner.run_all_tests()
        
        print("\n" + "=" * 50)
        if success:
            print("🎉 ALL TESTS PASSED!")
            print("✅ Hub run archival functionality working")
            print("✅ Direct multi-instance chat functionality working")
            print("✅ Prompt history persistence working")
            print("✅ Chat prompt retrieval working")
            print("✅ Authentication protection working")
        else:
            print("❌ SOME TESTS FAILED!")
            print("Please check the output above for details")
            sys.exit(1)
            
    except Exception as e:
        print(f"💥 Test runner crashed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    finally:
        runner.close()

if __name__ == "__main__":
    asyncio.run(main())