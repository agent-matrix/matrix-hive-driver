import pytest

from matrix_hive_driver.driver.errors import BudgetExceeded
from matrix_hive_driver.driver.interfaces import BudgetGrant
from matrix_hive_driver.enforcement.budget_meter import BudgetMeter


def _grant(**kwargs):
    defaults = {
        "grant_id": "b1",
        "max_mxu": 100.0,
        "max_tokens": None,
        "max_tool_calls": None,
        "hard_stop": True,
        "issued_at": "",
        "expires_at": "",
    }
    defaults.update(kwargs)
    return BudgetGrant(**defaults)


def test_budget_within_limits():
    meter = BudgetMeter(_grant())
    meter.charge_mxu(50.0)
    assert meter.snapshot().spent_mxu == 50.0


def test_budget_mxu_exceeded():
    meter = BudgetMeter(_grant(max_mxu=10.0))
    with pytest.raises(BudgetExceeded, match="MXU"):
        meter.charge_mxu(11.0)


def test_budget_tool_calls_exceeded():
    meter = BudgetMeter(_grant(max_tool_calls=5))
    for _ in range(5):
        meter.charge_tool_call()
    with pytest.raises(BudgetExceeded, match="Tool call"):
        meter.charge_tool_call()


def test_budget_tokens_exceeded():
    meter = BudgetMeter(_grant(max_tokens=1000))
    meter.charge_tokens(999)
    with pytest.raises(BudgetExceeded, match="Token"):
        meter.charge_tokens(2)
