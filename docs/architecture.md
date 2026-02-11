# matrix-hive-driver architecture

## Role

An execution driver service for Agent-Matrix that compiles PlanIR to durable
workflows executed by Hive Runtime.

## Trust boundaries

- **Guardian** (policy grants) is enforced before execution.
- **Treasury** (budget grants) is enforced before and during execution.
- **Architect** remains the authority; Hive provides workflow mechanics.
- All effectful operations must go through a controlled **Tool Proxy**.

## Execution Flow

```
Matrix Architect
    │
    ▼
POST /runs  ──────────────────────────────────────────────┐
    │                                                      │
    ▼                                                      │
┌─────────────────────┐                                    │
│ 1. Validate PlanIR  │ (schema, node types, deps)         │
│ 2. Enforce Policy   │ (capabilities, forbidden ops)      │
│ 3. Inject Approvals │ (where required by PolicyGrant)    │
│ 4. Compile to Hive  │ (PlanIR → Hive-Graph)              │
│ 5. Init BudgetMeter │ (track spend during execution)     │
│ 6. Submit to Hive   │ ────────► Hive Runtime             │
└─────────────────────┘           (durable workflow engine) │
    │                                    │                  │
    ▼                                    ▼                  │
GET /runs/{id}          Hive executes nodes:               │
GET /runs/{id}/events   - tool_proxy → Tool Proxy Client   │
GET /runs/{id}/artifacts- approval_gate → blocks for signal│
POST /runs/{id}/cancel  - decision → branching logic       │
                                                           │
                        Evidence bundle collected ◄─────────┘
                        Artifacts stored (local/hub/s3)
```

## MVP Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/runs` | Submit run with PlanIR + PolicyGrant + BudgetGrant |
| `GET` | `/runs/{id}` | Current run status |
| `GET` | `/runs/{id}/events` | Run event stream |
| `GET` | `/runs/{id}/artifacts` | Evidence bundles + artifacts |
| `POST` | `/runs/{id}/cancel` | Cancel running workflow |
| `POST` | `/runs/{id}/rollback` | Rollback (stubbed for MVP) |

## Key Design Decisions

1. **Hive as a driver, not a replacement** — Architect doesn't become Hive.
   Instead, Architect calls a standard driver interface.

2. **PlanIR as intermediate representation** — Plans compile cleanly into
   Hive graphs without leaking Hive-specific concepts upward.

3. **Controlled tool execution** — All effectful tool calls go through
   the Tool Proxy (Guardian-gated), never directly from Hive.

4. **Separate repo** — Keeps Matrix Architect clean and stable, lets you
   upgrade Hive independently, reduces supply-chain risk.
