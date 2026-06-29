"""Security hardening fragment — imported ONLY by prod (and staging).

Isolating these toggles guarantees:
  * Production is secure-by-default (HTTPS, secure cookies, HSTS, headers).
  * Development never accidentally inherits production-only constraints
    (e.g. SSL redirect) that would break local http.

Values are still env-overridable so an operator can tune per deployment, but
the *defaults here are the safe ones*.
"""
import environ

env = environ.Env()

# --- Transport ------------------------------------------------------------
# Trust the X-Forwarded-Proto header set by Nginx (TLS terminates at the edge).
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=True)

# --- HSTS -----------------------------------------------------------------
SECURE_HSTS_SECONDS = env.int("DJANGO_SECURE_HSTS_SECONDS", default=31536000)  # 1y
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# --- Cookies --------------------------------------------------------------
SESSION_COOKIE_SECURE = env.bool("DJANGO_SESSION_COOKIE_SECURE", default=True)
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = env.bool("DJANGO_CSRF_COOKIE_SECURE", default=True)
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[])

# --- Headers --------------------------------------------------------------
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
X_FRAME_OPTIONS = "DENY"

# --- CORS (API consumers; white-label front-ends) -------------------------
CORS_ALLOWED_ORIGINS = env.list("DJANGO_CORS_ALLOWED_ORIGINS", default=[])
CORS_ALLOW_CREDENTIALS = True
