# Integrating matrix-hive-driver with Matrix Architect

This guide explains how to wire matrix-hive-driver into Matrix Architect's
execution pipeline so Architect can delegate durable workflow execution to Hive.

## Overview

Matrix Architect already has a pluggable adapter pattern for deployment targets
(`DeploymentAdapter` in `deployment/base.py`). The same approach extends to
execution drivers. The integration consists of:

1. **Add matrix-hive-driver as a service** in Architect's Docker Compose
2. **Register a client adapter** inside Architect that calls the driver's HTTP API
3. **Route jobs** to the driver based on job configuration
4. **Point the driver's Tool Proxy** back to Architect's controlled gateway

```
┌───────────────────────────────────────────────────────────────────────┐
│                         Matrix Architect                              │
│                                                                       │
│  ┌──────────┐    ┌──────────┐    ┌───────────────────────────────┐   │
│  │ API      │───►│ Celery   │───►│ execute_job_task              │   │
│  │ :8080    │    │ Worker   │    │                               │   │
│  └──────────┘    └──────────┘    │  if driver == "hive":         │   │
│                                  │    POST matrix-hive-driver    │   │
│                                  │         :7000/runs            │   │
│                                  │  else:                        │   │
│                                  │    run local executor         │   │
│                                  └──────────┬────────────────────┘   │
│                                             │                        │
└─────────────────────────────────────────────┼────────────────────────┘
                                              │
                          ┌───────────────────▼───────────────────┐
                          │       matrix-hive-driver :7000        │
                          │                                       │
                          │  1. Validate PlanIR                   │
                          │  2. Enforce PolicyGrant                │
                          │  3. Enforce BudgetGrant                │
                          │  4. Compile PlanIR → Hive-Graph        │
                          │  5. Submit to Hive Runtime             │
                          │                                       │
                          │  Tool calls ──► Tool Proxy ──►        │
                          │       Architect :9000/tool-proxy       │
                          └───────────────────┬───────────────────┘
                                              │
                          ┌───────────────────▼───────────────────┐
                          │         Hive Runtime :8080             │
                          │   (durable workflow execution engine)  │
                          └───────────────────────────────────────┘
```

---

## Step 1: Add the Driver Service to Docker Compose

In Matrix Architect's `docker-compose.yml`, add the driver as a new service:

```yaml
services:
  # ... existing services (redis, postgres, api, worker, beat, frontend) ...

  matrix-hive-driver:
    image: ghcr.io/agent-matrix/matrix-hive-driver:latest
    # Or build from source:
    # build:
    #   context: ../matrix-hive-driver
    #   dockerfile: docker/Dockerfile
    ports:
      - "7000:7000"
    environment:
      - DRIVER_HOST=0.0.0.0
      - DRIVER_PORT=7000
      - HIVE_ENDPOINT=http://hive-runtime:8080
      - TOOL_PROXY_ENDPOINT=http://api:8080/tool-proxy
      - EVIDENCE_SINK=local
      - LOG_LEVEL=info
    depends_on:
      - hive-runtime

  hive-runtime:
    image: ghcr.io/agent-matrix/hive-runtime:latest
    ports:
      - "8081:8080"
    environment:
      - HIVE_LOG_LEVEL=info
```

---

## Step 2: Create a Driver Client in Architect

Add a thin HTTP client inside Matrix Architect that calls the driver's REST API.

### File: `matrix_architect/integrations/hive_driver_client.py`

