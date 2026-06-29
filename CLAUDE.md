# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Nextora POS — a production, multi-tenant **SaaS Restaurant POS** platform. Modular
monolith: one Django 5 project, many bounded contexts (Django apps under
`src/contexts/`) with Clean Architecture / DDD layering. Both a REST API
(`/api/v1/...`, DRF) and a server-rendered web UI (Django templates + a
hand-authored CSS design system) are served from the same project.

`PROJECT_CONTEXT.md` is the long-form architecture/handoff doc — read it for deep
detail on tenancy, RBAC, billing, and the POS engine. It predates some of the
codebase (the web UI, local SQLite dev, and the `customers`/`employees`/
`inventory`/`restaurant`/`reporting`/`marketing`/`super_admin` contexts), so trust
the actual source over it where they disagree.

## Commands

Two ways to run: **local (SQLite + venv)** is the current default dev mode;
**Docker (Postgres + Redis)** matches production and is required for anything
touching RLS, Celery brokers, or Postgres-specific behavior.

### Local (SQLite)
The repo's `.env` points `DATABASE_URL` at `sqlite:///db.sqlite3`. Run Django
directly through `manage.py` (which adds `src/` to the path):

```bash
python manage.py runserver          # dev server at http://localhost:8000
python manage.py migrate
python manage.py makemigrations
python manage.py createsuperuser
python manage.py shell
pytest                              # whole suite (uses config.settings.dev)
pytest tests/integration/test_pos_engine.py            # one file
pytest tests/integration/test_pos_engine.py::test_name # one test
pytest -k "discount and not refund"                    # by keyword
ruff check .                        # lint (also bandit security rules)
mypy src                            # type check
```

### Docker (production-shaped, Postgres + Redis)
`make help` lists everything. Common targets wrap `docker compose run --rm web ...`:

```bash
cp .env.example .env && edit .env   # set DJANGO_SECRET_KEY, point DATABASE_URL at postgres
make up          # build + run db, redis, web, worker, beat
make migrate / make makemigrations / make superuser / make shell
make test        # pytest in-container (real Postgres + Redis)
make lint / make typecheck / make audit   # ruff / mypy / pip-audit
make prod        # production-shaped stack (no dev override; adds nginx on :80)
```

### Project-specific setup commands (run after migrate)
```bash
python manage.py sync_permissions   # populate the global Permission catalog from code
python manage.py seed_roles         # seed the 9 system roles
python manage.py apply_rls          # install Postgres Row-Level Security (Postgres only; run as nextora_admin in prod)
python manage.py wait_for_db        # used by the Docker entrypoint
```

Root-level helper scripts (`create_admin.py`, `create_tenant.py`, `check_db.py`)
are throwaway local-dev bootstrap scripts run with `python <script>.py`; they are
not part of the application and should not be imported by app code.

## Testing notes

- `pytest` config lives in `pyproject.toml`. It runs with `--no-migrations`
  (schema built directly from models) and `--reuse-db`. If you change a model,
  the test DB is rebuilt only when you drop `--reuse-db` or delete it.
- Settings module for tests is `config.settings.dev`.
- Tests live in `tests/integration/` and `tests/unit/`; fixtures
  (`active_tenant`, `seeded`, `system_role`, …) are in `tests/conftest.py`.
- Because most rows are tenant-scoped and fail-closed, code that touches the ORM
  outside a request must run inside `tenant_scope(tenant_id)` (or `bypass_tenant()`)
  or queries return `.none()`. The same applies in the shell and in tests.

## Architecture essentials

### Clean Architecture layering (per context)
Dependencies point **inward**. Each context under `src/contexts/<name>/` is layered:
- `domain/` — pure Python, **no Django imports** (entities, value objects, enums,
  money/GST/bill calculations).
- `services/` (a.k.a. application) — use cases, orchestration, transactions. **All
  business logic lives here.** Views and serializers stay thin and call services.
- `models/` + `repositories/` — ORM persistence; keep models focused on persistence.
- `api/` — DRF serializers/viewsets; `urls.py` + `views.py` — server-rendered web UI.

`src/shared/` is the cross-context kernel with **no business rules**: base models,
tenancy machinery, structured logging, health probes, shared management commands.
Never reach into another context's ORM internals — go through its published services.

