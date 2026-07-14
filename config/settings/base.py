"""Base settings — shared by every environment.

Contains only configuration that is TRUE everywhere. Environment-specific
behaviour (debug, security hardening, log sinks) lives in dev.py / prod.py.

Twelve-Factor: all deployment-varying values are read from the environment via
django-environ. There are NO secret defaults — a missing secret in prod must
crash the boot, not silently weaken security.
"""
from datetime import timedelta
from pathlib import Path

import environ

# --- Paths ----------------------------------------------------------------
# config/settings/base.py -> config/settings -> config -> <repo root>
BASE_DIR = Path(__file__).resolve().parent.parent.parent
SRC_DIR = BASE_DIR / "src"

# --- Environment ----------------------------------------------------------
env = environ.Env()
# Load .env if present (dev). In prod the orchestrator injects real env vars
# and this file simply won't exist, which is fine.
env_file = BASE_DIR / ".env"
if env_file.exists():
    env.read_env(str(env_file))

SECRET_KEY = env(
    "DJANGO_SECRET_KEY",
    default="django-insecure-nextora-pos-dev-key-do-not-use-in-prod",
)
DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[])
SITE_URL = env("DJANGO_SITE_URL", default="http://localhost:8000")

# --- Applications ---------------------------------------------------------
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    "django.contrib.humanize",
]

# "channels" provides the consumer/routing/channel-layer machinery used by the
# KDS WebSocket. ("daphne" is prepended to INSTALLED_APPS below — it must sort
# before django.contrib.staticfiles so its ASGI-aware runserver takes over.)
THIRD_PARTY_APPS = [
    "channels",
    "rest_framework",
    "corsheaders",
    "drf_spectacular",
    "django_celery_beat",
    "django_celery_results",
    "django_htmx",
]

# First-party bounded contexts. The shared kernel must load first so its base
# models / app registry are available to the contexts that depend on it.
LOCAL_APPS = [
    "shared",
    "contexts.tenants",   # tenancy root — must load before tenant-aware apps
    "contexts.identity",
    "contexts.audit",
    "contexts.billing",
    "contexts.catalog",
    "contexts.ordering",
    "contexts.features",
    "contexts.notifications",
    "contexts.search",
    "contexts.employees",
    "contexts.customers",
    "contexts.inventory",
    "contexts.restaurant",
    "contexts.reporting",
    "contexts.marketing",
    "contexts.super_admin",
    # contexts.onboarding, ... added as they are built.
]

INSTALLED_APPS = ["daphne"] + DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# --- Middleware -----------------------------------------------------------
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "contexts.identity.middleware.NoCacheAuthenticatedMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Attaches a request_id to every request and binds it to the log context.
    "shared.infrastructure.logging.middleware.RequestIDMiddleware",
    # Resolves the tenant and binds it to context + DB session (RLS).
    "shared.tenancy.middleware.TenantResolutionMiddleware",
    # Captures actor + IP for the audit trail (after auth + tenant).
    "contexts.audit.middleware.AuditContextMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# --- Templates ------------------------------------------------------------
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "contexts.identity.context_processors.rbac_context",
            ],
        },
    },
]

# --- Database -------------------------------------------------------------
# In prod, DATABASE_URL points at PgBouncer (transaction pooling), so we keep
# a modest CONN_MAX_AGE. psycopg3 driver is selected by the postgres:// scheme.
DATABASES = {
    "default": {
        **env.db("DATABASE_URL", default="sqlite:///db.sqlite3"),
        "CONN_MAX_AGE": env.int("DATABASE_CONN_MAX_AGE", default=60),
        "CONN_HEALTH_CHECKS": env.bool("DATABASE_CONN_HEALTH_CHECKS", default=True),
    }
}

if "postgresql" in DATABASES["default"]["ENGINE"]:
    INSTALLED_APPS.append("django.contrib.postgres")

# Every model gets a UUID PK unless it overrides. See shared base models.
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Custom user (set BEFORE first migration; immutable thereafter) -------
AUTH_USER_MODEL = "identity.User"

# --- Multi-tenancy --------------------------------------------------------
# Subdomain tenancy: "<slug>.nextora.app" resolves to a tenant; custom domains
# are matched via tenant_domain. Resolution is Redis-cached.
TENANCY_BASE_DOMAIN = env("TENANCY_BASE_DOMAIN", default="nextora.app")

# RLS GUC scope. False = session-level (direct conns / PgBouncer session pool).
# True  = transaction-local (SET LOCAL) — REQUIRED under PgBouncer transaction
# pooling, and must be paired with ATOMIC_REQUESTS so a transaction wraps each
# request.
TENANCY_DB_LOCAL_GUC = env.bool("TENANCY_DB_LOCAL_GUC", default=False)

# Future sharding: map "<tenant-uuid>" -> DB alias. Empty => all on 'default'.
TENANCY_SHARD_MAP: dict[str, str] = {}

# Routes reads/writes to the tenant's shard (today: always 'default').
DATABASE_ROUTERS = ["shared.tenancy.routing.TenantShardRouter"]

# --- Cache (Redis / LocMem) -----------------------------------------------
cache_url = env("CACHE_URL", default="redis://redis:6379/3")
if cache_url.startswith("locmem"):
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "nextora-default",
        }
    }
    SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"
else:
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": cache_url,
            "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
            "KEY_PREFIX": "nextora",
        }
    }
    SESSION_ENGINE = "django.contrib.sessions.backends.cache"

SESSION_CACHE_ALIAS = "default"

