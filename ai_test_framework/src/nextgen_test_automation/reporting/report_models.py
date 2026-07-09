from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(slots=True)
class StepReport:
    step_index: int
    passed: bool
    message: str = ""


@dataclass(slots=True)
class TestRunReport:
    test_case_id: str
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: datetime | None = None
    steps: list[StepReport] = field(default_factory=list)
