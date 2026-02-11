from __future__ import annotations

from dataclasses import dataclass

from matrix_hive_driver.driver.errors import BudgetExceeded
from matrix_hive_driver.driver.interfaces import BudgetGrant


@dataclass
class BudgetState:
    spent_mxu: float = 0.0
    tool_calls: int = 0
    tokens: int = 0


class BudgetMeter:
    def __init__(self, grant: BudgetGrant) -> None:
        self.grant = grant
        self.state = BudgetState()

    def charge_mxu(self, mxu: float) -> None:
        self.state.spent_mxu += max(0.0, mxu)
        self._check()

    def charge_tool_call(self, n: int = 1) -> None:
        self.state.tool_calls += max(0, n)
        self._check()

    def charge_tokens(self, n: int) -> None:
        self.state.tokens += max(0, n)
        self._check()

    def _check(self) -> None:
        if self.state.spent_mxu > self.grant.max_mxu:
            raise BudgetExceeded("MXU budget exceeded")
        if (
            self.grant.max_tool_calls is not None
            and self.state.tool_calls > self.grant.max_tool_calls
        ):
            raise BudgetExceeded("Tool call budget exceeded")
        if self.grant.max_tokens is not None and self.state.tokens > self.grant.max_tokens:
            raise BudgetExceeded("Token budget exceeded")

    def snapshot(self) -> BudgetState:
        return self.state
