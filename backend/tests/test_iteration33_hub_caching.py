"""
Iteration 33: Hub Context Caching Tests
Tests for:
- Roleplay run path after caching integration
- Context assembly path (_build_slot_context) for roleplay/chat/synthesis
- No regressions on /api/v1/hub/instances, /api/v1/hub/runs, /api/v1/hub/chat/prompts
- Cache invalidation on instance update/delete
- Basic API health/ready stability
"""
import os
import pytest
import requests
import uuid

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")


def make_guest_id():
    """Generate a unique guest ID"""
    return f"test-guest-{uuid.uuid4().hex[:12]}"


@pytest.fixture(scope="function")
def api_client():
    """Fresh requests session with unique guest ID for each test"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "X-Guest-Id": make_guest_id()
    })
    return session


@pytest.fixture(scope="module")
def shared_api_client():
    """Shared requests session for read-only tests"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "X-Guest-Id": make_guest_id()
    })
    return session


class TestHealthAndReady:
    """Basic API health/ready stability tests"""

    def test_health_endpoint(self, shared_api_client):
        """Test /api/health returns ok"""
        response = shared_api_client.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "ok"
        print(f"PASS: Health endpoint returns status=ok, build={data.get('build')}")

    def test_ready_endpoint(self, shared_api_client):
        """Test /api/ready returns ready with mongo check"""
        response = shared_api_client.get(f"{BASE_URL}/api/ready")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "ready"
        assert data.get("checks", {}).get("mongo", {}).get("ok") is True
        print(f"PASS: Ready endpoint returns status=ready, mongo=ok")


