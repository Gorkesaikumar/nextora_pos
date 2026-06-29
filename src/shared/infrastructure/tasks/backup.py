import logging
import os
import subprocess
from uuid import UUID

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from shared.infrastructure.storage.services import store_file

logger = logging.getLogger(__name__)

# NIL UUID used for platform/system level files that cross tenants
SYSTEM_TENANT_ID = UUID("00000000-0000-0000-0000-000000000000")


@shared_task(queue="bulk")
def db_backup_task() -> str:
    """Invokes pg_dump to take a binary snapshot of the database.

    Saves the result to private system file storage.
    """
    db_conf = settings.DATABASES["default"]
    db_name = db_conf["NAME"]
    db_user = db_conf.get("USER", "postgres")
    db_password = db_conf.get("PASSWORD")
    db_host = db_conf.get("HOST", "localhost")
    db_port = db_conf.get("PORT", "5432")

    env = os.environ.copy()
    if db_password:
        env["PGPASSWORD"] = db_password

    # -F c creates a custom-format dump (highly compressed, restoreable via pg_restore)
    cmd = [
        "pg_dump",
        "-h",
        str(db_host),
        "-p",
        str(db_port),
        "-U",
        str(db_user),
        "-d",
        str(db_name),
        "-F",
        "c",
    ]

    try:
        logger.info("Starting database backup...")
        result = subprocess.run(cmd, env=env, capture_output=True, check=True)
        dump_data = result.stdout

        timestamp = timezone.now().strftime("%Y-%m-%d_%H-%M-%S")
        file_key = f"backups/db_backup_{timestamp}.dump"

        store_file(
            tenant_id=SYSTEM_TENANT_ID,
            file_key=file_key,
            original_name=f"db_backup_{timestamp}.dump",
            content=dump_data,
            content_type="application/octet-stream",
            is_private=True,
        )
        logger.info(f"Database backup completed successfully: {file_key}")
        return f"Backup successful: {file_key}"

    except subprocess.CalledProcessError as e:
        error_msg = f"pg_dump process failed: {e.stderr.decode('utf-8', errors='ignore')}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)
    except Exception as e:
        error_msg = f"Database backup failed: {e}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)
