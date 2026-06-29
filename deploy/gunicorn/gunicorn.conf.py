"""Gunicorn configuration (Twelve-Factor: read from env, sane defaults).

Worker model: gthread (threaded sync workers). For a Django app whose slow
work is mostly DB/network I/O, threads give cheap concurrency without an async
rewrite, while keeping CPU-bound request handling predictable. Heavy I/O is
already pushed to Celery, so request workers stay short-lived.

Worker count defaults to (2 * CPU) + 1 but is env-overridable so it can be
tuned per deployment / container CPU limit.
"""
import multiprocessing
import os

bind = os.environ.get("GUNICORN_BIND", "0.0.0.0:8000")

_default_workers = multiprocessing.cpu_count() * 2 + 1
workers = int(os.environ.get("GUNICORN_WORKERS") or _default_workers)
threads = int(os.environ.get("GUNICORN_THREADS", "4"))
worker_class = "gthread"

# Recycle workers periodically to bound memory leaks (with jitter to avoid a
# thundering-herd restart).
max_requests = int(os.environ.get("GUNICORN_MAX_REQUESTS", "1000"))
max_requests_jitter = int(os.environ.get("GUNICORN_MAX_REQUESTS_JITTER", "100"))

timeout = int(os.environ.get("GUNICORN_TIMEOUT", "30"))
graceful_timeout = int(os.environ.get("GUNICORN_GRACEFUL_TIMEOUT", "30"))
keepalive = int(os.environ.get("GUNICORN_KEEPALIVE", "5"))

# Log to stdout/stderr so the container runtime / log pipeline collects them.
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("GUNICORN_LOG_LEVEL", "info")

# Use /dev/shm for the worker heartbeat tmp dir (avoids slow-disk stalls).
worker_tmp_dir = "/dev/shm"
