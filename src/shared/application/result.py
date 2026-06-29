"""Result object — explicit success/failure for the service layer.

Services return Result rather than raising for *expected* business outcomes
(e.g. "insufficient stock"). Exceptions are reserved for truly exceptional
conditions. This makes API error mapping predictable and keeps control flow
readable (no exceptions-as-goto).
"""
from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class Result(Generic[T]):
    success: bool
    value: T | None = None
    error_code: str | None = None
    error_message: str | None = None

    @classmethod
    def ok(cls, value: T | None = None) -> "Result[T]":
        return cls(success=True, value=value)

    @classmethod
    def fail(cls, code: str, message: str) -> "Result[T]":
        return cls(success=False, error_code=code, error_message=message)

    def __bool__(self) -> bool:
        return self.success
