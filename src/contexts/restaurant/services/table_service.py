"""Table layout management and state machine service."""
import uuid
from typing import List, Optional

from django.db import transaction

from contexts.restaurant.domain.enums import TableStatus
from contexts.restaurant.exceptions import InvalidStatusTransition, TableMergeError
from contexts.restaurant.models import DiningTable


@transaction.atomic
def seat_guests(table_id: uuid.UUID) -> DiningTable:
    """Transition a table from VACANT or RESERVED to OCCUPIED."""
    table = DiningTable.objects.select_for_update().get(id=table_id)
    if table.status not in (TableStatus.VACANT, TableStatus.RESERVED):
        raise InvalidStatusTransition(f"Cannot seat guests at table in state {table.status}")
    
    table.status = TableStatus.OCCUPIED
    table.save(update_fields=["status", "updated_at"])
    return table


@transaction.atomic
def reserve_table(table_id: uuid.UUID) -> DiningTable:
    """Transition a table to RESERVED."""
    table = DiningTable.objects.select_for_update().get(id=table_id)
    if table.status != TableStatus.VACANT:
        raise InvalidStatusTransition(f"Cannot reserve table in state {table.status}")
    
    table.status = TableStatus.RESERVED
    table.save(update_fields=["status", "updated_at"])
    return table


@transaction.atomic
def release_table(table_id: uuid.UUID) -> DiningTable:
    """Free up a table, returning it to VACANT."""
    table = DiningTable.objects.select_for_update().get(id=table_id)
    table.status = TableStatus.VACANT
    table.save(update_fields=["status", "updated_at"])
    return table


@transaction.atomic
def block_table(table_id: uuid.UUID) -> DiningTable:
    """Block a table for maintenance/cleanup."""
    table = DiningTable.objects.select_for_update().get(id=table_id)
    table.status = TableStatus.BLOCKED
    table.save(update_fields=["status", "updated_at"])
    return table


@transaction.atomic
def merge_tables(primary_table_id: uuid.UUID, secondary_table_ids: List[uuid.UUID]) -> DiningTable:
    """
    Merge multiple secondary tables into a primary table.
    The secondary tables point to primary_table via merge_group.
    Their statuses are set to MERGED.
    """
    primary = DiningTable.objects.select_for_update().get(id=primary_table_id)
    
    if primary.status == TableStatus.MERGED:
        raise TableMergeError("Cannot merge into a table that is already merged into another.")

    secondaries = DiningTable.objects.select_for_update().filter(id__in=secondary_table_ids)
    
    for sec in secondaries:
        if sec.id == primary.id:
            continue
        if sec.status == TableStatus.OCCUPIED:
            raise TableMergeError(f"Cannot merge table {sec.number} because it is occupied.")
        
        sec.merge_group = primary
        sec.status = TableStatus.MERGED
        sec.save(update_fields=["merge_group", "status", "updated_at"])

    return primary


@transaction.atomic
def split_tables(primary_table_id: uuid.UUID) -> DiningTable:
    """
    Split a merged table, freeing all secondary tables associated with it.
    Sets all secondary tables back to VACANT.
    """
    primary = DiningTable.objects.get(id=primary_table_id)
    secondaries = DiningTable.objects.select_for_update().filter(merge_group=primary)
    
    for sec in secondaries:
        sec.merge_group = None
        sec.status = TableStatus.VACANT
        sec.save(update_fields=["merge_group", "status", "updated_at"])
        
    return primary


def generate_table_qr_url(table_id: uuid.UUID) -> str:
    """
    Generates a public ordering QR code URL for a table.
    Integrates with the shared storage service to upload a placeholder QR code.
    """
    from shared.infrastructure.storage.services import get_file_url, store_file
    from django.conf import settings
    
    table = DiningTable.objects.select_related("floor__branch__tenant").get(id=table_id)
    tenant = table.floor.branch.tenant
    
    # Target ordering URL for customer self-ordering
    target_url = f"https://{tenant.slug}.{getattr(settings, 'TENANCY_BASE_DOMAIN', 'nextora.app')}/order/?table={table_id}"
    
    # 1x1 transparent pixel placeholder
    png_bytes = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
        b"\x00\x00\x00\rIDATx\x9cc`\x00\x00\x00\x02\x00\x01H\xaf\xa4q\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    
    file_key = f"qrcodes/table_{table_id}.png"
    stored_file = store_file(
        tenant_id=tenant.id,
        file_key=file_key,
        original_name=f"table_{table_id}_qr.png",
        content=png_bytes,
        content_type="image/png",
        is_private=False,
    )
    
    qr_url = get_file_url(tenant.id, stored_file.file_key)
    table.qr_code_url = qr_url
    table.save(update_fields=["qr_code_url", "updated_at"])
    return qr_url
