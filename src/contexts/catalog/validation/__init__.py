"""Input validation for catalog use cases.

Validators enforce business rules **before** any write is attempted and raise
``catalog.exceptions.ValidationError`` (with a ``field -> message`` map) on
failure. They are pure with respect to the database except for uniqueness
checks, which they delegate to a repository. Keeping validation here — rather
than in models, serializers, or views — means every entry point (REST API,
CSV import, admin actions, internal callers) gets the same rules.
"""
from .category_validator import validate_reparent
from .product_validator import (
    validate_combo_item,
    validate_new_product,
    validate_product_changes,
)

__all__ = [
    "validate_combo_item",
    "validate_new_product",
    "validate_product_changes",
    "validate_reparent",
]
