import logging
import uuid

from django.conf import settings
from django.core.mail import EmailMessage

from .base import BaseNotificationProvider
from .fake import FakeNotificationProvider

logger = logging.getLogger(__name__)


class EmailProvider(BaseNotificationProvider):

    def send(self, recipient: str | dict, subject: str | None, body: str, **kwargs) -> str:
        if getattr(settings, "NOTIFICATIONS_EMAIL_PROVIDER", "smtp") == "fake":
            return FakeNotificationProvider("email").send(recipient, subject, body, **kwargs)

        to_email = recipient if isinstance(recipient, str) else recipient.get("email")
        if not to_email:
            raise ValueError("Email recipient address is missing.")

        msg = EmailMessage(
            subject=subject or "Notification",
            body=body,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@nextora.app"),
            to=[to_email],
        )

        attachments = kwargs.get('attachments', [])
        for attachment in attachments:
            if isinstance(attachment, tuple) and len(attachment) == 3:
                # Expected: (filename, content, mimetype)
                msg.attach(*attachment)

        sent = msg.send(fail_silently=False)
        if not sent:
            raise RuntimeError("Email failed to send via Django core mail.")

        return f"smtp_{uuid.uuid4().hex[:8]}"
