"""
Iteration 31: WS-Tier and WS-Admin Feature Tests

Tests:
1. Auth/WS-tier: @interdependentway.org emails get ws-tier automatically
2. WS-admin access control: WS-tier can access /api/v1/ws-admin/*, non-WS gets 403
3. WS-admin APIs: billing tiers, pricing packages, endpoints, analytics, CLI
4. Dynamic registry backend: /api/v1/readme/registry and /api/v1/readme/registry/sync
5. Compliance rule pipeline: marker + <=400 code-line checker
"""

import pytest
import requests
import os
import uuid
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


# ============ HEALTH CHECK ============
class TestHealthCheck:
    """Basic health check to ensure backend is running"""
    
    def test_health_check(self, api_client):
        response = api_client.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "ok"
        print("✓ Health check passed")


# ============ WS-TIER REGISTRATION ============
class TestWsTierRegistration:
    """Test that @interdependentway.org emails get ws-tier automatically"""
    
    def test_register_wayseer_email_gets_ws_tier(self, api_client):
        """Register with @interdependentway.org email should get ws-tier"""
        unique_id = uuid.uuid4().hex[:8]
        username = f"TEST_ws_{unique_id}@interdependentway.org"
        password = "TestPass123!"
        
        response = api_client.post(f"{BASE_URL}/api/auth/register", json={
            "username": username,
            "password": password
        })
        
        assert response.status_code == 200, f"Registration failed: {response.text}"
        data = response.json()
        
        # Verify ws-tier is assigned
        assert "user" in data
        assert data["user"]["subscription_tier"] == "ws-tier", f"Expected ws-tier, got {data['user']['subscription_tier']}"
        assert data["user"]["hide_emergent_badge"] == True
        
        # Store token for later tests
        self.__class__.ws_token = data.get("access_token")
        self.__class__.ws_username = username
        print(f"✓ WS-tier user registered: {username}")
        return data
    
    def test_register_regular_email_gets_free_tier(self, api_client):
        """Register with regular email should get free tier"""
        unique_id = uuid.uuid4().hex[:8]
        username = f"TEST_regular_{unique_id}"
        password = "TestPass123!"
        
        response = api_client.post(f"{BASE_URL}/api/auth/register", json={
            "username": username,
            "password": password
        })
        
        assert response.status_code == 200, f"Registration failed: {response.text}"
        data = response.json()
        
        # Verify free tier is assigned
        assert "user" in data
        assert data["user"]["subscription_tier"] == "free", f"Expected free, got {data['user']['subscription_tier']}"
        
        # Store token for later tests
        self.__class__.regular_token = data.get("access_token")
        self.__class__.regular_username = username
        print(f"✓ Regular user registered: {username}")
        return data
    
    def test_login_wayseer_email_gets_ws_tier(self, api_client):
        """Login with @interdependentway.org email should return ws-tier"""
        if not hasattr(self.__class__, 'ws_username'):
            pytest.skip("WS user not registered")
        
        response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "username": self.__class__.ws_username,
            "password": "TestPass123!"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["user"]["subscription_tier"] == "ws-tier"
        print("✓ WS-tier login verified")


