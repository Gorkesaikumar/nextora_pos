"""Pagination policies for Nextora POS API."""
from rest_framework.pagination import LimitOffsetPagination


class StandardPagination(LimitOffsetPagination):
    """Enforces standard limit/offset pagination with customizable limits."""

    default_limit = 50
    max_limit = 100
    limit_query_param = "limit"
    offset_query_param = "offset"
