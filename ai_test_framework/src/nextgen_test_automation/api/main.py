"""FastAPI service — Phase 1 REST API.

Endpoints
---------
GET  /health
GET  /suites
POST /suites
GET  /suites/{suite_id}
DELETE /suites/{suite_id}
POST /suites/{suite_id}/test-cases
GET  /suites/{suite_id}/test-cases
GET  /suites/{suite_id}/test-cases/{tc_id}
PUT  /suites/{suite_id}/test-cases/{tc_id}
DELETE /suites/{suite_id}/test-cases/{tc_id}
POST /suites/{suite_id}/test-cases/{tc_id}/execute
POST /api-tests/run
POST /walkthrough/sessions
"""
from __future__ import annotations

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import HTMLResponse
except Exception as exc:  # pragma: no cover
    raise RuntimeError("Install API dependencies with: pip install -e .[api]") from exc

from nextgen_test_automation.connectors.api_connector import APIAssertion, APIRequestSpec
from nextgen_test_automation.connectors.api_runner import APITestRunner
from nextgen_test_automation.core.models import ElementLocator, StepAction, TestCase, TestStep, TestSuite
from nextgen_test_automation.core.test_case_manager import InMemoryTestCaseManager
from nextgen_test_automation.execution.web_executor import WebAutomationExecutor
from nextgen_test_automation.reporting.report_builder import ReportBuilder
from nextgen_test_automation.walkthrough.browser_recorder import BrowserRecorder

app = FastAPI(title="NextGen Test Automation API", version="0.2.0")
manager = InMemoryTestCaseManager()
_api_runner = APITestRunner()
_recorder = BrowserRecorder()
_report_builder = ReportBuilder()

# ── stored run reports (in-memory for Phase 1) ────────────────────────────────
_run_reports: dict[str, dict] = {}


# =============================================================================
# Health
# =============================================================================

@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "version": "0.2.0"}


# =============================================================================
# Suites
# =============================================================================

@app.get("/suites", tags=["suites"])
def list_suites() -> list[dict]:
    return [_suite_summary(s) for s in manager.list_suites()]


