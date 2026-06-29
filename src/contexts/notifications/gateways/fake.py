import logging
import uuid

from .base import BaseNotificationProvider

logger = logging.getLogger(__name__)


class FakeNotificationProvider(BaseNotificationProvider):

    def __init__(self, channel_name: str):
        self.channel_name = channel_name

    def send(self, recipient: str | dict, subject: str | None, body: str, **kwargs) -> str:
        external_id = f"fake_{self.channel_name}_{uuid.uuid4().hex[:8]}"
        logger.info(
            f"[FAKE_NOTIFICATION] Channel: {self.channel_name} | "
            f"To: {recipient} | Subject: {subject} | Body: {body} | ID: {external_id}"
        )
        return external_id
