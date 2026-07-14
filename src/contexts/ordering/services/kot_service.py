"""KOT generation — routes newly added items to kitchen stations.

Items not yet printed (no KOT) are grouped by kitchen station; one KOT per
station is created with a daily-reset, concurrency-safe number.
"""
import uuid
from collections import defaultdict

from django.db import transaction

from contexts.audit.services import record_audit
from contexts.ordering.domain.enums import ItemStatus
from contexts.ordering.models import KOT, KOTItem, Order
from contexts.ordering.services import sequences
from contexts.ordering.realtime import broadcast_tenant_event


@transaction.atomic
def generate_kots(order_id: uuid.UUID) -> list[KOT]:
    order = Order.objects.select_for_update().get(id=order_id)

    pending = order.items.filter(status=ItemStatus.ACTIVE, kot__isnull=True)
    by_station: dict = defaultdict(list)
    for item in pending:
        by_station[item.kitchen_station_id].append(item)

    kots: list[KOT] = []
    for station_id, items in by_station.items():
        number = sequences.next_number(getattr(order, 'location_id', None), "kot")
        kot = KOT.objects.create(
            order=order, 
            kitchen_station_id=station_id, number=number,
        )
        for item in items:
            KOTItem.objects.create(
                kot=kot, order_item=item,
                name_snapshot=item.name_snapshot, qty=item.qty, notes=item.notes,
            )
            item.kot = kot
            item.save(update_fields=["kot", "updated_at"])
        kots.append(kot)

    if kots:
        record_audit("kot.generated", entity_type="order", entity_id=order_id,
                     changes={"count": len(kots)})
        transaction.on_commit(lambda: broadcast_tenant_event("kds_changed"))
    return kots
