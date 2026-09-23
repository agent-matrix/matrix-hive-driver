import pytest

from matrix_hive_driver.driver.errors import DriverError, PolicyViolation
from matrix_hive_driver.driver.interfaces import PolicyGrant
from matrix_hive_driver.mapping.work_graph_to_hive import (
    assert_work_graph_policy,
    compile_work_graph_to_hive_graph,
    validate_work_graph,
)


def graph():
    return {
        "schema_version": "1.0",
        "graph_id": "g1",
        "plan_id": "p1",
        "goal": "repair",
        "nodes": [
            {
                "node_id": "s1",
                "capability": "fs.apply_patch",
                "objective": "patch",
                "depends_on": [],
                "proof": {"success_criteria": ["tests pass"], "verifiers": ["pytest"]},
                "risk": "medium",
            }
        ],
    }


def grant(caps):
    return PolicyGrant(
        grant_id="pg",
        allowed_capabilities=caps,
        forbidden_capabilities=[],
        allowed_targets={},
        approval_requirements={},
        issued_at="2026-01-01T00:00:00Z",
        expires_at="2027-01-01T00:00:00Z",
    )


def test_work_graph_compiles_verbatim_capability():
    validate_work_graph(graph())
    hive = compile_work_graph_to_hive_graph(graph())
    assert hive["nodes"][0]["tool"] == "fs.apply_patch"


def test_ungranted_capability_is_blocked():
    with pytest.raises(PolicyViolation):
        assert_work_graph_policy(graph(), grant([]))


def test_missing_proof_is_blocked():
    g = graph()
    g["nodes"][0]["proof"] = {}
    with pytest.raises(DriverError):
        validate_work_graph(g)
