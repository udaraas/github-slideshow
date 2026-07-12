"""Unit tests for APITestRunner (httpx mocked)."""
import unittest
from unittest.mock import MagicMock, patch

from nextgen_test_automation.connectors.api_connector import APIAssertion, APIRequestSpec
from nextgen_test_automation.connectors.api_runner import APITestRunner


def _mock_response(status_code: int, json_body=None, text_body: str = "") -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.headers = {"content-type": "application/json"}
    if json_body is not None:
        resp.json.return_value = json_body
        resp.text = ""
    else:
        resp.json.side_effect = ValueError("not json")
        resp.text = text_body
    return resp


class TestAPITestRunner(unittest.TestCase):

    def setUp(self):
        self.runner = APITestRunner()

    def _run_with_mock(self, spec: APIRequestSpec, mock_resp: MagicMock) -> object:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.request.return_value = mock_resp

        mock_httpx = MagicMock()
        mock_httpx.Client.return_value = mock_client

        with patch("nextgen_test_automation.connectors.api_runner.httpx", mock_httpx), \
             patch("nextgen_test_automation.connectors.api_runner._HTTPX_AVAILABLE", True):
            return self.runner.run(spec)

    # ── Happy paths ────────────────────────────────────────────────────────

    def test_passes_when_status_code_matches(self):
        spec = APIRequestSpec(
            method="GET",
            url="https://api.example.com/health",
            assertions=APIAssertion(status_code=200),
        )
        result = self._run_with_mock(spec, _mock_response(200, {}))
        self.assertTrue(result.passed)
        self.assertEqual(result.failures, [])

    def test_passes_json_contains_assertion(self):
        spec = APIRequestSpec(
            method="GET",
            url="https://api.example.com/user",
            assertions=APIAssertion(
                status_code=200,
                json_contains={"name": "Alice"},
            ),
        )
        result = self._run_with_mock(spec, _mock_response(200, {"name": "Alice", "role": "admin"}))
        self.assertTrue(result.passed)

    def test_records_duration(self):
        spec = APIRequestSpec(method="GET", url="https://api.example.com/")
        result = self._run_with_mock(spec, _mock_response(200, {}))
        self.assertGreaterEqual(result.duration_ms, 0)

    def test_captures_response_body(self):
        spec = APIRequestSpec(method="GET", url="https://api.example.com/users")
        result = self._run_with_mock(spec, _mock_response(200, [{"id": 1}]))
        self.assertEqual(result.response_body, [{"id": 1}])

    # ── Failure paths ──────────────────────────────────────────────────────

    def test_fails_when_status_code_wrong(self):
        spec = APIRequestSpec(
            method="GET",
            url="https://api.example.com/secret",
            assertions=APIAssertion(status_code=200),
        )
        result = self._run_with_mock(spec, _mock_response(401, {"error": "unauthorized"}))
        self.assertFalse(result.passed)
        self.assertTrue(any("401" in f for f in result.failures))

    def test_fails_json_contains_wrong_value(self):
        spec = APIRequestSpec(
            method="GET",
            url="https://api.example.com/user",
            assertions=APIAssertion(json_contains={"name": "Bob"}),
        )
        result = self._run_with_mock(spec, _mock_response(200, {"name": "Alice"}))
        self.assertFalse(result.passed)
        self.assertTrue(any("name" in f for f in result.failures))

    def test_fails_json_contains_when_not_json(self):
        spec = APIRequestSpec(
            method="GET",
            url="https://api.example.com/html",
            assertions=APIAssertion(json_contains={"key": "val"}),
        )
        result = self._run_with_mock(spec, _mock_response(200, text_body="<html>"))
        self.assertFalse(result.passed)

    def test_handles_request_exception(self):
        spec = APIRequestSpec(method="GET", url="https://unreachable.invalid/")
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.request.side_effect = ConnectionError("timeout")

        mock_httpx = MagicMock()
        mock_httpx.Client.return_value = mock_client

        with patch("nextgen_test_automation.connectors.api_runner.httpx", mock_httpx), \
             patch("nextgen_test_automation.connectors.api_runner._HTTPX_AVAILABLE", True):
            result = self.runner.run(spec)
        self.assertFalse(result.passed)
        self.assertTrue(any("Request failed" in f for f in result.failures))

    def test_no_assertions_passes_any_response(self):
        spec = APIRequestSpec(method="GET", url="https://api.example.com/")
        result = self._run_with_mock(spec, _mock_response(500, {"error": "boom"}))
        # No assertions configured → always passes
        self.assertTrue(result.passed)


if __name__ == "__main__":
    unittest.main()
