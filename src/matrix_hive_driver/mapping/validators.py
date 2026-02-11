from __future__ import annotations

from typing import Any

from matrix_hive_driver.driver.errors import DriverError


def validate_plan_ir(plan_ir: dict[str, Any]) -> None:
    """Validate PlanIR structure before compilation."""
    if not isinstance(plan_ir, dict):
        raise DriverError("plan_ir must be an object")

    nodes = plan_ir.get("nodes")
    if not isinstance(nodes, list):
        raise DriverError("plan_ir.nodes must be a list")

    for node in nodes:
        if not isinstance(node, dict):
            raise DriverError("each node must be an object")
        if "id" not in node or "type" not in node:
            raise DriverError("each node must have id and type")
        if "depends_on" in node and not isinstance(node["depends_on"], list):
            raise DriverError("node.depends_on must be a list")
