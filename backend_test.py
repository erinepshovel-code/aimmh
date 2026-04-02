#!/usr/bin/env python3
"""
Backend Health/Readiness Endpoints Validation Test
Tests the health and readiness endpoints on the preview URL.
"""

import requests
import json
import sys
from typing import Dict, Any

# Use the production URL from frontend/.env
BASE_URL = "https://aimmh-hub-1.preview.emergentagent.com"

def test_endpoint(method: str, url: str, expected_status: int = 200) -> Dict[str, Any]:
    """Test an endpoint and return structured results."""
    try:
        if method.upper() == "GET":
            response = requests.get(url, timeout=10)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        result = {
            "url": url,
            "method": method,
            "status_code": response.status_code,
            "expected_status": expected_status,
            "success": response.status_code == expected_status,
            "response_time_ms": round(response.elapsed.total_seconds() * 1000, 2)
        }
        
        # Try to parse JSON response
        try:
            result["response_json"] = response.json()
        except:
            result["response_text"] = response.text[:500]  # Truncate long responses
            
        return result
        
    except Exception as e:
        return {
            "url": url,
            "method": method,
            "status_code": None,
            "expected_status": expected_status,
            "success": False,
            "error": str(e),
            "response_time_ms": None
        }

def validate_health_response(response_data: Dict[str, Any], endpoint_name: str) -> Dict[str, Any]:
    """Validate health endpoint response structure."""
    validation = {
        "endpoint": endpoint_name,
        "valid_structure": True,
        "issues": []
    }
    
    # Check required fields
    if "status" not in response_data:
        validation["valid_structure"] = False
        validation["issues"].append("Missing 'status' field")
    elif response_data["status"] != "ok":
        validation["valid_structure"] = False
        validation["issues"].append(f"Status is '{response_data['status']}', expected 'ok'")
    
    return validation

def validate_ready_response(response_data: Dict[str, Any], endpoint_name: str) -> Dict[str, Any]:
    """Validate readiness endpoint response structure."""
    validation = {
        "endpoint": endpoint_name,
        "valid_structure": True,
        "issues": []
    }
    
    # Check required fields
    required_fields = ["status", "checks"]
    for field in required_fields:
        if field not in response_data:
            validation["valid_structure"] = False
            validation["issues"].append(f"Missing '{field}' field")
    
    # Check status value
    if "status" in response_data:
        if response_data["status"] not in ["ready", "not_ready"]:
            validation["valid_structure"] = False
            validation["issues"].append(f"Invalid status '{response_data['status']}', expected 'ready' or 'not_ready'")
    
    # Check checks.mongo structure
    if "checks" in response_data:
        if "mongo" not in response_data["checks"]:
            validation["valid_structure"] = False
            validation["issues"].append("Missing 'checks.mongo' field")
        else:
            mongo_check = response_data["checks"]["mongo"]
            if "ok" not in mongo_check:
                validation["valid_structure"] = False
                validation["issues"].append("Missing 'checks.mongo.ok' field")
            if "message" not in mongo_check:
                validation["valid_structure"] = False
                validation["issues"].append("Missing 'checks.mongo.message' field")
    
    return validation

