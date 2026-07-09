from __future__ import annotations

try:
    from fastapi import FastAPI, HTTPException
except Exception as exc:  # pragma: no cover
    raise RuntimeError("Install API dependencies with: pip install -e .[api]") from exc

from nextgen_test_automation.core.models import TestSuite
from nextgen_test_automation.core.test_case_manager import InMemoryTestCaseManager

app = FastAPI(title="NextGen Test Automation API", version="0.1.0")
manager = InMemoryTestCaseManager()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/suites")
def list_suites() -> list[dict]:
    return [
        {
            "id": suite.id,
            "name": suite.name,
            "description": suite.description,
            "test_case_count": len(suite.test_cases),
        }
        for suite in manager.list_suites()
    ]


@app.post("/suites")
def create_suite(payload: dict) -> dict:
    name = (payload.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")
    suite = TestSuite(name=name, description=payload.get("description", ""))
    manager.create_suite(suite)
    return {"id": suite.id, "name": suite.name, "description": suite.description}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