### Multi-tenancy (the dominant cross-cutting concern)
Shared DB, shared schema, `tenant_id` on every owned row, with defense-in-depth in
`src/shared/tenancy/`:
1. **Middleware** resolves the tenant from host (white-label domain or
   `<slug>.basedomain`), falling back to the user's single membership; sets a
   contextvar and a Postgres session GUC `app.current_tenant`.
2. **ORM managers** auto-filter every query by the current tenant and are
   **fail-closed** — no tenant in context → `.none()`.
3. **Write guard** in `TenantAwareModel.save` stamps `tenant_id` and rejects
   cross-tenant writes.
4. **Postgres RLS** (`apply_rls`) as the hard DB backstop (Postgres only).

Every tenant-owned model extends `TenantAwareModel`. Global/platform models
(`Tenant`, RBAC tables) do not; RBAC tables are `__rls_exempt__`. Platform staff
have `Membership.tenant = NULL`.

### Base models (`src/shared/infrastructure/models/base.py`)
`BaseModel` = `UUIDModel` (UUID PK) + `TimeStampedModel` (`created_at`/`updated_at`)
+ `AuditModel` (`created_by`/`updated_by` as actor UUIDs) + `SoftDeleteModel`
(`is_deleted`/`deleted_at`; default `objects` hides deleted, `all_objects` sees all).
This is the concrete enforcement of the model requirements in the rules below.

### Settings
Env-driven via `django-environ`, **no secret has a code default**.
`config/settings/base.py` (env-agnostic) → `dev.py` (debug toolbar, console email,
relaxed throttles, no HTTPS) / `prod.py` (imports `security.py`, Sentry, Prometheus,
fail-fast). `logging.py` builds JSON/console structured logging with request-id +
tenant-id correlation.

### Async & money
- **Celery** with three isolated queues — `critical` (payments/invoicing),
  `default`, `bulk` (reports/renewals) — plus Beat. In dev set
  `CELERY_TASK_ALWAYS_EAGER=true` to run tasks inline.
- **Money is always `Decimal`** (`DecimalField`), never float; carry `currency`.
  Helpers in `ordering/domain/finance.py`. Every mutation is `transaction.atomic`;
  money/numbering paths use `select_for_update`.

### The two "billing" contexts (don't confuse them)
- `billing/` — **SaaS subscriptions**: the platform billing *tenants* (plans,
  subscriptions, invoices). Gateway via ports/adapters (`fake` for tests,
  `razorpay` in prod), selected by `BILLING_GATEWAY`.
- `ordering/` — the **POS billing engine**: a restaurant billing its *customers*
  (orders, KOTs, payments, invoices with daily-reset numbers).

### Web UI / CSS
Server-rendered Django templates under `templates/`. CSS is a **hand-authored
design system** under `static/css/` (`tokens.css`, `main.css`, `base/`,
`components/`, `layouts/`, `zones/`) — there is no Node/`package.json` build step;
`tailwind.config.js` exists but the served CSS is the authored files in `static/`.
Design references: `DESIGN-nextora.md`, `DESIGN-apple.md`, `design-system/`,
and `/styleguide/`.

## Conventions

- Enums as `models.TextChoices` (editable via migrations), not native PG enums.
- Constraint/index naming `pk_/fk_/uq_/ck_/ix_<table>__<cols>` (`__<cond>` for
  partial); composite indexes lead with `tenant_id`.
- Services return explicit results or raise typed exceptions from the context's
  `exceptions.py`. Audit significant create/update/delete via `record_audit(...)`.
- RBAC is fully DB-driven (no hardcoded permission checks). Enforce with
  `RequirePermission("code")` (DRF) or `@require_permission`; the catalog of
  permissions/roles is defined as data in `identity/permissions/catalog.py`.

---

# Nextora POS Development Rules

- Never generate demo code.
- Always assume production.
- Never hardcode secrets.
- Always use environment variables.
- Use UUID primary keys.
- Every model must have:
  - created_at
  - updated_at
  - created_by
  - updated_by
  - soft delete support where appropriate
- Write migrations carefully.
- Every API requires authentication unless explicitly public.
- Validate all inputs.
- Use transactions for financial operations.
- Never duplicate business logic.
- Put business logic in service classes, not views.
- Keep models focused on persistence.
- Optimize queries with select_related/prefetch_related where appropriate.
- Add tests for critical business logic.
- Follow PEP 8 and use type hints.
- Document every major architectural decision.