@app.post("/suites", status_code=201, tags=["suites"])
def create_suite(payload: dict) -> dict:
    name = (payload.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")
    suite = TestSuite(name=name, description=payload.get("description", ""))
    manager.create_suite(suite)
    return _suite_summary(suite)


@app.get("/suites/{suite_id}", tags=["suites"])
def get_suite(suite_id: str) -> dict:
    suite = manager.get_suite(suite_id)
    if suite is None:
        raise HTTPException(status_code=404, detail="suite not found")
    return _suite_detail(suite)


@app.delete("/suites/{suite_id}", status_code=204, tags=["suites"])
def delete_suite(suite_id: str) -> None:
    suite = manager.get_suite(suite_id)
    if suite is None:
        raise HTTPException(status_code=404, detail="suite not found")
    # Remove from internal store
    manager._suites.pop(suite_id, None)


# =============================================================================
# Test Cases
# =============================================================================

@app.get("/suites/{suite_id}/test-cases", tags=["test-cases"])
def list_test_cases(suite_id: str) -> list[dict]:
    suite = _require_suite(suite_id)
    return [_tc_summary(tc) for tc in suite.test_cases]


@app.post("/suites/{suite_id}/test-cases", status_code=201, tags=["test-cases"])
def create_test_case(suite_id: str, payload: dict) -> dict:
    _require_suite(suite_id)
    name = (payload.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")
    steps = [_parse_step(s) for s in payload.get("steps", [])]
    tc = TestCase(
        name=name,
        industry=payload.get("industry", "general"),
        steps=steps,
        tags=payload.get("tags", []),
    )
    manager.add_test_case(suite_id, tc)
    return _tc_summary(tc)


@app.get("/suites/{suite_id}/test-cases/{tc_id}", tags=["test-cases"])
def get_test_case(suite_id: str, tc_id: str) -> dict:
    suite = _require_suite(suite_id)
    tc = _find_tc(suite, tc_id)
    return _tc_detail(tc)


@app.put("/suites/{suite_id}/test-cases/{tc_id}", tags=["test-cases"])
def update_test_case(suite_id: str, tc_id: str, payload: dict) -> dict:
    _require_suite(suite_id)
    patch = {k: v for k, v in payload.items() if k in ("name", "industry", "tags")}
    if not patch:
        raise HTTPException(status_code=400, detail="No updatable fields provided")
    try:
        updated = manager.update_test_case(suite_id, tc_id, patch)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _tc_summary(updated)


@app.delete("/suites/{suite_id}/test-cases/{tc_id}", status_code=204, tags=["test-cases"])
def delete_test_case(suite_id: str, tc_id: str) -> None:
    _require_suite(suite_id)
    try:
        manager.delete_test_case(suite_id, tc_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# =============================================================================
# Execution
# =============================================================================

@app.post("/suites/{suite_id}/test-cases/{tc_id}/execute", tags=["execution"])
def execute_test_case(suite_id: str, tc_id: str, payload: dict | None = None) -> dict:
    """Trigger Playwright execution of a test case.

    Query / body options:
    - ``headless`` (bool, default true)
    - ``browser`` (str, default "chromium")
    """
    suite = _require_suite(suite_id)
    tc = _find_tc(suite, tc_id)
    opts = payload or {}
    executor = WebAutomationExecutor(
        browser_type=opts.get("browser", "chromium"),
        headless=bool(opts.get("headless", True)),
    )
    result = executor.run(tc)
    report_dict: dict = {}
    if result.report:
        report_dict = _report_builder.to_dict(result.report)
        _run_reports[tc_id] = report_dict
    return {
        "test_case_id": result.test_case_id,
        "passed": result.passed,
        "failed_step_index": result.failed_step_index,
        "message": result.message,
        "duration_ms": result.duration_ms,
        "screenshots": result.screenshots,
        "report": report_dict,
    }


@app.get("/reports/{tc_id}", tags=["execution"])
def get_report(tc_id: str) -> dict:
    report = _run_reports.get(tc_id)
    if report is None:
        raise HTTPException(status_code=404, detail="No report found for this test case")
    return report


@app.get("/reports/{tc_id}/html", response_class=HTMLResponse, tags=["execution"])
def get_report_html(tc_id: str) -> str:
    from nextgen_test_automation.reporting.report_models import StepReport, TestRunReport
    from datetime import datetime, timezone

    report_dict = _run_reports.get(tc_id)
    if report_dict is None:
        raise HTTPException(status_code=404, detail="No report found for this test case")

    # Reconstruct a minimal TestRunReport for the builder
    report = TestRunReport(
        test_case_id=report_dict["test_case_id"],
        started_at=datetime.fromisoformat(report_dict["started_at"]),
        finished_at=datetime.fromisoformat(report_dict["finished_at"])
        if report_dict.get("finished_at")
        else None,
        steps=[
            StepReport(step_index=s["index"], passed=s["passed"], message=s["message"])
            for s in report_dict.get("steps", [])
        ],
    )
    return _report_builder.to_html(report)


# =============================================================================
# API Testing
# =============================================================================

@app.post("/api-tests/run", tags=["api-testing"])
def run_api_test(payload: dict) -> dict:
    """Execute an API request and evaluate assertions.

    Body::

        {
          "method": "GET",
          "url": "https://api.example.com/users",
          "headers": {},
          "payload": {},
          "assertions": {
            "status_code": 200,
            "json_contains": {"key": "value"}
          }
        }
    """
    method = (payload.get("method") or "GET").strip().upper()
    url = (payload.get("url") or "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="url is required")

    assertions_raw = payload.get("assertions") or {}
    spec = APIRequestSpec(
        method=method,
        url=url,
        headers=payload.get("headers") or {},
        payload=payload.get("payload") or {},
        assertions=APIAssertion(
            status_code=assertions_raw.get("status_code"),
            json_contains=assertions_raw.get("json_contains") or {},
        ),
    )
    result = _api_runner.run(spec)
    return {
        "url": result.spec_url,
        "method": result.method,
        "status_code": result.status_code,
        "passed": result.passed,
        "failures": result.failures,
        "duration_ms": round(result.duration_ms, 2),
        "response_body": result.response_body,
    }


# =============================================================================
# Walk-through Sessions
# =============================================================================

@app.post("/walkthrough/sessions", status_code=201, tags=["walkthrough"])
def create_walkthrough_session(payload: dict) -> dict:
    """Convert a list of raw captured browser events into a walk-through session.

    Body::

        {
          "app_name": "MyApp",
          "platform": "web",
          "events": [
            {"action": "navigate", "locator": {}, "payload": {"url": "https://..."}},
            {"action": "click", "locator": {"css": "#login-btn"}, "payload": {}}
          ]
        }

    Returns the session ID and the number of events captured.
    """
    app_name = (payload.get("app_name") or "").strip()
    if not app_name:
        raise HTTPException(status_code=400, detail="app_name is required")
    events = payload.get("events") or []
    session = _recorder.record_from_events(
        events,
        app_name=app_name,
        platform=payload.get("platform", "web"),
    )
    return {
        "session_id": session.session_id,
        "app_name": session.app_name,
        "platform": session.platform,
        "event_count": len(session.events),
    }


# =============================================================================
# Helpers
# =============================================================================

def _require_suite(suite_id: str) -> TestSuite:
    suite = manager.get_suite(suite_id)
    if suite is None:
        raise HTTPException(status_code=404, detail="suite not found")
    return suite


def _find_tc(suite: TestSuite, tc_id: str) -> TestCase:
    for tc in suite.test_cases:
        if tc.id == tc_id:
            return tc
    raise HTTPException(status_code=404, detail="test case not found")


def _suite_summary(suite: TestSuite) -> dict:
    return {
        "id": suite.id,
        "name": suite.name,
        "description": suite.description,
        "test_case_count": len(suite.test_cases),
        "created_at": suite.created_at.isoformat(),
    }


def _suite_detail(suite: TestSuite) -> dict:
    return {
        **_suite_summary(suite),
        "test_cases": [_tc_summary(tc) for tc in suite.test_cases],
    }


def _tc_summary(tc: TestCase) -> dict:
    return {
        "id": tc.id,
        "name": tc.name,
        "industry": tc.industry,
        "step_count": len(tc.steps),
        "tags": tc.tags,
        "created_at": tc.created_at.isoformat(),
        "updated_at": tc.updated_at.isoformat(),
    }


def _tc_detail(tc: TestCase) -> dict:
    return {
        **_tc_summary(tc),
        "steps": [
            {
                "action": step.action.value,
                "description": step.description,
                "payload": step.payload,
                "expected": step.expected,
            }
            for step in tc.steps
        ],
    }


def _parse_step(raw: dict) -> TestStep:
    action = StepAction(raw.get("action", "navigate"))
    loc_raw = raw.get("locator") or {}
    locator = None
    if loc_raw:
        locator = ElementLocator(
            css=loc_raw.get("css"),
            text=loc_raw.get("text"),
            aria_label=loc_raw.get("aria_label"),
            xpath=loc_raw.get("xpath"),
        )
    return TestStep(
        action=action,
        description=raw.get("description", ""),
        locator=locator,
        payload=raw.get("payload") or {},
        expected=raw.get("expected") or {},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