# ============ WS-ADMIN ACCESS CONTROL ============
class TestWsAdminAccessControl:
    """Test WS-Admin endpoint access control"""
    
    def test_ws_admin_billing_tiers_requires_ws_tier(self, api_client):
        """Non-WS user should get 403 on WS-Admin endpoints"""
        if not hasattr(TestWsTierRegistration, 'regular_token'):
            pytest.skip("Regular user not registered")
        
        headers = {"Authorization": f"Bearer {TestWsTierRegistration.regular_token}"}
        response = api_client.get(f"{BASE_URL}/api/v1/ws-admin/billing-tiers", headers=headers)
        
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("✓ Non-WS user correctly denied access to WS-Admin")
    
    def test_ws_admin_endpoints_requires_ws_tier(self, api_client):
        """Non-WS user should get 403 on endpoints list"""
        if not hasattr(TestWsTierRegistration, 'regular_token'):
            pytest.skip("Regular user not registered")
        
        headers = {"Authorization": f"Bearer {TestWsTierRegistration.regular_token}"}
        response = api_client.get(f"{BASE_URL}/api/v1/ws-admin/endpoints", headers=headers)
        
        assert response.status_code == 403
        print("✓ Non-WS user correctly denied access to endpoints list")
    
    def test_ws_admin_analytics_requires_ws_tier(self, api_client):
        """Non-WS user should get 403 on analytics"""
        if not hasattr(TestWsTierRegistration, 'regular_token'):
            pytest.skip("Regular user not registered")
        
        headers = {"Authorization": f"Bearer {TestWsTierRegistration.regular_token}"}
        response = api_client.get(f"{BASE_URL}/api/v1/ws-admin/analytics", headers=headers)
        
        assert response.status_code == 403
        print("✓ Non-WS user correctly denied access to analytics")
    
    def test_ws_admin_cli_requires_ws_tier(self, api_client):
        """Non-WS user should get 403 on CLI execute"""
        if not hasattr(TestWsTierRegistration, 'regular_token'):
            pytest.skip("Regular user not registered")
        
        headers = {"Authorization": f"Bearer {TestWsTierRegistration.regular_token}"}
        response = api_client.post(
            f"{BASE_URL}/api/v1/ws-admin/cli/execute",
            headers=headers,
            json={"command": "health_check"}
        )
        
        assert response.status_code == 403
        print("✓ Non-WS user correctly denied access to CLI")


