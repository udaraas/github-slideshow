# NextGen Test Automation Framework

AI-powered, no-code, self-healing test automation platform — built in Python.

## Phase Status

| Phase | Status | Description |
|---|---|---|
| **Phase 0** | ✅ Complete | Architecture, domain models, API skeleton |
| **Phase 1** | ✅ Complete | Web + API MVP |
| Phase 2 | 🔜 Nov–Dec 2026 | Self-healing + Desktop + Database |
| Phase 3 | 🔜 Jan–Feb 2027 | Enterprise readiness, CI/CD, industry packs |
| Phase 4 | 🔜 Mar 2027 | Stabilisation & v1.0 release |

---

## Phase 1 — What's Built

### Core Modules

| Module | Description |
|---|---|
| `core/models.py` | Domain models: `TestSuite`, `TestCase`, `TestStep`, `ElementLocator`, `HealingLog` |
| `core/test_case_manager.py` | In-memory CRUD manager for suites and test cases |
| `walkthrough/events.py` | Walk-through session and event schema |
| `walkthrough/browser_recorder.py` | Playwright JS-injection recorder — captures click/type/submit events |
| `execution/locator_resolver.py` | **3-tier locator resolution**: CSS → ARIA label → visible text → XPath |
| `execution/web_executor.py` | **Playwright web executor** — runs test steps, captures screenshots |
| `connectors/api_runner.py` | **httpx API runner** — status code + JSON body assertions |
| `ai/generator.py` | Rule-based stub generator (no LLM key needed) |
| `ai/llm_generator.py` | **LangChain/GPT-4o generator** with automatic stub fallback |
| `accessibility/axe_checker.py` | **axe-core WCAG AA scanner** via Playwright injection |
| `reporting/report_builder.py` | **JSON + HTML report builder** |
| `api/main.py` | **FastAPI REST service** — full CRUD, execution, walk-through, API-test endpoints |

### REST API Endpoints (Phase 1)

```
GET  /health
GET  /suites
POST /suites
GET  /suites/{id}
DELETE /suites/{id}
GET  /suites/{id}/test-cases
POST /suites/{id}/test-cases
GET  /suites/{id}/test-cases/{tc_id}
PUT  /suites/{id}/test-cases/{tc_id}
DELETE /suites/{id}/test-cases/{tc_id}
POST /suites/{id}/test-cases/{tc_id}/execute
GET  /reports/{tc_id}
GET  /reports/{tc_id}/html
POST /api-tests/run
POST /walkthrough/sessions
```

---

## Quick Start

### 1. Install

```bash
cd ai_test_framework

# Minimal (no optional deps)
pip install -e .

# Phase 1 full stack (Playwright + httpx + FastAPI + LangChain)
pip install -e .[phase1]

# After installing Playwright, install browsers:
playwright install chromium
```

### 2. Run Tests

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

### 3. Start the API Server

```bash
pip install -e .[api]
python -m nextgen_test_automation.api.main
# → http://localhost:8000/docs
```

### 4. Record a Walk-through & Generate Tests

```python
from playwright.sync_api import sync_playwright
from nextgen_test_automation.walkthrough.browser_recorder import BrowserRecorder
from nextgen_test_automation.ai.llm_generator import LLMTestCaseGenerator

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=False)
    page = browser.new_page()

    recorder = BrowserRecorder()
    recorder.start(page)           # inject event capture

    page.goto("https://your-app.example.com")
    # ... interact with the app ...

    session = recorder.stop_and_build_session(page, app_name="MyApp")
    browser.close()

# Generate test cases (uses GPT-4o if OPENAI_API_KEY is set, else rule-based stub)
generator = LLMTestCaseGenerator()
test_case = generator.generate(session, industry="BFSI")
print(test_case.name, len(test_case.steps), "steps")
```

### 5. Execute Web Tests

```python
from nextgen_test_automation.execution.web_executor import WebAutomationExecutor

executor = WebAutomationExecutor(headless=True)
result = executor.run(test_case)
print("Passed:", result.passed, "| Duration:", result.duration_ms, "ms")
```

### 6. Run an API Test

```python
from nextgen_test_automation.connectors.api_connector import APIAssertion, APIRequestSpec
from nextgen_test_automation.connectors.api_runner import APITestRunner

runner = APITestRunner()
result = runner.run(APIRequestSpec(
    method="GET",
    url="https://api.example.com/users",
    assertions=APIAssertion(status_code=200, json_contains={"active": True}),
))
print("Passed:", result.passed, "Failures:", result.failures)
```

### 7. Run an Accessibility Scan

```python
from nextgen_test_automation.accessibility.axe_checker import AxeAccessibilityChecker

checker = AxeAccessibilityChecker(wcag_level="AA")
with sync_playwright() as pw:
    page = pw.chromium.launch().new_page()
    page.goto("https://your-app.example.com")
    report = checker.check(page)

print(report.summary())
for v in report.violations:
    print(f"  [{v.impact}] {v.id} — {v.description} ({v.nodes_affected} nodes)")
```

---

## Optional Dependency Groups

```bash
pip install -e .[api]     # FastAPI + uvicorn
pip install -e .[web]     # Playwright
pip install -e .[http]    # httpx (API runner)
pip install -e .[ai]      # LangChain + langchain-openai
pip install -e .[phase1]  # All of the above
pip install -e .[dev]     # pytest + fastapi + httpx (testing)
```

## Environment Variables

| Variable | Description |
|---|---|
| `OPENAI_API_KEY` | Enables GPT-4o test generation via LangChain |

