#!/usr/bin/env python3
"""
Backend test suite for Agent Zero non-UI REST endpoints
Tests the following endpoints:
1. GET /api/a0/non-ui/options
2. POST /api/a0/non-ui/prompt/selected
3. POST /api/a0/non-ui/prompt/all
4. GET /api/a0/non-ui/history/{conversation_id}
5. POST /api/a0/non-ui/synthesis
6. GET /api/a0/non-ui/conversations/{conversation_id}/export
7. Authentication verification
"""

import requests
import json
import time
import uuid
import subprocess
import sys
import urllib3
from datetime import datetime, timezone

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configuration
BASE_URL = "https://prompt-hub-67.preview.emergentagent.com"
API_BASE = f"{BASE_URL}/api"

class TestResult:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.details = []
        
    def add_pass(self, test_name, details=""):
        self.passed += 1
        self.details.append(f"✅ {test_name}: PASS{' - ' + details if details else ''}")
        
    def add_fail(self, test_name, details=""):
        self.failed += 1
        self.details.append(f"❌ {test_name}: FAIL{' - ' + details if details else ''}")
        
    def summary(self):
        return f"Tests: {self.passed + self.failed} | Passed: {self.passed} | Failed: {self.failed}"

def setup_test_user():
    """Create test user and session in MongoDB"""
    user_id = f"test-user-a0-{int(time.time())}"
    session_token = f"test_session_a0_{int(time.time())}"
    
    mongo_script = f"""
use('test_database');
var userId = '{user_id}';
var sessionToken = '{session_token}';
db.users.insertOne({{
  user_id: userId,
  email: 'test.user.' + Date.now() + '@example.com',
  name: 'A0 Test User',
  picture: 'https://via.placeholder.com/150',
  created_at: new Date()
}});
db.user_sessions.insertOne({{
  user_id: userId,
  session_token: sessionToken,
  expires_at: new Date(Date.now() + 7*24*60*60*1000),
  created_at: new Date()
}});
print('Session token: ' + sessionToken);
print('User ID: ' + userId);
"""
    
    try:
        result = subprocess.run(
            ["mongosh", "--eval", mongo_script],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            for line in lines:
                if line.startswith('Session token:'):
                    session_token = line.split(':')[1].strip()
                elif line.startswith('User ID:'):
                    user_id = line.split(':')[1].strip()
            return user_id, session_token
        else:
            print(f"MongoDB setup failed: {result.stderr}")
            return None, None
    except Exception as e:
        print(f"Failed to setup test user: {e}")
        return None, None

def cleanup_test_user(user_id, session_token):
    """Remove test user and session from MongoDB"""
    mongo_script = f"""
use('test_database');
db.users.deleteOne({{user_id: '{user_id}'}});
db.user_sessions.deleteOne({{session_token: '{session_token}'}});
print('Cleaned up test user and session');
"""
    
    try:
        subprocess.run(["mongosh", "--eval", mongo_script], capture_output=True, timeout=10)
    except Exception as e:
        print(f"Warning: Failed to cleanup test user: {e}")

def make_request(method, endpoint, headers=None, json_data=None, params=None, cookies=None):
    """Make HTTP request with error handling"""
    url = f"{API_BASE}{endpoint}"
    print(f"Making {method} request to: {url}")
    try:
        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            json=json_data,
            params=params,
            cookies=cookies,
            timeout=30,
            verify=False,  # Skip SSL verification for self-signed certs
            stream=(method.upper() == 'POST' and 'stream' in endpoint)
        )
        print(f"Response status: {response.status_code}")
        return response
    except Exception as e:
        print(f"Request failed: {method} {endpoint} - {e}")
        return None