```python
"""Client for matrix-hive-driver service."""
from __future__ import annotations

import os
from typing import Any

import httpx

DRIVER_URL = os.getenv("HIVE_DRIVER_URL", "http://matrix-hive-driver:7000")


class HiveDriverClient:
    """Calls matrix-hive-driver HTTP endpoints."""

    def __init__(self, base_url: str = DRIVER_URL) -> None:
        self.base_url = base_url.rstrip("/")

    async def submit_run(self, payload: dict[str, Any]) -> dict[str, Any]:
        """POST /runs — submit a PlanIR + grants for execution."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(f"{self.base_url}/runs", json=payload)
            r.raise_for_status()
            return r.json()

    async def get_status(self, run_id: str) -> dict[str, Any]:
        """GET /runs/{run_id} — poll execution status."""
        async with httpx.AsyncClient(timeout=20.0) as client:
            r = await client.get(f"{self.base_url}/runs/{run_id}")
            r.raise_for_status()
            return r.json()

    async def get_events(self, run_id: str) -> list[dict[str, Any]]:
        """GET /runs/{run_id}/events — retrieve execution events."""
        async with httpx.AsyncClient(timeout=20.0) as client:
            r = await client.get(f"{self.base_url}/runs/{run_id}/events")
            r.raise_for_status()
            return r.json()

    async def get_artifacts(self, run_id: str) -> list[dict[str, Any]]:
        """GET /runs/{run_id}/artifacts — retrieve evidence bundles."""
        async with httpx.AsyncClient(timeout=20.0) as client:
            r = await client.get(f"{self.base_url}/runs/{run_id}/artifacts")
            r.raise_for_status()
            return r.json()

    async def cancel(self, run_id: str) -> dict[str, Any]:
        """POST /runs/{run_id}/cancel — cancel a running workflow."""
        async with httpx.AsyncClient(timeout=20.0) as client:
            r = await client.post(f"{self.base_url}/runs/{run_id}/cancel")
            r.raise_for_status()
            return r.json()

    async def health(self) -> bool:
        """GET /health — check if the driver is up."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(f"{self.base_url}/health")
                return r.status_code == 200
        except Exception:
            return False
```

---

## Step 3: Convert Architect's Plan to PlanIR

Matrix Architect uses its own `Plan` / `Step` / `FileOp` models. The driver
expects **PlanIR** format. Add a converter:

### File: `matrix_architect/integrations/plan_to_planir.py`

```python
"""Convert Matrix Architect Plan to PlanIR for the Hive driver."""
from __future__ import annotations

from typing import Any


def plan_to_planir(plan: dict[str, Any], job_id: str) -> dict[str, Any]:
    """Convert an Architect Plan dict to PlanIR format.

    Architect Plan:
        {"goal": str, "summary": str, "steps": [{"id", "title", "ops": [FileOp], "verify": [str]}]}

    PlanIR:
        {"plan_id": str, "goal": str, "nodes": [{"id", "type", "inputs", "depends_on", ...}]}
    """
    nodes: list[dict[str, Any]] = []
    prev_id: str | None = None

    for step in plan.get("steps", []):
        step_id = str(step.get("id", f"step-{len(nodes)}"))

        # File operations → PATCH node
        if step.get("ops"):
            patch_id = f"{step_id}-patch"
            nodes.append({
                "id": patch_id,
                "type": "PATCH",
                "depends_on": [prev_id] if prev_id else [],
                "inputs": {
                    "ops": step["ops"],
                    "title": step.get("title", ""),
                },
                "required_capabilities": ["fs.apply_patch"],
                "risk": "medium",
            })
            prev_id = patch_id

        # Verify commands → TEST node
        if step.get("verify"):
            test_id = f"{step_id}-test"
            nodes.append({
                "id": test_id,
                "type": "TEST",
                "depends_on": [prev_id] if prev_id else [],
                "inputs": {
                    "commands": step["verify"],
                },
                "required_capabilities": ["verify.run"],
                "risk": "low",
            })
            prev_id = test_id

    return {
        "plan_id": job_id,
        "version": "1.0",
        "goal": plan.get("goal", ""),
        "nodes": nodes,
    }
```

---

## Step 4: Wire into the Celery Execution Task

In Matrix Architect's `matrix_architect/queue/tasks.py`, add a branch that
dispatches to the Hive driver when the job requests it:

