"""Request correlation middleware.

Assigns a request_id to every request (honouring an upstream X-Request-ID from
Nginx if present) and binds it to the logging context for the lifetime of the
request. The id is echoed on the response so clients and edge logs line up.
"""
import uuid
from collections.abc import Callable

from django.http import HttpRequest, HttpResponse

from .context import request_id_var, set_request_id

REQUEST_ID_HEADER = "HTTP_X_REQUEST_ID"
RESPONSE_HEADER = "X-Request-ID"


class RequestIDMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        request_id = request.META.get(REQUEST_ID_HEADER) or uuid.uuid4().hex
        token = request_id_var.set(request_id)
        request.request_id = request_id  # type: ignore[attr-defined]
        try:
            response = self.get_response(request)
        finally:
            request_id_var.reset(token)
        response[RESPONSE_HEADER] = request_id
        return response
