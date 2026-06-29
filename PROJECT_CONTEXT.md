# Nextora POS — Project Context & Handoff

> **Purpose of this file:** complete context for any AI tool or developer to understand
> the codebase and continue the work without re-deriving decisions. Read this top-to-bottom
> before changing anything. Last updated: 2026-06-27.

---

## 1. What this is

**Nextora POS** — a production, multi-tenant **SaaS Restaurant POS** platform (not a demo).

**Targets:** 10,000+ restaurants · 100,000 concurrent users · millions of invoices ·
multi-tenant · subscription-based · white-label capable · API-first · offline-capable (future).

**Engineering bar:** DDD-inspired, Clean Architecture, SOLID, Twelve-Factor, Repository/Service
layering, no fat views/models, no duplicated code, highly secure, highly maintainable.

---

## 2. Tech stack

- **Python 3.12+**, **Django 5**, **Django REST Framework**, Django Templates (web POS, later)
- **PostgreSQL** (shared DB, row-level multi-tenancy + RLS)
- **Redis** (cache, sessions, Celery broker, rate limits)
- **Celery + Celery Beat** (async + scheduled)
- **Docker** (multi-stage), **Gunicorn**, **Nginx**
- Tooling: `ruff`, `mypy`, `pytest`/`pytest-django`, `pip-audit`
- Payment gateway: **Razorpay** (integration-ready via ports/adapters; `fake` adapter for tests)

---

## 3. Architecture model (READ FIRST)

### 3.1 Modular monolith, Clean Architecture
- **One Django project, many bounded contexts** (Django apps under `src/contexts/`). Strict
  boundaries in code so contexts can later be extracted to services.
- **Dependency rule points inward.** Each context is layered:
  - `domain/` — pure Python, **NO Django imports** (entities, value objects, enums, calculations)
  - `application/` or `services/` — use cases, orchestration, transactions
  - `infrastructure/` / `models/` — ORM models, repositories, gateways
  - `api/` — DRF serializers/viewsets; `web/` — templates (later)
- Contexts talk via **published services** and (planned) **domain events / transactional outbox**.
  Never reach into another context's ORM internals.

### 3.2 Multi-tenancy (the most important cross-cutting concern)
**Model:** shared database, shared schema, `tenant_id` on every owned row, enforced by
**4 layers of defense-in-depth**:
1. **Middleware** (`shared/tenancy/middleware.py`) resolves tenant from host (white-label domain
   or `<slug>.basedomain`), falls back to the user's single membership, sets a contextvar **and**
   a Postgres session GUC `app.current_tenant`.
