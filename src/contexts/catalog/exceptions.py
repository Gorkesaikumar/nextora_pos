"""Catalog error hierarchy."""


class CatalogError(Exception):
    pass


class ProductNotFound(CatalogError):
    pass


class CategoryNotFound(CatalogError):
    pass


class CategoryCycle(CatalogError):
    """Setting this parent would create a cycle in the category tree."""


class ValidationError(CatalogError):
    """One or more inputs failed validation before any write was attempted.

    Carries a mapping of ``field -> message`` so the API layer can surface
    structured, per-field errors. ``__field__`` holds non-field (object-level)
    problems such as cross-field rules.
    """

    def __init__(self, errors: dict[str, str]):
        self.errors = errors
        super().__init__("; ".join(f"{k}: {v}" for k, v in errors.items()))


class DuplicateSku(ValidationError):
    """The SKU is already used by a live product/variant for this tenant."""

    def __init__(self, sku: str):
        super().__init__({"sku": f"SKU '{sku}' already exists."})


class DuplicateBarcode(ValidationError):
    """The barcode is already used by a live product/variant for this tenant."""

    def __init__(self, barcode: str):
        super().__init__({"barcode": f"Barcode '{barcode}' already exists."})


class ImportError_(CatalogError):
    """Raised for fatal import problems (e.g. malformed header)."""