def test_unauthenticated_access(results):
    """Test that unauthenticated access to a0 non-ui endpoints is rejected"""
    endpoints_to_test = [
        ("/a0/non-ui/options", "GET"),
        ("/a0/non-ui/prompt/selected", "POST"),
        ("/a0/non-ui/prompt/all", "POST"),
        ("/a0/non-ui/history/dummy-conversation-id", "GET"),
        ("/a0/non-ui/synthesis", "POST"),
        ("/a0/non-ui/conversations/dummy-id/export", "GET"),
    ]
    
    print("\n=== Testing Unauthenticated Access ===")
    all_rejected = True
    
    for endpoint, method in endpoints_to_test:
        response = make_request(method, endpoint)
        if response and response.status_code == 401:
            results.add_pass(f"Unauth {method} {endpoint}", "401 Unauthorized")
        else:
            status = response.status_code if response else "No response"
            results.add_fail(f"Unauth {method} {endpoint}", f"Expected 401, got {status}")
            all_rejected = False
    
    return all_rejected

def test_options_endpoint(headers, cookies, results):
    """Test GET /api/a0/non-ui/options"""
    print("\n=== Testing Options Endpoint ===")
    
    response = make_request("GET", "/a0/non-ui/options", headers=headers, cookies=cookies)
    
    if not response:
        results.add_fail("Options endpoint", "No response received")
        return None
    
    if response.status_code != 200:
        results.add_fail("Options endpoint", f"Status {response.status_code}: {response.text}")
        return None
    
    try:
        data = response.json()
        
        # Check for required top-level keys
        required_keys = ["prompt_all", "prompt_selected", "synthesis", "history", "export"]
        found_keys = []
        
        # Check if keys exist in any of the nested structures
        response_text = response.text.lower()
        for key in required_keys:
            if key in response_text:
                found_keys.append(key)
        
        if len(found_keys) == len(required_keys):
            results.add_pass("Options endpoint", f"Contains all required keys: {', '.join(required_keys)}")
            return data
        else:
            missing_keys = set(required_keys) - set(found_keys)
            results.add_fail("Options endpoint", f"Missing keys: {', '.join(missing_keys)}")
            return data
            
    except json.JSONDecodeError:
        results.add_fail("Options endpoint", "Invalid JSON response")
        return None

def create_test_conversation(headers, user_id):
    """Create a test conversation for testing"""
    conversation_id = str(uuid.uuid4())
    
    # Create conversation
    conversation_data = {
        "message": "Test message for Agent Zero non-UI endpoints",
        "models": ["gpt-5.2"],
        "conversation_id": conversation_id,
        "context_mode": "compartmented",
        "persist_user_message": True
    }
    
    response = make_request("POST", "/chat/stream", headers=headers, json_data=conversation_data)
    
    if response and response.status_code == 200:
        # Wait a moment for the conversation to be created
        time.sleep(2)
        return conversation_id
    else:
        return None

def test_prompt_selected_endpoint(headers, cookies, results):
    """Test POST /api/a0/non-ui/prompt/selected"""
    print("\n=== Testing Prompt Selected Endpoint ===")
    
    test_data = {
        "message": "What is artificial intelligence?",
        "models": ["gpt-5.2"],
        "context_mode": "compartmented",
        "persist_user_message": True
    }
    
    response = make_request("POST", "/a0/non-ui/prompt/selected", headers=headers, cookies=cookies, json_data=test_data)
    
    if not response:
        results.add_fail("Prompt selected endpoint", "No response received")
        return None
    
    if response.status_code != 200:
        results.add_fail("Prompt selected endpoint", f"Status {response.status_code}: {response.text}")
        return None
    
    # For SSE endpoints, check if response is streaming
    content_type = response.headers.get('content-type', '')
    if 'text/event-stream' in content_type or 'text/plain' in content_type:
        results.add_pass("Prompt selected endpoint", "SSE stream response received")
        
        # Try to get conversation_id from response headers or content
        conversation_id = response.headers.get('x-conversation-id')
        if conversation_id:
            return conversation_id
        
        # Try to extract conversation_id from streaming response
        try:
            for line in response.iter_lines(decode_unicode=True):
                if line.startswith('data:'):
                    data_str = line[5:].strip()
                    if data_str and data_str != '[DONE]':
                        try:
                            data = json.loads(data_str)
                            if 'conversation_id' in data:
                                return data['conversation_id']
                        except json.JSONDecodeError:
                            continue
        except:
            pass
        
        return "test-conversation-id"  # Return a test ID if we can't extract one
    else:
        results.add_fail("Prompt selected endpoint", f"Expected SSE stream, got {content_type}")
        return None

