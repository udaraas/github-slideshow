from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class DBAssertion:
    min_rows: int | None = None
    equals: list[dict[str, Any]] = field(default_factory=list)


@dataclass(slots=True)
class DBQuerySpec:
    connection_name: str
    query: str
    params: dict[str, Any] = field(default_factory=dict)
    assertions: DBAssertion = field(default_factory=DBAssertion)
