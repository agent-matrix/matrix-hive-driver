class DriverError(Exception):
    pass


class PolicyViolation(DriverError):
    pass


class BudgetExceeded(DriverError):
    pass


class DriverRuntimeError(DriverError):
    pass
