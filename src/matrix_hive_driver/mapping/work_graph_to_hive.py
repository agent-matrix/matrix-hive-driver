"""Architect WorkGraph v1 -> Hive graph adapter.

No planning occurs here. The capability selected by the approved plan is carried
verbatim to the controlled Tool Proxy.
"""

from __future__ import annotations

from typing import Any

from matrix_hive_driver.driver.errors import DriverError, PolicyViolation
from matrix_hive_driver.mapping.node_templates import tool_proxy_node


def validate_work_graph(graph: dict[str, Any]) -> None:
    if not isinstance(graph, dict):
        raise DriverError("work_graph must be an object")
    if graph.get("schema_version") != "1.0":
        raise DriverError("work_graph.schema_version must be 1.0")
    if not graph.get("graph_id") or not graph.get("plan_id"):
        raise DriverError("work_graph requires graph_id and plan_id")
    nodes = graph.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        raise DriverError("work_graph.nodes must be a non-empty list")
    ids: set[str] = set()
    for node in nodes:
        if not isinstance(node, dict):
            raise DriverError("each work_graph node must be an object")
        nid = str(node.get("node_id") or "")
        cap = str(node.get("capability") or "")
        if not nid or nid in ids:
            raise DriverError(f"invalid or duplicate node_id: {nid!r}")
        if not cap:
            raise DriverError(f"node {nid} requires capability")
        proof = node.get("proof") or {}
        if not proof.get("success_criteria") or not proof.get("verifiers"):
            raise DriverError(f"node {nid} is missing proof obligations")
        ids.add(nid)
    for node in nodes:
        unknown = set(node.get("depends_on") or []) - ids
        if unknown:
            raise DriverError(f"node {node['node_id']} depends on unknown nodes: {sorted(unknown)}")


def assert_work_graph_policy(graph: dict[str, Any], grant) -> None:
    allowed = set(grant.allowed_capabilities)
    forbidden = set(grant.forbidden_capabilities)
    for node in graph.get("nodes") or []:
        cap = str(node.get("capability") or "")
        if cap in forbidden:
            raise PolicyViolation(f"Capability forbidden by policy: {cap}")
        if cap not in allowed:
            raise PolicyViolation(f"Capability not granted: {cap}")


def compile_work_graph_to_hive_graph(graph: dict[str, Any]) -> dict[str, Any]:
    nodes_out = []
    for node in graph["nodes"]:
        inputs = {
            "objective": node.get("objective", ""),
            "inputs": node.get("inputs") or [],
            "preconditions": node.get("preconditions") or [],
            "expected_outputs": node.get("expected_outputs") or [],
            "proof": node.get("proof") or {},
            "rollback": node.get("rollback"),
            "risk": node.get("risk", "medium"),
        }
        nodes_out.append(
            tool_proxy_node(
                str(node["node_id"]),
                str(node["capability"]),
                inputs,
                list(node.get("depends_on") or []),
            )
        )
    return {
        "plan_id": graph["plan_id"],
        "graph_id": graph["graph_id"],
        "version": "1.0",
        "goal": graph.get("goal", ""),
        "nodes": nodes_out,
    }
