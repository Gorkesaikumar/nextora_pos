import logging
from datetime import datetime
from uuid import UUID

from django.db import transaction
from django.template import Context, Template

from shared.tenancy.scope import tenant_scope
from .models import ChannelType, InAppNotification, Notification, NotificationStatus, NotificationTemplate

logger = logging.getLogger(__name__)


def render_template(template: NotificationTemplate, context_data: dict) -> tuple[str, str]:
    """Render the notification subject and body using Django's template engine."""
    c = Context(context_data)
    subject = Template(template.subject).render(c) if template.subject else ""
    body = Template(template.body_template).render(c)
    return subject, body


def get_localized_template(
    tenant_id: UUID, template_name: str, channel: str, language: str = "en"
) -> NotificationTemplate | None:
    """Find the matching template, falling back to English ('en') if localized is missing."""
    # Since this queries tenant-specific template, we use unscoped or scope it.
    # To be safe, look up within tenant_scope or use all_objects.
    templates = NotificationTemplate.all_objects.filter(
        tenant_id=tenant_id, name=template_name, channel=channel, is_active=True
    )
    
    # Try preferred language
    template = templates.filter(language=language).first()
    if template:
        return template
        
    # Fallback to English
    if language != "en":
        return templates.filter(language="en").first()
        
    return None


def create_notification(
    tenant_id: UUID,
    channel: str,
    recipient: str | dict,
    template_name: str | None = None,
    context_data: dict | None = None,
    scheduled_for: datetime | None = None,
    language: str = "en",
) -> Notification:
    """Creates a notification. If scheduled_for is provided, status is SCHEDULED."""
    context_data = context_data or {}
    recipient_payload = recipient if isinstance(recipient, dict) else {"address": recipient}

    with tenant_scope(tenant_id):
        template = None
        if template_name:
            template = get_localized_template(tenant_id, template_name, channel, language)

        status = NotificationStatus.SCHEDULED if scheduled_for else NotificationStatus.PENDING

        notification = Notification.objects.create(
            channel=channel,
            recipient=recipient_payload,
            status=status,
            template=template,
            context_data=context_data,
            scheduled_for=scheduled_for,
        )

    # Trigger async dispatch immediately if not scheduled
    if not scheduled_for:
        from .tasks import send_notification_task
        # Delay import to avoid circular dependency
        transaction.on_commit(lambda: send_notification_task.delay(str(notification.id)))

    return notification


def bulk_send_notifications(
    tenant_id: UUID,
    recipients: list[str | dict],
    channel: str,
    template_name: str | None = None,
    context_data: dict | None = None,
    language: str = "en",
) -> list[Notification]:
    """Bulk create notifications and trigger async tasks."""
    context_data = context_data or {}
    notifications = []
    
    with tenant_scope(tenant_id):
        template = None
        if template_name:
            template = get_localized_template(tenant_id, template_name, channel, language)

        for recipient in recipients:
            recipient_payload = recipient if isinstance(recipient, dict) else {"address": recipient}
            notifications.append(
                Notification(
                    tenant_id=tenant_id,
                    channel=channel,
                    recipient=recipient_payload,
                    status=NotificationStatus.PENDING,
                    template=template,
                    context_data=context_data,
                )
            )

        # Batch create
        Notification.objects.bulk_create(notifications)
        
        # Refetch created notifications to get their IDs
        # (bulk_create doesn't always return IDs on all DB backends, but PostgreSQL does)
        created_notifications = Notification.objects.filter(
            tenant_id=tenant_id,
            channel=channel,
            status=NotificationStatus.PENDING,
        ).order_by("-created_at")[:len(recipients)]

    from .tasks import send_notification_task
    for notification in created_notifications:
        transaction.on_commit(
            lambda n_id=str(notification.id): send_notification_task.delay(n_id)
        )

    return list(created_notifications)


def create_in_app_notification(
    tenant_id: UUID, user_id: UUID, title: str, body_template: str, context_data: dict
) -> InAppNotification:
    """Creates a localized in-app notification directly in the user's inbox."""
    c = Context(context_data)
    rendered_body = Template(body_template).render(c)
    
    with tenant_scope(tenant_id):
        notification = InAppNotification.objects.create(
            user_id=user_id,
            title=title,
            body=rendered_body,
        )
    return notification
