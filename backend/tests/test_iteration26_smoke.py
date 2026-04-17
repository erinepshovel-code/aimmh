"""
Iteration 26: Smoke tests after large code-splitting refactor
Tests: /api/health, /api/ready, /api/v1/hub/options, /api/v1/hub/instances
"""
import os
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestHealthEndpoints:
    """Health and readiness endpoint tests"""
    
    def test_api_health_returns_200(self):
        """Test /api/health returns 200 with status ok"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "ok"
        assert "build" in data
        print(f"PASS: /api/health returns 200 with status=ok, build={data.get('build')}")
    
    def test_api_ready_returns_200(self):
        """Test /api/ready returns 200 with status ready"""
        response = requests.get(f"{BASE_URL}/api/ready")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "ready"
        assert "checks" in data
        assert data["checks"]["mongo"]["ok"] is True
        print(f"PASS: /api/ready returns 200 with status=ready, mongo=ok")


class TestHubEndpointsAuth:
    """Hub endpoints require authentication - verify 401 for unauthenticated requests"""
    
    def test_hub_options_requires_auth(self):
        """Test /api/v1/hub/options returns 401 for unauthenticated requests"""
        response = requests.get(f"{BASE_URL}/api/v1/hub/options")
        # Should return 401 Not authenticated
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
        print(f"PASS: /api/v1/hub/options returns 401 for unauthenticated request")
    
    def test_hub_instances_requires_auth(self):
        """Test /api/v1/hub/instances returns 401 for unauthenticated requests"""
        response = requests.get(f"{BASE_URL}/api/v1/hub/instances")
        # Should return 401 Not authenticated
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
        print(f"PASS: /api/v1/hub/instances returns 401 for unauthenticated request")


class TestHubEndpointsWithAuth:
    """Hub endpoints with authentication - register fresh user and test"""
    
    @pytest.fixture(scope="class")
    def auth_session(self):
        """Create authenticated session with fresh user"""
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        
        # Register a fresh test user (uses username field, not email)
        import time
        test_username = f"smoke_test_{int(time.time())}"
        test_password = "TestPass123!"
        
        register_response = session.post(
            f"{BASE_URL}/api/auth/register",
            json={"username": test_username, "password": test_password}
        )
        
        if register_response.status_code not in [200, 201]:
            # Try login if user already exists
            login_response = session.post(
                f"{BASE_URL}/api/auth/login",
                json={"username": test_username, "password": test_password}
            )
            if login_response.status_code not in [200, 201]:
                pytest.skip(f"Could not authenticate: register={register_response.status_code}, login={login_response.status_code if 'login_response' in dir() else 'N/A'}")
        
        return session
    
    def test_hub_options_with_auth(self, auth_session):
        """Test /api/v1/hub/options returns 200 with authenticated session"""
        response = auth_session.get(f"{BASE_URL}/api/v1/hub/options")
        assert response.status_code == 200
        data = response.json()
        assert "fastapi_connections" in data
        assert "patterns" in data
        assert "supports" in data
        print(f"PASS: /api/v1/hub/options returns 200 with auth, patterns={data.get('patterns')}")
    
    def test_hub_instances_with_auth(self, auth_session):
        """Test /api/v1/hub/instances returns 200 with authenticated session"""
        response = auth_session.get(f"{BASE_URL}/api/v1/hub/instances")
        assert response.status_code == 200
        data = response.json()
        assert "instances" in data
        assert "total" in data
        print(f"PASS: /api/v1/hub/instances returns 200 with auth, total={data.get('total')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
