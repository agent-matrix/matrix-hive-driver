import pytest

from matrix_hive_driver.driver.errors import PolicyViolation
from matrix_hive_driver.driver.interfaces import PolicyGrant
from matrix_hive_driver.enforcement.policy_enforcer import (
    assert_policy_allowed,
    inject_approval_gates,
)


def _grant(**kwargs):
    defaults = {
        "grant_id": "g1",
        "allowed_capabilities": [],
        "forbidden_capabilities": [],
        "allowed_targets": {},
        "approval_requirements": {},
        "issued_at": "",
        "expires_at": "",
    }
    defaults.update(kwargs)
    return PolicyGrant(**defaults)


def test_policy_allows():
    plan = {"nodes": [{"id": "n1", "type": "CMD", "required_capabilities": ["cmd.exec"]}]}
    grant = _grant(allowed_capabilities=["cmd.exec"])
    assert_policy_allowed(plan, grant)


def test_policy_denies_not_granted():
    plan = {"nodes": [{"id": "n1", "type": "CMD", "required_capabilities": ["cmd.exec"]}]}
    grant = _grant(allowed_capabilities=[])
    with pytest.raises(PolicyViolation, match="not granted"):
        assert_policy_allowed(plan, grant)


def test_policy_denies_forbidden():
    plan = {"nodes": [{"id": "n1", "type": "CMD", "required_capabilities": ["cmd.exec"]}]}
    grant = _grant(allowed_capabilities=["cmd.exec"], forbidden_capabilities=["cmd.exec"])
    with pytest.raises(PolicyViolation, match="forbidden"):
        assert_policy_allowed(plan, grant)


def test_inject_approval_gates():
    plan = {
        "nodes": [
            {"id": "n1", "type": "CMD", "requires_approval": True},
            {"id": "n2", "type": "CMD"},
        ]
    }
    grant = _grant()
    result = inject_approval_gates(plan, grant)
    node_ids = [n["id"] for n in result["nodes"]]
    assert "n1__approval" in node_ids
    assert len(result["nodes"]) == 3  # n1, n1__approval, n2


def test_inject_no_gates_when_not_required():
    plan = {"nodes": [{"id": "n1", "type": "CMD"}]}
    grant = _grant()
    result = inject_approval_gates(plan, grant)
    assert len(result["nodes"]) == 1
