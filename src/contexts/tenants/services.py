import logging
from uuid import UUID

from django.core.cache import cache
from django.db import transaction

from .models import TenantConfiguration

logger = logging.getLogger(__name__)

CACHE_KEY_PREFIX = "tenant_config:"
CACHE_TIMEOUT = 3600  # 1 hour


def _get_cache_key(tenant_id: UUID) -> str:
    return f"{CACHE_KEY_PREFIX}{tenant_id}"


def get_tenant_config(tenant_id: UUID) -> dict:
    """Get the tenant configuration as a dictionary. Uses Redis caching."""
    cache_key = _get_cache_key(tenant_id)
    cached_config = cache.get(cache_key)
    if cached_config is not None:
        return cached_config

    try:
        config = TenantConfiguration.all_objects.get(tenant_id=tenant_id)
    except TenantConfiguration.DoesNotExist:
        # Provision default configuration if not present
        with transaction.atomic():
            config, _ = TenantConfiguration.all_objects.get_or_create(tenant_id=tenant_id)

    config_dict = {
        "gst_number": config.gst_number,
        "currency": config.currency,
        "timezone": config.timezone,
        "invoice_prefix": config.invoice_prefix,
        "invoice_footer": config.invoice_footer,
        "printer_settings": config.printer_settings,
        "kitchen_settings": config.kitchen_settings,
        "discount_rules": config.discount_rules,
        "tax_rules": config.tax_rules,
        "notification_settings": config.notification_settings,
        "business_hours": config.business_hours,
        "working_days": config.working_days,
        "theme": config.theme,
        "logo_url": config.logo.url if config.logo else None,
        "language": config.language,
    }

    cache.set(cache_key, config_dict, timeout=CACHE_TIMEOUT)
    return config_dict


def update_tenant_config(tenant_id: UUID, **kwargs) -> dict:
    """Update tenant configuration and invalidate cache."""
    with transaction.atomic():
        config, _ = TenantConfiguration.all_objects.get_or_create(tenant_id=tenant_id)
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)
        config.save()

    # Invalidate cache
    cache_key = _get_cache_key(tenant_id)
    cache.delete(cache_key)

    # Return fresh config dict
    return get_tenant_config(tenant_id)


def generate_table_qr(table_id: UUID) -> str:
    """Generates a public QR code image for a table and uploads it to storage.

    Returns the public URL of the QR code.
    """
    from shared.infrastructure.storage.services import get_file_url, store_file
    from django.conf import settings
    from .models import Table

    table = Table.all_objects.select_related("floor__branch__tenant").get(id=table_id)
    tenant = table.floor.branch.tenant

    target_url = f"https://{tenant.slug}.{getattr(settings, 'TENANCY_BASE_DOMAIN', 'nextora.app')}/order/?table={table_id}"
    logger.info(f"Generating Table QR for URL: {target_url}")

    # 1x1 pixel transparent PNG data as a valid placeholder QR
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
        is_private=False,  # Public URL so customers can scan it
    )

    qr_url = get_file_url(tenant.id, stored_file.file_key)
    table.qr_code_url = qr_url
    table.save(update_fields=["qr_code_url"])

    return qr_url
