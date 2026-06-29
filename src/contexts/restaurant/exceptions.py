"""Custom exceptions for the Restaurant context."""


class RestaurantNotFound(Exception):
    pass


class BranchNotFound(Exception):
    pass


class ActivationPrerequisiteFailed(Exception):
    """Raised when activation guards are not met."""
    pass


class InvalidStatusTransition(Exception):
    """Raised when a state-machine transition is invalid."""
    pass


class InvalidGSTIN(Exception):
    """Raised when GSTIN validation fails."""
    pass


class TableMergeError(Exception):
    """Raised when table merge/split rules are violated."""
    pass


class OccupiedTableDeletionError(Exception):
    """Raised when attempting to delete a floor/table that has active orders."""
    pass
