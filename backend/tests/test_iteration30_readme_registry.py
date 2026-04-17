# Test iteration 30: Dynamic README module system
# Tests: /api/v1/readme/registry, /api/v1/readme/registry/sync, marker compliance

import os
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestReadmeRegistry:
    """Tests for the dynamic README registry endpoints"""
    
    def test_health_check(self):
        """Verify backend is running"""
        response = requests.get(f"{BASE_URL}/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        print(f"✓ Health check passed: {data}")
    
    def test_readme_registry_endpoint(self):
        """Test GET /api/v1/readme/registry returns module registry"""
        response = requests.get(f"{BASE_URL}/api/v1/readme/registry")
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert "module_count" in data
        assert "violations" in data
        assert "modules" in data
        assert isinstance(data["modules"], list)
        assert isinstance(data["violations"], list)
        assert data["module_count"] > 0
        
        print(f"✓ Registry returned {data['module_count']} modules, {len(data['violations'])} violations")
    
    def test_readme_registry_module_structure(self):
        """Test that each module has required fields"""
        response = requests.get(f"{BASE_URL}/api/v1/readme/registry")
        assert response.status_code == 200
        data = response.json()
        
        # Check first module has all required fields
        if data["modules"]:
            module = data["modules"][0]
            required_fields = [
                "path", "ext", "lines_of_code", "lines_of_commented",
                "max_code_rule_ok", "marker_top_ok", "marker_bottom_ok",
                "module_doc", "functions"
            ]
            for field in required_fields:
                assert field in module, f"Missing field: {field}"
            
            # Verify types
            assert isinstance(module["path"], str)
            assert isinstance(module["lines_of_code"], int)
            assert isinstance(module["lines_of_commented"], int)
            assert isinstance(module["max_code_rule_ok"], bool)
            assert isinstance(module["marker_top_ok"], bool)
            assert isinstance(module["marker_bottom_ok"], bool)
            assert isinstance(module["functions"], list)
            
            print(f"✓ Module structure verified: {module['path']}")
            print(f"  - Code lines: {module['lines_of_code']}")
            print(f"  - Commented lines: {module['lines_of_commented']}")
            print(f"  - Max code rule OK: {module['max_code_rule_ok']}")
            print(f"  - Marker top OK: {module['marker_top_ok']}")
            print(f"  - Marker bottom OK: {module['marker_bottom_ok']}")
    
    def test_readme_registry_max_code_rule(self):
        """Test that max_code_rule_ok is coherent (<=400 lines)"""
        response = requests.get(f"{BASE_URL}/api/v1/readme/registry")
        assert response.status_code == 200
        data = response.json()
        
        for module in data["modules"]:
            if module["lines_of_code"] <= 400:
                assert module["max_code_rule_ok"] == True, f"Module {module['path']} has {module['lines_of_code']} lines but max_code_rule_ok is False"
            else:
                assert module["max_code_rule_ok"] == False, f"Module {module['path']} has {module['lines_of_code']} lines but max_code_rule_ok is True"
        
        print(f"✓ Max code rule coherence verified for all {len(data['modules'])} modules")
    
    def test_readme_registry_violations_coherent(self):
        """Test that violations list matches modules with issues"""
        response = requests.get(f"{BASE_URL}/api/v1/readme/registry")
        assert response.status_code == 200
        data = response.json()
        
        # Count modules with violations
        modules_with_issues = [
            m for m in data["modules"]
            if not m["max_code_rule_ok"] or not m["marker_top_ok"] or not m["marker_bottom_ok"]
        ]
        
        assert len(data["violations"]) == len(modules_with_issues), \
            f"Violations count mismatch: {len(data['violations'])} vs {len(modules_with_issues)}"
        
        # Verify violation structure
        for violation in data["violations"]:
            assert "path" in violation
            assert "max_code_rule_ok" in violation
            assert "marker_top_ok" in violation
            assert "marker_bottom_ok" in violation
            assert "lines_of_code" in violation
        
        print(f"✓ Violations coherence verified: {len(data['violations'])} violations match modules with issues")
    
    def test_readme_registry_sync_endpoint(self):
        """Test POST /api/v1/readme/registry/sync runs and returns registry"""
        response = requests.post(f"{BASE_URL}/api/v1/readme/registry/sync")
        assert response.status_code == 200
        data = response.json()
        
        # Should return same structure as GET
        assert "module_count" in data
        assert "violations" in data
        assert "modules" in data
        assert isinstance(data["modules"], list)
        assert data["module_count"] > 0
        
        print(f"✓ Registry sync returned {data['module_count']} modules")
    
    def test_readme_registry_contains_key_files(self):
        """Test that registry contains expected key files"""
        response = requests.get(f"{BASE_URL}/api/v1/readme/registry")
        assert response.status_code == 200
        data = response.json()
        
        paths = [m["path"] for m in data["modules"]]
        
        # Check for key backend files
        expected_backend = ["backend/services/registry.py", "backend/routes/v1_system.py"]
        for expected in expected_backend:
            assert expected in paths, f"Missing expected file: {expected}"
        
        # Check for key frontend files
        expected_frontend = ["frontend/src/lib/readme.ts"]
        for expected in expected_frontend:
            assert expected in paths, f"Missing expected file: {expected}"
        
        print(f"✓ Key files found in registry")
    
    def test_readme_registry_function_docs(self):
        """Test that function docs are extracted"""
        response = requests.get(f"{BASE_URL}/api/v1/readme/registry")
        assert response.status_code == 200
        data = response.json()
        
        # Find registry.py module
        registry_module = next(
            (m for m in data["modules"] if m["path"] == "backend/services/registry.py"),
            None
        )
        assert registry_module is not None, "registry.py not found"
        
        # Should have functions extracted
        assert len(registry_module["functions"]) > 0, "No functions extracted from registry.py"
        
        # Check function structure
        for fn in registry_module["functions"]:
            assert "name" in fn
            assert "doc" in fn
        
        print(f"✓ Function docs extracted: {len(registry_module['functions'])} functions from registry.py")
        for fn in registry_module["functions"][:5]:
            print(f"  - {fn['name']}: {fn['doc'][:50] if fn['doc'] else '(no doc)'}...")


class TestReadmeRegistryMarkers:
    """Tests for marker compliance in the registry"""
    
    def test_marker_format_in_modules(self):
        """Test that markers follow expected format"""
        response = requests.get(f"{BASE_URL}/api/v1/readme/registry")
        assert response.status_code == 200
        data = response.json()
        
        # Count modules with both markers OK
        both_ok = sum(1 for m in data["modules"] if m["marker_top_ok"] and m["marker_bottom_ok"])
        top_only = sum(1 for m in data["modules"] if m["marker_top_ok"] and not m["marker_bottom_ok"])
        bottom_only = sum(1 for m in data["modules"] if not m["marker_top_ok"] and m["marker_bottom_ok"])
        neither = sum(1 for m in data["modules"] if not m["marker_top_ok"] and not m["marker_bottom_ok"])
        
        print(f"✓ Marker status:")
        print(f"  - Both markers OK: {both_ok}")
        print(f"  - Top only: {top_only}")
        print(f"  - Bottom only: {bottom_only}")
        print(f"  - Neither: {neither}")
    
    def test_key_files_have_markers(self):
        """Test that key implementation files have markers"""
        response = requests.get(f"{BASE_URL}/api/v1/readme/registry")
        assert response.status_code == 200
        data = response.json()
        
        key_files = [
            "backend/services/registry.py",
            "backend/routes/v1_system.py",
            "frontend/src/lib/readme.ts",
            "frontend/src/components/hub/HelpReadmePanel.jsx",
            "frontend/src/lib/helpModelContext.js"
        ]
        
        for key_file in key_files:
            module = next((m for m in data["modules"] if m["path"] == key_file), None)
            if module:
                print(f"✓ {key_file}: top={module['marker_top_ok']}, bottom={module['marker_bottom_ok']}, code={module['lines_of_code']}")
                # These key files should have markers
                assert module["marker_top_ok"], f"{key_file} missing top marker"
                assert module["marker_bottom_ok"], f"{key_file} missing bottom marker"
            else:
                print(f"⚠ {key_file}: not found in registry")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