2. **ORM managers** (`shared/tenancy/managers.py`) auto-filter every query by current tenant.
   **Fail-closed**: no tenant in context → `.none()` (never returns another tenant's data).
3. **Write guard** (`TenantAwareModel.save`) auto-stamps `tenant_id` and rejects cross-tenant writes.
4. **PostgreSQL Row-Level Security** (`apply_rls` mgmt command) — hard DB backstop.

**Two DB roles required in prod:** `nextora_app` (subject to RLS, used by web/worker) and
`nextora_admin` (`BYPASSRLS`, used by migrations/backups/cross-tenant jobs).

**`tenant_scope(tenant_id)`** (`shared/tenancy/scope.py`) binds both contextvar + DB GUC; used by
Celery tasks and services running outside a request. `bypass_tenant()` for deliberate cross-tenant
reads (resolver, backups, lifecycle scan).

### 3.3 Reusable base models (`shared/infrastructure/models/base.py`)
- `UUIDModel` — UUIDv4 PK (note: **design recommends UUIDv7 for high-volume tables** — not yet implemented)
- `TimeStampedModel` — `created_at`/`updated_at`
- `AuditModel` — `created_by`/`updated_by` (actor UUIDs, not FKs)
- `SoftDeleteModel` — `is_deleted`/`deleted_at`, default manager hides deleted; `all_objects` sees all
- `BaseModel` = all of the above
- `TenantAwareModel` (`shared/tenancy/models.py`) = `BaseModel` + `tenant` FK + tenant managers + write guard.
  **Every tenant-owned model extends this.**

---

## 4. Folder structure

```
D:\NEXTORA_POS\
├── config/                       # project config (NOT business code)
│   ├── settings/ base.py · dev.py · prod.py · security.py · logging.py
│   ├── celery.py (3 queues: critical/default/bulk) · urls.py · wsgi/asgi.py
├── src/
│   ├── shared/                   # cross-context kernel (no business rules)
│   │   ├── domain/               # Entity, AggregateRoot, ValueObject, DomainEvent (pure)
│   │   ├── application/           # Result, ApplicationService base
│   │   ├── infrastructure/
│   │   │   ├── models/base.py     # UUID/Timestamp/Audit/SoftDelete/BaseModel + managers
│   │   │   └── logging/           # JSON formatter, context filter, RequestIDMiddleware
│   │   ├── tenancy/               # context, managers, models, db(GUC), resolver, middleware,
│   │   │                          #   scope, routing(sharding stub), exceptions
│   │   ├── api/health.py          # liveness + readiness probes
│   │   └── management/commands/   # wait_for_db, seed_demo, apply_rls, export_tenant, import_tenant
│   └── contexts/                  # bounded contexts (Django apps)
│       ├── tenants/               # Tenant, TenantDomain (global root of isolation)
│       ├── identity/              # custom User (email) + RBAC (see §5)
│       ├── audit/                 # AuditLog (append-only) + record_audit() + actor middleware
│       ├── billing/               # SaaS subscriptions (see §6)
│       ├── catalog/               # products/categories/modifiers/variants/GST (see §7)
│       └── ordering/              # POS billing engine (see §8)
├── deploy/ docker/(Dockerfile, entrypoint.sh) · gunicorn/ · nginx/ · scripts/(backup/restore)
├── requirements/ base.txt · dev.txt · prod.txt
├── tests/ unit/ · integration/ · conftest.py
├── docker-compose.yml · docker-compose.override.yml (dev)
├── pyproject.toml · Makefile · manage.py · .env.example · README.md
└── PROJECT_CONTEXT.md  (this file)
```

---

## 5. Built contexts & status

### `tenants` ✅
`Tenant` (slug, status: trial/active/suspended/churned, currency, tz) + `TenantDomain`
(white-label hosts, one primary). Global (no tenant_id). Status state machine + partial unique on primary domain.

### `identity` + RBAC ✅
- Custom `User` (email login, UUID PK, Argon2). `AUTH_USER_MODEL="identity.User"`.
- **Enterprise RBAC, fully DB-driven, NO hardcoded permissions:**
  - `Permission` (global catalog) · `Role` (system templates or tenant-owned, scope: platform/company/branch)
    · `RolePermission` (editable grants) · `Membership` (user↔tenant↔role, optional `location_id` for branch scope)
  - 9 roles: super_admin, support, company_owner, branch_manager, cashier, kitchen_staff, waiter,
    inventory_manager, accountant. Defined as **blueprints** in `permissions/catalog.py` (data, seeded → DB).
  - `services/authorization.py` → `has_permission(user, code, tenant, location)` — reads DB, Redis-cached
    with a version counter bumped by signals on any RBAC change.
  - Enforcement: `api/permissions.py` → `RequirePermission("code")` DRF class + `@require_permission` decorator.
  - Commands: `sync_permissions`, `seed_roles`. `provision_tenant_roles()` clones templates per tenant.
  - RBAC tables are `__rls_exempt__` (nullable tenant_id = platform); `apply_rls` skips them.

### `audit` ✅
`AuditLog` (append-only, tenant-scoped, `delete()` raises). `record_audit(action, entity_type, entity_id, changes)`
reads tenant+actor+ip from context. `AuditContextMiddleware` captures actor/IP.

### `billing` (SaaS subscriptions — bills TENANTS, not restaurant customers) ✅
- `Plan` + `PlanPrice` (monthly/quarterly/yearly) with limits (max_branches/employees/invoices/storage) + features
- `Subscription` (trialing→active→past_due(+grace)→expired/canceled; one-live-per-tenant partial unique)
- `SubscriptionInvoice` + `BillingSequence` (gapless) · `SubscriptionPayment` · `UsageCounter` · `WebhookEvent`
- Services: `subscription_service` (create/change/cancel), `invoice_service` (generate/mark_paid),
  `lifecycle` (Celery Beat `run_billing_cycle`, hourly), `entitlements` (limits), `usage` (tracking + `enforce_limit`)
- **Gateway = ports/adapters:** `gateways/base.py` (port), `razorpay.py` (guarded SDK), `fake.py` (tests).
  Selected by `settings.BILLING_GATEWAY`. Webhook receiver at `/webhooks/billing/razorpay/` (idempotent, HMAC-verified).

### `catalog` (products) ✅
- `Category` (self-ref tree) · `Product` · `ProductVariant` · `ProductImage` · `ModifierGroup`/`Modifier`/`ProductModifierGroup`
  · `TaxClass` (GST rate+cess) · `Printer`/`KitchenStation` (routing targets)
- GST split (CGST/SGST vs IGST) computed in `domain/gst.py` (place-of-supply at sale time, not stored)
- SKU/barcode partial-unique per tenant (reusable after soft delete)
- `services/product_service.py` (CRUD + audit + `resolve_routing` inheritance + category cycle guard)
- `services/import_export.py` (CSV bulk import/export, row-resilient, streaming export)
- API: `ProductViewSet` gated by `catalog.view`/`catalog.manage`; `/api/v1/catalog/products/` + export/import_csv actions

### `ordering` (POS billing engine — bills restaurant CUSTOMERS) ✅
- `Order` + `OrderItem` + `OrderItemModifier` · `KOT`+`KOTItem` · `Payment` · `Invoice` · `DailyCounter`
- `domain/billing.py` `compute_bill()` — subtotal, proportional discount, per-line GST, service charge, round-off
- Services: `order_service` (create/add/discount/split/merge/void/recalc), `payment_service`
  (partial + multi-method cash/card/upi/credit + refund, **idempotent + IntegrityError-safe**),
  `invoice_service` (settle + **daily-reset** number, idempotent, row-locked), `kot_service`
  (kitchen routing), `sequences` (concurrency-safe `SELECT…FOR UPDATE` numbering), `printing` (ESC/POS thermal)
- Invoice numbers reset daily via `DailyCounter` keyed by date; format `INV{yymmdd}-{NNNN}`.

---

## 6. Conventions (FOLLOW THESE)

- **Money:** `Decimal` everywhere (`DecimalField(max_digits=12-14, decimal_places=2)`); never float.
  Helpers `q()` / `round_to_nearest()` in `ordering/domain/finance.py`. Always carry `currency`.
- **UUID PKs** on everything. (Switch high-volume tables to UUIDv7 generation when implementing — TODO.)
- **Time:** `timestamptz`, UTC, `_at` suffix.
- **Enums:** `models.TextChoices` (not native PG enums) so they're editable via migrations.
- **Constraints/indexes naming:** `pk_/fk_/uq_/ck_/ix_<table>__<cols>`; partial indexes append `__<cond>`.
- **Composite indexes lead with `tenant_id`** (every query is tenant-scoped).
- **Services return explicit results / raise typed exceptions** (per-context `exceptions.py`); thin views.
- **Every mutation** is `transaction.atomic`; money/numbering paths use `select_for_update`.
- **Audit** every significant create/update/delete via `record_audit(...)`.
- **Settings:** env-driven (`django-environ`), no secret defaults; `base.py` (env-agnostic) → `dev.py`/`prod.py`;
  `security.py` imported by prod only; `logging.py` builds JSON logging.

---

## 7. ⚠️ CRITICAL: current state & gotchas

1. **NO migration files exist yet.** Models are written but `makemigrations` has not been run/committed.
   - Tests run with `--no-migrations` (schema built from models — see `pyproject.toml addopts`).
   - **Before first real deploy:** `python manage.py makemigrations` for all contexts, review, commit.
   - `AUTH_USER_MODEL` is set, so the **first** migration must create `identity.User` correctly.
2. **RLS is not auto-applied.** After migrations run `python manage.py apply_rls` (as `nextora_admin`),
   or bake its `--dry-run` SQL into a `RunSQL` migration for prod.
3. **No DB/Redis available in the dev environment used so far** — all code was validated with
   `python -m compileall` (syntax) only. Tests are written but **have not been executed**; run them
   in the Docker stack (`make test`) which provides Postgres + Redis.
4. **Two contexts named "billing-ish":** `billing` = SaaS subscriptions (platform→tenant);
   `ordering` = POS bills (restaurant→customer). Don't confuse them.
5. **`Order` table is literally named `"order"`** (SQL reserved word; Django quotes it — fine, but noted).
6. **Branch/Location model not built yet.** `location_id` is a soft UUID reference in several places
   (ordering, catalog routing, RBAC membership). Promote to a real FK when the branch module is built.
7. Platform staff (super_admin/support) use `Membership.tenant = NULL`; resolver/authorization handle this.

---

## 8. How to run / develop

```bash
cp .env.example .env            # set DJANGO_SECRET_KEY etc.
make up                         # docker: db, redis, web, worker, beat
make makemigrations && make migrate
make superuser
python manage.py seed_roles     # RBAC permissions + 9 system roles
python manage.py apply_rls      # RLS policies (run as admin role in prod)
make test                       # pytest (Postgres+Redis via docker)
make lint                       # ruff
make typecheck                  # mypy
```

- Health: `/healthz/live/`, `/healthz/ready/`
- API: `/api/v1/catalog/products/` · Admin: `/admin/`
- Celery queues: `critical` (payments/invoicing), `default`, `bulk` (reports/renewals)

---

## 9. Known issues / deliberately deferred (from the last audit)

| Item | Status |
|---|---|
| Transactional audit everywhere | Done for payments/invoices; catalog/order audit is just-outside-tx by policy (audit failure won't roll back business write). Decide if you want it strictly transactional. |
| JWT-claim tenant resolution | Middleware resolves by host + session-membership fallback. **JWT tenant claim not resolved in middleware** (DRF sets `request.user` after middleware). Needs token decode in middleware or a DRF auth/permission layer. |
| `enforce_limit` TOCTOU | Soft-limit check-then-act; add `select_for_update` on the usage counter at each constrained call site when wiring enforcement. |
| UUIDv7 for hot tables | Design recommends it; still UUIDv4 everywhere. |
| `collectstatic` to shared volume | Works; cleaner is WhiteNoise-per-image (drop shared static volume). |
| Catalog full-text GIN search index | Designed, not built. |
| Proration on plan change | Out of scope; change applies next renewal. |

---

## 10. Roadmap / suggested next steps

1. **Generate & commit migrations** for all contexts; bake RLS into a `RunSQL` migration. (HIGHEST PRIORITY)
2. **Run the full test suite** in Docker; fix anything the live DB surfaces.
3. **Branch/Location module** (`tenants` or new context) → convert `location_id` soft refs to FKs.
4. **Tenant onboarding flow** (vertical slice): create tenant → provision RBAC roles → owner membership
   → start trial subscription → seed default branch/printers/kitchen stations.
5. **Inventory context** (stock per branch, recipes/BOM, deduct on order settle).
6. **Transactional outbox + domain events** (designed in architecture, not yet built) → reporting projections,
   notifications, webhooks, future offline sync.
7. **DRF API surface** for ordering (POS terminal) + KDS live board (websockets/ASGI).
8. **JWT tenant-claim resolution** + API-on-central-domain support.
9. Reporting context (read replicas + rollups), notifications context.

---

## 11. Key files to read first (for orientation)

- `config/settings/base.py` — wiring of everything
- `src/shared/tenancy/` — the isolation model (start with `models.py`, `middleware.py`, `managers.py`)
- `src/shared/infrastructure/models/base.py` — base model stack
- `src/contexts/identity/services/authorization.py` + `permissions/catalog.py` — RBAC
- `src/contexts/ordering/domain/billing.py` + `services/*` — POS engine
- `src/contexts/billing/services/lifecycle.py` + `gateways/` — subscriptions
- `tests/conftest.py` — fixtures (`active_tenant`, `seeded`, `system_role`, etc.)

---

## 12. Validation status

All code byte-compiles (`python -m compileall`). **Tests written, NOT yet executed** (no live DB in
the authoring environment). Test counts: RBAC ~18, billing ~16+6, catalog ~16+4, POS ~21+6 (+ earlier
foundation). Run `make test` to execute.
```
