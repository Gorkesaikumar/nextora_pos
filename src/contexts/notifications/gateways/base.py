from abc import ABC, abstractmethod


class BaseNotificationProvider(ABC):

    @abstractmethod
    def send(self, recipient: str | dict, subject: str | None, body: str, **kwargs) -> str:
        """Sends a notification.

        Returns the external_id/reference ID from the provider.
        Raises an exception on failure.
        """
        pass
