"""Application service base.

A service implements ONE use case. Subclasses expose a single ``execute``
method (command in, Result out). The base provides a logger bound to the
concrete service name so every use case gets consistent, structured logging.
"""
import logging
from abc import ABC, abstractmethod
from typing import Any

from .result import Result


class ApplicationService(ABC):
    def __init__(self) -> None:
        self.logger = logging.getLogger(f"nextora.app.{type(self).__name__}")

    @abstractmethod
    def execute(self, *args: Any, **kwargs: Any) -> Result[Any]:
        """Run the use case. One public entrypoint per service."""
        raise NotImplementedError
