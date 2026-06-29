import gzip
import io
import logging
import os

from django.conf import settings
from PIL import Image

logger = logging.getLogger(__name__)


def scan_file(content: bytes) -> bool:
    """Hook to scan file content for viruses.

    Returns True if clean, False if infected/malicious.
    """
    # EICAR test virus signature check
    if b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*" in content:
        logger.warning("EICAR test virus signature detected!")
        return False

    return True


def compress_image(content: bytes, format: str = "WEBP", quality: int = 80) -> bytes:
    """Compresses an image and converts it to WebP format."""
    try:
        image = Image.open(io.BytesIO(content))
        out_io = io.BytesIO()
        image.save(out_io, format=format, quality=quality)
        return out_io.getvalue()
    except Exception as e:
        logger.error(f"Image compression failed: {e}")
        return content


def compress_text(content: bytes) -> bytes:
    """Compresses text content using gzip."""
    out_io = io.BytesIO()
    with gzip.GzipFile(fileobj=out_io, mode="wb") as f:
        f.write(content)
    return out_io.getvalue()


def process_file(content: bytes, content_type: str, file_name: str) -> tuple[bytes, str, str]:
    """Processes the file through the pipeline: scanning and compressing.

    Returns (processed_content, new_content_type, new_file_name).
    """
    if getattr(settings, "STORAGE_SCAN_VIRUS", True):
        if not scan_file(content):
            raise ValueError("File rejected: Security threat / virus signature detected.")

    name, ext = os.path.splitext(file_name)
    ext = ext.lower()

    if content_type.startswith("image/") and ext not in (".gif", ".svg"):
        logger.info(f"Compressing image {file_name} to WebP.")
        compressed = compress_image(content, format="WEBP")
        return compressed, "image/webp", f"{name}.webp"

    elif content_type in ("text/csv", "application/json", "text/plain") and len(content) > 10240:
        logger.info(f"Compressing text file {file_name} with gzip.")
        compressed = compress_text(content)
        return compressed, content_type, f"{file_name}.gz"

    return content, content_type, file_name
