"""Logging filter that injects request-scoped context onto every record."""
import logging

from .context import get_request_id, get_tenant_id


class ContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()
        record.tenant_id = get_tenant_id()
        return True
