"""Unit tests for ReportBuilder."""
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from nextgen_test_automation.reporting.report_builder import ReportBuilder
from nextgen_test_automation.reporting.report_models import StepReport, TestRunReport


def _make_report(passed_steps: list[bool], tc_id: str = "tc-abc-123") -> TestRunReport:
    started = datetime(2026, 8, 16, 10, 0, 0, tzinfo=timezone.utc)
    finished = datetime(2026, 8, 16, 10, 0, 5, tzinfo=timezone.utc)  # 5 seconds
    report = TestRunReport(test_case_id=tc_id, started_at=started, finished_at=finished)
    for i, passed in enumerate(passed_steps):
        msg = "OK" if passed else f"Failure at step {i}"
        report.steps.append(StepReport(step_index=i, passed=passed, message=msg))
    return report


class TestReportBuilderToDict(unittest.TestCase):

    def setUp(self):
        self.builder = ReportBuilder()

    def test_passed_report_dict(self):
        report = _make_report([True, True, True])
        data = self.builder.to_dict(report)
        self.assertTrue(data["passed"])
        self.assertEqual(data["total_steps"], 3)
        self.assertEqual(data["passed_steps"], 3)
        self.assertEqual(data["failed_steps"], 0)

    def test_failed_report_dict(self):
        report = _make_report([True, False, True])
        data = self.builder.to_dict(report)
        self.assertFalse(data["passed"])
        self.assertEqual(data["failed_steps"], 1)

    def test_duration_computed(self):
        report = _make_report([True])
        data = self.builder.to_dict(report)
        self.assertAlmostEqual(data["duration_ms"], 5000.0, delta=1.0)

    def test_duration_none_when_not_finished(self):
        report = TestRunReport(test_case_id="x")
        data = self.builder.to_dict(report)
        self.assertIsNone(data["duration_ms"])

    def test_step_details_in_dict(self):
        report = _make_report([True, False])
        data = self.builder.to_dict(report)
        self.assertEqual(data["steps"][0]["passed"], True)
        self.assertEqual(data["steps"][1]["passed"], False)
        self.assertIn("Failure", data["steps"][1]["message"])


class TestReportBuilderToJson(unittest.TestCase):

    def setUp(self):
        self.builder = ReportBuilder()

    def test_to_json_is_valid_json(self):
        report = _make_report([True])
        s = self.builder.to_json(report)
        parsed = json.loads(s)
        self.assertIn("test_case_id", parsed)

    def test_to_json_round_trip(self):
        report = _make_report([True, False])
        data = json.loads(self.builder.to_json(report))
        self.assertEqual(data["total_steps"], 2)


class TestReportBuilderToHtml(unittest.TestCase):

    def setUp(self):
        self.builder = ReportBuilder()

    def test_html_contains_passed_badge(self):
        html = self.builder.to_html(_make_report([True, True]))
        self.assertIn("PASSED", html)

    def test_html_contains_failed_badge(self):
        html = self.builder.to_html(_make_report([True, False]))
        self.assertIn("FAILED", html)

    def test_html_contains_test_case_id(self):
        report = _make_report([True], tc_id="my-tc-xyz")
        html = self.builder.to_html(report)
        self.assertIn("my-tc-xyz", html)

    def test_html_is_valid_structure(self):
        html = self.builder.to_html(_make_report([True]))
        self.assertIn("<!DOCTYPE html>", html)
        self.assertIn("</html>", html)

    def test_html_empty_steps_shows_placeholder(self):
        report = TestRunReport(test_case_id="empty")
        html = self.builder.to_html(report)
        self.assertIn("No steps recorded", html)


class TestReportBuilderSave(unittest.TestCase):

    def setUp(self):
        self.builder = ReportBuilder()

    def test_save_creates_json_and_html(self):
        report = _make_report([True, True])
        with tempfile.TemporaryDirectory() as tmpdir:
            paths = self.builder.save(report, output_dir=tmpdir)
            self.assertTrue(Path(paths["json"]).exists())
            self.assertTrue(Path(paths["html"]).exists())

    def test_saved_json_is_parseable(self):
        report = _make_report([False])
        with tempfile.TemporaryDirectory() as tmpdir:
            paths = self.builder.save(report, output_dir=tmpdir)
            content = json.loads(Path(paths["json"]).read_text())
            self.assertFalse(content["passed"])

    def test_save_creates_output_dir(self):
        report = _make_report([True])
        with tempfile.TemporaryDirectory() as tmpdir:
            new_dir = Path(tmpdir) / "nested" / "reports"
            paths = self.builder.save(report, output_dir=str(new_dir))
            self.assertTrue(Path(paths["json"]).exists())


if __name__ == "__main__":
    unittest.main()
