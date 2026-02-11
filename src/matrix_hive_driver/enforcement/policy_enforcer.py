from __future__ import annotations

from typing import Any

from matrix_hive_driver.driver.errors import PolicyViolation
from matrix_hive_driver.driver.interfaces import PolicyGrant


def _node_caps(node: dict[str, Any]) -> list[str]:
    caps = node.get("required_capabilities", [])
    return [c for c in caps if isinstance(c, str)]


def assert_policy_allowed(plan_ir: dict[str, Any], grant: PolicyGrant) -> None:
    """Validate that every node's required capabilities are allowed by the grant."""
    nodes = plan_ir.get("nodes", [])
    if not isinstance(nodes, list):
        raise PolicyViolation("plan_ir.nodes must be a list")

    allowed = set(grant.allowed_capabilities)
    forbidden = set(grant.forbidden_capabilities)

    for node in nodes:
        if not isinstance(node, dict):
            raise PolicyViolation("each node must be an object")
        for cap in _node_caps(node):
            if cap in forbidden:
                raise PolicyViolation(f"Capability forbidden by policy: {cap}")
            if cap not in allowed:
                raise PolicyViolation(f"Capability not granted: {cap}")

    # Target checks placeholder: enforce allowed_targets based on PlanIR conventions.
    # Example: repo/cluster/namespace allowlists can be validated here.
    return


def inject_approval_gates(plan_ir: dict[str, Any], grant: PolicyGrant) -> dict[str, Any]:
    """Insert APPROVAL gate nodes after any node marked requires_approval=True."""
    nodes = plan_ir.get("nodes", [])
    if not isinstance(nodes, list):
        return plan_ir

    new_nodes: list[dict[str, Any]] = []
    for node in nodes:
        new_nodes.append(node)
        if isinstance(node, dict) and node.get("requires_approval") is True:
            node_id = str(node.get("id", "node"))
            gate_id = f"{node_id}__approval"
            new_nodes.append(
                {
                    "id": gate_id,
                    "type": "APPROVAL",
                    "name": f"Approval gate for {node_id}",
                    "depends_on": [node_id],
                    "inputs": {"policy_grant_id": grant.grant_id},
                    "required_capabilities": [],
                    "risk": "low",
                    "timeout_sec": 86400,
                }
            )

    out = dict(plan_ir)
    out["nodes"] = new_nodes
    return out
