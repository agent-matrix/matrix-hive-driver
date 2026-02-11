from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PolicyGrantModel(BaseModel):
    grant_id: str
    allowed_capabilities: list[str] = Field(default_factory=list)
    forbidden_capabilities: list[str] = Field(default_factory=list)
    allowed_targets: dict[str, Any] = Field(default_factory=dict)
    approval_requirements: dict[str, Any] = Field(default_factory=dict)
    issued_at: str = ""
    expires_at: str = ""


class BudgetGrantModel(BaseModel):
    grant_id: str
    max_mxu: float = 0.0
    max_tokens: int | None = None
    max_tool_calls: int | None = None
    hard_stop: bool = True
    issued_at: str = ""
    expires_at: str = ""


class RunRequestModel(BaseModel):
    plan_ir: dict[str, Any]
    policy_grant: PolicyGrantModel
    budget_grant: BudgetGrantModel
    workspace: dict[str, Any] = Field(default_factory=dict)
    trace: dict[str, str] = Field(default_factory=dict)
    tenant: dict[str, str] = Field(default_factory=dict)


class RunStatusModel(BaseModel):
    run_id: str
    state: str
    current_node: str | None = None
    progress: float | None = None
    budget_spent_mxu: float = 0.0
    token_spent: int | None = None
    tool_calls: int | None = None
    started_at: str | None = None
    updated_at: str | None = None
    error: dict[str, Any] | None = None


class ArtifactModel(BaseModel):
    type: str
    uri: str
    sha256: str
    created_at: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class DriverEventModel(BaseModel):
    ts: str
    level: str
    kind: str
    data: dict[str, Any] = Field(default_factory=dict)
