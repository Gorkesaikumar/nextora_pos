"""Input validation for the customer domain.

Validators run before any write and raise ``ValidationError`` (field -> message).
Keeping rules here means every entry point (API, import, internal callers) gets
the same checks.
"""
import re
from typing import Any

from .exceptions import ValidationError

_PHONE_RE = re.compile(r"^\+?[0-9]{7,15}$")
# GSTIN: 2-digit state + 10-char PAN + entity digit + 'Z' + checksum char.
_GSTIN_RE = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")


def validate_customer(data: dict[str, Any], *, partial: bool = False) -> None:
    errors: dict[str, str] = {}

    if "name" in data or not partial:
        if not str(data.get("name") or "").strip():
            errors["name"] = "Name is required."

    phone = data.get("phone")
    if "phone" in data or not partial:
        if not phone:
            errors["phone"] = "Phone is required."
        elif not _PHONE_RE.match(str(phone)):
            errors["phone"] = "Phone must be 7–15 digits (optional leading +)."

    gstin = data.get("gstin")
    if gstin:  # optional, but if present must be a valid GSTIN
        if not _GSTIN_RE.match(str(gstin).upper()):
            errors["gstin"] = "Invalid GSTIN format."
        # A GST customer needs a state for place-of-supply (IGST vs CGST/SGST).
        if not data.get("state_code"):
            errors["state_code"] = "state_code is required for a GST customer."

    if errors:
        raise ValidationError(errors)
