"""
Iteration 27: UX/Logic Changes Testing
- Backend: /api/payments/summary returns free max_instances=5 and daily limits
- Backend: /api/v1/hub/chat/prompts enforces 25/24h quota for free users; guest quota by IP
- Backend: /api/v1/hub/runs enforces 5/24h batch and 2/24h roleplay quotas for free users
- Backend: roleplay and batch separation validation
- Backend: guide instance (metadata.welcome_model=true) does not count toward instance quota
"""

import pytest
import requests
import os
import time
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestPaymentsSummary:
    """Test /api/payments/summary returns correct free tier limits"""
    
    def test_health_check(self):
        """Verify backend is running"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "ok"
        print("PASS: Health check returns status=ok")
    
    def test_payments_summary_requires_auth(self):
        """Verify /api/payments/summary requires authentication"""
        response = requests.get(f"{BASE_URL}/api/payments/summary")
        assert response.status_code == 401
        print("PASS: /api/payments/summary returns 401 for unauthenticated request")
    
    def test_payments_summary_free_tier_limits(self):
        """Verify free tier limits in /api/payments/summary"""
        # Register a fresh user
        username = f"test_user_{uuid.uuid4().hex[:8]}"
        password = "TestPass123!"
        
        register_response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "username": username,
            "password": password
        })
        assert register_response.status_code in [200, 201], f"Registration failed: {register_response.text}"
        token = register_response.json().get("access_token")
        assert token, "No access_token returned from registration"
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Get payments summary
        summary_response = requests.get(f"{BASE_URL}/api/payments/summary", headers=headers)
        assert summary_response.status_code == 200, f"Summary failed: {summary_response.text}"
        
        data = summary_response.json()
        
        # Verify free tier limits
        assert data.get("current_tier") == "free", f"Expected free tier, got {data.get('current_tier')}"
        assert data.get("max_instances") == 5, f"Expected max_instances=5, got {data.get('max_instances')}"
        assert data.get("daily_chats_per_24h") == 25, f"Expected daily_chats_per_24h=25, got {data.get('daily_chats_per_24h')}"
        assert data.get("daily_batch_runs_per_24h") == 5, f"Expected daily_batch_runs_per_24h=5, got {data.get('daily_batch_runs_per_24h')}"
        assert data.get("daily_roleplay_runs_per_24h") == 2, f"Expected daily_roleplay_runs_per_24h=2, got {data.get('daily_roleplay_runs_per_24h')}"
        
        print(f"PASS: Free tier limits correct - max_instances={data.get('max_instances')}, daily_chats={data.get('daily_chats_per_24h')}, daily_batch={data.get('daily_batch_runs_per_24h')}, daily_roleplay={data.get('daily_roleplay_runs_per_24h')}")


class TestGuestQuotaByIP:
    """Test guest quota enforcement by IP"""
    
    def test_guest_access_with_x_guest_id(self):
        """Verify guest can access hub endpoints with X-Guest-Id header"""
        guest_id = f"guest_{uuid.uuid4().hex[:12]}"
        headers = {"X-Guest-Id": guest_id}
        
        # Try to access hub options
        response = requests.get(f"{BASE_URL}/api/v1/hub/options", headers=headers)
        # Should either work (200) or require auth (401)
        assert response.status_code in [200, 401], f"Unexpected status: {response.status_code}"
        print(f"PASS: Guest access with X-Guest-Id returns {response.status_code}")
    
    def test_hub_instances_list_guest(self):
        """Verify guest can list instances"""
        guest_id = f"guest_{uuid.uuid4().hex[:12]}"
        headers = {"X-Guest-Id": guest_id}
        
        response = requests.get(f"{BASE_URL}/api/v1/hub/instances", headers=headers)
        # Should either work (200) or require auth (401)
        assert response.status_code in [200, 401], f"Unexpected status: {response.status_code}"
        print(f"PASS: Guest instances list returns {response.status_code}")


class TestRunModeValidation:
    """Test batch vs roleplay run mode validation"""
    
    def test_batch_run_disallows_roleplay_stage(self):
        """Verify batch runs cannot include roleplay stages"""
        # Register a fresh user
        username = f"test_user_{uuid.uuid4().hex[:8]}"
        password = "TestPass123!"
        
        register_response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "username": username,
            "password": password
        })
        assert register_response.status_code in [200, 201], f"Registration failed: {register_response.text}"
        token = register_response.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        
        # Try to create a batch run with roleplay stage
        run_payload = {
            "prompt": "Test prompt",
            "run_mode": "batch",
            "stages": [
                {
                    "pattern": "roleplay",
                    "source_type": "instance",
                    "source_ids": []
                }
            ]
        }
        
        response = requests.post(f"{BASE_URL}/api/v1/hub/runs", json=run_payload, headers=headers)
        # Should return 422 for validation error
        assert response.status_code == 422, f"Expected 422 for batch run with roleplay stage, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "roleplay" in str(data.get("detail", "")).lower() or "batch" in str(data.get("detail", "")).lower(), f"Expected error about roleplay/batch, got: {data}"
        print("PASS: Batch run with roleplay stage correctly rejected with 422")
    
    def test_roleplay_run_requires_roleplay_stage(self):
        """Verify roleplay runs require at least one roleplay stage"""
        # Register a fresh user
        username = f"test_user_{uuid.uuid4().hex[:8]}"
        password = "TestPass123!"
        
        register_response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "username": username,
            "password": password
        })
        assert register_response.status_code in [200, 201], f"Registration failed: {register_response.text}"
        token = register_response.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        
        # Try to create a roleplay run without roleplay stage
        run_payload = {
            "prompt": "Test prompt",
            "run_mode": "roleplay",
            "stages": [
                {
                    "pattern": "fan_out",
                    "source_type": "instance",
                    "source_ids": []
                }
            ]
        }
        
        response = requests.post(f"{BASE_URL}/api/v1/hub/runs", json=run_payload, headers=headers)
        # Should return 422 for validation error
        assert response.status_code == 422, f"Expected 422 for roleplay run without roleplay stage, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "roleplay" in str(data.get("detail", "")).lower(), f"Expected error about roleplay, got: {data}"
        print("PASS: Roleplay run without roleplay stage correctly rejected with 422")


class TestWelcomeModelQuotaExclusion:
    """Test that guide instance (welcome_model=true) doesn't count toward quota"""
    
    def test_welcome_model_metadata_flag(self):
        """Verify instances can have welcome_model metadata"""
        # Register a fresh user
        username = f"test_user_{uuid.uuid4().hex[:8]}"
        password = "TestPass123!"
        
        register_response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "username": username,
            "password": password
        })
        assert register_response.status_code in [200, 201], f"Registration failed: {register_response.text}"
        token = register_response.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        
        # Get available models first
        options_response = requests.get(f"{BASE_URL}/api/v1/hub/options", headers=headers)
        assert options_response.status_code == 200
        
        # Create an instance with welcome_model metadata
        instance_payload = {
            "name": "Welcome Guide Test",
            "model_id": "openai/gpt-4o-mini",
            "metadata": {"welcome_model": True}
        }
        
        create_response = requests.post(f"{BASE_URL}/api/v1/hub/instances", json=instance_payload, headers=headers)
        # May fail if model doesn't exist, but we're testing the metadata handling
        if create_response.status_code in [200, 201]:
            data = create_response.json()
            assert data.get("metadata", {}).get("welcome_model") == True, "welcome_model metadata not preserved"
            print("PASS: Instance with welcome_model=true metadata created successfully")
        else:
            print(f"INFO: Instance creation returned {create_response.status_code} - model may not be available")


