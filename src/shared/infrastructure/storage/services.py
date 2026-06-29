import logging
import os
from uuid import UUID

from django.db import transaction

from shared.tenancy.scope import tenant_scope
from .gateways import get_storage_adapter
from .models import StoredFile
from .pipeline import process_file

logger = logging.getLogger(__name__)


def store_file(
    tenant_id: UUID,
    file_key: str,
    original_name: str,
    content: bytes,
    content_type: str,
    is_private: bool = True,
) -> StoredFile:
    """Processes, versions, and saves a file in multi-tenant storage."""
    # 1. Pipeline processing (scan + compress)
    processed_content, final_mime, final_name = process_file(content, content_type, original_name)

    # Align file key extension with final processed name (e.g. .png -> .webp)
    base_key, _ = os.path.splitext(file_key)
    final_ext = os.path.splitext(final_name)[1]
    final_key = f"{base_key}{final_ext}".strip("/")

    adapter = get_storage_adapter()

    with transaction.atomic():
        # Get next version number
        latest_file = (
            StoredFile.all_objects.filter(tenant_id=tenant_id, file_key=final_key)
            .order_by("-version")
            .first()
        )
        next_version = (latest_file.version + 1) if latest_file else 1

        # Deactivate old version in index
        if latest_file:
            latest_file.is_active = False
            latest_file.save(update_fields=["is_active"])

        # Physical file key is isolated by tenant and versioned
        physical_key = f"{tenant_id}/v{next_version}/{final_key}"

        # 2. Write to storage gateway
        adapter.save(physical_key, processed_content, is_private=is_private)

        # 3. Write metadata to database
        with tenant_scope(tenant_id):
            stored_file = StoredFile.objects.create(
                file_key=final_key,
                original_name=final_name,
                file_size=len(processed_content),
                content_type=final_mime,
                is_private=is_private,
                version=next_version,
                is_active=True,
            )

    return stored_file


def retrieve_file(tenant_id: UUID, file_key: str, version: int | None = None) -> tuple[bytes, str]:
    """Retrieves file content and content type from storage."""
    query = StoredFile.all_objects.filter(tenant_id=tenant_id, file_key=file_key)
    if version:
        stored_file = query.filter(version=version).first()
    else:
        # Get active or latest version
        stored_file = query.order_by("-version").first()

    if not stored_file:
        raise FileNotFoundError(f"File {file_key} not found for tenant {tenant_id}")

    adapter = get_storage_adapter()
    physical_key = f"{tenant_id}/v{stored_file.version}/{stored_file.file_key}"
    content = adapter.read(physical_key)
    return content, stored_file.content_type


def delete_file(tenant_id: UUID, file_key: str) -> None:
    """Soft deletes metadata and deletes physical file versions from storage."""
    files = StoredFile.all_objects.filter(tenant_id=tenant_id, file_key=file_key)
    if not files.exists():
        return

    adapter = get_storage_adapter()
    for stored_file in files:
        physical_key = f"{tenant_id}/v{stored_file.version}/{stored_file.file_key}"
        try:
            adapter.delete(physical_key)
        except Exception as e:
            logger.error(f"Failed to delete physical file {physical_key}: {e}")

    # Delete DB records
    files.delete()


def get_file_url(tenant_id: UUID, file_key: str, expires_in: int = 3600) -> str:
    """Generates a secure access URL for the latest version of a file."""
    stored_file = (
        StoredFile.all_objects.filter(tenant_id=tenant_id, file_key=file_key)
        .order_by("-version")
        .first()
    )
    if not stored_file:
        raise FileNotFoundError(f"File {file_key} not found for tenant {tenant_id}")

    adapter = get_storage_adapter()
    # Path inside storage
    physical_key = f"{tenant_id}/v{stored_file.version}/{stored_file.file_key}"
    return adapter.generate_url(physical_key, expires_in=expires_in)
