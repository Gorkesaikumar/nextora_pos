#!/usr/bin/env bash
# ===========================================================================
# Container entrypoint. Dispatches on the first argument to select a role,
# so one image serves web / worker / beat. Web waits for the DB and runs
# migrations + collectstatic before serving.
# ===========================================================================
set -euo pipefail

ROLE="${1:-web}"

wait_for_db() {
    python manage.py wait_for_db
}

case "$ROLE" in
    web)
        wait_for_db
        # Migrations must NOT run from every web replica (concurrent migrate
        # race). Run the dedicated `migrate` role as a one-off job before
        # rollout. For single-node/dev convenience, set RUN_MIGRATIONS_ON_START.
        if [ "${RUN_MIGRATIONS_ON_START:-false}" = "true" ]; then
            python manage.py migrate --noinput
        fi
        python manage.py collectstatic --noinput
        # ASGI server (Daphne) — serves HTTP *and* WebSockets (Django Channels)
        # from one process, so the KDS gets true real-time push in prod.
        # --proxy-headers: trust Nginx's X-Forwarded-For/Proto for client IP +
        #                  scheme in the ASGI scope.
        # --access-log -:  emit access logs to stdout for the log pipeline.
        exec daphne -b 0.0.0.0 -p 8000 --proxy-headers --access-log - \
            config.asgi:application
        ;;
    worker)
        wait_for_db
        exec celery -A config worker \
            --loglevel=INFO -Q critical,default,bulk
        ;;
    beat)
        wait_for_db
        exec celery -A config beat \
            --loglevel=INFO \
            --scheduler django_celery_beat.schedulers:DatabaseScheduler
        ;;
    migrate)
        wait_for_db
        exec python manage.py migrate --noinput
        ;;
    *)
        exec "$@"
        ;;
esac