```python
# In execute_job_task, after planning stage:

from matrix_architect.integrations.hive_driver_client import HiveDriverClient
from matrix_architect.integrations.plan_to_planir import plan_to_planir

async def _execute_via_hive_driver(job: Job) -> dict:
    """Delegate execution to matrix-hive-driver."""
    client = HiveDriverClient()

    # Convert Architect Plan → PlanIR
    plan_ir = plan_to_planir(job.plan.model_dump(), job.id)

    # Build policy + budget grants from job constraints
    policy_grant = {
        "grant_id": f"pg-{job.id}",
        "allowed_capabilities": [
            "fs.apply_patch", "verify.run", "cmd.exec", "deploy.run"
        ],
        "forbidden_capabilities": [],
        "allowed_targets": {},
        "approval_requirements": {},
        "issued_at": job.created_at.isoformat() if job.created_at else "",
        "expires_at": "",
    }

    budget_grant = {
        "grant_id": f"bg-{job.id}",
        "max_mxu": job.constraints.max_duration or 3600.0,
        "max_tokens": None,
        "max_tool_calls": None,
        "hard_stop": True,
        "issued_at": job.created_at.isoformat() if job.created_at else "",
        "expires_at": "",
    }

    payload = {
        "plan_ir": plan_ir,
        "policy_grant": policy_grant,
        "budget_grant": budget_grant,
        "workspace": {"repo": job.repo.model_dump()},
        "trace": {"matrix_run_id": job.id, "job_id": job.id},
        "tenant": {},
    }

    # Submit to driver
    result = await client.submit_run(payload)
    run_id = result["run_id"]

    # Poll until complete (or use webhook callback in production)
    import asyncio
    while True:
        status = await client.get_status(run_id)
        state = status.get("state", "unknown")

        if state in ("succeeded", "completed"):
            # Collect evidence
            artifacts = await client.get_artifacts(run_id)
            events = await client.get_events(run_id)
            return {"ok": True, "artifacts": artifacts, "events": events}

        if state in ("failed", "error", "cancelled"):
            return {
                "ok": False,
                "error": status.get("error"),
                "events": await client.get_events(run_id),
            }

        await asyncio.sleep(5)  # Poll interval
```

Then in `execute_job_task`, add the dispatch:

```python
# Existing execute_job_task in tasks.py:

@celery_app.task(bind=True, base=CallbackTask, ...)
def execute_job_task(self, job_id: str):
    job = job_store.get(job_id)
    # ...existing planning logic...

    # === NEW: Check if job should use Hive driver ===
    execution_driver = getattr(job, "execution_driver", None)
    if execution_driver == "hive":
        import asyncio
        result = asyncio.run(_execute_via_hive_driver(job))
        if result["ok"]:
            job.status = JobStatus.succeeded
        else:
            job.status = JobStatus.failed
            job.error = str(result.get("error", "Hive driver execution failed"))
        job_store.update(job)
        return
    # === END NEW ===

    # ...existing local execution logic...
```

---

## Step 5: Extend the API to Accept a Driver Parameter

In `matrix_architect/api/routes_execute.py`, add `execution_driver` to the request:

```python
class ExecuteRequest(BaseModel):
    repo: RepoSpec
    plan: Plan
    verify_commands: list[str] = []
    matrix_ai_url: str | None = None
    execution_driver: str | None = None  # "hive" | None (default: local)
```

Store it on the Job before dispatching:

```python
@router.post("/execute")
async def execute(req: ExecuteRequest):
    job = Job(id=str(uuid4()), repo=req.repo, goal=req.plan.goal, plan=req.plan)
    if req.execution_driver:
        job.execution_driver = req.execution_driver  # Add field to Job model
    # ...rest of handler...
```

---

## Step 6: Environment Variables for Architect

Add to Matrix Architect's `.env` or `docker-compose.yml`:

```bash
# matrix-hive-driver endpoint
HIVE_DRIVER_URL=http://matrix-hive-driver:7000
```

---

## Step 7: Tool Proxy Endpoint (Architect Side)

The driver sends all effectful tool calls through `TOOL_PROXY_ENDPOINT`.
You need to expose this on Architect. A minimal implementation:

### File: `matrix_architect/api/routes_tool_proxy.py`

