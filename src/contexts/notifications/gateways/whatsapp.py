import logging
import uuid

from django.conf import settings

from .base import BaseNotificationProvider
from .fake import FakeNotificationProvider

logger = logging.getLogger(__name__)


class WhatsAppProvider(BaseNotificationProvider):

    def send(self, recipient: str | dict, subject: str | None, body: str, **kwargs) -> str:
        provider_type = getattr(settings, "NOTIFICATIONS_WHATSAPP_PROVIDER", "fake")
        if provider_type == "fake":
            return FakeNotificationProvider("whatsapp").send(recipient, subject, body, **kwargs)

        phone_number = recipient if isinstance(recipient, str) else recipient.get("phone")
        if not phone_number:
            raise ValueError("WhatsApp phone number is missing.")

        if provider_type == "twilio":
            logger.info(f"Sending Twilio WhatsApp message to {phone_number}: {body[:30]}")
            # Stub for Twilio WhatsApp client call
            return f"twilio_wa_{uuid.uuid4().hex[:8]}"

        raise NotImplementedError(f"WhatsApp Provider {provider_type} is not implemented.")
