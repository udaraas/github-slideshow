"""JSON and HTML report builder for test run results."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from nextgen_test_automation.reporting.report_models import TestRunReport


class ReportBuilder:
    """Build rich JSON and HTML reports from :class:`TestRunReport` objects.

    Usage::

        builder = ReportBuilder()
        report = TestRunReport(test_case_id="abc123", ...)
        paths = builder.save(report, output_dir="reports/")
        print(paths["html"])
    """

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self, report: TestRunReport) -> dict[str, Any]:
        """Convert *report* to a plain dict (JSON-serialisable)."""
        duration_ms: float | None = None
        if report.finished_at is not None:
            duration_ms = (report.finished_at - report.started_at).total_seconds() * 1000

        passed = all(s.passed for s in report.steps)
        return {
            "test_case_id": report.test_case_id,
            "started_at": report.started_at.isoformat(),
            "finished_at": report.finished_at.isoformat() if report.finished_at else None,
            "duration_ms": round(duration_ms, 2) if duration_ms is not None else None,
            "passed": passed,
            "total_steps": len(report.steps),
            "passed_steps": sum(1 for s in report.steps if s.passed),
            "failed_steps": sum(1 for s in report.steps if not s.passed),
            "steps": [
                {"index": s.step_index, "passed": s.passed, "message": s.message}
                for s in report.steps
            ],
        }

    def to_json(self, report: TestRunReport, indent: int = 2) -> str:
        """Return a pretty-printed JSON string for *report*."""
        return json.dumps(self.to_dict(report), indent=indent)

    def to_html(self, report: TestRunReport) -> str:
        """Return a self-contained HTML string for *report*."""
        data = self.to_dict(report)
        passed = data["passed"]
        status_color = "#2e7d32" if passed else "#c62828"
        status_label = "PASSED" if passed else "FAILED"
        duration_str = (
            f"{data['duration_ms']:.0f} ms" if data["duration_ms"] is not None else "N/A"
        )

        step_rows = "".join(
            "<tr style='background:{bg}'>"
            "<td style='width:3rem;text-align:center'>{num}</td>"
            "<td style='width:3rem;text-align:center;font-size:1.1rem'>{icon}</td>"
            "<td>{msg}</td></tr>".format(
                bg="#e8f5e9" if s["passed"] else "#ffebee",
                num=s["index"] + 1,
                icon="✓" if s["passed"] else "✗",
                msg=s["message"],
            )
            for s in data["steps"]
        )

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Test Report — {data['test_case_id']}</title>
  <style>
    *{{box-sizing:border-box;margin:0;padding:0}}
    body{{font-family:'Segoe UI',Arial,sans-serif;background:#f5f5f5;color:#212121;padding:2rem}}
    .card{{background:#fff;border-radius:8px;box-shadow:0 2px 6px rgba(0,0,0,.12);padding:1.5rem;max-width:900px;margin:auto}}
    h1{{font-size:1.4rem;margin-bottom:.8rem;color:#1565c0}}
    .badge{{display:inline-block;padding:.25rem .9rem;border-radius:4px;color:#fff;
            background:{status_color};font-weight:700;font-size:1rem;margin-bottom:1rem}}
    .meta{{color:#616161;font-size:.9rem;margin-bottom:1.5rem;line-height:2}}
    table{{border-collapse:collapse;width:100%}}
    th{{background:#1565c0;color:#fff;padding:.5rem .8rem;text-align:left;font-weight:600}}
    td{{padding:.45rem .8rem;border-bottom:1px solid #e0e0e0;vertical-align:top}}
    tr:last-child td{{border-bottom:none}}
  </style>
</head>
<body>
<div class="card">
  <h1>Test Run Report</h1>
  <span class="badge">{status_label}</span>
  <p class="meta">
    <strong>Test Case ID:</strong> {data['test_case_id']}<br>
    <strong>Duration:</strong> {duration_str}<br>
    <strong>Steps:</strong> {data['passed_steps']}/{data['total_steps']} passed
    ({data['failed_steps']} failed)
  </p>
  <table>
    <thead><tr><th>#</th><th>Status</th><th>Message</th></tr></thead>
    <tbody>{step_rows if step_rows else '<tr><td colspan="3" style="text-align:center;color:#9e9e9e">No steps recorded</td></tr>'}</tbody>
  </table>
</div>
</body>
</html>"""

    # ------------------------------------------------------------------
    # File I/O
    # ------------------------------------------------------------------

    def save(self, report: TestRunReport, output_dir: str | Path = "reports") -> dict[str, str]:
        """Write JSON and HTML reports to *output_dir*.

        Returns a dict with keys ``"json"`` and ``"html"`` pointing to the
        created file paths.
        """
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        base = f"report_{report.test_case_id[:8]}_{ts}"
        json_path = out / f"{base}.json"
        html_path = out / f"{base}.html"
        json_path.write_text(self.to_json(report), encoding="utf-8")
        html_path.write_text(self.to_html(report), encoding="utf-8")
        return {"json": str(json_path), "html": str(html_path)}
