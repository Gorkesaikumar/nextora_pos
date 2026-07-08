import logging

from celery import shared_task
from celery.exceptions import MaxRetriesExceededError
from django.utils import timezone

from shared.tenancy.scope import tenant_scope
from .gateways import get_provider
from .models import ChannelType, InAppNotification, Notification, NotificationStatus
from .services import render_template

logger = logging.getLogger(__name__)


@shared_task(bind=True, queue="default", max_retries=5, default_retry_delay=60)
def send_notification_task(self, notification_id: str):
    """Asynchronously process and send a single notification."""
    try:
        notification = Notification.all_objects.get(id=notification_id)
    except Notification.DoesNotExist:
        logger.error(f"Notification {notification_id} not found.")
        return

    if notification.status in (NotificationStatus.SENT, NotificationStatus.DELIVERED):
        return

    with tenant_scope(notification.tenant_id):
        notification.status = NotificationStatus.QUEUED
        notification.save(update_fields=["status"])

        try:
            # 1. Resolve content
            if notification.template:
                subject, body = render_template(notification.template, notification.context_data)
            else:
                subject = notification.context_data.get("subject", "")
                body = notification.context_data.get("body", "")

            # 2. Dispatch
            if notification.channel == ChannelType.IN_APP:
                recipient_user_id = notification.recipient.get("user_id") or notification.recipient.get("address")
                InAppNotification.objects.create(
                    tenant_id=notification.tenant_id,
                    user_id=recipient_user_id,
                    title=subject or "New Notification",
                    body=body,
                )
                external_id = f"in_app_{notification_id}"
            else:
                provider = get_provider(notification.channel)
                recipient_address = notification.recipient.get("address") or notification.recipient
                
                # Check for JIT dynamic attachments
                attachments = []
                attachment_instruction = notification.context_data.get("_attachment_instruction")
                if attachment_instruction:
                    if attachment_instruction.get("type") == "invoice_pdf":
                        order_id = attachment_instruction.get("order_id")
                        if order_id:
                            try:
                                from contexts.reporting.services.pdf_generator import generate_invoice_pdf
                                filename, pdf_bytes = generate_invoice_pdf(order_id)
                                attachments.append((filename, pdf_bytes, "application/pdf"))
                            except Exception as e:
                                logger.error(f"Failed to generate PDF attachment for notification {notification_id}: {e}")
                                raise
                
                external_id = provider.send(
                    recipient=recipient_address,
                    subject=subject,
                    body=body,
                    attachments=attachments,
                )

            # 3. Mark success
            notification.status = NotificationStatus.SENT
            notification.sent_at = timezone.now()
            notification.external_id = external_id
            notification.save(update_fields=["status", "sent_at", "external_id"])

        except Exception as exc:
            # Handle retry policy
            notification.retry_count += 1
            notification.last_error = str(exc)
            notification.save(update_fields=["retry_count", "last_error"])

            try:
                countdown = self.default_retry_delay * (2 ** self.request.retries)
                raise self.retry(exc=exc, countdown=countdown)
            except MaxRetriesExceededError:
                notification.status = NotificationStatus.FAILED
                notification.save(update_fields=["status"])
                logger.error(
                    f"Notification {notification_id} failed permanently after max retries. Error: {exc}"
                )


@shared_task(queue="default")
def process_scheduled_notifications():
    """Celery Beat task to sweep and queue scheduled notifications."""
    now = timezone.now()
    scheduled = Notification.all_objects.filter(
        status=NotificationStatus.SCHEDULED, scheduled_for__lte=now
    )

    for notification in scheduled:
        # Update status to PENDING before delay to prevent race conditions
        notification.status = NotificationStatus.PENDING
        notification.save(update_fields=["status"])
        send_notification_task.delay(str(notification.id))
