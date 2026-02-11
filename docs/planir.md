# PlanIR Specification

PlanIR is the intermediate representation used to describe execution plans.
It is compiled into Hive-Graph format before being submitted to Hive Runtime.

## Top-Level Schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `plan_id` | string | yes | Unique plan identifier |
| `version` | string | no | Schema version (default: `1.0`) |
| `goal` | string | no | Human-readable goal description |
| `nodes` | array[Node] | yes | Execution nodes |

## Node Schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | yes | Unique node identifier |
| `type` | enum | yes | Node type (see below) |
| `depends_on` | array[string] | no | IDs of prerequisite nodes |
| `inputs` | object | no | Node-specific input parameters |
| `required_capabilities` | array[string] | no | Capabilities this node needs |
| `risk` | enum | no | Risk level: `low`, `medium`, `high` |
| `retry` | object | no | Retry config: `{max_attempts, backoff_sec}` |
| `requires_approval` | bool | no | Whether this node needs human approval |

## Node Types

| Type | Hive Mapping | Description |
|------|-------------|-------------|
| `CMD` | `tool_proxy(cmd.exec)` | Execute a shell command |
| `PATCH` | `tool_proxy(fs.apply_patch)` | Apply file changes |
| `CHECK` | `tool_proxy(verify.run)` | Run verification checks |
| `TEST` | `tool_proxy(verify.run)` | Run test suite |
| `DEPLOY` | `tool_proxy(deploy.run)` | Deploy to target |
| `REPAIR` | `tool_proxy(repair.run)` | Self-repair on failure |
| `APPROVAL` | `approval_gate` | Block for human approval |
| `DECISION` | `decision` | Branching decision point |

## Example PlanIR

```json
{
  "plan_id": "plan-abc123",
  "version": "1.0",
  "goal": "Apply security patch and deploy to staging",
  "nodes": [
    {
      "id": "patch-vuln",
      "type": "PATCH",
      "inputs": {"diff": "...", "target": "src/auth.py"},
      "required_capabilities": ["fs.apply_patch"],
      "risk": "medium"
    },
    {
      "id": "run-tests",
      "type": "TEST",
      "depends_on": ["patch-vuln"],
      "inputs": {"command": "pytest -q"},
      "required_capabilities": ["verify.run"]
    },
    {
      "id": "approve-deploy",
      "type": "APPROVAL",
      "depends_on": ["run-tests"],
      "requires_approval": true
    },
    {
      "id": "deploy-staging",
      "type": "DEPLOY",
      "depends_on": ["approve-deploy"],
      "inputs": {"target": "staging", "namespace": "app"},
      "required_capabilities": ["deploy.run"],
      "risk": "high"
    }
  ]
}
```
