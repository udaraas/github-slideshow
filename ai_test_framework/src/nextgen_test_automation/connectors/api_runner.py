"""httpx-backed API test runner with a full assertion engine."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from nextgen_test_automation.connectors.api_connector import APIAssertion, APIRequestSpec

try:
    import httpx
    _HTTPX_AVAILABLE = True
except ImportError:  # pragma: no cover
    httpx = None  # type: ignore[assignment]
    _HTTPX_AVAILABLE = False


@dataclass(slots=True)
class APIRunResult:
    spec_url: str
    method: str
    status_code: int
    passed: bool
    failures: list[str] = field(default_factory=list)
    response_body: Any = None
    response_headers: dict[str, str] = field(default_factory=dict)
    duration_ms: float = 0.0


class APITestRunner:
    """Execute an :class:`APIRequestSpec` via httpx and validate assertions.

    Usage::

        runner = APITestRunner()
        result = runner.run(APIRequestSpec(
            method="GET",
            url="https://api.example.com/users",
            assertions=APIAssertion(status_code=200),
        ))
    """

    def run(self, spec: APIRequestSpec) -> APIRunResult:
        if not _HTTPX_AVAILABLE or httpx is None:
            return APIRunResult(
                spec_url=spec.url,
                method=spec.method,
                status_code=0,
                passed=False,
                failures=["httpx not installed. Run: pip install -e .[http]"],
            )

        start = time.monotonic()
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.request(
                    method=spec.method.upper(),
                    url=spec.url,
                    headers=spec.headers,
                    json=spec.payload if spec.payload else None,
                )
        except Exception as exc:
            return APIRunResult(
                spec_url=spec.url,
                method=spec.method,
                status_code=0,
                passed=False,
                failures=[f"Request failed: {exc}"],
                duration_ms=(time.monotonic() - start) * 1000,
            )

        duration_ms = (time.monotonic() - start) * 1000

        body: Any = None
        try:
            body = response.json()
        except Exception:
            body = response.text

        failures = self._assert(spec.assertions, response, body)
        return APIRunResult(
            spec_url=spec.url,
            method=spec.method,
            status_code=response.status_code,
            passed=len(failures) == 0,
            failures=failures,
            response_body=body,
            response_headers=dict(response.headers),
            duration_ms=duration_ms,
        )

    # ------------------------------------------------------------------
    # Assertion engine
    # ------------------------------------------------------------------

    def _assert(self, assertion: APIAssertion, response: Any, body: Any) -> list[str]:
        failures: list[str] = []

        # Status code
        if assertion.status_code is not None and response.status_code != assertion.status_code:
            failures.append(
                f"Expected HTTP {assertion.status_code}, got {response.status_code}"
            )

        # JSON body contains (key/value pairs)
        if assertion.json_contains:
            if not isinstance(body, dict):
                failures.append(
                    "json_contains assertion requires a JSON object response body"
                )
            else:
                for key, expected_value in assertion.json_contains.items():
                    actual_value = body.get(key)
                    if actual_value != expected_value:
                        failures.append(
                            f"json_contains['{key}']: expected {expected_value!r}, "
                            f"got {actual_value!r}"
                        )

        return failures
