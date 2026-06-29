import logging
import uuid

from django.conf import settings

from .base import BaseNotificationProvider
from .fake import FakeNotificationProvider

logger = logging.getLogger(__name__)


class PushProvider(BaseNotificationProvider):

    def send(self, recipient: str | dict, subject: str | None, body: str, **kwargs) -> str:
        provider_type = getattr(settings, "NOTIFICATIONS_PUSH_PROVIDER", "fake")
        if provider_type == "fake":
            return FakeNotificationProvider("push").send(recipient, subject, body, **kwargs)

        device_token = recipient if isinstance(recipient, str) else recipient.get("token")
        if not device_token:
            raise ValueError("Push device token is missing.")

        if provider_type == "fcm":
            logger.info(f"Sending FCM Push notification to token: {device_token[:15]}...")
            # Stub for Firebase Cloud Messaging (FCM) call
            return f"fcm_push_{uuid.uuid4().hex[:8]}"

        raise NotImplementedError(f"Push Provider {provider_type} is not implemented.")
