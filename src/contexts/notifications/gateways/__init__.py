from contexts.notifications.models import ChannelType

from .base import BaseNotificationProvider
from .email import EmailProvider
from .push import PushProvider
from .sms import SMSProvider
from .whatsapp import WhatsAppProvider


def get_provider(channel: str) -> BaseNotificationProvider:
    if channel == ChannelType.EMAIL:
        return EmailProvider()
    elif channel == ChannelType.SMS:
        return SMSProvider()
    elif channel == ChannelType.WHATSAPP:
        return WhatsAppProvider()
    elif channel == ChannelType.PUSH:
        return PushProvider()
    raise ValueError(f"No external provider for channel: {channel}")
