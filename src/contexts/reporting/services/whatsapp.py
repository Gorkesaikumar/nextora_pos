import urllib.parse
from uuid import UUID
from django.utils import timezone

from contexts.notifications.models import Notification, ChannelType, NotificationStatus
from shared.tenancy.scope import tenant_scope


class WhatsAppSharingService:
    @staticmethod
    def generate_wa_me_link(phone_number: str, message_text: str) -> str:
        """
        Generates a direct wa.me link that launches WhatsApp Web/App.
        Strips non-numeric characters from the phone number except '+'.
        """
        clean_phone = ''.join(c for c in phone_number if c.isdigit() or c == '+')
        # wa.me usually wants numbers without the '+' sign though, let's remove it
        if clean_phone.startswith('+'):
            clean_phone = clean_phone[1:]
            
        encoded_message = urllib.parse.quote(message_text)
        return f"https://wa.me/{clean_phone}?text={encoded_message}"

    @staticmethod
    def log_and_send_whatsapp(tenant_id: UUID, phone_number: str, message_text: str, context_data: dict = None) -> str:
        """
        Logs the sharing event to the Notification table for auditability and 
        returns the wa.me link. When we switch to the official API, this will 
        trigger the actual API HTTP request instead of returning a link.
        """
        if context_data is None:
            context_data = {}
            
        with tenant_scope(tenant_id):
            Notification.objects.create(
                channel=ChannelType.WHATSAPP,
                recipient={"address": phone_number},
                status=NotificationStatus.SENT, # Assuming sent via wa.me manual action
                context_data=context_data,
                sent_at=timezone.now(),
                external_id="wa.me manual share"
            )
            
        return WhatsAppSharingService.generate_wa_me_link(phone_number, message_text)