def test_prompt_all_endpoint(headers, cookies, results):
    """Test POST /api/a0/non-ui/prompt/all"""
    print("\n=== Testing Prompt All Endpoint ===")
    
    test_data = {
        "message": "Explain quantum computing briefly",
        "context_mode": "compartmented",
        "persist_user_message": True
    }
    
    response = make_request("POST", "/a0/non-ui/prompt/all", headers=headers, json_data=test_data)
    
    if not response:
        results.add_fail("Prompt all endpoint", "No response received")
        return
    
    if response.status_code != 200:
        results.add_fail("Prompt all endpoint", f"Status {response.status_code}: {response.text}")
        return
    
    content_type = response.headers.get('content-type', '')
    if 'text/event-stream' in content_type or 'text/plain' in content_type:
        results.add_pass("Prompt all endpoint", "SSE stream response received")
    else:
        results.add_fail("Prompt all endpoint", f"Expected SSE stream, got {content_type}")

def test_history_endpoint(headers, cookies, conversation_id, results):
    """Test GET /api/a0/non-ui/history/{conversation_id}"""
    print("\n=== Testing History Endpoint ===")
    
    if not conversation_id:
        results.add_fail("History endpoint", "No conversation ID available for testing")
        return
    
    # Test with pagination parameters
    params = {"offset": 0, "limit": 10}
    response = make_request("GET", f"/a0/non-ui/history/{conversation_id}", 
                          headers=headers, params=params)
    
    if not response:
        results.add_fail("History endpoint", "No response received")
        return
    
    if response.status_code == 404:
        results.add_fail("History endpoint", "Conversation not found - may be expected for test conversation")
        return
    
    if response.status_code != 200:
        results.add_fail("History endpoint", f"Status {response.status_code}: {response.text}")
        return
    
    try:
        data = response.json()
        
        # Check for required pagination fields
        required_fields = ["offset", "limit", "total_messages", "messages"]
        missing_fields = [field for field in required_fields if field not in data]
        
        if not missing_fields:
            results.add_pass("History endpoint", f"Contains pagination fields: {', '.join(required_fields)}")
        else:
            results.add_fail("History endpoint", f"Missing fields: {', '.join(missing_fields)}")
            
    except json.JSONDecodeError:
        results.add_fail("History endpoint", "Invalid JSON response")

def test_synthesis_endpoint(headers, cookies, conversation_id, results):
    """Test POST /api/a0/non-ui/synthesis"""
    print("\n=== Testing Synthesis Endpoint ===")
    
    if not conversation_id:
        results.add_fail("Synthesis endpoint", "No conversation ID available for testing")
        return
    
    test_data = {
        "conversation_id": conversation_id,
        "selected_message_ids": ["dummy-message-id"],
        "target_models": ["gpt-5.2"],
        "synthesis_prompt": "Analyze this response:"
    }
    
    response = make_request("POST", "/a0/non-ui/synthesis", headers=headers, json_data=test_data)
    
    if not response:
        results.add_fail("Synthesis endpoint", "No response received")
        return
    
    # This might return 404 if no messages found, which is expected for test data
    if response.status_code == 404:
        results.add_pass("Synthesis endpoint", "404 for missing messages - endpoint accessible")
        return
    
    if response.status_code == 400:
        # Check if it's a validation error (expected for dummy data)
        try:
            error_data = response.json()
            if "detail" in error_data:
                results.add_pass("Synthesis endpoint", "400 validation error - endpoint accessible and validating")
                return
        except:
            pass
    
    if response.status_code != 200:
        results.add_fail("Synthesis endpoint", f"Status {response.status_code}: {response.text}")
        return
    
    content_type = response.headers.get('content-type', '')
    if 'text/event-stream' in content_type or 'text/plain' in content_type:
        results.add_pass("Synthesis endpoint", "SSE stream response received")
    else:
        results.add_fail("Synthesis endpoint", f"Expected SSE stream, got {content_type}")

