from django.db import models
from shared.tenancy.models import TenantAwareModel


class StoredFile(TenantAwareModel):
    file_key = models.CharField(max_length=500, db_index=True)
    original_name = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField(help_text="File size in bytes")
    content_type = models.CharField(max_length=100)
    is_private = models.BooleanField(default=True)
    version = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)

    class Meta(TenantAwareModel.Meta):
        db_table = "stored_file"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "file_key", "version"],
                name="uq_stored_file__tenant_key_version",
            )
        ]

    def __str__(self) -> str:
        return f"{self.file_key} (v{self.version})"
