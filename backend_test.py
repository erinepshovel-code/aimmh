#!/usr/bin/env python3
"""
Backend API regression test for prompt hub application
Tests: auth-protected access, chat stream persistence, feedback, payments catalog/summary/checkout
"""

import requests
import json
import time
import uuid
from typing import Dict, Any, Optional

BASE_URL = "https://prompt-hub-67.preview.emergentagent.com"
API_BASE = f"{BASE_URL}/api"

class BackendTester:
    def __init__(self):
        self.session_token = None
        self.user_id = None
        self.test_results = []
        
    def log_result(self, test_name: str, success: bool, message: str, details: str = ""):
        """Log test result"""
        result = {
            "test": test_name,
            "success": success,
            "message": message,
            "details": details
        }
        self.test_results.append(result)
        status = "✅" if success else "❌"
        print(f"{status} {test_name}: {message}")
        if details and not success:
            print(f"   Details: {details}")
    
    def setup_auth_session(self) -> bool:
        """Setup authentication using existing session token from MongoDB"""
        try:
            # Use existing valid session token
            self.session_token = "test_session_1772298188498"
            
            # Test auth with this session
            response = requests.get(
                f"{API_BASE}/auth/me",
                cookies={"session_token": self.session_token},
                timeout=10
            )
            
            if response.status_code == 200:
                user_data = response.json()
                self.user_id = user_data.get("user_id")
                self.log_result("Auth Setup", True, f"Authenticated as user: {self.user_id}")
                return True
            else:
                self.log_result("Auth Setup", False, f"Auth failed: {response.status_code}", response.text[:200])
                return False
                
        except Exception as e:
            self.log_result("Auth Setup", False, f"Auth setup error: {str(e)}")
            return False
    
    def test_auth_protected_access(self):
        """Test 1: Auth-protected access rules"""
        
        # Test unauthorized access
        try:
            response = requests.get(f"{API_BASE}/auth/me", timeout=10)
            if response.status_code == 401:
                self.log_result("Auth - Unauthorized Access", True, "Correctly blocked unauthorized access")
            else:
                self.log_result("Auth - Unauthorized Access", False, f"Expected 401, got {response.status_code}")
        except Exception as e:
            self.log_result("Auth - Unauthorized Access", False, f"Error testing unauthorized: {str(e)}")
        
        # Test authorized access
        try:
            response = requests.get(
                f"{API_BASE}/auth/me",
                cookies={"session_token": self.session_token},
                timeout=10
            )
            if response.status_code == 200:
                user_data = response.json()
                if "user_id" in user_data:
                    self.log_result("Auth - Authorized Access", True, "Successfully authenticated and returned user data")
                else:
                    self.log_result("Auth - Authorized Access", False, "Missing user_id in response")
            else:
                self.log_result("Auth - Authorized Access", False, f"Expected 200, got {response.status_code}")
        except Exception as e:
            self.log_result("Auth - Authorized Access", False, f"Error testing authorized: {str(e)}")
        
        # Test conversations endpoint (auth required)
        try:
            response = requests.get(
                f"{API_BASE}/conversations",
                cookies={"session_token": self.session_token},
                timeout=10
            )
            if response.status_code == 200:
                self.log_result("Auth - Protected Endpoint", True, f"Conversations accessible, returned {len(response.json())} conversations")
            else:
                self.log_result("Auth - Protected Endpoint", False, f"Conversations failed: {response.status_code}")
        except Exception as e:
            self.log_result("Auth - Protected Endpoint", False, f"Error testing conversations: {str(e)}")
    
    def test_chat_stream_persistence(self):
        """Test 2: Chat stream persistence + message retrieval"""
        
        conversation_id = str(uuid.uuid4())
        message_id = None
        
        # Send a message via chat stream
        try:
            chat_payload = {
                "message": "Backend regression test message",
                "models": ["gpt-5.2"],
                "conversation_id": conversation_id,
                "context_mode": "shared",
                "shared_room_mode": "parallel_all",
                "persist_user_message": True,
                "history_limit": 10
            }
            
            response = requests.post(
                f"{API_BASE}/chat/stream",
                json=chat_payload,
                cookies={"session_token": self.session_token},
                headers={"Accept": "text/event-stream"},
                timeout=30,
                stream=True
            )
            
            if response.status_code == 200:
                # Parse SSE stream to get message_id
                events = []
                for line in response.iter_lines(decode_unicode=True):
                    if line and line.startswith('data: '):
                        try:
                            data_str = line[6:]  # Remove 'data: ' prefix
                            if data_str.strip():  # Only process non-empty data
                                data = json.loads(data_str)
                                events.append(data)
                                if not message_id and 'message_id' in data:
                                    message_id = data.get('message_id')
                        except json.JSONDecodeError:
                            continue
                        except:
                            continue
                
                if events:
                    self.log_result("Chat Stream - Send Message", True, f"Stream completed with {len(events)} events")
                else:
                    self.log_result("Chat Stream - Send Message", False, "Stream completed but no events parsed")
            else:
                self.log_result("Chat Stream - Send Message", False, f"Stream failed: {response.status_code}", response.text[:200])
        
        except Exception as e:
            self.log_result("Chat Stream - Send Message", False, f"Error sending message: {str(e)}")
        
        # Wait a moment for persistence
        time.sleep(2)
        
        # Test message retrieval
        try:
            response = requests.get(
                f"{API_BASE}/conversations/{conversation_id}/messages",
                cookies={"session_token": self.session_token},
                timeout=10
            )
            
            if response.status_code == 200:
                messages = response.json()
                if len(messages) >= 1:  # At least user message should be persisted
                    user_msgs = [m for m in messages if m.get('role') == 'user']
                    assistant_msgs = [m for m in messages if m.get('role') == 'assistant']
                    
                    if user_msgs:
                        self.log_result("Chat Persistence - Message Retrieval", True, 
                                      f"Retrieved {len(messages)} messages: {len(user_msgs)} user, {len(assistant_msgs)} assistant")
                        # Get message_id from assistant message for feedback testing
                        if assistant_msgs:
                            message_id = assistant_msgs[0].get('id')
                    else:
                        self.log_result("Chat Persistence - Message Retrieval", False, "No user messages found in conversation")
                else:
                    self.log_result("Chat Persistence - Message Retrieval", False, "No messages found after sending")
            else:
                self.log_result("Chat Persistence - Message Retrieval", False, f"Retrieval failed: {response.status_code}")
        
        except Exception as e:
            self.log_result("Chat Persistence - Message Retrieval", False, f"Error retrieving messages: {str(e)}")
        
        return message_id, conversation_id
    
    def test_feedback_endpoints(self, message_id: Optional[str]):
        """Test 3: Chat feedback up/down and 404 for invalid message ID"""
        
        if not message_id:
            self.log_result("Feedback - No Message ID", False, "Skipping feedback test: no valid message ID")
            return
        
        # Test thumbs up feedback
        try:
            feedback_payload = {
                "message_id": message_id,
                "feedback": "up"
            }
            
            response = requests.post(
                f"{API_BASE}/chat/feedback",
                json=feedback_payload,
                cookies={"session_token": self.session_token},
                timeout=10
            )
            
            if response.status_code == 200:
                self.log_result("Feedback - Thumbs Up", True, "Successfully submitted thumbs up feedback")
            elif response.status_code == 404:
                self.log_result("Feedback - Thumbs Up", False, "Message not found for feedback (404)")
            else:
                self.log_result("Feedback - Thumbs Up", False, f"Unexpected status: {response.status_code}")
        
        except Exception as e:
            self.log_result("Feedback - Thumbs Up", False, f"Error submitting thumbs up: {str(e)}")
        
        # Test thumbs down feedback
        try:
            feedback_payload = {
                "message_id": message_id,
                "feedback": "down"
            }
            
            response = requests.post(
                f"{API_BASE}/chat/feedback",
                json=feedback_payload,
                cookies={"session_token": self.session_token},
                timeout=10
            )
            
            if response.status_code == 200:
                self.log_result("Feedback - Thumbs Down", True, "Successfully submitted thumbs down feedback")
            elif response.status_code == 404:
                self.log_result("Feedback - Thumbs Down", False, "Message not found for feedback (404)")
            else:
                self.log_result("Feedback - Thumbs Down", False, f"Unexpected status: {response.status_code}")
        
        except Exception as e:
            self.log_result("Feedback - Thumbs Down", False, f"Error submitting thumbs down: {str(e)}")
        
        # Test invalid message ID (should return 404)
        try:
            invalid_feedback = {
                "message_id": "invalid-message-id",
                "feedback": "up"
            }
            
            response = requests.post(
                f"{API_BASE}/chat/feedback",
                json=invalid_feedback,
                cookies={"session_token": self.session_token},
                timeout=10
            )
            
            if response.status_code == 404:
                self.log_result("Feedback - Invalid Message ID", True, "Correctly returned 404 for invalid message ID")
            else:
                self.log_result("Feedback - Invalid Message ID", False, f"Expected 404, got {response.status_code}")
        
        except Exception as e:
            self.log_result("Feedback - Invalid Message ID", False, f"Error testing invalid ID: {str(e)}")
    
    def test_payments_catalog(self):
        """Test 4: Payments catalog fields and categories"""
        
        try:
            response = requests.get(
                f"{API_BASE}/payments/catalog",
                cookies={"session_token": self.session_token},
                timeout=10
            )
            
            if response.status_code == 200:
                catalog = response.json()
                
                # Check required fields exist
                required_fields = ["prices", "founder_slots_total", "founder_slots_remaining"]
                missing_fields = [field for field in required_fields if field not in catalog]
                
                if missing_fields:
                    self.log_result("Payments Catalog - Fields", False, f"Missing fields: {missing_fields}")
                else:
                    self.log_result("Payments Catalog - Fields", True, "All required catalog fields present")
                
                # Check categories
                prices = catalog.get("prices", [])
                categories = set(price.get("category") for price in prices)
                expected_categories = {"core", "support", "founder", "credits"}
                
                if expected_categories.issubset(categories):
                    self.log_result("Payments Catalog - Categories", True, f"Found all expected categories: {sorted(categories)}")
                else:
                    missing = expected_categories - categories
                    self.log_result("Payments Catalog - Categories", False, f"Missing categories: {missing}")
                
                # Check price structure
                if prices:
                    sample_price = prices[0]
                    price_fields = ["package_id", "name", "amount", "currency", "billing_type", "category"]
                    missing_price_fields = [field for field in price_fields if field not in sample_price]
                    
                    if missing_price_fields:
                        self.log_result("Payments Catalog - Price Structure", False, f"Missing price fields: {missing_price_fields}")
                    else:
                        self.log_result("Payments Catalog - Price Structure", True, "Price objects have correct structure")
                else:
                    self.log_result("Payments Catalog - Price Structure", False, "No prices in catalog")
            
            else:
                self.log_result("Payments Catalog - Request", False, f"Catalog request failed: {response.status_code}")
        
        except Exception as e:
            self.log_result("Payments Catalog - Request", False, f"Error fetching catalog: {str(e)}")
    
    def test_payments_summary(self):
        """Test 5: Payments summary shape"""
        
        try:
            response = requests.get(
                f"{API_BASE}/payments/summary",
                cookies={"session_token": self.session_token},
                timeout=10
            )
            
            if response.status_code == 200:
                summary = response.json()
                
                # Check required fields
                required_fields = [
                    "total_paid_usd", "total_support_usd", "total_founder_usd", 
                    "total_compute_usd", "total_core_usd", "estimated_usage_cost_usd", 
                    "total_estimated_tokens"
                ]
                
                missing_fields = [field for field in required_fields if field not in summary]
                
                if missing_fields:
                    self.log_result("Payments Summary - Shape", False, f"Missing fields: {missing_fields}")
                else:
                    # Verify field types
                    numeric_fields = required_fields  # All should be numeric
                    type_errors = []
                    
                    for field in numeric_fields:
                        value = summary.get(field)
                        if not isinstance(value, (int, float)):
                            type_errors.append(f"{field}: {type(value).__name__}")
                    
                    if type_errors:
                        self.log_result("Payments Summary - Shape", False, f"Wrong types: {type_errors}")
                    else:
                        self.log_result("Payments Summary - Shape", True, f"Summary shape correct: {len(summary)} fields")
            
            else:
                self.log_result("Payments Summary - Request", False, f"Summary request failed: {response.status_code}")
        
        except Exception as e:
            self.log_result("Payments Summary - Request", False, f"Error fetching summary: {str(e)}")
    
    def test_checkout_session(self):
        """Test 6: Checkout session creation for package IDs"""
        
        test_packages = ["core_monthly", "support_one_time_1", "credits_10", "founder_one_time"]
        
        for package_id in test_packages:
            try:
                checkout_payload = {
                    "package_id": package_id,
                    "origin_url": BASE_URL
                }
                
                response = requests.post(
                    f"{API_BASE}/payments/checkout/session",
                    json=checkout_payload,
                    cookies={"session_token": self.session_token},
                    timeout=10
                )
                
                if response.status_code == 200:
                    session_data = response.json()
                    
                    # Check required response fields
                    required_fields = ["url", "session_id"]
                    missing_fields = [field for field in required_fields if field not in session_data]
                    
                    if missing_fields:
                        self.log_result(f"Checkout - {package_id}", False, f"Missing fields: {missing_fields}")
                    else:
                        # Verify URL format
                        url = session_data.get("url")
                        if url and url.startswith("https://checkout.stripe.com"):
                            self.log_result(f"Checkout - {package_id}", True, "Session created with valid Stripe URL")
                        else:
                            self.log_result(f"Checkout - {package_id}", False, f"Invalid URL format: {url}")
                
                elif response.status_code == 409 and package_id == "founder_one_time":
                    self.log_result(f"Checkout - {package_id}", True, "Founder slots sold out (409 expected)")
                else:
                    self.log_result(f"Checkout - {package_id}", False, f"Request failed: {response.status_code}")
            
            except Exception as e:
                self.log_result(f"Checkout - {package_id}", False, f"Error creating session: {str(e)}")
    
    def test_checkout_status(self):
        """Test 7: Checkout status endpoint response fields"""
        
        # Create a dummy session first
        try:
            checkout_payload = {
                "package_id": "support_one_time_1",
                "origin_url": BASE_URL
            }
            
            response = requests.post(
                f"{API_BASE}/payments/checkout/session",
                json=checkout_payload,
                cookies={"session_token": self.session_token},
                timeout=10
            )
            
            if response.status_code != 200:
                self.log_result("Checkout Status - Session Creation", False, f"Could not create test session: {response.status_code}")
                return
            
            session_data = response.json()
            session_id = session_data.get("session_id")
            
            if not session_id:
                self.log_result("Checkout Status - Session ID", False, "No session_id in response")
                return
            
            # Now test the status endpoint
            status_response = requests.get(
                f"{API_BASE}/payments/checkout/status/{session_id}",
                cookies={"session_token": self.session_token},
                timeout=10
            )
            
            if status_response.status_code == 200:
                status_data = status_response.json()
                
                # Check required response fields
                required_fields = ["session_id", "status", "payment_status", "amount_total", "currency"]
                missing_fields = [field for field in required_fields if field not in status_data]
                
                if missing_fields:
                    self.log_result("Checkout Status - Response Fields", False, f"Missing fields: {missing_fields}")
                else:
                    # Verify session_id matches
                    if status_data.get("session_id") == session_id:
                        self.log_result("Checkout Status - Response Fields", True, "All required fields present and session_id matches")
                    else:
                        self.log_result("Checkout Status - Response Fields", False, "Session ID mismatch")
            else:
                self.log_result("Checkout Status - Request", False, f"Status request failed: {status_response.status_code}")
        
        except Exception as e:
            self.log_result("Checkout Status - Request", False, f"Error testing status: {str(e)}")
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*80)
        print("BACKEND API REGRESSION TEST SUMMARY")
        print("="*80)
        
        passed = sum(1 for result in self.test_results if result["success"])
        failed = len(self.test_results) - passed
        
        print(f"Total Tests: {len(self.test_results)}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        
        if failed > 0:
            print(f"\nFAILED TESTS:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"❌ {result['test']}: {result['message']}")
                    if result["details"]:
                        print(f"   {result['details'][:100]}...")
        
        print(f"\nOVERALL RESULT: {'PASS' if failed == 0 else 'FAIL'}")
        return failed == 0


def main():
    """Run backend API regression tests"""
    print("Starting Backend API Regression Tests")
    print(f"Target: {BASE_URL}")
    print("="*60)
    
    tester = BackendTester()
    
    # Setup authentication
    if not tester.setup_auth_session():
        print("❌ Failed to setup authentication - aborting tests")
        return False
    
    # Run all tests
    tester.test_auth_protected_access()
    message_id, conversation_id = tester.test_chat_stream_persistence()
    tester.test_feedback_endpoints(message_id)
    tester.test_payments_catalog()
    tester.test_payments_summary()
    tester.test_checkout_session()
    tester.test_checkout_status()
    
    # Print final results
    success = tester.print_summary()
    return success


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)