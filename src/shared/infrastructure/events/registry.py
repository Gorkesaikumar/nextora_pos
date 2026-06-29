"""Event Registry.

Maps DomainEvent names to handler functions.
Handlers should typically be Celery tasks to ensure they are processed asynchronously.
"""
from typing import Callable

_REGISTRY: dict[str, list[Callable]] = {}


def register_handler(event_name: str) -> Callable:
    """Decorator to register a function as an event handler."""
    def decorator(func: Callable) -> Callable:
        if event_name not in _REGISTRY:
            _REGISTRY[event_name] = []
        _REGISTRY[event_name].append(func)
        return func
    return decorator


def get_handlers(event_name: str) -> list[Callable]:
    """Retrieve all handlers registered for a given event name."""
    return _REGISTRY.get(event_name, [])