# ============ WS-ADMIN API FUNCTIONALITY ============
class TestWsAdminApis:
    """Test WS-Admin API functionality for WS-tier users"""
    
    def test_ws_admin_get_billing_tiers(self, api_client):
        """WS-tier user can get billing tiers"""
        if not hasattr(TestWsTierRegistration, 'ws_token'):
            pytest.skip("WS user not registered")
        
        headers = {"Authorization": f"Bearer {TestWsTierRegistration.ws_token}"}
        response = api_client.get(f"{BASE_URL}/api/v1/ws-admin/billing-tiers", headers=headers)
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert "tiers" in data
        tiers = data["tiers"]
        assert "free" in tiers
        assert "supporter" in tiers
        assert "pro" in tiers
        assert "team" in tiers
        assert "ws-tier" in tiers
        
        # Verify ws-tier has unlimited access
        ws_tier = tiers["ws-tier"]
        assert ws_tier.get("max_instances") is None  # unlimited
        assert ws_tier.get("queue_priority") == "highest"
        print("✓ WS-Admin billing tiers retrieved successfully")
    
    def test_ws_admin_update_billing_tier(self, api_client):
        """WS-tier user can update billing tier limits"""
        if not hasattr(TestWsTierRegistration, 'ws_token'):
            pytest.skip("WS user not registered")
        
        headers = {"Authorization": f"Bearer {TestWsTierRegistration.ws_token}"}
        
        # Update free tier max_batch_size
        response = api_client.put(
            f"{BASE_URL}/api/v1/ws-admin/billing-tiers/free",
            headers=headers,
            json={"updates": {"max_batch_size": 25}}
        )
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert data.get("ok") == True
        assert data.get("tier") == "free"
        assert data["limits"]["max_batch_size"] == 25
        print("✓ WS-Admin billing tier updated successfully")
    
    def test_ws_admin_get_pricing_packages(self, api_client):
        """WS-tier user can get pricing packages"""
        if not hasattr(TestWsTierRegistration, 'ws_token'):
            pytest.skip("WS user not registered")
        
        headers = {"Authorization": f"Bearer {TestWsTierRegistration.ws_token}"}
        response = api_client.get(f"{BASE_URL}/api/v1/ws-admin/pricing-packages", headers=headers)
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "packages" in data
        print(f"✓ WS-Admin pricing packages retrieved: {len(data['packages'])} packages")
    
    def test_ws_admin_get_endpoints(self, api_client):
        """WS-tier user can get endpoints list"""
        if not hasattr(TestWsTierRegistration, 'ws_token'):
            pytest.skip("WS user not registered")
        
        headers = {"Authorization": f"Bearer {TestWsTierRegistration.ws_token}"}
        response = api_client.get(f"{BASE_URL}/api/v1/ws-admin/endpoints", headers=headers)
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert "endpoints" in data
        endpoints = data["endpoints"]
        assert len(endpoints) > 0
        
        # Verify endpoint structure
        sample = endpoints[0]
        assert "path" in sample
        assert "methods" in sample
        assert "name" in sample
        
        # Verify ws-admin endpoints are listed
        ws_admin_paths = [e["path"] for e in endpoints if "/ws-admin/" in e["path"]]
        assert len(ws_admin_paths) > 0, "WS-Admin endpoints should be listed"
        print(f"✓ WS-Admin endpoints retrieved: {len(endpoints)} endpoints")
    
    def test_ws_admin_get_analytics(self, api_client):
        """WS-tier user can get analytics"""
        if not hasattr(TestWsTierRegistration, 'ws_token'):
            pytest.skip("WS user not registered")
        
        headers = {"Authorization": f"Bearer {TestWsTierRegistration.ws_token}"}
        response = api_client.get(f"{BASE_URL}/api/v1/ws-admin/analytics", headers=headers)
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Verify analytics fields
        assert "users_total" in data
        assert "instances_total" in data
        assert "groups_total" in data
        assert "runs_total" in data
        assert "chat_prompts_total" in data
        assert "synthesis_batches_total" in data
        assert "payments_total" in data
        print(f"✓ WS-Admin analytics retrieved: {data['users_total']} users, {data['instances_total']} instances")
    
    def test_ws_admin_cli_health_check(self, api_client):
        """WS-tier user can execute CLI health_check"""
        if not hasattr(TestWsTierRegistration, 'ws_token'):
            pytest.skip("WS user not registered")
        
        headers = {"Authorization": f"Bearer {TestWsTierRegistration.ws_token}"}
        response = api_client.post(
            f"{BASE_URL}/api/v1/ws-admin/cli/execute",
            headers=headers,
            json={"command": "health_check"}
        )
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert data.get("command") == "health_check"
        assert "exit_code" in data
        print("✓ WS-Admin CLI health_check executed")
    
    def test_ws_admin_cli_line_rules(self, api_client):
        """WS-tier user can execute CLI line_rules"""
        if not hasattr(TestWsTierRegistration, 'ws_token'):
            pytest.skip("WS user not registered")
        
        headers = {"Authorization": f"Bearer {TestWsTierRegistration.ws_token}"}
        response = api_client.post(
            f"{BASE_URL}/api/v1/ws-admin/cli/execute",
            headers=headers,
            json={"command": "line_rules"}
        )
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert data.get("command") == "line_rules"
        print("✓ WS-Admin CLI line_rules executed")
    
    def test_ws_admin_cli_sync_readme_registry(self, api_client):
        """WS-tier user can execute CLI sync_readme_registry"""
        if not hasattr(TestWsTierRegistration, 'ws_token'):
            pytest.skip("WS user not registered")
        
        headers = {"Authorization": f"Bearer {TestWsTierRegistration.ws_token}"}
        response = api_client.post(
            f"{BASE_URL}/api/v1/ws-admin/cli/execute",
            headers=headers,
            json={"command": "sync_readme_registry"}
        )
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert data.get("command") == "sync_readme_registry"
        assert "result" in data
        assert "module_count" in data["result"]
        print(f"✓ WS-Admin CLI sync_readme_registry executed: {data['result']['module_count']} modules")
    
    def test_ws_admin_cli_unsupported_command(self, api_client):
        """Unsupported CLI command should return 400"""
        if not hasattr(TestWsTierRegistration, 'ws_token'):
            pytest.skip("WS user not registered")
        
        headers = {"Authorization": f"Bearer {TestWsTierRegistration.ws_token}"}
        response = api_client.post(
            f"{BASE_URL}/api/v1/ws-admin/cli/execute",
            headers=headers,
            json={"command": "rm -rf /"}
        )
        
        assert response.status_code == 400
        print("✓ Unsupported CLI command correctly rejected")


