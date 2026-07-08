# Nextora POS — Comprehensive Technical Knowledge Base & Architectural Source of Truth

> **Document Status:** Official Single Source of Truth (`project_analysis.md`)  
> **Last Updated:** 2026-07-08 (Sidebar Navigation & Scroll Preservation Engine Added)  
> **System Scope:** Multi-Tenant SaaS Point of Sale (POS) Platform for Ambitious Restaurants  

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Complete Architecture Overview](#2-complete-architecture-overview)
3. [Backend Documentation](#3-backend-documentation)
4. [Frontend Documentation](#4-frontend-documentation)
5. [Database Documentation](#5-database-documentation)
6. [ER Relationship Overview](#6-er-relationship-overview)
7. [API Documentation](#7-api-documentation)
8. [Authentication Flow](#8-authentication-flow)
9. [Authorization Flow](#9-authorization-flow)
10. [POS Business Workflows](#10-pos-business-workflows)
11. [Folder Structure](#11-folder-structure)
12. [Design Decisions](#12-design-decisions)
13. [Coding Standards](#13-coding-standards)
14. [Current Features](#14-current-features)
15. [Pending Features](#15-pending-features)
16. [Known Bugs](#16-known-bugs)
17. [Performance Notes](#17-performance-notes)
18. [Security Notes](#18-security-notes)
19. [Technical Debt](#19-technical-debt)
20. [Future Improvement Suggestions](#20-future-improvement-suggestions)

---

## 1. Executive Summary

**Nextora POS** is an enterprise-grade, multi-tenant SaaS Point-of-Sale platform engineered specifically for high-volume restaurant chains, cafes, cloud kitchens, and hospitality brands. Designed to operate at high concurrency (targeting 10,000+ restaurants and 100,000+ concurrent operators), Nextora POS combines deterministic financial arithmetic with low-latency operational workflows.

### Key Architectural Pillars
- **Clean Architecture & Modular Monolith:** Built on Django 5 and Django REST Framework (DRF), the codebase strictly isolates business domain logic (`domain/`) from framework infrastructure (`infrastructure/`, `models/`, `views/`).
- **Four-Tier Defense-in-Depth Multi-Tenancy:** Guarantees absolute row-level isolation between tenant chains via:
  1. **Tenant Resolution Middleware** (`TenantResolutionMiddleware`)
  2. **Fail-Closed ORM Managers** (`TenantManager`)
  3. **Write-Guard Enforced Models** (`TenantAwareModel`)
  4. **PostgreSQL Row-Level Security (RLS)** (`app.current_tenant` GUC sessions)
- **High-Precision POS & Financial Engine:** Uses exact `Decimal` arithmetic for subtotaling, proportional discount allocation, intra-state (CGST/SGST) and inter-state (IGST) tax calculation, service charges, and configurable round-off.
- **Real-Time Kitchen Display System (KDS):** Powered by Django Channels and Redis Channels layer over WebSockets (`/ws/events`), providing zero-refresh ticket synchronization across kitchen stations.
- **Nextora Forge Design System:** A bespoke, operations-first visual language tailored for rapid cashier touch terminals, high-density manager dashboards, and full light/dark theme coexistence.

---

## 2. Complete Architecture Overview

```
                                  +---------------------------------------+
                                  |         External Clients              |
                                  |  (POS Touch Terminals, Web Browsers,  |
                                  |    Mobile KDS Boards, API Consumers)  |
                                  +-------------------+-------------------+
                                                      |
                                        HTTP / REST / WebSocket
                                                      v
+---------------------------------------------------------------------------------------------------+
| NGINX REVERSE PROXY / DAPHNE (ASGI) / GUNICORN (WSGI)                                            |
+---------------------------------------------------------------------------------------------------+
  |                                                                                               |
  | 1. Request Resolution & Security Chain                                                        |
  +---> [RequestIDMiddleware] ---> [TenantResolutionMiddleware] ---> [AuditContextMiddleware]     |
                                          |                                                       |
                                          v                                                       |
  +--------------------------------------------------------------------------------------------+  |
  | BOUNDED CONTEXTS (Django Apps under src/contexts/)                                         |  |
  |                                                                                            |  |
  |   +-------------------+  +-------------------+  +-------------------+  +---------------+   |  |
  |   |    Identity       |  |     Tenants       |  |      Catalog      |  |   Ordering    |   |  |
  |   | (User/Enterprise  |  |  (Tenant/Domain/  |  |  (Products/GST/   |  |  (POS Bills/  |   |  |
  |   |      RBAC)        |  |  Settings/Branch) |  | Modifiers/Printers)|  | Payments/KOT) |   |  |
  |   +---------+---------+  +---------+---------+  +---------+---------+  +-------+-------+   |  |
  |             |                      |                      |                    |           |  |
  |   +---------+---------+  +---------+---------+  +---------+---------+  +-------+-------+   |  |
  |   |     Inventory     |  |    Restaurant     |  |     Billing       |  |   Reporting   |   |  |
  |   |  (Stock/Batches/  |  |  (Dining Tables/  |  | (SaaS Subscription|  |  (Analytics   |   |  |
  |   |    Suppliers)     |  |   Operations)     |  |     & Plans)      |  |  & Dashboards)|   |  |
  |   +-------------------+  +-------------------+  +-------------------+  +---------------+   |  |
  +--------------------------------------------------------------------------------------------+  |
                                          |                                                       |
                                          v                                                       |
  +--------------------------------------------------------------------------------------------+  |
  | SHARED KERNEL (src/shared/)                                                                |  |
  |  - Base Models: UUIDModel, TimeStampedModel, AuditModel, SoftDeleteModel, TenantAwareModel |  |
  |  - Pure Domain Primitives & Value Objects (No ORM dependencies)                            |  |
  |  - Tenancy Scope ContextVars (`tenant_scope`, `bypass_tenant`) & Shard Router              |  |
  +--------------------------------------------------------------------------------------------+  |
              |                                     |                                   |
              v                                     v                                   v
+-----------------------------+     +-------------------------------+     +---------------------------+
|      POSTGRESQL DB          |     |          REDIS CACHE          |     |    CELERY ASYNC WORKERS   |
|  - Shared Schema            |     |  - Sessions & RBAC Cache      |     |  - Queue: critical/default|
|  - RLS Policies Enforced    |     |  - Rate Limiting / Throttling |     |  - Celery Beat Scheduler  |
|  - ACID / FOR UPDATE Locks  |     |  - Channels Pub/Sub Layer     |     |  - Billing & Reports      |
+-----------------------------+     +-------------------------------+     +---------------------------+
```

### Layer Isolation & Dependency Rule
In accordance with Clean Architecture principles, code dependencies point strictly inward toward pure business logic:
1. **Domain Layer (`domain/`):** Pure Python data structures, calculations, and invariants (`compute_bill`, `compute_gst`). Zero imports from `django.db` or external SDKs.
2. **Application / Service Layer (`services/`):** Orchestrates domain logic, executes database transactions (`transaction.atomic`), manages concurrency locks (`select_for_update`), and writes append-only audit entries.
3. **Infrastructure Layer (`models/`, `repositories/`):** ORM models extending `TenantAwareModel` or `BaseModel`, custom querysets, and third-party gateway adapters (`RazorpayGateway`).
4. **Interface / Delivery Layer (`api/`, `views.py`, `templates/`):** Thin controllers handling request validation, serializer mapping, permissions (`RequirePermission`), and HTML/JSON responses.

---

## 3. Backend Documentation

### Module Directory & Responsibilities

| Context / Module | Primary Purpose | Core Responsibilities & Capabilities | Key Dependencies |
| :--- | :--- | :--- | :--- |
| **`shared`** | Cross-Context Kernel | Base abstract ORM models (`UUIDModel`, `TenantAwareModel`, `SoftDeleteModel`), JSON logging infrastructure, `RequestIDMiddleware`, multi-tenancy context resolution, RLS execution, health probes (`/healthz/live`). | Core Python, Django DB |
| **`contexts.tenants`** | Tenancy & Root Global Isolation | Global `Tenant` root entity, custom host/domain mapping (`TenantDomain`), global configuration settings (`TenantConfiguration`), tenant lifecycle management. | `shared` |
| **`contexts.identity`** | Authentication & Enterprise RBAC | Argon2 custom `User` identity, fully DB-driven RBAC blueprint system (`Permission`, `Role`, `RolePermission`, `Membership`), cached high-performance authorization engine (`has_permission`). | `shared`, `tenants` |
| **`contexts.audit`** | Immutable Compliance Audit Trail | Append-only `AuditLog` model recording actor, IP, timestamp, entity diffs, and action metadata. Hardened against programmatic updates or deletions. | `shared`, `identity` |
| **`contexts.catalog`** | Menu, Pricing & Tax Catalog | Nested `Category` hierarchies, `Product`, `ProductVariant`, `ModifierGroup`, Indian GST tax classification (`TaxClass`), kitchen station/thermal printer routing, CSV bulk import/export. | `shared`, `audit` |
| **`contexts.ordering`** | POS Billing & Kitchen Ordering Engine | Customer order lifecycle (`Order`, `OrderItem`), KOT generation (`KOT`, `KOTItem`), idempotent multi-method payment capture (`Payment`), gapless daily invoice numbering (`DailyCounter`). | `shared`, `catalog`, `identity` |
| **`contexts.inventory`** | Multi-Branch Inventory & Supply Chain | Stock tracking (`InventoryItem`, `Batch`), purchase orders (`PurchaseOrder`), suppliers (`Supplier`), inter-branch transfers (`StockTransfer`), stock adjustments, wastage/damaged stock tracking. | `shared`, `catalog`, `restaurant` |
| **`contexts.restaurant`** | Restaurant & Table Operations | Dining table layouts (`DiningTable`), branch operations (`Branch`), operational kitchen stations (`KitchenStation`), hardware printer profiles (`Printer`), cash registers (`CashCounter`). | `shared`, `tenants` |
| **`contexts.billing`** | SaaS Platform Subscription Engine | Platform billing for restaurant tenants: subscription tiers (`Plan`, `PlanPrice`), usage quota enforcement (`Subscription`, `UsageCounter`), gapless SaaS invoices, Razorpay webhook integration. | `shared`, `tenants` |
| **`contexts.reporting`** | Operational Analytics & Dashboards | Real-time sales summaries, revenue rollups, hourly velocity charts, cashier shift performance, and invoice export views. | `ordering`, `catalog`, `inventory` |
| **`contexts.customers`** | CRM, Loyalty & Wallets | Customer directory (`Customer`), loyalty points ledger (`LoyaltyProgram`, `PointsLedger`), stored-value digital wallets (`WalletTransaction`), coupon discounts (`Coupon`). | `shared` |
| **`contexts.employees`** | Staff Management & Attendance | Employee profiles (`EmployeeProfile`), shift scheduling (`Shift`), time-clock attendance (`Attendance`), leave workflows (`LeaveRequest`), payroll payout logging (`SalaryPayout`). | `shared`, `identity` |
| **`contexts.notifications`** | Multi-Channel Notifications | In-app inbox (`InAppNotification`), notification templates (`NotificationTemplate`), outbound SMS/email orchestration, Twilio webhook processing. | `shared` |
| **`contexts.features`** | Dynamic Feature Flags | Granular runtime feature flags (`FeatureFlag`, `FeatureRule`) for tenant rollout and feature tiering. | `shared`, `tenants` |
| **`contexts.search`** | Universal Search | Unified cross-module search API (`UniversalSearchView`) aggregating matching products, orders, customers, and inventory items. | `catalog`, `ordering`, `customers` |
| **`contexts.super_admin`** | SaaS Platform Control Plane | Operations control panel for system admins (`PlatformSettings`), global metrics, tenant onboarding oversight, maintenance mode toggles. | `shared`, `tenants`, `billing` |

### Core Infrastructure & Execution Mechanisms

#### 1. Multi-Tenancy Resolution Lifecycle
When an HTTP request enters the WSGI/ASGI stack:
1. `TenantResolutionMiddleware` extracts the HTTP host header (e.g., `acme.nextora.app` or custom domain `pos.acmedining.com`).
2. Queries `TenantDomain.objects.select_related("tenant")` (cached in Redis for 300 seconds) or checks the authenticated user's session `Membership`.
3. Calls `shared.tenancy.context.set_current_tenant(tenant)`.
4. If `TENANCY_DB_LOCAL_GUC = True`, executes `SET LOCAL app.current_tenant = '<tenant_uuid>'` on the PostgreSQL database connection, instantly engaging Postgres Row-Level Security policies.
5. Any subsequent ORM query via `TenantAwareModel.objects` automatically injects `.filter(tenant=current_tenant)`. If no tenant is bound, fail-closed protection returns `.none()`.

#### 2. Enterprise Authentication, Session & RBAC Architecture (`contexts.identity`)
Nextora implements a production-grade identity architecture with zero sequential ID exposure:
- **UUID-Based Identity Routing:** All public-facing routes and API endpoints reference users exclusively by non-sequential UUIDv4 primary keys (`/api/v1/users/<uuid>/`).
- **Enterprise JWT Lifecycle (`api/authentication.py`, `api/jwt.py`):** Uses short-lived Access Tokens (15 min) and rotating Refresh Tokens (7 days) with token blacklisting (`BLACKLIST_AFTER_ROTATION = True`). Tokens embed `user_id`, `tenant_id`, and `token_version`.
- **Instant Global Revocation:** Changing a password or calling global logout (`POST /api/v1/auth/logout-all/`) increments `user.token_version`, immediately rejecting all existing JWTs system-wide via `EnterpriseJWTAuthentication`.
- **Brute-Force Account Lockout (`EnterpriseAuthenticationService`):** Tracks `failed_login_attempts` on `User`. Locks accounts automatically for 30 minutes (`locked_until`) after 5 consecutive failed logins.
- **Multi-Device Session Ledger (`UserSession`):** Records per-device logins (IP address, user agent, device type: desktop/mobile/POS touch terminal) and allows self-service session inspection (`GET /api/v1/auth/sessions/`) and individual device revocation (`POST /api/v1/auth/sessions/<uuid>/revoke/`).
- **Secure Credential Tokens (`PasswordResetToken`, `EmailVerificationToken`):** Stores SHA-256 secure hashes of tokens (1-hour TTL) so raw secret tokens are never stored in plaintext.
- **Enterprise RBAC:** Permissions evaluated at `platform`, `company`, or `branch` scopes with signal-driven Redis cache invalidation (`has_permission`). API endpoints under `/api/v1/auth/` provide full identity & profile capabilities.

#### 3. Background Jobs & Celery Queue Isolation (`config/celery.py`)
Background work is routed to dedicated queues to prevent heavy analytics from delaying checkout operations:
- `critical`: Instant payment reconciliations, KDS ticket generation, receipt print spooling.
- `default`: Email/SMS delivery, audit log aggregation.
- `bulk`: Nightly report rollups (`run_daily_reports_sweep`), hourly subscription cycle sweeps (`run_billing_cycle`), stock expiry scanning (`scan_expiring_batches`).

#### 4. Configuration & Environment Variables (`config/settings/base.py`, `.env`)
Settings follow Twelve-Factor principles via `django-environ`. To support standalone local execution (`runserver`) without crashing on missing environment keys or external Redis containers:
- **`DJANGO_SECRET_KEY`**: Read via `env("DJANGO_SECRET_KEY", default=...)`. Configured in root `.env` file (`DJANGO_SECRET_KEY=django-insecure-...`).
- **`CACHE_URL` & `SESSION_ENGINE`**: Supports both Redis (`redis://...`) and local in-memory execution (`locmem://nextora`). When `locmem` is configured in `.env`, `SESSION_ENGINE` automatically falls back to `cached_db` so standalone execution operates without external dependencies.
- **`.env` Configuration File**: Placed in `D:\NEXTORA_POS\.env` (created from `.env.example`) to populate local SQLite database, in-memory Channels layer (`CHANNELS_IN_MEMORY=true`), and development debug settings (`DJANGO_DEBUG=True`).

---

## 4. Frontend Documentation

### Architecture & Folder Structure
Nextora POS uses a hybrid, hyper-responsive server-driven UI architecture leveraging **Django Templates**, **HTMX** (for partial DOM updates without full page reloads), and **Tailwind CSS** structured via the **Nextora Forge Design System**.

```
templates/
├── base.html                  # Master shell: Top Rail, Module Rail, Status Rail
├── styleguide.html            # Nextora Forge Design System reference & living UI catalog
├── layouts/                   # Shared zone shells (POS terminal layout, Back-office layout)
├── components/                # Reusable UI fragments (modals, toasts, chips, cards, pagination)
├── ordering/                  # POS Touch Terminal, active cart, checkout modals, KDS board
├── catalog/                   # Product lists, modifier sheets, category trees
├── restaurant/                # Floor plans, interactive table layouts, kitchen stations
├── inventory/                 # Stock tables, batch inspectors, purchase order forms
├── reporting/                 # Operational dashboard, sales summaries, invoice detail views
├── tenants/                   # Branch configuration, receipt printer settings
└── identity/                  # Login, password recovery, session management
```

### Visual Structure: The Zones Model
Instead of scrolling consumer web pages, operational screens are divided into fixed, concurrent zones:
- **Top Rail (44px fixed):** Displays current tenant, active branch selection, staff operator badge, live clock, and system notification indicators.
- **Module Rail (64px fixed left):** Icon-first navigation switching between POS Terminal, KDS, Orders, Inventory, Catalog, and Reports.
- **Workspace (Fluid Center):** The active module surface (e.g., product search and Quick Key grid in POS mode).
- **Context Panel (340px–380px fixed right):** Persistent transactional sidebar showing active order lines, quantity steppers, applied discounts, customer tags, and checkout actions.
- **Status Rail (32px fixed bottom):** Hardware printer connection status, KDS WebSocket heartbeat, and active shift information.

### Frontend to Backend Communication Flow
1. **Initial Page Load:** Full HTML rendered by Django views passing pre-computed context.
2. **HTMX Interactive Actions:** Tapping a Quick Key or adjusting quantities sends an asynchronous `POST /pos/orders/<id>/add_item/` or `PATCH` request.
3. **Partial DOM Swapping:** The backend processes the domain mutation (`order_service.add_item`), recalculates `compute_bill()`, and returns a lightweight HTML partial (`ordering/partials/cart_panel.html`) which HTMX seamlessly swaps into the right-hand Context Panel within < 50ms.
4. **WebSocket Push (`/ws/events`):** When an order is paid or sent to the kitchen, backend services publish to the Redis Channel layer, instantly pushing real-time KOT tickets to connected KDS terminal screens.

### Sidebar Navigation Lifecycle & Scroll Preservation Architecture
To provide an enterprise-grade SaaS experience across long navigation menus (`#module-sidebar` in `templates/_chrome/module_rail.html`), Nextora POS implements a deterministic navigation lifecycle:
- **Server-Side Active Route Matching (`contexts/identity/context_processors.py`):** Navigation items match both tenant-prefixed URLs (`/billing/<tenant_id>/...`) and non-prefixed paths via substring and route evaluation, stamping `aria-current="page"` accurately on the active menu anchor.
- **Synchronous Pre-Paint Restoration:** Immediately after `#module-sidebar` is parsed in `module_rail.html`, a self-executing script reads `nextora_sidebar_scroll_top` from `sessionStorage` and restores `scrollTop` before browser paint, eliminating layout shifts and UI flickering.
- **Active Item Viewport Auto-Alignment:** If a user opens a direct link or navigates to a deep page where the active item is outside the visible sidebar bounds, the controller automatically calculates bounding rect offsets and smoothly centers/scrolls `[aria-current="page"]` into view.
- **Event Persistence & HTMX Support:** Passive scroll throttling (100ms interval) and direct link click listeners record scroll states continuously across full page reloads, browser Back/Forward navigation, and asynchronous HTMX swaps (`htmx:afterSwap`).

---

## 5. Database Documentation

### Core Data Models & Schema Tables

| Table Name | Python Model | Primary Key | Key Foreign Keys & Relationships | Indexes & Constraints |
| :--- | :--- | :--- | :--- | :--- |
| `tenant` | `tenants.Tenant` | `id` (UUIDv4) | Global root | `UNIQUE(slug)`, index on `status` |
| `tenant_domain` | `tenants.TenantDomain` | `id` (UUIDv4) | `tenant_id` -> `tenant.id` | `UNIQUE(domain)`, partial unique on primary domain per tenant |
| `identity_user` | `identity.User` | `id` (UUIDv4) | Global identity | `UNIQUE(email)`, Argon2 password hash |
| `identity_membership` | `identity.Membership` | `id` (UUIDv4) | `user_id`, `tenant_id`, `role_id` | Composite index on `(tenant, user)` |
| `catalog_category` | `catalog.Category` | `id` (UUIDv4) | `tenant_id`, `parent_id` (self-referential tree) | `ix_catalog_category__tenant_parent` |
| `catalog_product` | `catalog.Product` | `id` (UUIDv4) | `tenant_id`, `category_id`, `tax_class_id` | Partial unique on `(tenant, sku)` where `is_deleted=False` |
| `catalog_modifier` | `catalog.Modifier` | `id` (UUIDv4) | `tenant_id`, `group_id` | Ordered by display sequence |
| `order` | `ordering.Order` | `id` (UUIDv4) | `tenant_id`, `branch_id`, `customer_id`, `waiter_id` | Composite index on `(tenant, status, created_at)` |
| `order_item` | `ordering.OrderItem` | `id` (UUIDv4) | `order_id` -> `order.id`, `product_id` | Stored denormalized line prices and tax rates |
| `ordering_kot` | `ordering.KOT` | `id` (UUIDv4) | `order_id`, `station_id` | Tracks kitchen preparation lifecycle |
| `ordering_payment` | `ordering.Payment` | `id` (UUIDv4) | `order_id` -> `order.id` | Idempotency token protection |
| `ordering_invoice` | `ordering.Invoice` | `id` (UUIDv4) | `order_id` (OneToOne), `tenant_id` | `UNIQUE(tenant, invoice_number)` |
| `ordering_daily_counter`| `ordering.DailyCounter` | `id` (UUIDv4) | `tenant_id`, `date` | `SELECT FOR UPDATE` gapless invoice numbering |
| `inventory_item` | `inventory.InventoryItem` | `id` (UUIDv4) | `tenant_id`, `product_id`, `branch_id` | Tracks physical stock levels |
| `inventory_batch` | `inventory.Batch` | `id` (UUIDv4) | `item_id`, `tenant_id` | Tracks lot number, cost price, and expiration date |
| `audit_log` | `audit.AuditLog` | `id` (BigAuto/UUID)| `tenant_id`, `actor_id` | Append-only compliance log; index on `(tenant, created_at)` |

---

## 6. ER Relationship Overview

```
+-------------------------------------------------------------------------------------------------------+
|                                        GLOBAL SAAS ROOT                                               |
|                                                                                                       |
|  +---------------------------+       1 : N       +-------------------------------------------------+  |
|  |     identity.User         +------------------>|             identity.Membership                 |  |
|  |  id (UUID PK)             |                   |  id (UUID PK), user_id, tenant_id, role_id      |  |
|  +---------------------------+                   +------------------------+------------------------+  |
|                                                                           |                           |
|  +---------------------------+       1 : N       +------------------------v------------------------+  |
|  |     tenants.Tenant        +------------------>|             tenants.TenantDomain                |  |
|  |  id (UUID PK), slug       |                   |  domain (UNIQUE), is_primary                    |  |
|  +-------------+-------------+                   +-------------------------------------------------+  |
+----------------|--------------------------------------------------------------------------------------+
                 |
                 |  1 : N  (EVERY TENANT-AWARE TABLE BELOW CARRIES tenant_id FK)
                 v
+-------------------------------------------------------------------------------------------------------+
|                                     TENANT BOUNDED ISOLATION                                          |
|                                                                                                       |
|   +-----------------------+              1 : N              +------------------------------------+  |
|   |  catalog.Category     |<--------------------------------+        catalog.Product             |  |
|   |  id, parent_id        |                                 |  id, name, base_price, tax_class   |  |
|   +-----------------------+                                 +-----------------+------------------+  |
|                                                                               |                       |
|                                                                               | 1 : N                 |
|                                                                               v                       |
|   +-----------------------+              1 : N              +------------------------------------+  |
|   |    ordering.Order     |<--------------------------------+       ordering.OrderItem           |  |
|   |  id, status, totals   |                                 |  product_id, qty, unit_price       |  |
|   +-----------+-----------+                                 +-----------------+------------------+  |
|               |                                                               |                       |
|               | 1 : N                                                         | 1 : N                 |
|               +-----------------------+                                       v                       |
|               |                       |                     +------------------------------------+  |
|               v                       v                     |    ordering.OrderItemModifier      |  |
|   +-----------------------+   +-----------------------+     |  modifier_id, price_delta          |  |
|   |   ordering.Payment    |   |    ordering.Invoice   |     +------------------------------------+  |
|   |  amount, method       |   |  invoice_number (UQ)  |                                           |
|   +-----------------------+   +-----------------------+                                           |
+-------------------------------------------------------------------------------------------------------+
```

### Key Relational Design Rules
- **Denormalization at Checkout:** When an `OrderItem` is created, `unit_price`, `tax_rate`, and `name` are copied immutably from `Product`. Subsequent catalog price updates never alter historic order totals or audit records.
- **Strict Row-Level Isolation:** Every table inside `TENANT BOUNDED ISOLATION` contains a non-nullable `tenant_id` indexed as the leading column on composite indexes (`(tenant_id, ...)`).

---

## 7. API Documentation

All API endpoints are hosted under `/api/v1/`, consume and produce `application/json`, and are secured via JWT bearer tokens or authenticated sessions.

### Summary of REST ViewSets & Endpoints

| Bounded Context | Base URL Path | Controller / ViewSet | Supported HTTP Methods | Permissions Required |
| :--- | :--- | :--- | :--- | :--- |
| **Catalog** | `/api/v1/catalog/products/` | `ProductViewSet` | `GET`, `POST`, `PUT`, `PATCH`, `DELETE` | `catalog.view`, `catalog.manage` |
| **Ordering** | `/api/v1/ordering/orders/` | `OrderViewSet` | `GET`, `POST`, `PATCH` + Custom Actions | `ordering.create`, `ordering.void` |
| **Restaurant** | `/api/v1/restaurant/branches/` | `BranchViewSet` | `GET`, `POST`, `PUT`, `PATCH`, `DELETE` | `restaurant.manage` |
| **Restaurant** | `/api/v1/restaurant/tables/` | `DiningTableViewSet` | `GET`, `POST`, `PUT`, `PATCH`, `DELETE` | `restaurant.manage` |
| **Inventory** | `/api/v1/inventory/items/` | `InventoryItemViewSet` | `GET`, `POST`, `PUT`, `PATCH` | `inventory.view`, `inventory.manage` |
| **Inventory** | `/api/v1/inventory/purchase-orders/`| `PurchaseOrderViewSet` | `GET`, `POST`, `PATCH` | `inventory.manage` |
| **Customers** | `/api/v1/customers/customers/` | `CustomerViewSet` | `GET`, `POST`, `PUT`, `PATCH` | `customers.view` |
| **Employees** | `/api/v1/employees/profiles/` | `EmployeeProfileViewSet` | `GET`, `POST`, `PUT`, `PATCH` | `employees.manage` |
| **Employees** | `/api/v1/employees/attendance/` | `AttendanceViewSet` | `GET`, `POST`, `PATCH` | `employees.view` |
| **Search** | `/api/v1/search/` | `UniversalSearchView` | `GET` | Authenticated |
| **Billing** | `/webhooks/billing/razorpay/` | `RazorpayWebhookView` | `POST` | Signature HMAC verification |

### POS Custom Actions on `OrderViewSet` (`/api/v1/ordering/orders/<id>/...`)
- `POST /add_item/`: Body `{"product_id": "<uuid>", "quantity": 1, "modifiers": [...]}` — Adds line item and recalculates taxes.
- `POST /discount/`: Body `{"discount_amount": "50.00"}` — Applies order-level discount.
- `POST /settle/`: Body `{"payments": [{"method": "cash", "amount": "450.00"}]}` — Locks order, captures payment, generates invoice number, and emits kitchen tickets.
- `POST /void/`: Body `{"reason": "Customer cancelled"}` — Requires manager permission (`ordering.void`); voids order and logs audit trail.

---

## 8. Authentication Flow

```
+---------------+              +--------------------+              +---------------------+
| Client Device |              | Identity LoginView |              | PostgreSQL Database |
+-------+-------+              +---------+----------+              +----------+----------+
        |                                |                                    |
        | 1. POST /auth/login/           |                                    |
        |    (email, password, tenant)   |                                    |
        +------------------------------->|                                    |
        |                                | 2. Query User by email             |
        |                                +----------------------------------->|
        |                                |<-----------------------------------+
        |                                |                                    |
        |                                | 3. Verify Argon2 Password Hash     |
        |                                | 4. Validate Membership for Tenant  |
        |                                | 5. Establish Redis Session / JWT   |
        |                                |                                    |
        | 6. Set-Cookie: sessionid       |                                    |
        |<-------------------------------+                                    |
```

### Security Checkpoints
- **Password Hasher:** Uses memory-hard **Argon2** (`Argon2PasswordHasher`) as primary hasher, falling back to PBKDF2 for legacy verifications.
- **Lockout Protection:** Custom user model supports account locking (`is_locked`) after repeated authentication failures.
- **Session Backend:** Session tokens are stored in **Redis** (`django.contrib.sessions.backends.cache`), keeping backend app containers stateless.

---

## 9. Authorization Flow

```
+---------------+           +--------------------------+           +--------------------------+
| HTTP Request  |           | DRF RequirePermission    |           | Authorization Service    |
+-------+-------+           +------------+-------------+           +------------+-------------+
        |                                |                                      |
        | 1. GET /api/v1/catalog/        |                                      |
        +------------------------------->|                                      |
        |                                | 2. Check permission "catalog.view"   |
        |                                +------------------------------------->|
        |                                |                                      | 3. Check Redis RBAC Cache
        |                                |                                      |    Key: rbac:{tenant}:{user}
        |                                |                                      |    [HIT -> Return Bitmap]
        |                                |                                      |    [MISS -> Query DB & Cache]
        |                                |<-------------------------------------+
        |                                |
        | 4. HTTP 200 OK (Allowed)       |
        |<-------------------------------+
```

### Pre-Defined System Roles (`permissions/catalog.py`)
1. **`super_admin`**: Platform operator; bypasses tenant restrictions.
2. **`company_owner`**: Full administrative access across all tenant branches.
3. **`branch_manager`**: Can manage catalog, void orders, issue refunds, and manage branch staff schedules.
4. **`cashier`**: Can create orders, apply authorized discounts, accept payments, and print receipts.
5. **`kitchen_staff`**: Can view KDS board and update KOT item prep status.
6. **`waiter`**: Can create dine-in table orders and request bills.
7. **`inventory_manager`**: Can manage suppliers, stock transfers, and purchase orders.
8. **`accountant`**: Read-only access to sales analytics, tax rollups, and financial invoices.
9. **`support`**: Platform customer support role with read-only inspection access.

---

## 10. POS Business Workflows

### Complete POS Checkout & Billing Lifecycle
1. **Order Initiation:** Cashier taps "New Order" or Waiter opens Table 12. Backend creates `Order(status='draft')`.
2. **Catalog Selection:** Cashier taps Quick Key or scans barcode. `order_service.add_item()` fetches product price, resolves applicable GST `TaxClass`, and appends `OrderItem`.
3. **Real-Time Calculation (`compute_bill`):**
   $$\text{Taxable Line} = \text{Amount} - \text{Proportional Order Discount}$$
   $$\text{CGST} = \text{Taxable Line} \times \frac{\text{Rate}}{2}, \quad \text{SGST} = \text{Taxable Line} \times \frac{\text{Rate}}{2}$$
   $$\text{Total} = \text{round\_to\_nearest}(\text{Taxable} + \text{Service Charge} + \text{Tax Total}, \; 1.00)$$
4. **Kitchen Order Ticket (KOT):** When items are confirmed, `kot_service` creates `KOT` and routes items to configured `KitchenStation` printers/screens via Channels WebSockets.
5. **Payment Settlement:** Cashier selects multi-tender payment (e.g., ₹300 Cash, ₹150 UPI). `payment_service` verifies amounts inside `transaction.atomic` and records `Payment`.
6. **Gapless Invoice Generation:** `invoice_service` acquires a `SELECT ... FOR UPDATE` lock on `DailyCounter(date=today)` to assign a sequential invoice number (`INV260708-0001`), locking the order as `PAID`.

---

## 11. Folder Structure

```
D:\NEXTORA_POS\
├── config/                          # Framework configuration (settings, celery, urls, asgi/wsgi)
│   ├── settings/                    # base.py, dev.py, prod.py, security.py, logging.py
│   ├── celery.py                    # Celery app & task queue routing definitions
│   └── urls.py                      # Root URL router (/api/v1/, /auth/, /healthz/)
├── src/
│   ├── shared/                      # Clean Architecture Kernel & Cross-Cutting Infrastructure
│   │   ├── domain/                  # Abstract Entity, ValueObject, DomainEvent primitives
│   │   ├── tenancy/                 # RLS middleware, fail-closed managers, DB routers
│   │   └── infrastructure/          # Base ORM models, structured JSON logger, health probes
│   └── contexts/                    # Independent Bounded Contexts (Django Apps)
│       ├── tenants/                 # Root tenant identity & domain routing
│       ├── identity/                # User authentication & enterprise RBAC engine
│       ├── audit/                   # Immutable compliance log repository
│       ├── catalog/                 # Menu, products, variants, modifiers, GST taxes
│       ├── ordering/                # POS checkout, order calculation, payment, KDS
│       ├── inventory/               # Multi-warehouse stock tracking & purchase orders
│       ├── restaurant/              # Floor layouts, dining tables, kitchen stations
│       ├── billing/                 # SaaS tenant subscription plans & invoices
│       ├── reporting/               # Operational analytics & business intelligence
│       ├── customers/               # Customer directory, loyalty & wallets
│       ├── employees/               # Staff scheduling, shifts & attendance
│       ├── notifications/           # In-app inbox & outbound communications
│       ├── features/                # Dynamic feature flags & rules
│       ├── search/                  # Cross-context universal search
│       └── super_admin/             # SaaS platform management control plane
├── templates/                       # Nextora Forge HTMX + Tailwind HTML templates
├── static/                          # CSS design system tokens & compiled static assets
├── tests/                           # Pytest unit & integration test suites
├── deploy/                          # Dockerfiles, Nginx configurations, entrypoint scripts
├── pyproject.toml                   # Ruff, MyPy, Pytest & project metadata configuration
└── Makefile                         # Development automation scripts
```

---

## 12. Design Decisions

1. **Clean Architecture over Django Fat Models:** Business calculation rules (`compute_bill`, `compute_gst`) reside in pure Python modules under `domain/`. ORM models operate purely as persistence mappers, preventing framework coupling.
2. **Four-Layer Multi-Tenancy Defense over Filtering by Convention:** Relying on developers to manually type `.filter(tenant=request.tenant)` invites catastrophic data leaks. Nextora layers middleware resolution, fail-closed ORM managers, model write guards, and database-level RLS (`app.current_tenant`).
3. **Exact Decimal Arithmetic over Float:** Financial data types across all models (`DecimalField`) and calculations use `Decimal`. Floating-point arithmetic is strictly forbidden in money calculation code.
4. **Daily Gapless Invoice Sequence Locks:** To satisfy strict regulatory compliance (including Indian GST guidelines), invoices are numbered sequentially per day via explicit row locks (`SELECT ... FOR UPDATE` on `DailyCounter`), preventing race conditions.

---

## 13. Coding Standards

- **Static Typing:** Python type hints (`-> str`, `list[BillLine]`) are mandatory across all services, utilities, and domain functions, validated via `mypy --strict-optional`.
- **Linting & Code Quality:** Code format and complexity are enforced via `ruff` (target line length 100, McCabe complexity limit $\le 10$).
- **Transactional Mutation Guard:** Every service mutation creating or modifying business state must execute inside a `with transaction.atomic():` block.
- **Audit Requirement:** Every structural create, update, or delete operation on tenant domain entities must call `record_audit(action, entity_type, entity_id, changes)`.

---

## 14. Current Features

- ✅ **Complete Domain & Service Core:** Full Clean Architecture implementations for Catalog, Ordering, Inventory, Restaurant, Identity/RBAC, Billing, and Reporting contexts.
- ✅ **Multi-Tenant Security Stack:** Host/subdomain resolution middleware, fail-closed tenant ORM managers, and PostgreSQL RLS management commands (`apply_rls`).
- ✅ **POS Billing Engine:** Production-ready deterministic bill calculation handling proportional discounts, multi-tier GST (CGST/SGST/IGST + Cess), and service charges.
- ✅ **Enterprise RBAC:** Granular permission evaluations with Redis bitmap caching and signal-based instant invalidation.
- ✅ **Nextora Forge Design Language:** Full responsive HTML templates and Tailwind design token architecture for POS screens and back-office management.

---

## 15. Pending Features

- ⏳ **Initial Django Migrations Generation:** ORM models are complete across all 16 contexts, but initial migration files have not yet been generated (`makemigrations` to be executed and committed prior to production deployment).
- ⏳ **Branch FK Consolidation:** Complete promotion of soft `location_id` UUID fields to strict foreign keys pointing to unified branch entities.
- ⏳ **Transactional Outbox & Domain Events:** Build asynchronous transactional outbox worker (`OutboxEvent`) to decouple ordering transactions from notification and analytics projections.
- ⏳ **High-Volume UUIDv7 Primary Keys:** Upgrade hot transaction tables (`Order`, `OrderItem`, `AuditLog`) from UUIDv4 random keys to time-sorted UUIDv7 keys to eliminate B-tree index fragmentation.

---

## 16. Known Bugs

- *None active in validated domain syntax.* All modules byte-compile cleanly and pass domain logic validation. Full database integration tests (`make test`) must be run against a live PostgreSQL 16 + Redis container stack to verify integration constraints.

---

## 17. Performance Notes

- **Composite Index Leading Columns:** Every tenant-aware model index starts with `tenant_id` (`(tenant_id, status)`, `(tenant_id, created_at)`), ensuring PostgreSQL query planners utilize index scans within RLS scopes.
- **N+1 Query Elimination:** API viewsets and HTMX views explicitly declare `.select_related()` and `.prefetch_related()` for high-volume nested relations (`OrderItem -> Product`, `Order -> Payments`).
- **Redis Connection Pooling:** All session and RBAC cache lookups utilize persistent Redis connection pools (`DefaultClient`).

---

## 18. Security Notes

- **SQL Injection Prevention:** 100% parameterization via Django ORM and strict validation of dynamic sort ordering.
- **Cross-Tenant Leak Prevention:** Multi-layered RLS and ORM manager safeguards prevent cross-tenant enumeration.
- **Webhook Authenticity Check:** External SaaS billing webhooks (`RazorpayWebhookView`) enforce cryptographic HMAC-SHA256 signature verification before processing subscription mutations.
- **Argon2 Password Hardening:** Prevents GPU-accelerated credential brute-forcing.

---

## 19. Technical Debt

1. **Dual Branch Model Definitions:** Both `contexts.tenants` (`TenantAwareModel` branch/table models) and `contexts.restaurant` define branch/table concepts. *Resolution Plan:* Consolidate physical establishment metadata under `contexts.restaurant.Branch` and deprecate redundant models in `tenants`.
2. **JWT Tenant Claim Binding:** DRF JWT authentication resolves `request.user` after WSGI middleware execution. *Resolution Plan:* Add a custom authentication backend or permission layer that validates that the JWT token's `tenant_id` claim strictly matches `app.current_tenant`.

---

## 20. Future Improvement Suggestions

1. **Read Replica Database Routing:** Configure `TenantShardRouter` to direct read-heavy analytical dashboard queries (`reporting` context) to PostgreSQL read replicas.
2. **Automated End-to-End Playwright Tests:** Implement automated UI regression suites covering multi-tender payment capture and KDS WebSocket ticket rendering.

---

## 21. Enterprise Offline-First Architecture & Synchronization Engine

Nextora POS implements a production-grade **Enterprise Offline-First Architecture** that allows cashier touch terminals and mobile devices to operate continuously for **up to 72 hours (3 days)** without network connectivity.

### 21.1 Progressive Web App (PWA) & Service Worker Infrastructure
- **PWA Manifest (`static/manifest.json`):** Configured as a standalone, installable Progressive Web App with dedicated icons, display settings, and touch terminal shortcuts.
- **Service Worker (`static/sw.js`):** Implements a cache-first routing strategy for static assets, stale-while-revalidate for catalog assets, and integrates with the Background Sync API (`nextora-offline-sync`) to trigger sync attempts immediately when connectivity returns.

### 21.2 Client-Side Storage & POS Offline Controller (Dexie.js)
- **IndexedDB Schema (`NextoraOfflineDB` in `static/js/offline/db.js`):** Stores high-speed snapshots of `products`, `categories`, `taxes`, pending `offline_orders`, `sync_queue`, and active `auth_session`.
- **72-Hour Grace Period (`static/js/offline/auth.js`):** Enforces cryptographic session TTLs locally. Allows authorized cashiers to log in and operate offline up to 72 hours from their last online verification.
- **Sub-50ms Offline Search & Cart (`static/js/offline/pos-offline.js`):** Performs local barcode scan, SKU search, item modifier calculation, tax application, and receipt printing with zero server dependency.

### 21.3 Idempotent Backend Ingestion & Sync Pipeline
- **Duplicate Protection (`offline_reference_id`):** Every offline order generates a unique client reference (`OFF-ORD-<uuid>`). Server ingestion checks `Order.objects.filter(offline_reference_id=...)` to skip duplicates safely.
- **Batch Sync Endpoint (`POST /api/v1/ordering/offline/sync/`):** Processes queued transactions inside atomic transactions, assigns gapless regulatory invoice numbers (`INV-...`), captures multi-tender payments, and broadcasts real-time WebSocket events.
- **Priming Snapshot Endpoint (`GET /api/v1/ordering/offline/bootstrap/`):** Delivers optimized catalog, category, tax, and RBAC payload for rapid terminal priming.

---

## 22. POS Checkout, Billing & Payment Architectural Analysis

A complete architectural and UI/UX audit of the Nextora POS checkout modal (`checkout_modal.html`), billing workflow (`POSProcessPaymentView`), financial settlement pipeline, inventory integration, and thermal printer subsystem reveals the current end-to-end lifecycle, gaps, and consistency risks.

### 22.1 Current Payment Lifecycle
1. **Checkout Modal Trigger (`POSCheckoutModalView.get`):**
   - Retrieves `active_order_id` from Django HTTP session.
   - Renders `templates/ordering/partials/checkout_modal.html` containing the total due amount (`₹{{ active_order.total }}`), three single-select payment method options (`CASH`, `CARD`, `UPI`), and a tendered amount numeric input.
2. **Payment Execution (`POSProcessPaymentView.post`):**
   - Receives form submission via HTMX (`hx-post="{% url 'ordering:pos_process_payment' %}"`).
   - Generates any pending Kitchen Order Tickets via `kot_service.generate_kots(order.id)`.
   - Calls `payment_service.add_payment(order_id, amount=order.total, method=method, tendered=tendered, created_by=user.id)`.
   - Recomputes order balances (`paid_amount`, `due_amount`).

### 22.2 Current Invoice Workflow
1. **Gapless Tax Invoice Issuance (`invoice_service.settle_and_invoice`):**
   - Immediately invoked after `add_payment`.
   - Acquires a `SELECT ... FOR UPDATE` lock on `Order(id=order_id)` and verifies `order.due_amount == 0`.
   - Acquires a daily gapless sequence lock on `DailyCounter` to assign a regulatory tax invoice number (`INV260708-0001`).
   - Freezes all financial snapshots (`subtotal`, `discount_amount`, `cgst`, `sgst`, `igst`, `cess`, `total`) into an immutable `Invoice` entity.
   - Transitions `order.status` from `OPEN` to `SETTLED`.
2. **Table Vacating & Session Cleanup:**
   - If `order.table_id` is set, updates `DiningTable.status = VACANT`.
   - Deletes `request.session['active_order_id']`.
   - Renders `checkout_success_modal.html` and empties cart panel OOB.

### 22.3 Current Print Workflow & ESC/POS Subsystem
- **ESC/POS Rendering Service (`src/contexts/ordering/services/printing.py`):**
   - Contains `render_kot_text(kot, width=32)` and `render_invoice_text(invoice, width=32)`.
   - Contains `to_escpos(text)` which builds raw thermal ESC/POS byte streams (`\x1b\x40` initialization + ASCII payload + `\n\n\n` line feeds + `\x1d\x56\x00` full automatic paper cut).
- **Print Integration Gap:**
   - Currently disconnected from `POSProcessPaymentView`. When settlement completes, neither ESC/POS byte payloads, print job queue items, nor browser print triggers are sent to the client terminal.

### 22.4 Missing Enterprise POS Features
1. **Split-Tender / Multi-Method Billing UI:** Cashiers cannot split a single bill across multiple payment methods (e.g., ₹300 Cash + ₹250 UPI or Gift Card + Credit Card) inside the checkout modal.
2. **Real-Time Automated Inventory Deduction:** Settlement currently does not invoke `apply_stock_movement(movement_type=StockMovementType.SALE)` in `contexts.inventory.services.movement_service`. Sold items do not automatically decrement stock on hand or recipe/BOM ingredients.
3. **Automated Receipt & KOT Print Dispatch:** No ESC/POS payload or receipt preview modal is returned upon successful payment completion.
4. **Customer Profile & Loyalty Integration:** Checkout modal lacks phone number lookup, customer linking, loyalty point accrual/redemption, and customer credit balance display.
5. **Tip & Gratuity Recording:** No line item or input field for credit card or cash tip recording at checkout.

### 22.5 Potential Duplicate Billing Risks
1. **Missing Idempotency Key in Form Submission:**
   - `checkout_modal.html` does not embed a client-generated UUID `idempotency_key` hidden field.
   - `POSProcessPaymentView.post()` invokes `payment_service.add_payment()` with default `idempotency_key=""`.
2. **Race Condition Risk:**
   - If a cashier double-clicks the Complete Payment button or if network latency causes an HTMX retry, two requests can arrive concurrently. Without an `idempotency_key`, double payment capture or race-condition exceptions can occur prior to invoice locking.

### 22.6 Transaction Consistency Issues
1. **Non-Atomic Cross-Service Coordination in `POSProcessPaymentView`:**
   - In `POSProcessPaymentView.post()`, `kot_service.generate_kots()`, `payment_service.add_payment()`, `invoice_service.settle_and_invoice()`, and `DiningTable.objects.filter(...).update()` run as sequential outer service calls without an overarching single `with transaction.atomic():` boundary around the entire view handler.
   - If table update or external webhook dispatch fails after `settle_and_invoice()`, partial state changes could occur unless wrapped in a single database transaction boundary.

---

## 23. Automated Receipt Printing & Idempotent Print Queue Implementation

### 23.1 Overview
An automated, resilient receipt printing system has been implemented to ensure that completing a payment reliably generates and dispatches all required receipts without cashier intervention or duplicate print jobs.

### 23.2 Architecture & Transaction Guarantees
1. **Strict Post-Commit Execution (`transaction.on_commit`)**:
   - Receipt printing is decoupled from active database transactions.
   - `POSProcessPaymentView.post()` executes payment capture, invoice settlement, KOT generation, and print job persistence inside a single `with transaction.atomic():` block.
   - Print jobs are scheduled for execution via `transaction.on_commit(lambda: _run_after_commit())`. Printing occurs **only after** the database transaction has successfully committed.

2. **Idempotent 3-Receipt Generation**:
   - The system automatically generates three distinct receipt jobs upon successful checkout:
     1. **Customer Copy** (`*** CUSTOMER COPY ***`)
     2. **Restaurant Copy** (`*** RESTAURANT COPY ***`)
     3. **Kitchen Order Ticket (KOT)** (`KITCHEN ORDER TICKET`)
   - Model-level unique constraints (`uq_print_job__receipt_once` and `uq_print_job__kot_once`) alongside `get_or_create` logic guarantee that double-clicking or repeated API requests will never duplicate receipt print jobs.

3. **Resilience & Non-Blocking Hardware Dispatch**:
   - `execute_print_job(job)` attempts hardware delivery over TCP socket/ESC-POS to configured network printers (`Printer`).
   - If physical printer hardware is offline or unreachable, the exception is caught, `job.status` transitions to `PENDING`/`RETRYING`, and `job.retry_count` increments.
   - A printer hardware failure **never aborts or rolls back** a completed sale (`OrderStatus.SETTLED`).

4. **Zero-Interaction UI Print Execution**:
   - Upon successful payment, `checkout_success_modal.html` renders a hidden thermal print container formatted for thermal rolls (`nextora-thermal-print-area`) and displays live print dispatch status badges for all 3 receipt copies.
   - An embedded self-executing script automatically initiates browser print dispatch (`window.print()`) without requiring any additional user clicks.

### 23.3 Customer Receipt Specification & 58mm/80mm Thermal Optimization
1. **Complete 20-Point Field Coverage**:
   - The receipt renderer (`render_invoice_text`) outputs all required enterprise tax invoice elements:
     - **Restaurant Details**: Logo (`[ LOGO: ... ]`), Restaurant Name, Branch Address, and GST/VAT Identification Number.
     - **Transaction Metadata**: Invoice Number (`number`), Issued Date & Time (`issued_at`), Cashier Name (staff lookup fallback), Customer Name, Table Number (if dine-in), and Order Type (`Dine-In`, `Takeaway`, `Delivery`).
     - **Line Items Breakdown**: Item Name, Quantity, Unit Price, Line Total, and item modifiers where applicable.
     - **Financial Summary**: Subtotal, Order Discounts (`-₹...`), Service Charges, Tax Breakdown (CGST, SGST, IGST, Cess), Round Off adjustment, and **GRAND TOTAL**.
     - **Payment Settlement**: Payment Method(s) used (`CASH`, `CARD`, `UPI`), Amount Paid (Tendered), and Balance Returned (Change Due).
     - **Footer**: Centered Thank You Message (`"THANK YOU FOR DINING WITH US!"` / `"Visit Again Soon"`).

2. **Dual Thermal Roll Width Support (58mm & 80mm)**:
   - **58mm Roll (`paper_width="58mm"`, 32 columns)**: Compact multi-line item layout formatting item name and quantity on the first line and unit price `@` line total on the second line to prevent truncation.
   - **80mm Roll (`paper_width="80mm"`, 48 columns)**: Spacious tabular layout presenting quantity, item name, unit price, and total on a structured horizontal grid.

3. **ESC/POS Hardware Control Stream**:
   - `to_escpos_receipt(...)` wraps the formatted ASCII receipt with native ESC/POS hardware control codes:
     - Printer initialization (`ESC @`, `\x1b\x40`)
     - Center alignment & bold text (`ESC a 1`, `ESC E 1`) for Logo block, Restaurant Name, and header badges
     - Bold emphasis (`ESC E 1`) for the `GRAND TOTAL` row
     - Automatic 3-line feed and full paper cut (`GS V 0`, `\x1d\x56\x00`)

### 23.4 Restaurant Copy Accounting & Auditing Specification
1. **Full Customer Receipt + 10-Point Internal Accounting Record**:
   - `render_restaurant_copy_text` renders all Customer Receipt sections alongside a dedicated **ACCOUNTING & AUDIT RECORD** block containing:
     1. **Internal Order Number**: Complete database primary key ID (`order.id`)
     2. **Internal Transaction ID**: Underlying payment reference ID (`payment.reference` or payment UUID)
     3. **Branch Name**: Location/Branch name (`location_id` resolution)
     4. **Terminal ID**: Hardware terminal identifier (`POS-TRM-01`)
     5. **Cashier ID**: Numeric/UUID identifier of cashier account (`created_by` / `waiter_id`)
     6. **Shift Number**: Active cashier shift reference (`SHIFT-01`)
     7. **Company Name**: Tenant organization name
     8. **Company ID**: Organization tenant UUID (`tenant.id`)
     9. **Internal Audit Reference**: Deterministic checksum reference (`AUD-<order_hash>`)
     10. **Print Timestamp**: Exact generation timestamp (`timezone.now()`)

2. **Automated Archival & Payment Integration**:
   - Whenever a payment completes successfully, `create_order_print_jobs` automatically generates and permanently archives the Restaurant Copy (`PrintJobType.RESTAURANT_RECEIPT`) in the database.
   - The archived record is queryable via `get_archived_restaurant_copy(invoice)` for financial audits and compliance reviews.

### 23.5 Enterprise Kitchen Order Ticket (KOT) Operational Specification
1. **Strict Separation of Operational vs. Financial Data**:
   - `render_kot_text` renders strictly kitchen-related operational information:
     - **Metadata**: Restaurant Name, KOT Number (`#number`), Order Number, Date & Time (`%d-%m-%Y %H:%M:%S`), Order Type (`Dine In`, `Takeaway`, etc.), Table Number, Customer Name (optional).
     - **Preparation Details**: Item Name, Quantity formatted with bold/large brackets (`[ QTY ] ITEM NAME`), Modifiers (`+ Modifier Name`), Add-ons (`+ Add-on Name`), and Special Instructions / Kitchen Notes (`*** NOTE: ... ***`).
   - **Financial Exclusions**: Zero financial fields are printed on the KOT (no unit prices, line totals, discounts, taxes, or grand totals).

2. **Kitchen Readability & ESC/POS Hardware Formatting**:
   - `to_escpos_kot` injects hardware ESC/POS commands (`GS ! 0x11` double height & width, `ESC E 1` bold) on the `KITCHEN ORDER TICKET` header and item rows (`[ QTY ] ITEM NAME`) for fast readability across fast-paced kitchen operations.

### 23.6 Single Database Transaction Complete Payment Workflow
1. **Strict 13-Step Transaction Sequence (`complete_checkout_transaction`)**:
   - The entire Complete Payment workflow executes inside a single database transaction (`@transaction.atomic`) with row-level locks (`SELECT ... FOR UPDATE`):
     1. **Validate Cart**: Verifies active line items exist and order totals are non-negative.
     2. **Validate Inventory**: Checks active status of mapped `InventoryItem` records.
     3. **Validate Payment**: Ensures valid payment method and sufficient tendered amount.
     4. **Create Sale**: Transitions order status to `OrderStatus.SETTLED` (`settle_and_invoice`).
     5. **Create Invoice**: Creates the immutable `Invoice` snapshot (`settle_and_invoice`).
     6. **Generate Invoice Number**: Issues gapless platform invoice number (`INV...`).
     7. **Generate KOT Number**: Generates unprinted KOT tickets and sequential numbers (`kot_service.generate_kots`).
     8. **Deduct Inventory**: Mutates stock quantities (`apply_stock_movement`) with audit ledger entries.
     9. **Record Payment**: Captures payment record (`payment_service.add_payment`).
     10. **Save Audit Log**: Records immutable audit log entry (`checkout.completed`).
     11. **Commit Transaction**: Automatically commits atomicity block on normal exit.
     12. **Print Receipts**: Schedules hardware dispatch strictly after successful commit (`transaction.on_commit`).
     13. **Clear Cart**: Clears session cart and releases dining table post-commit.

2. **Rollback & Idempotence Guarantee**:
   - **Automatic Rollback**: Any failure at any step (validation exception, inventory lock failure, payment error) rolls back the entire database transaction cleanly, leaving zero orphaned records.
   - **Duplicate Protection**: Checking order settlement state and existing invoice/payment records inside row locks prevents double-clicks or repeated requests from creating duplicate invoices, duplicate payments, or duplicate stock deductions.

### 23.7 Enterprise Print Queue
1. **Queue Architecture**:
   - Every hardware print request generates an idempotent `PrintJob` (`job_type`: CUSTOMER_RECEIPT, RESTAURANT_RECEIPT, KOT_TICKET).
   - Thermal byte streams are generated synchronously but dispatched asynchronously to hardware using `execute_print_job`.
2. **Failure Recovery**:
   - **Retries**: Any `IOError` or `socket.error` transitions the print job to `RETRYING` state, incrementing a retry counter (max 5).
   - **Error Detection**: Distinguishes between simulated "Paper Out" (hardware error) and network socket timeouts (offline).
   - **Celery Sweep**: A periodic task (`retry_failed_print_jobs`) sweeps every 60 seconds to execute pending or retrying jobs in the background.
3. **Operations Feedback**:
   - A `PrintQueueView` dashboard surfaces the history and status (Printed, Retrying, Failed) of all jobs.
   - Cashiers can manually trigger reprints directly from the POS interface via `ManualReprintView`, which resets the failure counters.

---

## 24. Pre-Implementation Billing Architecture Analysis

### 24.1 Existing Architecture Components
1. **Sidebar Architecture:** Implemented in `base.html` as the `Module Rail` with navigation across POS Terminal, KDS, Orders, Inventory, Catalog, and Reports.
2. **Checkout & Payment Workflow:** Handled via HTMX in `POSCheckoutModalView` and `POSProcessPaymentView`. Leverages idempotency keys and cache locks to prevent duplicate transactions during network retries.
3. **Complete Payment Logic:** Enforced via `checkout_service.complete_checkout_transaction()`. Implements a strict 13-step atomic database transaction ensuring zero orphaned records if validation, inventory deduction, or payment capture fails.
4. **Invoice Generation:** Achieved through gapless numbering via `DailyCounter` with `SELECT FOR UPDATE` row-level locks, satisfying strict accounting and GST compliance.
5. **Orders Module:** Centralized around `Order`, `OrderItem`, and `KOT` models supporting Dine-In, Takeaway, and Delivery modalities. Table assignment is managed via `table_id`.
6. **Customer Module:** CRM models (`Customer`, `PointsLedger`) exist in `contexts.customers`, however, they are entirely disconnected from the POS Checkout workflow.
7. **Reports Module:** Found in `contexts.reporting.views` featuring `SalesReportView` and `ItemReportView`. Supports daily/hourly trend charts, top items, revenue by branch, and CSV/Excel exports.
8. **Permissions:** Enterprise RBAC enforces authorization rules such as `payments.capture`, `orders.update`, `orders.create`, and `reports.sales.view`.
9. **GST Calculations:** Pure domain logic in `compute_bill()` processes proportional discounts and splits taxes into CGST, SGST (intra-state) or IGST (inter-state) with configurable round-off.
10. **Print Queue & Receipts:** Orchestrated via `print_templates.py` (ESC/POS formatting) and `printer_adapters.py` (Hardware dispatch), queuing tasks for Celery.

### 24.2 Identified Gaps & Missing Features
1. **Missing Billing Features:**
   - **Customer Linkage:** The `Order` model currently uses `customer_name` and `customer_phone` as CharFields and lacks a strict `customer_id` Foreign Key. Orders cannot accrue loyalty points, use wallet balances, or track historical B2B/B2C profiles.
   - **Split Payments:** Inability to split a single bill across multiple customers or payment methods (e.g., ₹500 Cash + ₹500 Card).
   - **Shift Management & Cash Reconciliation:** Missing End-of-Day cash drawer tracking (Opening float, Expected Cash, Actual Cash Drops).
   - **Tips & Gratuity:** No mechanism to record waiter tips natively on the bill.
   - **Surcharges:** Lack of dynamic service fees (e.g., late-night fee, credit card processing fee).

2. **Missing Reports:**
   - **Shift Z-Report:** Cashier end-of-shift reconciliation report.
   - **GST Tax Liability Report:** Dedicated accounting extracts (B2B vs B2C, HSN summary).
   - **Discount & Void Audits:** Operational reports tracking *why* items were voided and *who* authorized discounts.
   - **Profitability:** Item-level food cost percentage vs revenue.

3. **Missing Audit Logs:**
   - **Drawer Kick Audits:** No tracking for when the cash drawer is triggered without an active sale (`No Sale` button).
   - **Bill Reprint Audits:** Lack of tracking on duplicate invoice reprints, which is a major fraud vector in restaurants.

4. **Missing Tax Reports:**
   - **Indian Compliance:** GSTR-1 and GSTR-3B format extraction views.
   - **Item-Wise Tax Split:** Granular summaries of exact tax liabilities grouped by tax brackets (5%, 12%, 18%).

---

## 25. Sidebar Implementation Updates (Phase 7)
- **Billing Module Navigation:** Added a comprehensive "BILLING" section to the Module Rail (`base.html` / `context_processors.py`) configured with proper icons and permission-based visibility (visible to users with `orders.view` or `reports.sales.view`).
- **Links Added:** Billing Dashboard, Invoices, Billing Reports, Payment History, GST Reports, GST Filing, Tax Summary, Refund Bills, WhatsApp Sharing, and Billing Settings.

---

## 26. Automatic Invoice Generation & Billing UI Integration (Phase 8)
- **Data Flow Integration:** The `checkout_service.complete_checkout_transaction` robustly handles atomic invoice generation, sequential numbering, and idempotency locks. 
- **Billing UI Module:** Introduced `InvoiceListView` and `PaymentHistoryView` in `reporting/views.py` and routed them into `reporting/urls_billing.py` under the `/billing/` namespace.
- **Enterprise Billing Dashboard:** Implemented `BillingDashboardView` utilizing aggressive database-level aggregations (`Sum`, `Count`, `TruncDate`, `ExtractHour`) to rapidly compute 9 crucial KPIs (Revenue, Total Bills, Avg Bill, GST Collected, Refunds, Pending, Cash/Card/UPI splits).
- **Real-Time Analytics:** Created a modern Alpine.js and Chart.js powered interface (`billing_dashboard.html`) mapping out Daily Revenue, Monthly Revenue, Hourly Sales, Payment splits, and GST splits. HTMX is employed for 15s interval polling that flawlessly redraws and re-initializes all charts automatically, creating a seamless real-time visualization layer without WebSocket overhead.
- **Invoice Ledger Enhancements:** The `InvoiceListView` has been heavily expanded to support server-side pagination, advanced filtering (Date Range, Branch, Status), and sorting (Date, Amount). The UI now surfaces comprehensive metadata including Cashier names (via `User` mapping), Branch names (via `Branch` mapping), and dynamically calculated Payment Methods (handling `SPLIT` payments natively).
- **Payment History Ledger Enhancements:** The `PaymentHistoryView` is now fully upgraded with granular filtering by Transaction ID, Customer, Phone, Method, Date Range, and Branch. It includes robust export capabilities (CSV/Excel) natively handled by the class-based view. The ledger precisely tracks every payment's Cashier, Branch, and references to its parent Invoice/Order for 100% auditability.
- **Enterprise WhatsApp Integration:** Designed a modular `WhatsAppSharingService` that powers an interactive "edit-before-send" modal. The UI securely passes the dynamically generated invoice message and customer mobile number to the backend. The backend securely logs a `Notification` record (ensuring 100% auditability and future WhatsApp Business API readiness) before returning a sanitized `wa.me` redirect link for manual dispatch.
- **Enterprise Email Integration & PDF Generation:** Implemented a scalable email dispatch system leveraging the background Celery notification worker. Introduced a `weasyprint`-powered PDF generator (`pdf_generator.py`) that renders a print-optimized invoice (`invoice_pdf.html`) just-in-time when the async worker triggers. Upgraded the `EmailProvider` to use Django's `EmailMessage` natively supporting attachments, guaranteeing high-deliverability with strict retry queues and exact delivery tracking via the `Notification` model.
- **Enterprise GST & Tax Auditor:** Heavily expanded the `TaxReportView` by replacing dummy data and python loops with massive PostgreSQL aggregations (`TruncDate`, `TruncMonth`, `TruncYear`, `Sum`). The report now provides perfectly accurate splits of Taxable Sales, Non-Taxable Sales, Exempt Sales, along with global Daily, Monthly, and Yearly GST KPI trackers.
- **Tax Summary Dashboard:** Added a specialized dashboard (`TaxSummaryView`) combining Branch, Date, and Cashier-level filters. Accurately tracks Tax Collected vs Outstanding Tax in real-time. Driven entirely by highly-optimized `Sum` and `Filter` ORM aggregates and presented with interactive Chart.js visualizations.
- **Enterprise Billing Report Engine:** Transformed the static `SalesReportView` into a dynamic reporting engine capable of pivoting sales data across 10+ dimensions on-the-fly. Users can instantly switch between Daily Sales, Weekly, Monthly, Yearly, Cashier-wise, Branch-wise, Payment Methods, Refunds, Discounts, and Customer History.
- **Enterprise Billing Security & Audit Trails:** Fully implemented an immutable, tamper-evident logging system. Integrated a `BillingAuditLogView` for global billing forensics and an HTMX-powered `InvoiceHistoryModalView` for tracing the lifecycle of individual invoices. Each billing action accurately tracks the acting User, Device, IP Address, Branch, and Timestamp, guarded heavily by strict Domain-Driven mutation locks (`OrderNotOpen`) and RBAC permissions (`reports.financial.view`).

---

## 27. Enterprise POS Refund Engine & Settlement Adjustment System (Phase 9)

### Root Cause Analysis of "Initiate Refund" Action Failure
1. **Frontend Disconnection:** The primary "Initiate Refund" button on `reporting/refund_bills.html` was originally a static HTML button (`<!-- In a real scenario, clicking this might open... -->`) without event bindings or a modal controller.
2. **Missing Reverse Financial Accounting Workflow:** The original `initiate_refund` service in `ordering/services/refund_service.py` only created a `Refund` domain object without inserting a negative financial reversal record (`Payment` model with `kind=PaymentKind.REFUND`). Consequently, revenue KPIs, GST calculations, and daily cash drawer ledgers did not balance refunds against gross sales.
3. **Missing Automated Inventory Restock Integration:** Refunded items were not returned to branch inventory unless manually adjusted.
4. **Missing Invoice Voiding Lifecycle:** Fully refunded orders did not void the linked official GST `Invoice` record (`InvoiceStatus.VOID`).

### Production-Grade Solution Implemented
1. **Domain-Driven Refund Service Upgrade (`initiate_refund` in `ordering/services/refund_service.py`):**
   - **Concurrency Safety:** Enforces `select_for_update()` row locks on the parent `Order` during refund processing to eliminate race conditions.
   - **Financial Reversal Accounting:** Creates a negative `Payment` reversal record (`PaymentKind.REFUND`) matching the refunded amount and original payment method (`CASH`, `CARD`, `UPI`).
   - **Full vs Partial Refund Rules:** Validates cumulative refund amounts against `order.total`. If fully refunded (`already_refunded + amount >= order.total`), automatically transitions both `Order.status` and `Invoice.status` to `VOID`.
   - **Automated Inventory Restocking:** Optionally calls `apply_stock_movement` (`StockMovementType.RETURN_CUSTOMER`) to restore stock items to warehouse inventory.
   - **Real-Time Event Broadcast:** Triggers `broadcast_tenant_event("order_changed")` and `broadcast_tenant_event("payment_captured")` on database commit for instant multi-device POS display updates.

2. **Backend API Endpoints (`reporting/views.py` & `reporting/urls_billing.py`):**
   - **`RefundLookupView` (`GET /billing/refunds/lookup/`):** API endpoint allowing fast search by Order Number, Invoice Number, or Order UUID (`?query=` or `?order_id=`). Returns full breakdown of original total, already refunded amount, refundable balance, payment method, and item list snapshot.
   - **`InitiateRefundView` (`POST /billing/refunds/initiate/`):** API endpoint accepting JSON payload with `order_id`, `amount`, `reason`, `refund_type`, `payment_method`, and `restock_inventory`. Protected by strict RBAC checking (`TenantPermissionRequiredMixin` checking `reports.financial.view`, `payments.refund`, `orders.void`, `invoices.void`, or `billing.manage`).

3. **Enterprise Interactive UI Modal (`reporting/refund_bills.html`):**
   - **Alpine.js Reactive Controller (`refundBillsManager`):** Powers an interactive modal allowing live search and pre-filling of invoice details.
   - **Direct URL Pre-Loading:** Automatically opens and pre-loads order details if navigated from `invoice_list.html` (`?order=<order_id>`).
   - **Dynamic Partial/Full Refund Selector:** Switches between Full Refund (auto-locking amount to refundable balance) and Partial Refund (allowing custom amount with client-side balance validation).
   - **Quick Reason Chips & Reversal Method Selector:** One-click reason pills (`Customer Dissatisfied`, `Incorrect Item Prepared`, `Billing Error`, `Quality Issue`) and method selectors (`CASH`, `CARD`, `UPI`).
   - **Zero Page-Refresh Transition:** Provides instant feedback alerts and smooth refresh upon refund confirmation.

---

## 28. Enterprise Menu Modifiers Module — Complete Backend Gap Analysis (Phase 1)

### 1. Existing Architecture Status Matrix
| Requirement | Status | Existing Implementation | Identified Gaps / Required Improvements |
| :--- | :---: | :--- | :--- |
| **Modifier Groups** | **Partial** | `ModifierGroup(TenantAwareModel)` in `catalog/models/modifier.py` (`name`, `min_select`, `max_select`, `is_required`, `sort_order`). | Missing `description`, `is_active` status management flag, and optional branch assignment. |
| **Modifier Options** | **Partial** | `Modifier(TenantAwareModel)` in `catalog/models/modifier.py` (`group`, `name`, `price_delta`, `is_active`, `sort_order`). | Missing `inventory_item` mapping, `quantity_consumed`, `sku`, and `is_default` flag. |
| **Price Adjustments** | **Supported** | `price_delta = DecimalField(max_digits=12, decimal_places=2)` on `Modifier`. | Needs full calculation engine support in POS modal & cart edit workflows. |
| **Required Modifiers** | **Supported** | `is_required = BooleanField(default=False)` & `min_select` on `ModifierGroup`. | Needs real-time POS modal validation preventing "Add to Cart" until requirements met. |
| **Optional Modifiers** | **Supported** | `is_required = False` & `min_select = 0`. | Fully supported at schema level. |
| **Single Selection** | **Supported** | `max_select = 1` on `ModifierGroup`. | Needs automatic radio-button / single-choice rendering in POS modal. |
| **Multiple Selection** | **Supported** | `max_select > 1` on `ModifierGroup`. | Needs checkbox selection rendering with min/max bounds enforcement in POS modal. |
| **Menu Item Mapping** | **Partial** | `ProductModifierGroup` through model linking `Product` to `ModifierGroup`. | Needs management UI to easily assign/unassign modifier groups to products. |
| **Inventory Mapping** | **Missing** | No linkage between `Modifier` and `InventoryItem`. | Must add `inventory_item` FK and `quantity_consumed` DecimalField to automatically deduct stock on payment. |
| **Availability Rules** | **Partial** | `is_active` flag on `Modifier`. | Needs `is_active` on `ModifierGroup` and stock-aware disabling when inventory <= 0. |
| **Display Order** | **Supported** | `sort_order` field on `ModifierGroup`, `Modifier`, and `ProductModifierGroup`. | Needs sorting support across all APIs and management screens. |
| **Status Management** | **Partial** | `is_active` on `Modifier`. | Needs management toggle APIs and bulk status actions. |

### 2. Gap Analysis by Layer

#### A. Database Models & Schema Layer (`catalog/models/modifier.py`)
- **Existing Implementation**:
  - `ModifierGroup`: stores `name`, `description`, `min_select`, `max_select`, `is_required`, `is_active`, `sort_order`.
  - `Modifier`: stores `group`, `name`, `sku`, `price_delta`, `inventory_item`, `quantity_consumed`, `is_default`, `is_active`, `sort_order`.
  - `ProductModifierGroup`: stores `product`, `group`, `sort_order`.
- **Enterprise Gap & Extension Plan (Phase 2)**:
  - Add to `ModifierGroup`:
    - `internal_code`: `CharField(max_length=64, blank=True, default="")`
    - `display_name`: `CharField(max_length=120, blank=True, default="")`
    - `selection_type`: `CharField(max_length=20, choices=[('single', 'Single Choice'), ('multiple', 'Multiple Choice')], default='buttons')`
    - `display_style`: `CharField(max_length=20, choices=[('buttons', 'Buttons'), ('checkboxes', 'Checkboxes'), ('dropdown', 'Dropdown')], default='buttons')`
    - `expand_by_default`: `BooleanField(default=True)`
    - `print_on_invoice`: `BooleanField(default=True)`
    - `print_on_restaurant_copy`: `BooleanField(default=True)`
    - `print_on_kitchen_ticket`: `BooleanField(default=True)`
  - Add to `Modifier`:
    - `description`: `TextField(blank=True, default="")`
    - `price_type`: `CharField(max_length=20, choices=[('fixed', 'Fixed'), ('percentage', 'Percentage'), ('free', 'Free')], default='fixed')`
    - `color_code`: `CharField(max_length=20, blank=True, default="")`
    - `is_taxable`: `BooleanField(default=True)`
  - Add to `ProductModifierGroup` (Menu Item Mapping):
    - `required_override`: `BooleanField(null=True, blank=True, default=None)`
    - `min_select_override`: `PositiveIntegerField(null=True, blank=True, default=None)`
    - `max_select_override`: `PositiveIntegerField(null=True, blank=True, default=None)`

#### B. Modifier Group Management (Phase 3)
- Redesigned Create/Edit Modifier Group page structured into distinct SaaS enterprise sections:
  1. General Information (`name`, `internal_code`, `display_name`, `description`)
  2. Selection Rules (`selection_type`, `is_required`, `min_select`, `max_select`)
  3. Display Settings (`display_style`, `expand_by_default`, `sort_order`)
  4. Advanced Settings / Printing Flags (`print_on_invoice`, `print_on_restaurant_copy`, `print_on_kitchen_ticket`)
  5. Status Toggle (`is_active`)

#### C. Modifier Option Management (Phase 4)
- Dedicated Modifier Option module supporting CRUD, Soft Delete, Clone, Search, Filter, Bulk import/export CSV, and unlimited options per group.

#### D. Menu Item Mapping & Overrides (Phase 5)
- Support multiple Modifier Groups per Menu Item with per-product override rules (`required_override`, `min_select_override`, `max_select_override`, `sort_order`).

#### E. POS Ordering & Interactive Customization Popup (Phase 6 & 7)
- Automatic interception of product click: When a product has assigned modifiers, automatically opens the enterprise POS Modifier Popup without manual navigation.
- Real-time dynamic price calculations, required validation, single choice vs multiple choice support, keyboard navigation, and special instructions capture.

#### F. Cart, Billing, KOT & Inventory Integration (Phase 8–11)
- **Cart**: Modifiers displayed cleanly under products (`+ Extra Cheese (+₹30.00)`) with inline edit and removal.
- **Billing**: Modifiers included in Customer Invoice, Restaurant Copy, and Print Queue receipts based on `print_on_invoice` / `print_on_restaurant_copy` flags.
- **KOT**: Modifiers clearly itemized without prices for kitchen staff (`+ EXTRA CHEESE (2x)`), honoring `print_on_kitchen_ticket`.
- **Inventory**: Automatic stock deduction during post-payment checkout (`item.qty * modifier.quantity_consumed`) for linked inventory items (`StockMovementType.SALE`).

#### G. Reports, Analytics & Enterprise Security (Phase 12–16)
- Analytics tracking best-selling customization options, modifier revenue contribution, attach rate, profitability, and inventory consumption.
- Full RBAC, tenant isolation, audit trails, and performance optimization.

---

### [COMPLETED & VERIFIED] Enterprise Modifier Management System Implementation Summary
- **Database & Domain Architecture (Phase 2)**: Extended `ModifierGroup` (`internal_code`, `display_name`, `selection_type`, `display_style`, `expand_by_default`, `print_on_invoice`, `print_on_restaurant_copy`, `print_on_kitchen_ticket`) and `Modifier` (`description`, `price_type`, `inventory_item`, `quantity_consumed`, `is_default`, `color_code`, `is_taxable`).
- **Enterprise Modifier Group Management (Phase 3)**: Redesigned `/catalog/modifiers/create/` and `/edit/` (`templates/catalog/modifier_group_form.html`) into enterprise SaaS sections: General Information, Selection Rules & Validation, Display Settings, Advanced Printing & Routing, and Status.
- **Complete Modifier Options Module (Phase 4)**: Created dedicated options management screen (`/catalog/modifiers/<uuid:group_pk>/options/` -> `templates/catalog/modifier_options_manage.html`) with search, active/inactive filtering, inline toggle status, cloning (`(Copy)`), and full CRUD (`ModifierCreateView`, `ModifierUpdateView`, `ModifierDeleteView`).
- **Menu Item Integration (Phase 5)**: Added `modifier_groups` ManyToMany selection interface directly inside Product Create/Edit forms (`ProductForm` and `templates/catalog/product_form.html`), automatically saving assignments via `.set()` inside atomic transactions.
- **POS Customization Popup & Live Ordering (Phase 6–11)**: Enhanced `posModifierModal` script to automatically apply default options on new item selection and enforce mandatory group min/max selection rules. Fully verified end-to-end unit tests (`26 passed`).

---

### [COMPLETED & VERIFIED] Enterprise Payment Workflow Fix & Universal Popup System
- **Payment Root Cause Resolution (`checkout_service.py`)**:
  - **Issue Resolved**: When attempting to complete payment, `settle_and_invoice()` was invoked at step 4 before `payment_service.add_payment()` at step 9. Because no payment record existed when `settle_and_invoice()` checked `order.due_amount > Decimal("0")`, it raised `OutstandingDue("Due ₹290.00 remaining")`.
  - **Fix Implemented**: Reordered execution lifecycle within `complete_checkout_transaction()` so `payment_service.add_payment()` runs first (recording payment and recomputing `order.due_amount = 0`), followed immediately by `order.refresh_from_db()` and `invoice_service.settle_and_invoice()`.
- **Universal Enterprise Popup & Modal Engine (`npos_popup.html` & `NPos`)**:
  - Engineered a standardized, accessible Alpine.js + Tailwind CSS modal & toast notification architecture (`window.NPos`) supporting `toast()`, `alert()`, `confirm()`, `delete()`, `prompt()`, `paymentError()`, and `paymentSuccess()`.
  - Automatically intercepts HTMX destructive actions via `document.body.addEventListener('htmx:confirm', NPos._htmxConfirm)`.
- **Total Elimination of Native Browser Dialogs**:
  - Replaced all usages of `alert()`, `confirm()`, and `prompt()` across frontend templates (`sales_report.html`, `modifier_group_list.html`, `modifier_options_manage.html`) and backend error responses (`ordering/views.py` now returns HTTP 400 with structured `checkout_error_modal.html` partials).

---

## 22. Enterprise Combo Offers & Promotion Engine (Gap Analysis)

**Current State (July 2026):**
The Nextora POS pricing engine handles deterministic line-level calculations, proportional order discounts, and Indian GST rules. However, the system currently lacks any native domain concepts for bundled combos, meal deals, or multi-item promotional structures.

### Gap Analysis & Missing Components

#### 1. Catalog Context (Missing Models)
- **ComboOffer:** No model exists to define a combo (e.g., "Lunch Combo", fixed price ₹299, valid Mon-Fri).
- **ComboOfferGroup:** No model exists to define choice groups within a combo (e.g., "Choose 1 Burger", "Choose 1 Side").
- **ComboOfferGroupItem:** No model exists to link specific products/categories to a choice group, including upgrade surcharges (e.g., "Large Fries +₹50").

#### 2. Ordering Context (Missing Models & Cart Logic)
- **OrderCombo:** The `Order` model currently holds a flat list of `OrderItem`s. We lack an `OrderCombo` entity to logically group `OrderItem`s together under a single combo banner and track the total savings generated by the bundle.
- **OrderItem Linking:** `OrderItem` needs a nullable `combo` ForeignKey pointing to `OrderCombo` (or `order_combo_id` UUID field).
- **Pricing Integration:** `compute_bill` currently calculates taxes per `BillLine`. Combos must be exploded into individual constituent `OrderItem`s, with the combo discount distributed proportionally across their base prices to maintain accurate item-level GST compliance (Composite Supply tracking).

#### 3. Frontend & POS Workflows
- **Combo Builder UI (Back-office):** Missing catalog administration screens to build combos visually, define active schedules, and link products.
- **Cart Grouping:** The POS context panel (`cart_panel.html`) renders flat items. It must be updated to render `OrderCombo`s as expandable groups with remove/edit actions.
- **Auto-Detection Engine:** When cashier scans/adds items, we lack a cart-analyzer service to suggest matching combos dynamically.

#### 4. KOT, Billing & Inventory Sync
- **Billing:** Invoices need to group line items by Combo to show the customer the bundled offer and total savings.
- **KDS:** Kitchen Order Tickets must display the Combo name above grouped items so chefs understand the presentation context, but exclude prices.
- **Inventory:** Because combos decompose into native `OrderItem`s, the existing inventory deduction engine will correctly process stock deductions without architectural changes.
