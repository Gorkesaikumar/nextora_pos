"""WebSocket URL routing for the ordering context (KDS live updates)."""
from django.urls import re_path

from contexts.ordering import consumers

websocket_urlpatterns = [
    re_path(r"^ws/events/$", consumers.TenantEventsConsumer.as_asgi()),
    re_path(r"^ws/kds/$", consumers.TenantEventsConsumer.as_asgi()),
]
