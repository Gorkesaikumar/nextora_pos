"""Canonical usage/limit metric names.

These are the keys shared by Plan limit columns, UsageCounter rows, and usage
providers. Other contexts import these constants rather than free-typing strings.
"""

BRANCHES = "branches"
EMPLOYEES = "employees"
INVOICES = "invoices"          # per billing month
STORAGE_MB = "storage_mb"

# Metrics tracked per calendar month (vs absolute counts).
PERIODIC = frozenset({INVOICES})

ALL = (BRANCHES, EMPLOYEES, INVOICES, STORAGE_MB)
