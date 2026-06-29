"""Block until the database accepts connections.

Used by the container entrypoint so web/worker processes don't crash-loop while
Postgres (or PgBouncer) is still starting. Bounded retries with backoff so a
genuinely-down DB still surfaces an error instead of hanging forever.
"""
import time

from django.core.management.base import BaseCommand
from django.db import connections
from django.db.utils import OperationalError


class Command(BaseCommand):
    help = "Wait for the default database to become available."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--max-attempts", type=int, default=30)
        parser.add_argument("--interval", type=float, default=1.0)

    def handle(self, *args, **options) -> None:
        attempts = options["max_attempts"]
        interval = options["interval"]

        for attempt in range(1, attempts + 1):
            try:
                connections["default"].cursor().execute("SELECT 1")
                self.stdout.write(self.style.SUCCESS("Database is available."))
                return
            except OperationalError:
                self.stdout.write(
                    f"Database unavailable (attempt {attempt}/{attempts}); "
                    f"retrying in {interval}s..."
                )
                time.sleep(interval)

        self.stderr.write(self.style.ERROR("Database did not become available."))
        raise SystemExit(1)
