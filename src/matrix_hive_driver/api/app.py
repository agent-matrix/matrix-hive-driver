from __future__ import annotations

import uuid
from dataclasses import asdict

from fastapi import FastAPI, HTTPException

from matrix_hive_driver.api.schemas import (
    ArtifactModel,
    DriverEventModel,
    RunRequestModel,
    RunStatusModel,
)
from matrix_hive_driver.driver.config import settings
from matrix_hive_driver.driver.errors import (
    BudgetExceeded,
    DriverError,
    DriverRuntimeError,
    PolicyViolation,
)
from matrix_hive_driver.driver.hive_driver import HiveDriver
from matrix_hive_driver.driver.interfaces import BudgetGrant, PolicyGrant, RunRequest
from matrix_hive_driver.observability.logging import configure_logging
from matrix_hive_driver.observability.metrics import configure_metrics
from matrix_hive_driver.observability.tracing import configure_tracing

app = FastAPI(title="matrix-hive-driver", version="0.1.0")
driver = HiveDriver()


@app.on_event("startup")
def _startup() -> None:
    configure_logging(settings.log_level)
    configure_tracing()
    configure_metrics()


@app.get("/health")
def health() -> dict:
    return {"ok": True, "service": "matrix-hive-driver"}


@app.post("/runs", response_model=dict)
def create_run(req: RunRequestModel) -> dict:
    try:
        pg = PolicyGrant(**req.policy_grant.model_dump())
        bg = BudgetGrant(**req.budget_grant.model_dump())
        trace = dict(req.trace or {})
        trace.setdefault("matrix_run_id", str(uuid.uuid4()))

        rr = RunRequest(
            plan_ir=req.plan_ir,
            policy_grant=pg,
            budget_grant=bg,
            workspace=req.workspace,
            trace=trace,
            tenant=req.tenant,
        )
        hive_run_id = driver.submit(rr)
        return {"run_id": hive_run_id, "trace": trace}
    except (PolicyViolation, BudgetExceeded) as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except (DriverRuntimeError, DriverError) as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/runs/{run_id}", response_model=RunStatusModel)
def get_status(run_id: str) -> RunStatusModel:
    try:
        s = driver.status(run_id)
        return RunStatusModel(**asdict(s))
    except DriverError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/runs/{run_id}/events", response_model=list[DriverEventModel])
def get_events(run_id: str) -> list[DriverEventModel]:
    try:
        return [DriverEventModel(**asdict(ev)) for ev in driver.stream_events(run_id)]
    except DriverError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/runs/{run_id}/artifacts", response_model=list[ArtifactModel])
def get_artifacts(run_id: str) -> list[ArtifactModel]:
    try:
        arts = driver.artifacts(run_id)
        return [ArtifactModel(**asdict(a)) for a in arts]
    except DriverError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/runs/{run_id}/cancel", response_model=dict)
def cancel(run_id: str) -> dict:
    try:
        driver.cancel(run_id)
        return {"ok": True}
    except DriverError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/runs/{run_id}/rollback", response_model=dict)
def rollback(run_id: str) -> dict:
    try:
        driver.rollback(run_id)
        return {"ok": True}
    except DriverError as e:
        raise HTTPException(status_code=501, detail=str(e)) from e


def main() -> None:
    import uvicorn

    uvicorn.run(
        "matrix_hive_driver.api.app:app",
        host=settings.driver_host,
        port=settings.driver_port,
        reload=False,
    )