# ============ DYNAMIC README REGISTRY ============
class TestDynamicReadmeRegistry:
    """Test dynamic README registry endpoints"""
    
    def test_readme_registry_endpoint(self, api_client):
        """GET /api/v1/readme/registry returns valid payload"""
        # This endpoint should be public (no auth required)
        response = api_client.get(f"{BASE_URL}/api/v1/readme/registry")
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert "module_count" in data
        assert "violations" in data
        assert "modules" in data
        assert data["module_count"] > 0
        print(f"✓ README registry: {data['module_count']} modules")
    
    def test_readme_registry_module_structure(self, api_client):
        """Verify module structure in registry"""
        response = api_client.get(f"{BASE_URL}/api/v1/readme/registry")
        assert response.status_code == 200
        data = response.json()
        
        modules = data.get("modules", [])
        assert len(modules) > 0
        
        sample = modules[0]
        assert "path" in sample
        assert "ext" in sample
        assert "lines_of_code" in sample
        assert "lines_of_commented" in sample
        assert "max_code_rule_ok" in sample
        assert "marker_top_ok" in sample
        assert "marker_bottom_ok" in sample
        assert "module_doc" in sample
        assert "functions" in sample
        print("✓ README registry module structure verified")
    
    def test_readme_registry_sync_endpoint(self, api_client):
        """POST /api/v1/readme/registry/sync returns refreshed registry"""
        response = api_client.post(f"{BASE_URL}/api/v1/readme/registry/sync")
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert "module_count" in data
        assert "violations" in data
        assert "modules" in data
        print(f"✓ README registry sync: {data['module_count']} modules, {len(data['violations'])} violations")
    
    def test_readme_registry_max_code_rule(self, api_client):
        """Verify max_code_rule_ok is coherent (<=400 lines)"""
        response = api_client.get(f"{BASE_URL}/api/v1/readme/registry")
        assert response.status_code == 200
        data = response.json()
        
        for module in data.get("modules", []):
            lines = module.get("lines_of_code", 0)
            rule_ok = module.get("max_code_rule_ok", False)
            
            if lines <= 400:
                assert rule_ok == True, f"{module['path']}: {lines} lines should be ok"
            else:
                assert rule_ok == False, f"{module['path']}: {lines} lines should not be ok"
        
        print("✓ README registry max_code_rule coherence verified")
    
    def test_readme_registry_violations_coherent(self, api_client):
        """Verify violations list matches modules with issues"""
        response = api_client.get(f"{BASE_URL}/api/v1/readme/registry")
        assert response.status_code == 200
        data = response.json()
        
        violations = data.get("violations", [])
        modules = data.get("modules", [])
        
        # Count modules with issues
        modules_with_issues = [
            m for m in modules
            if not m.get("max_code_rule_ok") or not m.get("marker_top_ok") or not m.get("marker_bottom_ok")
        ]
        
        assert len(violations) == len(modules_with_issues), \
            f"Violations count ({len(violations)}) should match modules with issues ({len(modules_with_issues)})"
        print(f"✓ README registry violations coherent: {len(violations)} violations")
    
    def test_readme_registry_contains_key_files(self, api_client):
        """Verify registry contains key backend/frontend files"""
        response = api_client.get(f"{BASE_URL}/api/v1/readme/registry")
        assert response.status_code == 200
        data = response.json()
        
        paths = [m["path"] for m in data.get("modules", [])]
        
        # Check for key files
        key_files = [
            "backend/server.py",
            "backend/services/auth.py",
            "backend/services/billing_tiers.py",
            "backend/routes/ws_admin.py",
            "backend/services/registry.py",
        ]
        
        for key_file in key_files:
            assert any(key_file in p for p in paths), f"Key file {key_file} not found in registry"
        
        print("✓ README registry contains key files")


# ============ CLEANUP ============
class TestCleanup:
    """Cleanup test data"""
    
    def test_cleanup_test_users(self, api_client):
        """Note: Test users with TEST_ prefix should be cleaned up"""
        # In a real scenario, we'd delete test users here
        # For now, just note that cleanup should happen
        print("✓ Test cleanup noted (TEST_ prefixed users created)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
