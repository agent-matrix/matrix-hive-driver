# WorkGraph v1 execution

The v2 Matrix execution chain is:

```
Matrix AI PlanIR v2
  -> Guardian PolicyGrant
  -> Treasury BudgetGrant
  -> Matrix Architect WorkGraph v1
  -> matrix-hive-driver /v2/runs
  -> Hive Runtime
  -> controlled Tool Proxy / MatrixLab
  -> evidence bundle
```

`POST /v2/runs` accepts the WorkGraph **without re-planning**. Every node's
capability is checked against the PolicyGrant and carried verbatim into the
controlled Tool Proxy. Proof obligations and rollback metadata stay attached to
the node inputs so verifiers can evaluate them after execution.

Unknown capabilities are not converted to no-ops; they must still be explicitly
granted and handled by the controlled proxy.
