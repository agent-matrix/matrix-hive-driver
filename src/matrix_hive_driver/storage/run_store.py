from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class StoredRun:
    run_id: str
    plan_id: str
    state: str = "queued"
    hive_run_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    events: list[dict[str, Any]] = field(default_factory=list)
    artifacts: list[dict[str, Any]] = field(default_factory=list)


class RunStore:
    """In-memory run store (MVP). Replace with Redis/Postgres for production."""

    def __init__(self) -> None:
        self._runs: dict[str, StoredRun] = {}

    def put(self, r: StoredRun) -> None:
        self._runs[r.run_id] = r

    def get(self, run_id: str) -> StoredRun | None:
        return self._runs.get(run_id)

    def update_state(self, run_id: str, state: str) -> None:
        r = self._runs.get(run_id)
        if r:
            r.state = state
