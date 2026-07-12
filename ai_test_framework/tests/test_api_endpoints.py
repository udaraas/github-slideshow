"""Integration-style tests for the FastAPI REST endpoints (httpx TestClient)."""
import unittest

try:
    from fastapi.testclient import TestClient
    _FASTAPI_AVAILABLE = True
except ImportError:
    _FASTAPI_AVAILABLE = False


@unittest.skipUnless(_FASTAPI_AVAILABLE, "fastapi not installed")
class TestHealthEndpoint(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from nextgen_test_automation.api.main import app
        cls.client = TestClient(app)

    def test_health_returns_ok(self):
        r = self.client.get("/health")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "ok")


@unittest.skipUnless(_FASTAPI_AVAILABLE, "fastapi not installed")
class TestSuitesEndpoints(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Import a fresh app instance for isolation
        import importlib
        import nextgen_test_automation.api.main as mod
        importlib.reload(mod)
        from nextgen_test_automation.api.main import app
        cls.client = TestClient(app)

    def _create_suite(self, name: str = "E2E Suite", description: str = "") -> dict:
        r = self.client.post("/suites", json={"name": name, "description": description})
        self.assertEqual(r.status_code, 201)
        return r.json()

    def test_list_suites_empty_initially(self):
        r = self.client.get("/suites")
        self.assertEqual(r.status_code, 200)
        self.assertIsInstance(r.json(), list)

    def test_create_suite_returns_201(self):
        data = self._create_suite("My Suite")
        self.assertIn("id", data)
        self.assertEqual(data["name"], "My Suite")

    def test_create_suite_missing_name_returns_400(self):
        r = self.client.post("/suites", json={"description": "no name"})
        self.assertEqual(r.status_code, 400)

    def test_get_suite_by_id(self):
        data = self._create_suite("Get Test")
        r = self.client.get(f"/suites/{data['id']}")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["id"], data["id"])

    def test_get_suite_not_found(self):
        r = self.client.get("/suites/nonexistent-id")
        self.assertEqual(r.status_code, 404)

    def test_delete_suite(self):
        data = self._create_suite("Delete Me")
        r = self.client.delete(f"/suites/{data['id']}")
        self.assertEqual(r.status_code, 204)
        r2 = self.client.get(f"/suites/{data['id']}")
        self.assertEqual(r2.status_code, 404)

    def test_delete_suite_not_found(self):
        r = self.client.delete("/suites/ghost-id")
        self.assertEqual(r.status_code, 404)


@unittest.skipUnless(_FASTAPI_AVAILABLE, "fastapi not installed")
class TestTestCaseEndpoints(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        import importlib
        import nextgen_test_automation.api.main as mod
        importlib.reload(mod)
        from nextgen_test_automation.api.main import app
        cls.client = TestClient(app)
        # Create a shared suite
        r = cls.client.post("/suites", json={"name": "TC Suite"})
        cls.suite_id = r.json()["id"]

    def _create_tc(self, name: str = "Login test", industry: str = "BFSI") -> dict:
        r = self.client.post(
            f"/suites/{self.suite_id}/test-cases",
            json={
                "name": name,
                "industry": industry,
                "steps": [
                    {"action": "navigate", "description": "go to login",
                     "payload": {"url": "https://demo.bank/login"}},
                ],
                "tags": [industry],
            },
        )
        self.assertEqual(r.status_code, 201)
        return r.json()

    def test_list_test_cases_empty(self):
        r = self.client.get(f"/suites/{self.suite_id}/test-cases")
        self.assertEqual(r.status_code, 200)
        self.assertIsInstance(r.json(), list)

    def test_create_test_case(self):
        data = self._create_tc("Smoke Login")
        self.assertIn("id", data)
        self.assertEqual(data["name"], "Smoke Login")
        self.assertEqual(data["step_count"], 1)

    def test_create_tc_missing_name_returns_400(self):
        r = self.client.post(
            f"/suites/{self.suite_id}/test-cases",
            json={"industry": "general"},
        )
        self.assertEqual(r.status_code, 400)

    def test_get_test_case(self):
        data = self._create_tc("Get TC")
        r = self.client.get(f"/suites/{self.suite_id}/test-cases/{data['id']}")
        self.assertEqual(r.status_code, 200)
        self.assertIn("steps", r.json())

    def test_get_test_case_not_found(self):
        r = self.client.get(f"/suites/{self.suite_id}/test-cases/ghost")
        self.assertEqual(r.status_code, 404)

    def test_update_test_case(self):
        data = self._create_tc("Before Update")
        r = self.client.put(
            f"/suites/{self.suite_id}/test-cases/{data['id']}",
            json={"name": "After Update"},
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["name"], "After Update")

    def test_update_no_fields_returns_400(self):
        data = self._create_tc("No Update")
        r = self.client.put(
            f"/suites/{self.suite_id}/test-cases/{data['id']}",
            json={"steps": []},
        )
        self.assertEqual(r.status_code, 400)

    def test_delete_test_case(self):
        data = self._create_tc("Delete TC")
        r = self.client.delete(f"/suites/{self.suite_id}/test-cases/{data['id']}")
        self.assertEqual(r.status_code, 204)
        r2 = self.client.get(f"/suites/{self.suite_id}/test-cases/{data['id']}")
        self.assertEqual(r2.status_code, 404)


@unittest.skipUnless(_FASTAPI_AVAILABLE, "fastapi not installed")
class TestWalkthroughEndpoint(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        import importlib
        import nextgen_test_automation.api.main as mod
        importlib.reload(mod)
        from nextgen_test_automation.api.main import app
        cls.client = TestClient(app)

    def test_create_walkthrough_session(self):
        r = self.client.post(
            "/walkthrough/sessions",
            json={
                "app_name": "TestApp",
                "platform": "web",
                "events": [
                    {"action": "navigate", "locator": {}, "payload": {"url": "https://x.com"}},
                    {"action": "click", "locator": {"css": "#btn"}, "payload": {}},
                ],
            },
        )
        self.assertEqual(r.status_code, 201)
        data = r.json()
        self.assertEqual(data["app_name"], "TestApp")
        self.assertEqual(data["event_count"], 2)
        self.assertIn("session_id", data)

    def test_missing_app_name_returns_400(self):
        r = self.client.post("/walkthrough/sessions", json={"events": []})
        self.assertEqual(r.status_code, 400)


@unittest.skipUnless(_FASTAPI_AVAILABLE, "fastapi not installed")
class TestAPITestEndpoint(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        import importlib
        import nextgen_test_automation.api.main as mod
        importlib.reload(mod)
        from nextgen_test_automation.api.main import app
        cls.client = TestClient(app)

    def test_missing_url_returns_400(self):
        r = self.client.post("/api-tests/run", json={"method": "GET"})
        self.assertEqual(r.status_code, 400)


if __name__ == "__main__":
    unittest.main()
