"""Query filtering, searching, and ordering utilities for the Nextora POS API."""
from rest_framework.filters import BaseFilterBackend
from rest_framework.filters import OrderingFilter as DRFOrderingFilter
from rest_framework.filters import SearchFilter as DRFSearchFilter


class SimpleFilterBackend(BaseFilterBackend):
    """Lightweight, dependency-free filter backend.

    Filters querysets based on matching URL query parameters and fields specified
    in `filterset_fields` on the View.
    """

    def filter_queryset(self, request, queryset, view):
        filter_fields = getattr(view, "filterset_fields", None)
        if not filter_fields:
            return queryset

        filters = {}
        for field in filter_fields:
            val = request.query_params.get(field)
            if val is not None and val != "":
                # Format checks for boolean parameter resolution
                if val.lower() in ("true", "1"):
                    filters[field] = True
                elif val.lower() in ("false", "0"):
                    filters[field] = False
                else:
                    filters[field] = val

        if filters:
            return queryset.filter(**filters)
        return queryset


# Expose DRF standard filters under our unified namespace
SearchFilter = DRFSearchFilter
OrderingFilter = DRFOrderingFilter
