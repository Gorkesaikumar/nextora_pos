#!/usr/bin/env python
"""Django administrative entrypoint.

Defaults to the dev settings module so local commands work without extra
flags; production processes set DJANGO_SETTINGS_MODULE explicitly in the
environment (Twelve-Factor: config).
"""
import os
import sys
from pathlib import Path


def main() -> None:
    # Make the `src/` packages importable (shared, contexts, interface).
    sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "Couldn't import Django. Is it installed and is your virtual "
            "environment activated?"
        ) from exc

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
