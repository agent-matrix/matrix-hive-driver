from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timezone

import structlog

from matrix_hive_driver.driver.config import settings
from matrix_hive_driver.driver.errors import DriverError
from matrix_hive_driver.driver.interfaces import (
    Artifact,
    DriverCapabilities,
    DriverEvent,
    RunRequest,
    RunStatus,
)
from matrix_hive_driver.enforcement.budget_meter import BudgetMeter
from matrix_hive_driver.enforcement.policy_enforcer import (
    assert_policy_allowed,
    inject_approval_gates,
)
from matrix_hive_driver.enforcement.sandbox import normalize_workspace
from matrix_hive_driver.evidence.collector import build_evidence_bundle
from matrix_hive_driver.mapping.plan_ir_to_hive import compile_plan_ir_to_hive_graph
from matrix_hive_driver.mapping.validators import validate_plan_ir
from matrix_hive_driver.runtime.hive_client import HiveClient
from matrix_hive_driver.storage.local_store import write_bytes

log = structlog.get_logger()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class HiveDriver:
    """ExecutionDriver implementation backed by Hive Runtime.

    Pipeline:
      1. Validate PlanIR
      2. Enforce PolicyGrant (capabilities, forbidden ops)
      3. Normalize workspace/sandbox
      4. Inject approval gates where required
      5. Compile PlanIR → Hive-Graph
      6. Initialize BudgetMeter
      7. Submit to Hive Runtime
    """

    def __init__(self) -> None:
        self.hive = HiveClient()

    def capabilities(self) -> DriverCapabilities:
        return DriverCapabilities()

    def submit(self, req: RunRequest) -> str:
        # 1. Validate PlanIR structure
        validate_plan_ir(req.plan_ir)

        # 2. Enforce policy grant
        assert_policy_allowed(req.plan_ir, req.policy_grant)

        # 3. Normalize sandbox/workspace
        workspace = normalize_workspace(req.workspace)

        # 4. Inject approval gates
        plan2 = inject_approval_gates(req.plan_ir, req.policy_grant)

        # 5. Compile to Hive graph
        graph = compile_plan_ir_to_hive_graph(plan2)

        # 6. Initialize budget meter (MVP: instantiate; integrate charging on tool calls later)
        _ = BudgetMeter(req.budget_grant)

        # 7. Metadata passed to Hive runtime
        metadata = {
            "matrix_run_id": req.trace.get("matrix_run_id", ""),
            "policy_grant_id": req.policy_grant.grant_id,
            "budget_grant_id": req.budget_grant.grant_id,
            "tenant": req.tenant,
            "workspace": workspace,
        }

        hive_run_id = self.hive.start(graph=graph, metadata=metadata)
        log.info(
            "hive_run_started",
            hive_run_id=hive_run_id,
            plan_id=req.plan_ir.get("plan_id"),
        )
        return hive_run_id

    def status(self, run_id: str) -> RunStatus:
        s = self.hive.status(run_id)
        return RunStatus(
            run_id=run_id,
            state=str(s.get("state", "unknown")),
            current_node=s.get("current_node"),
            progress=s.get("progress"),
            budget_spent_mxu=float(s.get("budget_spent_mxu", 0.0)),
            token_spent=s.get("token_spent"),
            tool_calls=s.get("tool_calls"),
            started_at=s.get("started_at"),
            updated_at=s.get("updated_at"),
            error=s.get("error"),
        )

    def stream_events(self, run_id: str) -> Iterable[DriverEvent]:
        evs = self.hive.events(run_id)
        for e in evs:
            yield DriverEvent(
                ts=str(e.get("ts", _now())),
                level=str(e.get("level", "info")),
                kind=str(e.get("kind", "event")),
                data=dict(e),
            )

    def artifacts(self, run_id: str) -> list[Artifact]:
        evs = self.hive.events(run_id)
        bundle, sha = build_evidence_bundle(run_id, evs)
        uri = "local://evidence-bundle"
        if settings.evidence_sink == "local":
            path = write_bytes(f"{run_id}/evidence-bundle.json", bundle.to_bytes())
            uri = f"file://{path}"

        return [
            Artifact(
                type="evidence-bundle",
                uri=uri,
                sha256=sha,
                created_at=bundle.created_at,
                metadata={"sink": settings.evidence_sink},
            )
        ]

    def cancel(self, run_id: str) -> None:
        self.hive.cancel(run_id)

    def rollback(self, run_id: str) -> None:
        raise DriverError("rollback not implemented (MVP)")
