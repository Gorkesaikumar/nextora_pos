# ===========================================================================
# Nextora POS — production image (multi-stage).
#
# Stage 1 (builder): build a self-contained virtualenv with all deps.
# Stage 2 (runtime): slim image, non-root user, venv copied in. No compilers
#                    ship to production -> smaller image, smaller attack surface.
#
# The SAME image runs web (Daphne ASGI — HTTP + WebSockets), celery worker, and
# celery beat; only the command differs (Twelve-Factor: processes / dev-prod parity).
# ===========================================================================

# --- Stage 1: builder ------------------------------------------------------
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Build deps for psycopg / argon2 etc.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

ARG REQUIREMENTS=prod
COPY requirements/ /tmp/requirements/
RUN pip install --upgrade pip && \
    pip install -r /tmp/requirements/${REQUIREMENTS}.txt
# (argon2-cffi is now pinned in requirements/base.txt)

# --- Stage 2: runtime ------------------------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE=config.settings.prod \
    PYTHONPATH=/app/src

# Runtime-only libs (no compilers).
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 curl \
    && rm -rf /var/lib/apt/lists/*

# Non-root user.
RUN groupadd --system app && useradd --system --gid app --home /app app

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
COPY --chown=app:app . /app

# Make entrypoint executable.
RUN chmod +x /app/deploy/docker/entrypoint.sh

USER app

EXPOSE 8000
ENTRYPOINT ["/app/deploy/docker/entrypoint.sh"]
CMD ["web"]