def main():
    """Run all health/readiness endpoint tests."""
    print("🔍 BACKEND HEALTH/READINESS ENDPOINTS VALIDATION")
    print(f"Testing against: {BASE_URL}")
    print("=" * 60)
    
    test_results = []
    validations = []
    
    # Test 1: GET /api/health should return 200 with JSON containing status=ok
    print("\n1️⃣  Testing GET /api/health")
    result = test_endpoint("GET", f"{BASE_URL}/api/health", 200)
    test_results.append(result)
    
    if result["success"] and "response_json" in result:
        validation = validate_health_response(result["response_json"], "/api/health")
        validations.append(validation)
        print(f"   ✅ Status: {result['status_code']} | Response time: {result['response_time_ms']}ms")
        print(f"   📄 Response: {json.dumps(result['response_json'], indent=2)}")
        if validation["valid_structure"]:
            print(f"   ✅ Structure validation: PASSED")
        else:
            print(f"   ❌ Structure validation: FAILED - {', '.join(validation['issues'])}")
    else:
        print(f"   ❌ Failed: Status {result.get('status_code', 'N/A')} | Error: {result.get('error', 'Unknown')}")
    
    # Test 2: GET /api/ready should return 200/503 with proper structure
    print("\n2️⃣  Testing GET /api/ready")
    result = test_endpoint("GET", f"{BASE_URL}/api/ready")  # Don't specify expected status
    test_results.append(result)
    
    if "response_json" in result:
        validation = validate_ready_response(result["response_json"], "/api/ready")
        validations.append(validation)
        
        response_data = result["response_json"]
        mongo_status = response_data.get("checks", {}).get("mongo", {}).get("ok", False)
        expected_status = 200 if mongo_status else 503
        
        print(f"   ✅ Status: {result['status_code']} | Response time: {result['response_time_ms']}ms")
        print(f"   📄 Response: {json.dumps(result['response_json'], indent=2)}")
        
        if result["status_code"] == expected_status:
            print(f"   ✅ Status code validation: PASSED (expected {expected_status} based on mongo.ok={mongo_status})")
        else:
            print(f"   ❌ Status code validation: FAILED (got {result['status_code']}, expected {expected_status})")
            
        if validation["valid_structure"]:
            print(f"   ✅ Structure validation: PASSED")
        else:
            print(f"   ❌ Structure validation: FAILED - {', '.join(validation['issues'])}")
    else:
        print(f"   ❌ Failed: Status {result.get('status_code', 'N/A')} | Error: {result.get('error', 'Unknown')}")
    
    # Test 3: GET /api/v1/health should return 200
    print("\n3️⃣  Testing GET /api/v1/health")
    result = test_endpoint("GET", f"{BASE_URL}/api/v1/health", 200)
    test_results.append(result)
    
    if result["success"] and "response_json" in result:
        validation = validate_health_response(result["response_json"], "/api/v1/health")
        validations.append(validation)
        print(f"   ✅ Status: {result['status_code']} | Response time: {result['response_time_ms']}ms")
        print(f"   📄 Response: {json.dumps(result['response_json'], indent=2)}")
        if validation["valid_structure"]:
            print(f"   ✅ Structure validation: PASSED")
        else:
            print(f"   ❌ Structure validation: FAILED - {', '.join(validation['issues'])}")
    else:
        print(f"   ❌ Failed: Status {result.get('status_code', 'N/A')} | Error: {result.get('error', 'Unknown')}")
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    total_tests = len(test_results)
    passed_tests = sum(1 for r in test_results if r["success"])
    failed_tests = total_tests - passed_tests
    
    print(f"Total tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {failed_tests}")
    
    if failed_tests == 0:
        print("\n🎉 ALL TESTS PASSED!")
    else:
        print(f"\n⚠️  {failed_tests} TEST(S) FAILED")
        
    # Detailed results
    print("\n📋 DETAILED RESULTS:")
    for i, result in enumerate(test_results, 1):
        status_icon = "✅" if result["success"] else "❌"
        print(f"{i}. {status_icon} {result['method']} {result['url']} - Status: {result.get('status_code', 'N/A')}")
        if not result["success"] and "error" in result:
            print(f"   Error: {result['error']}")
    
    # Structure validation summary
    print("\n🔍 STRUCTURE VALIDATION SUMMARY:")
    for validation in validations:
        status_icon = "✅" if validation["valid_structure"] else "❌"
        print(f"{status_icon} {validation['endpoint']}")
        if not validation["valid_structure"]:
            for issue in validation["issues"]:
                print(f"   - {issue}")
    
    return failed_tests == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)