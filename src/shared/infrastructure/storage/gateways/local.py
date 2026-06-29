import os
from pathlib import Path

from django.conf import settings
from django.core.signing import TimestampSigner
from django.urls import reverse

from .base import BaseStorageAdapter


class LocalStorageAdapter(BaseStorageAdapter):

    def __init__(self):
        self.public_dir = Path(settings.MEDIA_ROOT) / "public"
        # Store private files outside the standard web-accessible media root
        self.private_dir = Path(settings.BASE_DIR) / "private_media"
        
        self.public_dir.mkdir(parents=True, exist_ok=True)
        self.private_dir.mkdir(parents=True, exist_ok=True)

    def _get_path(self, file_key: str, is_private: bool) -> Path:
        base_dir = self.private_dir if is_private else self.public_dir
        return base_dir / file_key

    def save(self, file_key: str, content: bytes, is_private: bool = False) -> str:
        file_path = self._get_path(file_key, is_private)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, "wb") as f:
            f.write(content)
            
        return file_key

    def read(self, file_key: str) -> bytes:
        # Check both directories, prioritizing private
        private_path = self._get_path(file_key, is_private=True)
        if private_path.exists():
            path = private_path
        else:
            path = self._get_path(file_key, is_private=False)
            
        with open(path, "rb") as f:
            return f.read()

    def delete(self, file_key: str) -> None:
        private_path = self._get_path(file_key, is_private=True)
        public_path = self._get_path(file_key, is_private=False)
        
        if private_path.exists():
            os.remove(private_path)
        if public_path.exists():
            os.remove(public_path)

    def generate_url(self, file_key: str, expires_in: int = 3600) -> str:
        # Check if the file is private in database or metadata.
        # But wait! If we don't know, we can check the file presence in private_dir.
        is_private = self._get_path(file_key, is_private=True).exists()
        
        if not is_private:
            # Public file url
            return f"{settings.MEDIA_URL}public/{file_key}"
            
        # Secure signed url for private files
        signer = TimestampSigner()
        token = signer.sign(file_key)
        
        # Build the URL to the download view
        # Using reverse to get the path
        path = reverse("storage:private-download", kwargs={"token": token})
        return f"{settings.SITE_URL}{path}"
