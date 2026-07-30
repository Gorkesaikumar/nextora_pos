"""Global exception handler for the Nextora POS API.

Translates framework and business exceptions into a unified list format.
"""
import logging
from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import exceptions as drf_exceptions
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger("nextora.api.exceptions")


def global_exception_handler(exc, context):
    """Intercepts and standardizes exceptions raised inside DRF views."""
    # Translate core Django exception types to DRF equivalents first
    if isinstance(exc, DjangoValidationError):
        # Django validation errors can have dict or list formats
        message_dict = getattr(exc, "message_dict", None)
        if message_dict:
            exc = drf_exceptions.ValidationError(detail=message_dict)
        else:
            exc = drf_exceptions.ValidationError(detail=exc.messages)
    elif isinstance(exc, DjangoPermissionDenied):
        exc = drf_exceptions.PermissionDenied(detail=str(exc))

    # Also capture key multi-tenancy errors and convert to HTTP forbidden
    from shared.tenancy.exceptions import CrossTenantAccess, TenantNotResolved
    if isinstance(exc, (CrossTenantAccess, TenantNotResolved)):
        exc = drf_exceptions.PermissionDenied(detail=str(exc))

    # Call DRF's default handler to get standard format
    response = exception_handler(exc, context)

    errors = []

    if response is not None:
        # Standardize the response payload
        data = response.data
        if isinstance(data, dict):
            if "detail" in data:
                errors.append({
                    "message": str(data["detail"]),
                    "code": getattr(exc, "default_code", "error"),
                })
            else:
                # Validation error structure (fields mapped to error messages)
                for field, error_list in data.items():
                    if isinstance(error_list, list):
                        for err in error_list:
                            errors.append({
                                "field": field,
                                "message": str(err),
                                "code": "validation_error",
                            })
                    else:
                        errors.append({
                            "field": field,
                            "message": str(error_list),
                            "code": "validation_error",
                        })
        elif isinstance(data, list):
            for err in data:
                errors.append({
                    "message": str(err),
                    "code": "validation_error",
                })
        else:
            errors.append({
                "message": str(data),
                "code": "error",
            })

        response.data = errors
        response.exception = True
    else:
        # Log unhandled exceptions (500s)
        logger.error(
            "Unhandled API Exception",
            exc_info=exc,
            extra={
                "view": str(context.get("view")),
                "request_path": context.get("request").path if context.get("request") else "unknown",
            },
        )

        errors.append({
            "message": "A critical system error occurred. Please contact administrator.",
            "code": "internal_server_error",
        })

        response = Response(
            data=errors,
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
        response.exception = True

    return response
