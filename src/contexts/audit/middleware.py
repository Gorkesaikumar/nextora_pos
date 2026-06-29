"""Captures the acting user + client IP into the audit context per request.

Runs after AuthenticationMiddleware (needs request.user) and the tenant
middleware. Always clears in finally so a pooled worker never attributes one
request's actor to the next.
"""
from collections.abc import Callable

from django.http import HttpRequest, HttpResponse
from user_agents import parse

from .context import clear_actor, set_actor


def _client_ip(request: HttpRequest) -> str | None:
    # X-Forwarded-For is set by Nginx; take the first (original client) hop.
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _parse_user_agent(request: HttpRequest) -> tuple[str | None, str | None]:
    ua_string = request.META.get("HTTP_USER_AGENT", "")
    if not ua_string:
        return None, None
    user_agent = parse(ua_string)
    
    device = f"{user_agent.device.family} {user_agent.os.family} {user_agent.os.version_string}".strip()
    browser = f"{user_agent.browser.family} {user_agent.browser.version_string}".strip()
    return device, browser


class AuditContextMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        user = getattr(request, "user", None)
        actor_id = user.id if (user is not None and user.is_authenticated) else None
        
        device, browser = _parse_user_agent(request)
        correlation_id = request.META.get("HTTP_X_CORRELATION_ID")
        
        set_actor(actor_id, _client_ip(request), device, browser, correlation_id)
        try:
            return self.get_response(request)
        finally:
            clear_actor()
