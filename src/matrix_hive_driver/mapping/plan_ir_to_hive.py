from __future__ import annotations

from typing import Any

from matrix_hive_driver.mapping.node_templates import (
    approval_gate_node,
    decision_node,
    tool_proxy_node,
)


def compile_plan_ir_to_hive_graph(plan_ir: dict[str, Any]) -> dict[str, Any]:
    """Compile PlanIR to a minimal Hive-Graph payload.

    The Hive runtime adapter translates this into real Hive workflow definitions.
    """
    nodes_out: list[dict[str, Any]] = []
    for n in plan_ir.get("nodes", []):
        ntype = str(n.get("type", "")).upper()
        nid = str(n.get("id"))
        deps = n.get("depends_on", []) or []
        inputs = n.get("inputs", {}) or {}

        if ntype == "CMD":
            nodes_out.append(tool_proxy_node(nid, "cmd.exec", inputs, deps))
        elif ntype == "PATCH":
            nodes_out.append(tool_proxy_node(nid, "fs.apply_patch", inputs, deps))
        elif ntype in ("CHECK", "TEST"):
            nodes_out.append(tool_proxy_node(nid, "verify.run", inputs, deps))
        elif ntype == "DEPLOY":
            nodes_out.append(tool_proxy_node(nid, "deploy.run", inputs, deps))
        elif ntype == "REPAIR":
            nodes_out.append(tool_proxy_node(nid, "repair.run", inputs, deps))
        elif ntype == "APPROVAL":
            pgid = str(inputs.get("policy_grant_id", ""))
            nodes_out.append(approval_gate_node(nid, deps, pgid))
        elif ntype == "DECISION":
            nodes_out.append(decision_node(nid, deps, inputs))
        else:
            # Safe default: represent unknown node type as no-op
            nodes_out.append(
                {
                    "id": nid,
                    "kind": "noop",
                    "depends_on": deps,
                    "inputs": inputs,
                    "note": f"Unhandled type: {ntype}",
                }
            )

    return {
        "plan_id": plan_ir.get("plan_id"),
        "version": plan_ir.get("version", "1.0"),
        "goal": plan_ir.get("goal", ""),
        "nodes": nodes_out,
    }