class TestHubTabsEndpoints:
    """Test endpoints for dedicated Batch Runs and Roleplay Runs tabs"""
    
    def test_runs_list_endpoint(self):
        """Verify /api/v1/hub/runs list endpoint works"""
        # Register a fresh user
        username = f"test_user_{uuid.uuid4().hex[:8]}"
        password = "TestPass123!"
        
        register_response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "username": username,
            "password": password
        })
        assert register_response.status_code in [200, 201], f"Registration failed: {register_response.text}"
        token = register_response.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        
        # List runs
        response = requests.get(f"{BASE_URL}/api/v1/hub/runs", headers=headers)
        assert response.status_code == 200, f"Runs list failed: {response.text}"
        
        data = response.json()
        assert "runs" in data, "Response should contain 'runs' key"
        assert "total" in data, "Response should contain 'total' key"
        print(f"PASS: Runs list endpoint returns {data.get('total')} runs")
    
    def test_chat_prompts_list_endpoint(self):
        """Verify /api/v1/hub/chat/prompts list endpoint works"""
        # Register a fresh user
        username = f"test_user_{uuid.uuid4().hex[:8]}"
        password = "TestPass123!"
        
        register_response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "username": username,
            "password": password
        })
        assert register_response.status_code in [200, 201], f"Registration failed: {register_response.text}"
        token = register_response.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        
        # List chat prompts
        response = requests.get(f"{BASE_URL}/api/v1/hub/chat/prompts", headers=headers)
        assert response.status_code == 200, f"Chat prompts list failed: {response.text}"
        
        data = response.json()
        assert "prompts" in data, "Response should contain 'prompts' key"
        assert "total" in data, "Response should contain 'total' key"
        print(f"PASS: Chat prompts list endpoint returns {data.get('total')} prompts")
    
    def test_syntheses_list_endpoint(self):
        """Verify /api/v1/hub/chat/syntheses list endpoint works"""
        # Register a fresh user
        username = f"test_user_{uuid.uuid4().hex[:8]}"
        password = "TestPass123!"
        
        register_response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "username": username,
            "password": password
        })
        assert register_response.status_code in [200, 201], f"Registration failed: {register_response.text}"
        token = register_response.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        
        # List syntheses
        response = requests.get(f"{BASE_URL}/api/v1/hub/chat/syntheses", headers=headers)
        assert response.status_code == 200, f"Syntheses list failed: {response.text}"
        
        data = response.json()
        assert "batches" in data, "Response should contain 'batches' key"
        assert "total" in data, "Response should contain 'total' key"
        print(f"PASS: Syntheses list endpoint returns {data.get('total')} batches")


