#!/usr/bin/env python3
"""
AIMMH Backend Test Script
Testing hub chat/synthesis metadata fields in instance history responses.

Test scenarios from review request:
1. Register a fresh user and authenticate
2. Create at least 2 hub instances via `/api/v1/hub/instances`
3. Send a direct chat prompt via `/api/v1/hub/chat/prompts` to those instances
4. Fetch one instance history via `/api/v1/hub/instances/{instance_id}/history`
5. Verify the recent chat history messages include `hub_prompt_id` on both input and response messages, and `hub_role` values remain correct
6. Create a synthesis batch via `/api/v1/hub/chat/synthesize` using a selected block and one synthesis instance
7. Fetch the synthesis instance history again
8. Verify the recent synthesis history messages include `hub_synthesis_batch_id` on both synthesis input and synthesis output messages, and `hub_role` values remain correct
9. Confirm no regression in the normal chat/synthesis API response structures
"""

import asyncio
import json
import random
import string
import time
from typing import Dict, List, Optional

import aiohttp


class AimmhBackendTester:
    def __init__(self, base_url: str = "https://synthesis-chat.preview.emergentagent.com"):
        self.base_url = base_url
        self.session_token: Optional[str] = None
        self.user_id: Optional[str] = None
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    def _generate_test_user(self) -> tuple[str, str]:
        """Generate a unique test username and password."""
        suffix = ''.join(random.choices(string.digits, k=10))
        username = f"aimmh_test_{suffix}"
        password = f"TestPass{suffix}!"
        return username, password

    async def _make_request(self, method: str, endpoint: str, json_data: dict = None, params: dict = None) -> tuple[int, dict]:
        """Make an HTTP request with proper authentication headers."""
        url = f"{self.base_url}{endpoint}"
        headers = {}
        if self.session_token:
            headers["Authorization"] = f"Bearer {self.session_token}"
        
        try:
            async with self.session.request(method, url, json=json_data, params=params, headers=headers) as response:
                try:
                    response_data = await response.json()
                except:
                    response_data = {"error": "Invalid JSON response", "text": await response.text()}
                return response.status, response_data
        except Exception as e:
            return 500, {"error": str(e)}

    async def test_1_register_and_authenticate(self) -> bool:
        """Test 1: Register a fresh user and authenticate."""
        print("🔐 Test 1: Register a fresh user and authenticate")
        
        username, password = self._generate_test_user()
        print(f"   Generated test user: {username}")
        
        # Register user
        register_data = {
            "username": username,
            "password": password
        }
        
        status, response = await self._make_request("POST", "/api/auth/register", register_data)
        if status != 200:
            print(f"   ❌ Registration failed: {status} - {response}")
            return False
            
        if "access_token" not in response:
            print(f"   ❌ No access_token in registration response: {response}")
            return False
            
        self.session_token = response["access_token"]
        self.user_id = response.get("user", {}).get("id")
        print(f"   ✅ User registered successfully, access_token obtained")
        print(f"   ✅ User ID: {self.user_id}")
        
        # Verify authentication with /api/auth/me
        status, response = await self._make_request("GET", "/api/auth/me")
        if status != 200:
            print(f"   ❌ Auth verification failed: {status} - {response}")
            return False
            
        print(f"   ✅ Authentication verified: {response.get('username')}")
        return True

    async def test_2_create_hub_instances(self) -> List[str]:
        """Test 2: Create at least 2 hub instances."""
        print("🏗️  Test 2: Create at least 2 hub instances")
        
        instance_ids = []
        models = ["gpt-4o", "claude-sonnet-4-5-20250929"]
        
        for i, model in enumerate(models, 1):
            instance_data = {
                "name": f"Test Instance {i}",
                "model_id": model,
                "role_preset": None,
                "instance_prompt": f"You are test instance {i} using {model}",
                "history_window_messages": 20,
                "archived": False
            }
            
            status, response = await self._make_request("POST", "/api/v1/hub/instances", instance_data)
            if status != 200:
                print(f"   ❌ Failed to create instance {i}: {status} - {response}")
                continue
                
            instance_id = response.get("instance_id")
            if not instance_id:
                print(f"   ❌ No instance_id in response: {response}")
                continue
                
            instance_ids.append(instance_id)
            print(f"   ✅ Created instance {i}: {instance_id} ({model})")
            
        if len(instance_ids) < 2:
            print(f"   ❌ Only created {len(instance_ids)} instances, need at least 2")
            return []
            
        print(f"   ✅ Successfully created {len(instance_ids)} instances")
        return instance_ids

    async def test_3_send_chat_prompt(self, instance_ids: List[str]) -> Optional[str]:
        """Test 3: Send a direct chat prompt to instances."""
        print("💬 Test 3: Send a direct chat prompt to instances")
        
        prompt_data = {
            "prompt": "Explain quantum computing in exactly 2 sentences. Focus on superposition and entanglement.",
            "label": "Quantum Computing Test Prompt",
            "instance_ids": instance_ids
        }
        
        status, response = await self._make_request("POST", "/api/v1/hub/chat/prompts", prompt_data)
        if status != 200:
            print(f"   ❌ Failed to send chat prompt: {status} - {response}")
            return None
            
        prompt_id = response.get("prompt_id")
        if not prompt_id:
            print(f"   ❌ No prompt_id in response: {response}")
            return None
            
        responses = response.get("responses", [])
        print(f"   ✅ Chat prompt sent successfully: {prompt_id}")
        print(f"   ✅ Received {len(responses)} responses from instances")
        
        # Verify response structure
        for i, resp in enumerate(responses):
            instance_id = resp.get("instance_id")
            content_preview = resp.get("content", "")[:100] + "..." if len(resp.get("content", "")) > 100 else resp.get("content", "")
            print(f"   ✅ Response {i+1} from {instance_id}: {content_preview}")
            
        return prompt_id

    async def test_4_fetch_instance_history(self, instance_id: str) -> List[dict]:
        """Test 4: Fetch instance history and verify structure."""
        print(f"📜 Test 4: Fetch instance history for {instance_id}")
        
        status, response = await self._make_request("GET", f"/api/v1/hub/instances/{instance_id}/history")
        if status != 200:
            print(f"   ❌ Failed to fetch instance history: {status} - {response}")
            return []
            
        messages = response.get("messages", [])
        thread_id = response.get("thread_id")
        
        print(f"   ✅ Fetched history for instance {instance_id}")
        print(f"   ✅ Thread ID: {thread_id}")
        print(f"   ✅ Found {len(messages)} messages in history")
        
        return messages

    async def test_5_verify_chat_metadata(self, messages: List[dict], expected_prompt_id: str) -> bool:
        """Test 5: Verify chat history messages include hub_prompt_id and correct hub_role values."""
        print("🔍 Test 5: Verify chat history metadata fields")
        
        chat_messages = []
        for msg in messages:
            if msg.get("hub_prompt_id") == expected_prompt_id:
                chat_messages.append(msg)
                
        if not chat_messages:
            print(f"   ❌ No messages found with hub_prompt_id: {expected_prompt_id}")
            return False
            
        print(f"   ✅ Found {len(chat_messages)} messages with hub_prompt_id: {expected_prompt_id}")
        
        # Verify required fields and hub_role values
        input_found = False
        response_found = False
        
        for msg in chat_messages:
            role = msg.get("role")
            hub_role = msg.get("hub_role")
            hub_prompt_id = msg.get("hub_prompt_id")
            
            print(f"   📝 Message: role={role}, hub_role={hub_role}, hub_prompt_id={hub_prompt_id}")
            
            # Verify hub_prompt_id is present and matches
            if hub_prompt_id != expected_prompt_id:
                print(f"   ❌ hub_prompt_id mismatch: expected {expected_prompt_id}, got {hub_prompt_id}")
                return False
                
            # Verify hub_role values
            if role == "user" and hub_role == "input":
                input_found = True
                print(f"   ✅ Found user input message with correct hub_role: {hub_role}")
            elif role == "assistant" and hub_role == "response":
                response_found = True
                print(f"   ✅ Found assistant response message with correct hub_role: {hub_role}")
            else:
                print(f"   ⚠️  Unexpected role/hub_role combination: role={role}, hub_role={hub_role}")
                
        if not input_found:
            print("   ❌ No user input message with hub_role='input' found")
            return False
            
        if not response_found:
            print("   ❌ No assistant response message with hub_role='response' found")
            return False
            
        print("   ✅ All chat metadata fields verified correctly")
        return True

    async def test_6_create_synthesis_batch(self, instance_ids: List[str], messages: List[dict]) -> Optional[str]:
        """Test 6: Create a synthesis batch using a selected block and one synthesis instance."""
        print("🔬 Test 6: Create synthesis batch")
        
        # Find a response message to use as synthesis source
        response_message = None
        for msg in messages:
            if msg.get("role") == "assistant" and msg.get("content"):
                response_message = msg
                break
                
        if not response_message:
            print("   ❌ No assistant response message found for synthesis")
            return None
            
        # Use the first instance as synthesis instance
        synthesis_instance_id = instance_ids[0]
        
        synthesis_data = {
            "label": "Test Synthesis Batch",
            "instruction": "Compare and synthesize the quantum computing explanations, highlighting key differences in approach.",
            "selected_blocks": [
                {
                    "source_id": response_message.get("message_id"),
                    "source_label": "Quantum Computing Response",
                    "instance_id": response_message.get("hub_instance_id"),
                    "instance_name": "Test Instance Response",
                    "model": response_message.get("model"),
                    "content": response_message.get("content")
                }
            ],
            "synthesis_instance_ids": [synthesis_instance_id]
        }
        
        status, response = await self._make_request("POST", "/api/v1/hub/chat/synthesize", synthesis_data)
        if status != 200:
            print(f"   ❌ Failed to create synthesis batch: {status} - {response}")
            return None
            
        batch_id = response.get("synthesis_batch_id")
        if not batch_id:
            print(f"   ❌ No synthesis_batch_id in response: {response}")
            return None
            
        outputs = response.get("outputs", [])
        print(f"   ✅ Synthesis batch created successfully: {batch_id}")
        print(f"   ✅ Generated {len(outputs)} synthesis outputs")
        
        for i, output in enumerate(outputs):
            content_preview = output.get("content", "")[:100] + "..." if len(output.get("content", "")) > 100 else output.get("content", "")
            print(f"   ✅ Synthesis output {i+1}: {content_preview}")
            
        return batch_id

    async def test_7_fetch_synthesis_history(self, instance_id: str) -> List[dict]:
        """Test 7: Fetch synthesis instance history again."""
        print(f"📜 Test 7: Fetch synthesis instance history for {instance_id}")
        
        status, response = await self._make_request("GET", f"/api/v1/hub/instances/{instance_id}/history")
        if status != 200:
            print(f"   ❌ Failed to fetch synthesis instance history: {status} - {response}")
            return []
            
        messages = response.get("messages", [])
        print(f"   ✅ Fetched synthesis history: {len(messages)} total messages")
        
        return messages

    async def test_8_verify_synthesis_metadata(self, messages: List[dict], expected_batch_id: str) -> bool:
        """Test 8: Verify synthesis history messages include hub_synthesis_batch_id and correct hub_role values."""
        print("🔍 Test 8: Verify synthesis history metadata fields")
        
        synthesis_messages = []
        for msg in messages:
            if msg.get("hub_synthesis_batch_id") == expected_batch_id:
                synthesis_messages.append(msg)
                
        if not synthesis_messages:
            print(f"   ❌ No messages found with hub_synthesis_batch_id: {expected_batch_id}")
            return False
            
        print(f"   ✅ Found {len(synthesis_messages)} messages with hub_synthesis_batch_id: {expected_batch_id}")
        
        # Verify required fields and hub_role values
        synthesis_input_found = False
        synthesis_output_found = False
        
        for msg in synthesis_messages:
            role = msg.get("role")
            hub_role = msg.get("hub_role")
            hub_synthesis_batch_id = msg.get("hub_synthesis_batch_id")
            
            print(f"   📝 Message: role={role}, hub_role={hub_role}, hub_synthesis_batch_id={hub_synthesis_batch_id}")
            
            # Verify hub_synthesis_batch_id is present and matches
            if hub_synthesis_batch_id != expected_batch_id:
                print(f"   ❌ hub_synthesis_batch_id mismatch: expected {expected_batch_id}, got {hub_synthesis_batch_id}")
                return False
                
            # Verify hub_role values
            if role == "user" and hub_role == "synthesis_input":
                synthesis_input_found = True
                print(f"   ✅ Found synthesis input message with correct hub_role: {hub_role}")
            elif role == "assistant" and hub_role == "synthesis_output":
                synthesis_output_found = True
                print(f"   ✅ Found synthesis output message with correct hub_role: {hub_role}")
            else:
                print(f"   ⚠️  Unexpected role/hub_role combination: role={role}, hub_role={hub_role}")
                
        if not synthesis_input_found:
            print("   ❌ No synthesis input message with hub_role='synthesis_input' found")
            return False
            
        if not synthesis_output_found:
            print("   ❌ No synthesis output message with hub_role='synthesis_output' found")
            return False
            
        print("   ✅ All synthesis metadata fields verified correctly")
        return True

    async def test_9_verify_api_response_structures(self, instance_ids: List[str]) -> bool:
        """Test 9: Confirm no regression in normal chat/synthesis API response structures."""
        print("🔧 Test 9: Verify API response structures (no regression)")
        
        # Test hub options endpoint
        status, response = await self._make_request("GET", "/api/v1/hub/options")
        if status != 200:
            print(f"   ❌ Hub options endpoint failed: {status} - {response}")
            return False
            
        required_keys = ["fastapi_connections", "patterns", "supports"]
        for key in required_keys:
            if key not in response:
                print(f"   ❌ Missing key in hub options: {key}")
                return False
                
        print("   ✅ Hub options endpoint structure verified")
        
        # Test instances list endpoint
        status, response = await self._make_request("GET", "/api/v1/hub/instances")
        if status != 200:
            print(f"   ❌ Instances list endpoint failed: {status} - {response}")
            return False
            
        if "instances" not in response or "total" not in response:
            print(f"   ❌ Invalid instances list response structure: {response}")
            return False
            
        print("   ✅ Instances list endpoint structure verified")
        
        # Test chat prompts list endpoint
        status, response = await self._make_request("GET", "/api/v1/hub/chat/prompts")
        if status != 200:
            print(f"   ❌ Chat prompts list endpoint failed: {status} - {response}")
            return False
            
        if "prompts" not in response or "total" not in response:
            print(f"   ❌ Invalid chat prompts list response structure: {response}")
            return False
            
        print("   ✅ Chat prompts list endpoint structure verified")
        
        # Test synthesis batches list endpoint
        status, response = await self._make_request("GET", "/api/v1/hub/chat/syntheses")
        if status != 200:
            print(f"   ❌ Synthesis batches list endpoint failed: {status} - {response}")
            return False
            
        if "batches" not in response or "total" not in response:
            print(f"   ❌ Invalid synthesis batches list response structure: {response}")
            return False
            
        print("   ✅ Synthesis batches list endpoint structure verified")
        print("   ✅ All API response structures verified - no regressions detected")
        
        return True

    async def run_comprehensive_test(self) -> bool:
        """Run all test scenarios in sequence."""
        print("🚀 Starting AIMMH Backend Comprehensive Test")
        print("=" * 60)
        
        try:
            # Test 1: Register and authenticate
            if not await self.test_1_register_and_authenticate():
                return False
                
            print()
            
            # Test 2: Create hub instances
            instance_ids = await self.test_2_create_hub_instances()
            if not instance_ids:
                return False
                
            print()
            
            # Test 3: Send chat prompt
            prompt_id = await self.test_3_send_chat_prompt(instance_ids)
            if not prompt_id:
                return False
                
            print()
            
            # Test 4: Fetch instance history
            messages = await self.test_4_fetch_instance_history(instance_ids[0])
            if not messages:
                return False
                
            print()
            
            # Test 5: Verify chat metadata
            if not await self.test_5_verify_chat_metadata(messages, prompt_id):
                return False
                
            print()
            
            # Test 6: Create synthesis batch
            synthesis_batch_id = await self.test_6_create_synthesis_batch(instance_ids, messages)
            if not synthesis_batch_id:
                return False
                
            print()
            
            # Test 7: Fetch synthesis history
            synthesis_messages = await self.test_7_fetch_synthesis_history(instance_ids[0])
            if not synthesis_messages:
                return False
                
            print()
            
            # Test 8: Verify synthesis metadata
            if not await self.test_8_verify_synthesis_metadata(synthesis_messages, synthesis_batch_id):
                return False
                
            print()
            
            # Test 9: Verify API response structures
            if not await self.test_9_verify_api_response_structures(instance_ids):
                return False
                
            print()
            print("🎉 ALL TESTS PASSED! AIMMH backend metadata fields are working correctly.")
            return True
            
        except Exception as e:
            print(f"❌ Test suite failed with exception: {e}")
            import traceback
            traceback.print_exc()
            return False


async def main():
    """Main test runner."""
    async with AimmhBackendTester() as tester:
        success = await tester.run_comprehensive_test()
        if success:
            print("\n✅ AIMMH Backend Test Suite: PASSED")
            exit(0)
        else:
            print("\n❌ AIMMH Backend Test Suite: FAILED")
            exit(1)


if __name__ == "__main__":
    asyncio.run(main())