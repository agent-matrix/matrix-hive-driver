from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class DriverCapabilities:
    name: str = "hive"
    supports_durable_runs: bool = True
    supports_retries: bool = True
    supports_branching: bool = True
    supports_hitl_gates: bool = True
    supports_rollback: bool = False


@dataclass(frozen=True)
class PolicyGrant:
    grant_id: str
    allowed_capabilities: list[str]
    forbidden_capabilities: list[str]
    allowed_targets: dict[str, Any]
    approval_requirements: dict[str, Any]
    issued_at: str
    expires_at: str


@dataclass(frozen=True)
class BudgetGrant:
    grant_id: str
    max_mxu: float
    max_tokens: int | None
    max_tool_calls: int | None
    hard_stop: bool
    issued_at: str
    expires_at: str


@dataclass(frozen=True)
class RunRequest:
    plan_ir: dict[str, Any]
    policy_grant: PolicyGrant
    budget_grant: BudgetGrant
    workspace: dict[str, Any]
    trace: dict[str, str]
    tenant: dict[str, str]


@dataclass(frozen=True)
class RunStatus:
    run_id: str
    state: str
    current_node: str | None
    progress: float | None
    budget_spent_mxu: float
    token_spent: int | None
    tool_calls: int | None
    started_at: str | None
    updated_at: str | None
    error: dict[str, Any] | None


@dataclass(frozen=True)
class Artifact:
    type: str
    uri: str
    sha256: str
    created_at: str
    metadata: dict[str, Any]


@dataclass(frozen=True)
class DriverEvent:
    ts: str
    level: str
    kind: str
    data: dict[str, Any]


class ExecutionDriver(Protocol):
    def capabilities(self) -> DriverCapabilities: ...

    def submit(self, req: RunRequest) -> str: ...

    def status(self, run_id: str) -> RunStatus: ...

    def stream_events(self, run_id: str) -> Iterable[DriverEvent]: ...

    def artifacts(self, run_id: str) -> list[Artifact]: ...

    def cancel(self, run_id: str) -> None: ...

    def rollback(self, run_id: str) -> None: ...