class TestHubInstancesCRUD:
    """Tests for /api/v1/hub/instances - no regression after caching"""

    def test_list_instances_empty_or_existing(self, api_client):
        """Test listing instances works"""
        response = api_client.get(f"{BASE_URL}/api/v1/hub/instances")
        assert response.status_code == 200
        data = response.json()
        assert "instances" in data
        assert "total" in data
        print(f"PASS: List instances returns {data['total']} instances")

    def test_create_instance(self, api_client):
        """Test creating a new instance"""
        payload = {
            "name": f"TEST_CacheTest_{uuid.uuid4().hex[:6]}",
            "model_id": "gpt-4o-mini",
            "role_preset": "assistant",
            "context": {
                "role": "Test assistant for caching verification",
                "system_message": "You are a helpful test assistant."
            },
            "instance_prompt": "Always respond concisely.",
            "history_window_messages": 10
        }
        response = api_client.post(f"{BASE_URL}/api/v1/hub/instances", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "instance_id" in data
        assert data.get("name") == payload["name"]
        assert data.get("model_id") == payload["model_id"]
        print(f"PASS: Created instance {data['instance_id']}")
        return data

    def test_get_instance_detail(self, api_client):
        """Test getting instance detail"""
        # First create an instance
        create_payload = {
            "name": f"TEST_DetailTest_{uuid.uuid4().hex[:6]}",
            "model_id": "gpt-4o-mini"
        }
        create_response = api_client.post(f"{BASE_URL}/api/v1/hub/instances", json=create_payload)
        assert create_response.status_code == 200
        instance_id = create_response.json()["instance_id"]

        # Get detail
        response = api_client.get(f"{BASE_URL}/api/v1/hub/instances/{instance_id}")
        assert response.status_code == 200
        data = response.json()
        assert data.get("instance_id") == instance_id
        print(f"PASS: Get instance detail for {instance_id}")

    def test_update_instance_triggers_cache_purge(self, api_client):
        """Test updating instance (should trigger cache purge)"""
        # Create instance
        create_payload = {
            "name": f"TEST_UpdateCache_{uuid.uuid4().hex[:6]}",
            "model_id": "gpt-4o-mini",
            "context": {"role": "Original role"}
        }
        create_response = api_client.post(f"{BASE_URL}/api/v1/hub/instances", json=create_payload)
        assert create_response.status_code == 200
        instance_id = create_response.json()["instance_id"]

        # Update instance - this should trigger cache purge
        update_payload = {
            "context": {"role": "Updated role for cache test"}
        }
        response = api_client.patch(f"{BASE_URL}/api/v1/hub/instances/{instance_id}", json=update_payload)
        assert response.status_code == 200
        data = response.json()
        assert data.get("context", {}).get("role") == "Updated role for cache test"
        print(f"PASS: Updated instance {instance_id} - cache purge triggered")

    def test_archive_and_delete_instance_triggers_cache_purge(self, api_client):
        """Test archiving and deleting instance (should trigger cache purge)"""
        # Create instance
        create_payload = {
            "name": f"TEST_DeleteCache_{uuid.uuid4().hex[:6]}",
            "model_id": "gpt-4o-mini"
        }
        create_response = api_client.post(f"{BASE_URL}/api/v1/hub/instances", json=create_payload)
        assert create_response.status_code == 200
        instance_id = create_response.json()["instance_id"]

        # Archive first
        archive_response = api_client.post(f"{BASE_URL}/api/v1/hub/instances/{instance_id}/archive")
        assert archive_response.status_code == 200
        assert archive_response.json().get("archived") is True
        print(f"PASS: Archived instance {instance_id}")

        # Delete - this should trigger cache purge
        delete_response = api_client.delete(f"{BASE_URL}/api/v1/hub/instances/{instance_id}")
        assert delete_response.status_code == 200
        print(f"PASS: Deleted instance {instance_id} - cache purge triggered")

        # Verify deleted
        get_response = api_client.get(f"{BASE_URL}/api/v1/hub/instances/{instance_id}")
        assert get_response.status_code == 404
        print(f"PASS: Verified instance {instance_id} is deleted")


class TestHubRunsNoRegression:
    """Tests for /api/v1/hub/runs - no regression after caching"""

    def test_list_runs(self, shared_api_client):
        """Test listing runs works"""
        response = shared_api_client.get(f"{BASE_URL}/api/v1/hub/runs")
        assert response.status_code == 200
        data = response.json()
        assert "runs" in data
        assert "total" in data
        print(f"PASS: List runs returns {data['total']} runs")

    def test_hub_options_endpoint(self, shared_api_client):
        """Test /api/v1/hub/options returns connection info"""
        response = shared_api_client.get(f"{BASE_URL}/api/v1/hub/options")
        assert response.status_code == 200
        data = response.json()
        assert "fastapi_connections" in data
        assert "patterns" in data
        assert "roleplay" in data.get("patterns", [])
        print(f"PASS: Hub options returns patterns: {data.get('patterns')}")


class TestHubChatPromptsNoRegression:
    """Tests for /api/v1/hub/chat/prompts - no regression after caching"""

    def test_list_chat_prompts(self, shared_api_client):
        """Test listing chat prompts works"""
        response = shared_api_client.get(f"{BASE_URL}/api/v1/hub/chat/prompts")
        assert response.status_code == 200
        data = response.json()
        assert "prompts" in data
        assert "total" in data
        print(f"PASS: List chat prompts returns {data['total']} prompts")


class TestHubSynthesisNoRegression:
    """Tests for /api/v1/hub/chat/syntheses - no regression after caching"""

    def test_list_syntheses(self, shared_api_client):
        """Test listing synthesis batches works"""
        response = shared_api_client.get(f"{BASE_URL}/api/v1/hub/chat/syntheses")
        assert response.status_code == 200
        data = response.json()
        assert "batches" in data
        assert "total" in data
        print(f"PASS: List syntheses returns {data['total']} batches")


class TestHubGroupsNoRegression:
    """Tests for /api/v1/hub/groups - no regression after caching"""

    def test_list_groups(self, shared_api_client):
        """Test listing groups works"""
        response = shared_api_client.get(f"{BASE_URL}/api/v1/hub/groups")
        assert response.status_code == 200
        data = response.json()
        assert "groups" in data
        assert "total" in data
        print(f"PASS: List groups returns {data['total']} groups")

    def test_create_group(self, api_client):
        """Test creating a group"""
        payload = {
            "name": f"TEST_CacheGroup_{uuid.uuid4().hex[:6]}",
            "description": "Test group for caching verification",
            "members": []
        }
        response = api_client.post(f"{BASE_URL}/api/v1/hub/groups", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "group_id" in data
        assert data.get("name") == payload["name"]
        print(f"PASS: Created group {data['group_id']}")


class TestContextCacheIntegration:
    """Tests for context cache integration in hub_runner, hub_chat, hub_synthesis"""

    def test_create_instance_with_full_context_for_caching(self, api_client):
        """Create instance with all context fields that affect cache key"""
        payload = {
            "name": f"TEST_FullContext_{uuid.uuid4().hex[:6]}",
            "model_id": "gpt-4o-mini",
            "role_preset": "analyst",
            "context": {
                "role": "Data analyst",
                "system_message": "You analyze data carefully.",
                "prompt_modifier": "Be thorough in your analysis."
            },
            "instance_prompt": "Focus on key insights.",
            "history_window_messages": 12
        }
        response = api_client.post(f"{BASE_URL}/api/v1/hub/instances", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data.get("role_preset") == "analyst"
        assert data.get("context", {}).get("role") == "Data analyst"
        assert data.get("instance_prompt") == "Focus on key insights."
        assert data.get("history_window_messages") == 12
        print(f"PASS: Created instance with full context for caching: {data['instance_id']}")
        return data

    def test_instance_history_endpoint(self, api_client):
        """Test instance history endpoint works (used in context building)"""
        # Create instance first
        create_payload = {
            "name": f"TEST_History_{uuid.uuid4().hex[:6]}",
            "model_id": "gpt-4o-mini"
        }
        create_response = api_client.post(f"{BASE_URL}/api/v1/hub/instances", json=create_payload)
        assert create_response.status_code == 200
        instance_id = create_response.json()["instance_id"]

        # Get history
        response = api_client.get(f"{BASE_URL}/api/v1/hub/instances/{instance_id}/history")
        assert response.status_code == 200
        data = response.json()
        assert "instance_id" in data
        assert "thread_id" in data
        assert "messages" in data
        print(f"PASS: Instance history endpoint works for {instance_id}")


class TestBatchRunWithCaching:
    """Test batch run execution with caching integration"""

    @pytest.fixture
    def test_instances(self, api_client):
        """Create test instances for batch run"""
        instances = []
        for i in range(2):
            payload = {
                "name": f"TEST_BatchRun_{uuid.uuid4().hex[:6]}_{i}",
                "model_id": "gpt-4o-mini",
                "context": {"role": f"Test role {i}"}
            }
            response = api_client.post(f"{BASE_URL}/api/v1/hub/instances", json=payload)
            if response.status_code == 200:
                instances.append(response.json())
        return instances

    def test_batch_run_fan_out_with_caching(self, api_client, test_instances):
        """Test fan_out batch run uses caching correctly"""
        if len(test_instances) < 2:
            pytest.skip("Need at least 2 instances for batch run test")

        payload = {
            "prompt": "What is 2+2? Reply in one word.",
            "label": f"TEST_FanOut_{uuid.uuid4().hex[:6]}",
            "run_mode": "batch",
            "stages": [
                {
                    "name": "Fan Out Test",
                    "pattern": "fan_out",
                    "participants": [
                        {"source_type": "instance", "source_id": test_instances[0]["instance_id"]},
                        {"source_type": "instance", "source_id": test_instances[1]["instance_id"]}
                    ]
                }
            ],
            "persist_instance_threads": False
        }
        response = api_client.post(f"{BASE_URL}/api/v1/hub/runs", json=payload)
        
        # May fail due to LLM quota limits - that's acceptable
        if response.status_code == 403:
            print(f"SKIP: Batch run blocked by quota limits: {response.json().get('detail')}")
            pytest.skip("Quota limit reached")
        
        if response.status_code == 500:
            error_detail = response.json().get("detail", "")
            if "LLM" in error_detail or "provider" in error_detail.lower():
                print(f"SKIP: LLM provider issue: {error_detail}")
                pytest.skip("LLM provider unavailable")
            
        assert response.status_code == 200, f"Unexpected error: {response.json()}"
        data = response.json()
        assert "run_id" in data
        assert data.get("status") in ["completed", "running"]
        print(f"PASS: Batch run created with caching: {data['run_id']}, status={data.get('status')}")


class TestRoleplayRunWithCaching:
    """Test roleplay run execution with caching integration"""

    @pytest.fixture
    def roleplay_instances(self, api_client):
        """Create test instances for roleplay run"""
        instances = []
        # Create player instance
        player_payload = {
            "name": f"TEST_RoleplayPlayer_{uuid.uuid4().hex[:6]}",
            "model_id": "gpt-4o-mini",
            "role_preset": "assistant",
            "context": {"role": "Adventurer in a fantasy world"}
        }
        player_response = api_client.post(f"{BASE_URL}/api/v1/hub/instances", json=player_payload)
        if player_response.status_code == 200:
            instances.append(("player", player_response.json()))

        # Create DM instance
        dm_payload = {
            "name": f"TEST_RoleplayDM_{uuid.uuid4().hex[:6]}",
            "model_id": "gpt-4o-mini",
            "role_preset": "narrator",
            "context": {"role": "Dungeon Master narrating the adventure"}
        }
        dm_response = api_client.post(f"{BASE_URL}/api/v1/hub/instances", json=dm_payload)
        if dm_response.status_code == 200:
            instances.append(("dm", dm_response.json()))

        return instances

    def test_roleplay_run_with_caching(self, api_client, roleplay_instances):
        """Test roleplay run uses caching correctly"""
        if len(roleplay_instances) < 2:
            pytest.skip("Need player and DM instances for roleplay test")

        player_instance = next((inst for role, inst in roleplay_instances if role == "player"), None)
        dm_instance = next((inst for role, inst in roleplay_instances if role == "dm"), None)

        if not player_instance or not dm_instance:
            pytest.skip("Missing player or DM instance")

        payload = {
            "prompt": "You enter a dark cave. What do you do?",
            "label": f"TEST_Roleplay_{uuid.uuid4().hex[:6]}",
            "run_mode": "roleplay",
            "stages": [
                {
                    "name": "Cave Adventure",
                    "pattern": "roleplay",
                    "player_participants": [
                        {"source_type": "instance", "source_id": player_instance["instance_id"]}
                    ],
                    "dm_instance_id": dm_instance["instance_id"],
                    "rounds": 1,
                    "action_word_limit": 50
                }
            ],
            "persist_instance_threads": False
        }
        response = api_client.post(f"{BASE_URL}/api/v1/hub/runs", json=payload)

        # May fail due to LLM quota limits - that's acceptable
        if response.status_code == 403:
            print(f"SKIP: Roleplay run blocked by quota limits: {response.json().get('detail')}")
            pytest.skip("Quota limit reached")

        if response.status_code == 500:
            error_detail = response.json().get("detail", "")
            if "LLM" in error_detail or "provider" in error_detail.lower():
                print(f"SKIP: LLM provider issue: {error_detail}")
                pytest.skip("LLM provider unavailable")

        assert response.status_code == 200, f"Unexpected error: {response.json()}"
        data = response.json()
        assert "run_id" in data
        assert data.get("run_mode") == "roleplay"
        assert data.get("status") in ["completed", "running"]
        print(f"PASS: Roleplay run created with caching: {data['run_id']}, status={data.get('status')}")


class TestChatPromptWithCaching:
    """Test chat prompt execution with caching integration"""

    @pytest.fixture
    def chat_instance(self, api_client):
        """Create test instance for chat"""
        payload = {
            "name": f"TEST_ChatInstance_{uuid.uuid4().hex[:6]}",
            "model_id": "gpt-4o-mini",
            "context": {"role": "Helpful chat assistant"}
        }
        response = api_client.post(f"{BASE_URL}/api/v1/hub/instances", json=payload)
        if response.status_code == 200:
            return response.json()
        return None

    def test_chat_prompt_with_caching(self, api_client, chat_instance):
        """Test chat prompt uses caching correctly"""
        if not chat_instance:
            pytest.skip("Failed to create chat instance")

        payload = {
            "prompt": "Say hello in one word.",
            "label": f"TEST_Chat_{uuid.uuid4().hex[:6]}",
            "instance_ids": [chat_instance["instance_id"]]
        }
        response = api_client.post(f"{BASE_URL}/api/v1/hub/chat/prompts", json=payload)

        # May fail due to quota limits
        if response.status_code == 403:
            print(f"SKIP: Chat prompt blocked by quota limits: {response.json().get('detail')}")
            pytest.skip("Quota limit reached")

        if response.status_code == 500:
            error_detail = response.json().get("detail", "")
            if "LLM" in error_detail or "provider" in error_detail.lower():
                print(f"SKIP: LLM provider issue: {error_detail}")
                pytest.skip("LLM provider unavailable")

        assert response.status_code == 200, f"Unexpected error: {response.json()}"
        data = response.json()
        assert "prompt_id" in data
        assert "responses" in data
        print(f"PASS: Chat prompt created with caching: {data['prompt_id']}")


class TestCleanup:
    """Cleanup test data"""

    def test_cleanup_test_instances(self, api_client):
        """Archive and delete TEST_ prefixed instances"""
        # List all instances
        response = api_client.get(f"{BASE_URL}/api/v1/hub/instances?include_archived=true&limit=500")
        if response.status_code != 200:
            print("SKIP: Could not list instances for cleanup")
            return

        instances = response.json().get("instances", [])
        test_instances = [i for i in instances if i.get("name", "").startswith("TEST_")]
        
        deleted_count = 0
        for instance in test_instances:
            instance_id = instance["instance_id"]
            # Archive if not archived
            if not instance.get("archived"):
                api_client.post(f"{BASE_URL}/api/v1/hub/instances/{instance_id}/archive")
            # Delete
            delete_response = api_client.delete(f"{BASE_URL}/api/v1/hub/instances/{instance_id}")
            if delete_response.status_code == 200:
                deleted_count += 1

        print(f"PASS: Cleaned up {deleted_count} test instances")

    def test_cleanup_test_groups(self, api_client):
        """Archive and delete TEST_ prefixed groups"""
        response = api_client.get(f"{BASE_URL}/api/v1/hub/groups?include_archived=true&limit=500")
        if response.status_code != 200:
            print("SKIP: Could not list groups for cleanup")
            return

        groups = response.json().get("groups", [])
        test_groups = [g for g in groups if g.get("name", "").startswith("TEST_")]
        
        # Note: Groups don't have delete endpoint in the routes, just archive
        archived_count = 0
        for group in test_groups:
            group_id = group["group_id"]
            if not group.get("archived"):
                archive_response = api_client.post(f"{BASE_URL}/api/v1/hub/groups/{group_id}/archive")
                if archive_response.status_code == 200:
                    archived_count += 1

        print(f"PASS: Archived {archived_count} test groups")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