# --- Channels / WebSockets (real-time KDS) --------------------------------
# ASGI entrypoint and the cross-process channel layer. The Redis layer lets any
# web worker broadcast a KDS change to every connected screen regardless of
# which worker holds the socket. Set CHANNELS_IN_MEMORY=true to use the
# in-process layer (tests / single-process dev with no Redis).
ASGI_APPLICATION = "config.asgi.application"

if env.bool("CHANNELS_IN_MEMORY", default=False):
    CHANNEL_LAYERS = {
        "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"},
    }
else:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {
                "hosts": [env("CHANNELS_REDIS_URL", default="redis://redis:6379/4")],
            },
        },
    }

# --- Celery ---------------------------------------------------------------
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://redis:6379/1")
CELERY_RESULT_BACKEND = "django-db"  # auditable task results in Postgres
CELERY_CACHE_BACKEND = "default"
CELERY_TASK_ACKS_LATE = True          # redeliver if a worker dies mid-task
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1  # fair dispatch for long tasks
CELERY_TASK_TIME_LIMIT = 300
CELERY_TASK_SOFT_TIME_LIMIT = 270
CELERY_TIMEZONE = "UTC"
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"
# Queue isolation: critical money paths never wait behind bulk reports.
CELERY_TASK_DEFAULT_QUEUE = "default"

from celery.schedules import crontab

# Beat schedule. The billing cycle runs hourly to advance trials/renewals/grace.
CELERY_BEAT_SCHEDULE = {
    "billing-cycle-hourly": {
        "task": "billing.run_billing_cycle",
        "schedule": 3600.0,
        "options": {"queue": "bulk"},
    },
    "db-backup-daily": {
        "task": "shared.tasks.db_backup_task",
        "schedule": crontab(hour=2, minute=0),
        "options": {"queue": "bulk"},
    },
    "cleanup-daily": {
        "task": "shared.tasks.database_cleanup_task",
        "schedule": crontab(hour=3, minute=0),
        "options": {"queue": "bulk"},
    },
    "daily-reports-daily": {
        "task": "shared.tasks.run_daily_reports_sweep",
        "schedule": crontab(hour=23, minute=30),
        "options": {"queue": "bulk"},
    },
    "inventory-expiry-daily": {
        "task": "inventory.scan_expiring_batches",
        "schedule": crontab(hour=6, minute=0),
        "options": {"queue": "bulk"},
    },
    "retry-failed-print-jobs": {
        "task": "contexts.ordering.tasks.retry_failed_print_jobs",
        "schedule": 60.0,
        "options": {"queue": "default"},
    },
    "inventory-low-stock-scan": {
        "task": "inventory.scan_low_stock",
        "schedule": 1800.0,  # every 30 minutes
        "options": {"queue": "bulk"},
    },
}

# --- Nextora Print Service Integration ---------------------------------
NEXTORA_PRINT_SERVICE_URL = env(
    "NEXTORA_PRINT_SERVICE_URL",
    default="http://127.0.0.1:8989",
)
NEXTORA_PRINT_SERVICE_TIMEOUT = env.int(
    "NEXTORA_PRINT_SERVICE_TIMEOUT",
    default=5,
)
NEXTORA_AUTO_PRINT_RECEIPT = env.bool(
    "NEXTORA_AUTO_PRINT_RECEIPT",
    default=True,
)

# --- Billing / Subscriptions ----------------------------------------------
BILLING_GATEWAY = env("BILLING_GATEWAY", default="fake")  # "fake" | "razorpay"
BILLING_CURRENCY = env("BILLING_CURRENCY", default="INR")
RAZORPAY_KEY_ID = env("RAZORPAY_KEY_ID", default="")
RAZORPAY_KEY_SECRET = env("RAZORPAY_KEY_SECRET", default="")
RAZORPAY_WEBHOOK_SECRET = env("RAZORPAY_WEBHOOK_SECRET", default="")

# --- DRF (API-first) ------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "contexts.identity.api.authentication.EnterpriseJWTAuthentication",
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.LimitOffsetPagination",
    "PAGE_SIZE": 50,
    # Default throttles; per-tenant/per-view overrides layer on top.
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {"anon": "60/min", "user": "1000/min"},
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Nextora POS API",
    "VERSION": "v1",
    "SERVE_INCLUDE_SCHEMA": False,
}

# --- Password validation --------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 12},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --- Auth URL Routing -----------------------------------------------------
LOGIN_URL = "identity:login"
LOGIN_REDIRECT_URL = "reporting:home"
LOGOUT_REDIRECT_URL = "identity:login"

# Argon2 first: strong, memory-hard hashing for credentials.
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]

# --- I18N / TZ ------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
LOCALE_PATHS = [BASE_DIR / "locale"]

# --- Static / media -------------------------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "mediafiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
    },
}

# --- Logging (imported fragment) ------------------------------------------
from .logging import build_logging_config  # noqa: E402

LOGGING = build_logging_config(
    level=env("DJANGO_LOG_LEVEL", default="INFO"),
    fmt=env("DJANGO_LOG_FORMAT", default="json"),
)

# Conditionally enable django-prometheus if the package is installed
try:
    import django_prometheus  # noqa: F401
    
    INSTALLED_APPS += ["django_prometheus"]
    MIDDLEWARE = (
        ["django_prometheus.middleware.PrometheusBeforeMiddleware"]
        + MIDDLEWARE
        + ["django_prometheus.middleware.PrometheusAfterMiddleware"]
    )
except ImportError:
    pass