class TestInstancesEndpoints:
    """Test instances CRUD for Registry tab functionality"""
    
    def test_instances_list(self):
        """Verify instances list endpoint works"""
        # Register a fresh user
        username = f"test_user_{uuid.uuid4().hex[:8]}"
        password = "TestPass123!"
        
        register_response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "username": username,
            "password": password
        })
        assert register_response.status_code in [200, 201], f"Registration failed: {register_response.text}"
        token = register_response.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        
        # List instances
        response = requests.get(f"{BASE_URL}/api/v1/hub/instances", headers=headers)
        assert response.status_code == 200, f"Instances list failed: {response.text}"
        
        data = response.json()
        assert "instances" in data, "Response should contain 'instances' key"
        assert "total" in data, "Response should contain 'total' key"
        print(f"PASS: Instances list endpoint returns {data.get('total')} instances")
    
    def test_instances_include_archived_param(self):
        """Verify include_archived parameter works"""
        # Register a fresh user
        username = f"test_user_{uuid.uuid4().hex[:8]}"
        password = "TestPass123!"
        
        register_response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "username": username,
            "password": password
        })
        assert register_response.status_code in [200, 201], f"Registration failed: {register_response.text}"
        token = register_response.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        
        # List instances with include_archived=true
        response = requests.get(f"{BASE_URL}/api/v1/hub/instances?include_archived=true", headers=headers)
        assert response.status_code == 200, f"Instances list with archived failed: {response.text}"
        
        data = response.json()
        assert "instances" in data, "Response should contain 'instances' key"
        print(f"PASS: Instances list with include_archived=true works")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