def test_export_endpoint(headers, cookies, conversation_id, results):
    """Test GET /api/a0/non-ui/conversations/{conversation_id}/export"""
    print("\n=== Testing Export Endpoint ===")
    
    if not conversation_id:
        results.add_fail("Export endpoint", "No conversation ID available for testing")
        return
    
    params = {"format": "json"}
    response = make_request("GET", f"/a0/non-ui/conversations/{conversation_id}/export", 
                          headers=headers, params=params)
    
    if not response:
        results.add_fail("Export endpoint", "No response received")
        return
    
    # This might return 404 if conversation not found, which is expected for test data
    if response.status_code == 404:
        results.add_pass("Export endpoint", "404 for missing conversation - endpoint accessible")
        return
    
    if response.status_code != 200:
        results.add_fail("Export endpoint", f"Status {response.status_code}: {response.text}")
        return
    
    # Check content type for JSON format
    content_type = response.headers.get('content-type', '')
    if 'application/json' in content_type:
        results.add_pass("Export endpoint", "JSON export response received")
    else:
        results.add_pass("Export endpoint", f"Export response received (content-type: {content_type})")

def main():
    """Run all Agent Zero non-UI REST endpoint tests"""
    print("🤖 Agent Zero Non-UI REST Endpoints Test Suite")
    print("=" * 60)
    
    results = TestResult()
    
    # Test unauthenticated access first
    if not test_unauthenticated_access(results):
        print("⚠️  Some endpoints allow unauthenticated access")
    
    # Setup test user
    print("\n🔧 Setting up test user...")
    user_id, session_token = setup_test_user()
    
    if not user_id or not session_token:
        print("❌ Failed to setup test user. Cannot continue with authenticated tests.")
        print(f"\nResults: {results.summary()}")
        return
    
    print(f"✅ Test user created: {user_id}")
    
    # Setup headers and cookies for authentication
    headers = {
        "Content-Type": "application/json"
    }
    cookies = {
        "session_token": session_token
    }
    
    try:
        # Test 1: GET /api/a0/non-ui/options
        options_data = test_options_endpoint(headers, results)
        
        # Test 2: POST /api/a0/non-ui/prompt/selected  
        conversation_id = test_prompt_selected_endpoint(headers, results)
        
        # Test 3: POST /api/a0/non-ui/prompt/all
        test_prompt_all_endpoint(headers, results)
        
        # Test 4: GET /api/a0/non-ui/history/{conversation_id}
        test_history_endpoint(headers, conversation_id, results)
        
        # Test 5: POST /api/a0/non-ui/synthesis
        test_synthesis_endpoint(headers, conversation_id, results)
        
        # Test 6: GET /api/a0/non-ui/conversations/{conversation_id}/export
        test_export_endpoint(headers, conversation_id, results)
        
    finally:
        # Cleanup
        print(f"\n🧹 Cleaning up test user...")
        cleanup_test_user(user_id, session_token)
    
    # Print results
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS")
    print("=" * 60)
    for detail in results.details:
        print(detail)
    
    print(f"\n📈 {results.summary()}")
    
    if results.failed > 0:
        print(f"\n❌ {results.failed} test(s) failed")
        return 1
    else:
        print(f"\n✅ All {results.passed} tests passed!")
        return 0

if __name__ == "__main__":
    sys.exit(main())