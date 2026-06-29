"""Value Object base — immutable, equality by value.

Value objects (Money, TaxRate, Address, Quantity) centralise rules and kill
primitive obsession. They never touch the framework or the database.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class ValueObject:
    """Marker base. Subclass with ``@dataclass(frozen=True)``.

    ``frozen=True`` gives immutability and value-based __eq__/__hash__ for free.
    """
