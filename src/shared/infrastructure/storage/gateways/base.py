from abc import ABC, abstractmethod


class BaseStorageAdapter(ABC):

    @abstractmethod
    def save(self, file_key: str, content: bytes, is_private: bool = False) -> str:
        """Saves a file to storage.

        Returns the saved file path / URL.
        """
        pass

    @abstractmethod
    def read(self, file_key: str) -> bytes:
        """Reads file content from storage."""
        pass

    @abstractmethod
    def delete(self, file_key: str) -> None:
        """Deletes a file from storage."""
        pass

    @abstractmethod
    def generate_url(self, file_key: str, expires_in: int = 3600) -> str:
        """Generates a secure, optionally signed URL for the file."""
        pass
