"""API Views for Notifications."""
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from shared.api.views import BaseAPIView, BaseModelViewSet
from shared.tenancy.context import get_current_tenant
from contexts.notifications.models import (
    Notification,
    NotificationTemplate,
    InAppNotification,
    NotificationStatus
)
from contexts.notifications.services import create_notification
from contexts.notifications.tasks import send_notification_task

from .serializers import (
    NotificationSerializer,
    NotificationTemplateSerializer,
    InAppNotificationSerializer,
    SendNotificationSerializer,
    SendReceiptSerializer
)


class NotificationTemplateViewSet(BaseModelViewSet):
    """Manage Notification Templates for Email, SMS, WhatsApp, Push."""
    serializer_class = NotificationTemplateSerializer

    def get_queryset(self):
        return NotificationTemplate.objects.filter(tenant_id=get_current_tenant())


class NotificationViewSet(BaseModelViewSet):
    """View Notification History and handle retries."""
    serializer_class = NotificationSerializer
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        return Notification.objects.filter(tenant_id=get_current_tenant())

    @extend_schema(responses={200: dict})
    @action(detail=True, methods=["post"])
    def retry(self, request, pk=None):
        """Manually trigger a retry for a failed or pending notification."""
        notification = self.get_object()
        if notification.status in [NotificationStatus.SENT, NotificationStatus.DELIVERED]:
            return Response({"detail": "Notification already sent."}, status=status.HTTP_400_BAD_REQUEST)
        
        # Trigger Celery task asynchronously
        send_notification_task.delay(str(notification.id))
        return Response({"detail": "Notification queued for retry."}, status=status.HTTP_200_OK)


class InAppNotificationViewSet(BaseModelViewSet):
    """Manage In-App Push Notifications for the current user."""
    serializer_class = InAppNotificationSerializer
    http_method_names = ["get", "patch", "head", "options"]

    def get_queryset(self):
        return InAppNotification.objects.filter(
            tenant_id=get_current_tenant(),
            user_id=self.request.user.id
        )

    @extend_schema(request=None, responses={200: dict})
    @action(detail=True, methods=["patch"])
    def read(self, request, pk=None):
        """Mark an in-app notification as read."""
        from django.utils import timezone
        notification = self.get_object()
        if not notification.is_read:
            notification.is_read = True
            notification.read_at = timezone.now()
            notification.save(update_fields=["is_read", "read_at"])
        return Response({"detail": "Marked as read"}, status=status.HTTP_200_OK)


class DispatchNotificationView(BaseAPIView):
    """Directly send a notification using Email, SMS, WhatsApp or Push."""
    @extend_schema(request=SendNotificationSerializer, responses=NotificationSerializer)
    def post(self, request, *args, **kwargs) -> Response:
        serializer = SendNotificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        notification = create_notification(
            tenant_id=get_current_tenant(),
            channel=data["channel"],
            recipient=data["recipient"],
            template_name=data.get("template_name"),
            context_data=data.get("context_data", {}),
            scheduled_for=data.get("scheduled_for"),
            language=data.get("language", "en"),
        )
        resp_serializer = NotificationSerializer(notification)
        return Response(resp_serializer.data, status=status.HTTP_201_CREATED)


class SendReceiptView(BaseAPIView):
    """Send an Order Receipt via Email, SMS or WhatsApp with PDF attachment."""
    @extend_schema(request=SendReceiptSerializer, responses={202: dict})
    def post(self, request, *args, **kwargs) -> Response:
        serializer = SendReceiptSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Provide a special context instruction for the Celery task to attach the PDF
        context_data = {
            "order_id": str(data["order_id"]),
            "_attachment_instruction": {
                "type": "invoice_pdf",
                "order_id": str(data["order_id"])
            }
        }

        create_notification(
            tenant_id=get_current_tenant(),
            channel=data["channel"],
            recipient=data["recipient"],
            template_name="order.receipt",
            context_data=context_data,
        )
        return Response({"detail": "Receipt dispatch queued successfully."}, status=status.HTTP_202_ACCEPTED)
