from __future__ import annotations

from typing import Any


def tool_proxy_node(
    node_id: str, tool: str, args: dict[str, Any], depends_on: list[str]
) -> dict[str, Any]:
    return {
        "id": node_id,
        "kind": "tool_proxy",
        "tool": tool,
        "args": args,
        "depends_on": depends_on,
    }


def approval_gate_node(node_id: str, depends_on: list[str], policy_grant_id: str) -> dict[str, Any]:
    return {
        "id": node_id,
        "kind": "approval_gate",
        "depends_on": depends_on,
        "policy_grant_id": policy_grant_id,
    }


def decision_node(node_id: str, depends_on: list[str], inputs: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": node_id,
        "kind": "decision",
        "depends_on": depends_on,
        "inputs": inputs,
    }