```python
"""Tool Proxy — controlled gateway for driver tool execution."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

ALLOWED_TOOLS = {"cmd.exec", "fs.apply_patch", "verify.run", "deploy.run", "repair.run"}


class ToolRequest(BaseModel):
    tool: str
    args: dict
    context: dict


@router.post("/tool-proxy")
async def tool_proxy(req: ToolRequest):
    if req.tool not in ALLOWED_TOOLS:
        raise HTTPException(status_code=403, detail=f"Tool not allowed: {req.tool}")

    # Dispatch to appropriate handler based on tool name
    # This is where Guardian policy checks happen in production
    # For now, delegate to existing Architect tooling

    return {"ok": True, "tool": req.tool, "result": {}}
```

Register in `app.py`:

```python
from matrix_architect.api.routes_tool_proxy import router as tool_proxy_router
app.include_router(tool_proxy_router)
```

---

## Complete Request/Response Examples

### Submit a Run

```bash
curl -X POST http://localhost:7000/runs \
  -H "Content-Type: application/json" \
  -d '{
    "plan_ir": {
      "plan_id": "job-abc123",
      "version": "1.0",
      "goal": "Fix auth vulnerability and deploy to staging",
      "nodes": [
        {
          "id": "patch-auth",
          "type": "PATCH",
          "inputs": {"ops": [{"op": "update", "path": "src/auth.py", "content": "..."}]},
          "required_capabilities": ["fs.apply_patch"],
          "depends_on": []
        },
        {
          "id": "run-tests",
          "type": "TEST",
          "inputs": {"commands": ["pytest -q"]},
          "required_capabilities": ["verify.run"],
          "depends_on": ["patch-auth"]
        },
        {
          "id": "deploy-staging",
          "type": "DEPLOY",
          "inputs": {"target": "staging"},
          "required_capabilities": ["deploy.run"],
          "depends_on": ["run-tests"],
          "requires_approval": true
        }
      ]
    },
    "policy_grant": {
      "grant_id": "pg-001",
      "allowed_capabilities": ["fs.apply_patch", "verify.run", "deploy.run"],
      "forbidden_capabilities": [],
      "allowed_targets": {},
      "approval_requirements": {}
    },
    "budget_grant": {
      "grant_id": "bg-001",
      "max_mxu": 100.0,
      "hard_stop": true
    },
    "workspace": {"repo": {"kind": "github", "url": "https://github.com/org/repo"}},
    "trace": {"matrix_run_id": "job-abc123"},
    "tenant": {"org": "agent-matrix"}
  }'
```

**Response:**
```json
{
  "run_id": "hive-run-xyz789",
  "trace": {"matrix_run_id": "job-abc123"}
}
```

### Poll Status

```bash
curl http://localhost:7000/runs/hive-run-xyz789
```

**Response:**
```json
{
  "run_id": "hive-run-xyz789",
  "state": "running",
  "current_node": "run-tests",
  "progress": 0.66,
  "budget_spent_mxu": 12.5,
  "started_at": "2025-01-15T10:00:00Z",
  "updated_at": "2025-01-15T10:02:30Z"
}
```

### Get Artifacts

```bash
curl http://localhost:7000/runs/hive-run-xyz789/artifacts
```

**Response:**
```json
[
  {
    "type": "evidence-bundle",
    "uri": "file:///data/artifacts/hive-run-xyz789/evidence-bundle.json",
    "sha256": "a1b2c3d4...",
    "created_at": "2025-01-15T10:05:00Z",
    "metadata": {"sink": "local"}
  }
]
```

---

## Architecture Decision Records

### Why HTTP Service (not Python library)?

| Approach | Pros | Cons |
|----------|------|------|
| **HTTP service** (chosen) | Independent deploy cycle, language-agnostic, clear trust boundary, can run on different host | Network overhead, one more container |
| Python library | No network hop, simpler dev setup | Tight coupling, shared process, harder to upgrade independently |

The HTTP boundary enforces the trust model: Architect cannot bypass the driver's
policy/budget enforcement because it only has network access, not process access.

### Why PlanIR (not Architect's Plan directly)?

Architect's `Plan` model contains implementation details (FileOp content, repo
credentials) that should not leak into the workflow engine. PlanIR is a clean
intermediate representation that:

- Maps 1:1 to Hive graph nodes
- Contains only execution intent, not data
- Can be validated independently
- Keeps Hive-specific concepts out of Architect
