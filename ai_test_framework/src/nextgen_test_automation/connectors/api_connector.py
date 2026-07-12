from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class APIAssertion:
    status_code: int | None = None
    json_contains: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class APIRequestSpec:
    method: str
    url: str
    headers: dict[str, str] = field(default_factory=dict)
    payload: dict[str, Any] = field(default_factory=dict)
    assertions: APIAssertion = field(default_factory=APIAssertion)
