from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import InAppNotification, Notification, NotificationStatus
from .serializers import InAppNotificationSerializer


class InAppInboxViewSet(viewsets.ReadOnlyModelViewSet):
    """API viewset for users to list and interact with their In-App notifications inbox."""

    serializer_class = InAppNotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Tenantaware managers automatically filter by current resolved tenant
        return InAppNotification.objects.filter(user_id=self.request.user.id).order_by(
            "-created_at"
        )

    @action(detail=True, methods=["post"], url_path="read")
    def mark_as_read(self, request, pk=None):
        notification = self.get_object()
        if not notification.is_read:
            notification.is_read = True
            notification.read_at = timezone.now()
            notification.save(update_fields=["is_read", "read_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class TwilioWebhookView(APIView):
    """Receives Twilio delivery status callbacks and updates Notification tracking status.

    Bypasses RLS filtering using all_objects manager, as callbacks are
    tenant-agnostic.
    """

    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        message_sid = request.data.get("MessageSid") or request.data.get("SmsSid")
        message_status = request.data.get("MessageStatus") or request.data.get("SmsStatus")

        if not message_sid or not message_status:
            return Response("Missing payload fields", status=status.HTTP_400_BAD_REQUEST)

        status_map = {
            "delivered": NotificationStatus.DELIVERED,
            "failed": NotificationStatus.FAILED,
            "undelivered": NotificationStatus.FAILED,
            "sent": NotificationStatus.SENT,
        }

        mapped_status = status_map.get(message_status.lower())
        if mapped_status:
            # We use all_objects since Twilio calls are cross-tenant/tenant-agnostic
            Notification.all_objects.filter(external_id=message_sid).update(
                status=mapped_status, updated_at=timezone.now()
            )

        return Response({"status": "ok"}, status=status.HTTP_200_OK)
