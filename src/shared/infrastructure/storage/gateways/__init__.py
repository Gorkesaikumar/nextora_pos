from django.conf import settings

from .base import BaseStorageAdapter
from .gcs import GoogleCloudStorageAdapter
from .local import LocalStorageAdapter


def get_storage_adapter() -> BaseStorageAdapter:
    """Factory to get the configured storage adapter based on settings."""
    provider = getattr(settings, "STORAGE_PROVIDER", "local").lower()
    if provider == "local":
        return LocalStorageAdapter()
    elif provider == "gcs":
        return GoogleCloudStorageAdapter()
    raise ValueError(f"Unknown storage provider: {provider}")
