import logging
import uuid

from django.conf import settings

from .base import BaseNotificationProvider
from .fake import FakeNotificationProvider

logger = logging.getLogger(__name__)


class SMSProvider(BaseNotificationProvider):

    def send(self, recipient: str | dict, subject: str | None, body: str, **kwargs) -> str:
        provider_type = getattr(settings, "NOTIFICATIONS_SMS_PROVIDER", "fake")
        if provider_type == "fake":
            return FakeNotificationProvider("sms").send(recipient, subject, body, **kwargs)

        phone_number = recipient if isinstance(recipient, str) else recipient.get("phone")
        if not phone_number:
            raise ValueError("SMS phone number is missing.")

        if provider_type == "twilio":
            logger.info(f"Sending Twilio SMS to {phone_number}: {body[:30]}")
            # Stub for Twilio Client call
            return f"twilio_sms_{uuid.uuid4().hex[:8]}"

        raise NotImplementedError(f"SMS Provider {provider_type} is not implemented.")
