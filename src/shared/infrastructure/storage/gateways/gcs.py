import datetime
import logging

from django.conf import settings

from .base import BaseStorageAdapter

logger = logging.getLogger(__name__)


class GoogleCloudStorageAdapter(BaseStorageAdapter):

    def __init__(self):
        self.bucket_name = getattr(settings, "GCS_BUCKET_NAME", "nextora-storage")
        self._client = None

    @property
    def client(self):
        if not self._client:
            try:
                from google.cloud import storage
                self._client = storage.Client()
            except ImportError:
                logger.warning(
                    "google-cloud-storage is not installed. GCS calls will fail. "
                    "Please install the dependency."
                )
                raise RuntimeError("Google Cloud Storage client is not installed.")
        return self._client

    def save(self, file_key: str, content: bytes, is_private: bool = False) -> str:
        bucket = self.client.bucket(self.bucket_name)
        blob = bucket.blob(file_key)

        blob.upload_from_string(content)
        if not is_private:
            blob.make_public()

        return file_key

    def read(self, file_key: str) -> bytes:
        bucket = self.client.bucket(self.bucket_name)
        blob = bucket.blob(file_key)
        return blob.download_as_bytes()

    def delete(self, file_key: str) -> None:
        bucket = self.client.bucket(self.bucket_name)
        blob = bucket.blob(file_key)
        if blob.exists():
            blob.delete()

    def generate_url(self, file_key: str, expires_in: int = 3600) -> str:
        bucket = self.client.bucket(self.bucket_name)
        blob = bucket.blob(file_key)

        # For public files, just return the public URL
        # For private files, generate a signed URL
        # We can check metadata or check settings.
        # Here we generate signed URL by default for safety.
        url = blob.generate_signed_url(
            version="v4",
            expiration=datetime.timedelta(seconds=expires_in),
            method="GET",
        )
        return url
