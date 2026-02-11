import pytest

from matrix_hive_driver.driver.errors import DriverError
from matrix_hive_driver.mapping.validators import validate_plan_ir


def test_planir_ok():
    validate_plan_ir(
        {
            "plan_id": "p1",
            "nodes": [{"id": "n1", "type": "CMD", "depends_on": [], "inputs": {}}],
        }
    )


def test_planir_missing_nodes():
    with pytest.raises(DriverError):
        validate_plan_ir({"plan_id": "p1", "nodes": "nope"})


def test_planir_missing_id():
    with pytest.raises(DriverError):
        validate_plan_ir({"plan_id": "p1", "nodes": [{"type": "CMD"}]})


def test_planir_missing_type():
    with pytest.raises(DriverError):
        validate_plan_ir({"plan_id": "p1", "nodes": [{"id": "n1"}]})


def test_planir_bad_depends_on():
    with pytest.raises(DriverError):
        validate_plan_ir(
            {
                "plan_id": "p1",
                "nodes": [{"id": "n1", "type": "CMD", "depends_on": "not-a-list"}],
            }
        )


def test_planir_not_dict():
    with pytest.raises(DriverError):
        validate_plan_ir("not a dict")
