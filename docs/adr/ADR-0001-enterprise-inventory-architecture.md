# ADR-0001: Enterprise Inventory Architecture

**Status:** Proposed
**Date:** 2026-06-27
**Deciders:** Platform Architecture, Backend Lead, Product (Inventory), Finance/Compliance
**Context (bounded context):** `src/contexts/inventory`
**Related:** PROJECT_CONTEXT.md §5 (`ordering`, `catalog`), §10 roadmap item 5 (Inventory), §10 item 6 (outbox/events), catalog ADR on transactional outbox (events established in `catalog`).

---

## Context

Nextora POS needs an **enterprise-grade inventory module** for multi-tenant
restaurants: stock per branch/warehouse, batch + expiry control, purchasing,
inter-warehouse transfers, adjustments/damage with audit, recipe-driven
consumption on sale, automatic reorder, and alerting. Targets from
PROJECT_CONTEXT: 10k+ tenants, 100k concurrent users, millions of stock
movements.

### Forces at play

- **Financial correctness.** Stock valuation feeds COGS, GST input credit, and
  P&L. Quantity and cost must be auditable and reconcilable to the cent/gram.
- **Concurrency.** A busy kitchen sells, receives, transfers, and counts the
  same item concurrently. Lost updates corrupt stock.
- **Bounded-context isolation (DDD).** `inventory` must not hard-FK into
  `catalog`, `ordering`, or `restaurant`. Those contexts may later be extracted
  to services (PROJECT_CONTEXT §3.1).
- **Throughput on the hot path.** A POS sale must settle in milliseconds; it
  cannot block on inventory recalculation, recipe explosion, or alert fan-out.
- **Traceability/compliance.** Damage, expiry write-offs, and stocktakes need
  defensible records (insurance, audit, FSSAI/FIFO compliance).
- **Existing investment.** An inventory context is already scaffolded with an
  immutable ledger (`StockMovement`), `InventoryItem` master, batches, POs,
  transfers, adjustments, damage, and alerts. This ADR **ratifies** those
  decisions and **resolves the open ones** (Recipe/BOM, Consumption, reorder
  automation, cross-context integration, negative-stock policy).

### Constraints

- Python 3.12 / Django 5 / DRF / PostgreSQL / Redis / Celery (existing stack).
- All money is `Decimal`; quantities `Decimal(14,3)`, costs `Decimal(14,4)`.
- Every owned row extends `TenantAwareModel` (tenant scoping + RLS, 4-layer
  defense). UUID PKs. `created_at/updated_at/created_by/updated_by` + soft delete.
- Cross-context references are **soft UUID FKs** with denormalized snapshots.

---

## Decision

Adopt a **ledger-first, event-driven, per-(product × warehouse) inventory**
model inside the modular monolith:

1. **The immutable `StockMovement` ledger is the single source of truth.** Every
   quantity change — purchase, sale/consumption, transfer, adjustment, damage,
   opening — is an append-only, signed ledger entry. `InventoryItem.quantity_on_hand`
   is a **denormalized running balance** maintained by, and reconcilable to, the
   sum of movements.
2. **One mutation path.** All stock changes go through
   `services/movement_service.apply_stock_movement(...)`, which row-locks the
   item (`SELECT … FOR UPDATE`), validates non-negative balance, updates the
   batch, recomputes weighted-average cost, writes the movement, and schedules
   alert evaluation `on_commit`. No other code may write `quantity_on_hand`.
3. **Stock is located per warehouse.** The grain is `(tenant, product_id,
   warehouse)`. Warehouses carry a soft `branch_id` so stock rolls up per branch.
4. **Cross-context integration is event-driven via the shared transactional
   outbox** (the pattern `catalog` already established). `ordering` publishes a
   domain event on sale settlement; `inventory` subscribes and performs
   recipe-driven consumption asynchronously and idempotently. Inventory never
   blocks the POS bill.
5. **New components to close the requirement gaps:** `Recipe`/`RecipeComponent`
   (BOM), a consumption handler, and a scheduled **reorder suggestion** engine.

This is largely an **"accept and extend"** decision: it formalizes the as-built
ledger architecture and fills the missing Recipe/Consumption/reorder pieces.

---

## Options Considered

### Option A: Mutable quantity snapshot (counter-on-product)

A single `quantity` column per product/warehouse, mutated in place; history (if
any) kept in a separate audit log.

| Dimension | Assessment |
|-----------|------------|
| Complexity | Low |
| Cost | Low |
| Scalability | High write throughput, low read cost |
| Auditability | **Poor** — no defensible trail; cost layers lost |
| Team familiarity | High |

**Pros:** Simplest; fastest reads; minimal storage.
**Cons:** No reconcilable history; weighted-average/FIFO costing impossible to
reconstruct; concurrent updates easily lost; fails compliance (damage/expiry).

### Option B: Immutable movement ledger + denormalized balance (CHOSEN)

Append-only `StockMovement` is truth; `quantity_on_hand`, `average_cost`, and
batch quantities are denormalized projections updated transactionally.

| Dimension | Assessment |
|-----------|------------|
| Complexity | Medium |
| Cost | Medium (movement rows grow; partitionable) |
| Scalability | High — single locked item row per change; ledger is append-only |
| Auditability | **Excellent** — every gram traceable to a document |
| Team familiarity | High (mirrors `ordering`/`audit` ledger patterns) |

**Pros:** Full traceability; reconcilable (`Σ movements == on_hand`); supports
WAC/FIFO costing; natural fit for events and reporting projections; already
built.
**Cons:** Two writes per change (movement + projection); requires a reconciliation
job; ledger table needs partitioning/archival at scale.

### Option C: Full event-sourced inventory / external WMS

Inventory state rebuilt purely from an event stream (Kafka/event store), or
delegated to a dedicated WMS service.

| Dimension | Assessment |
|-----------|------------|
| Complexity | **High** |
| Cost | High (new infra, ops burden) |
| Scalability | Very high |
| Auditability | Excellent |
| Team familiarity | Low |

**Pros:** Ultimate scalability and temporal querying; clean service extraction.
**Cons:** Massive over-engineering for current scale; new infrastructure
(Kafka/event store) and operational maturity we don't have; premature given the
modular monolith. Revisit only if inventory is extracted to its own service.

---

## Trade-off Analysis

- **A vs B — auditability beats simplicity.** Inventory drives COGS, GST input
  credit, and shrinkage/insurance claims. A mutable counter cannot defend a
  number to an auditor or reconstruct cost layers. The ledger's extra write and
  reconciliation job are a cheap price for correctness, and Postgres handles the
  volume with table partitioning by `created_at`.
- **B vs C — don't pay for scale we don't have.** Event sourcing/external WMS
  buys extraction and extreme scale we won't need before the inventory context
  is split out. Option B keeps strong consistency *within* inventory (DB
  transactions) while using the **transactional outbox** for *cross-context*
  eventing — we get event-driven decoupling without standing up Kafka.
- **Sync vs async consumption (the crux).** Deducting recipe ingredients
  synchronously inside the POS settle transaction couples `ordering` to
  `inventory` availability and latency, and risks blocking a sale on a stock
  lock. Deducting **asynchronously via the outbox** keeps the bill fast and the
  contexts decoupled, at the cost of **eventual consistency** (stock can be
  briefly negative/stale). For restaurants this is acceptable — you serve the
  dish and reconcile stock — provided consumption is **idempotent** and supports
  a configurable negative-stock policy. This is the decisive trade-off and is
  recorded as Component Decision D6.
- **Costing: weighted-average vs FIFO.** WAC (as-built) is simple, stable, and
  adequate for restaurant ingredients; FIFO is more accurate for volatile prices
  but requires cost-layer tracking on consumption. We keep **WAC** and revisit
  per-tenant FIFO if finance requires it (D2).

---

## Component Decisions

Each row is a decision this ADR commits to. "As-built" = ratifies existing code;
"New" = to be designed/added.

| # | Area | Decision | Rationale | State |
|---|------|----------|-----------|-------|
| D1 | **Stock grain** | Track stock per `(tenant, product_id, warehouse)` via `InventoryItem`; `quantity_on_hand/reserved/on_order` denormalized; `quantity_available = on_hand − reserved`. | Multi-warehouse is a hard requirement; per-warehouse grain enables transfers and branch rollups. | As-built |
| D2 | **Costing** | **Weighted-average cost**, recomputed on every stock-in in `movement_service`. Costs `Decimal(14,4)`. | Simple, stable, audit-friendly for ingredients. FIFO deferred. | As-built |
| D3 | **Mutation invariant** | All changes via `apply_stock_movement` only; row-lock with `SELECT … FOR UPDATE`; reject moves that drive balance < 0 unless policy allows (D6). | Prevents lost updates and back-door writes; the ledger stays authoritative. | As-built |
| D4 | **Batch / Lot** | `Batch` per `(item, batch_number)` with `manufacture_date`/`expiry_date`; quantity maintained by the ledger; non-negative check. | Enables expiry control and recall traceability. | As-built |
| D5 | **Expiry strategy** | **FEFO** (First-Expired-First-Out) batch selection on consumption/transfer; expired stock written off via an adjustment (`AdjustmentReason.EXPIRED`). | Minimizes spoilage; compliance-friendly. Default FEFO, overridable per item. | As-built (FEFO ordering) + New (write-off flow) |
| D6 | **Sale consumption** | `ordering` publishes `OrderSettled`/`SaleCompleted` to the **transactional outbox**; an `inventory` handler explodes the recipe (D7) and deducts components **FEFO**, idempotently (keyed by order id). **Negative-stock policy is per-tenant config**: `BLOCK` (default for retail goods) or `ALLOW_NEGATIVE` (default for kitchen ingredients) — the latter records the movement and raises an alert instead of failing. | Keeps the POS bill fast and contexts decoupled; eventual consistency is acceptable for kitchens. Idempotency protects against at-least-once redelivery. | **New** |
| D7 | **Recipe / BOM** | New `Recipe` (1 per sellable `catalog.Product`, **versioned**, soft FK) + `RecipeComponent` (component `inventory_item`, `quantity`, optional `wastage_pct`, `yield_qty`). Consumption uses the **active version** at sale time. | Restaurants need ingredient deduction and food-cost; versioning preserves historical COGS. | **New** |
| D8 | **Purchasing** | `PurchaseOrder` lifecycle `DRAFT→SENT→PARTIALLY_RECEIVED→RECEIVED|CANCELLED`; **partial receipts** create a `Batch` + `PURCHASE` movement, update WAC, and decrement `quantity_on_order`. PO numbers gapless per tenant. | Mirrors real procurement; partial receipts are the norm. | As-built |
| D9 | **Supplier** | `Supplier` master with GSTIN/PAN/bank/credit terms; used for input-tax-credit and payment reconciliation. | GST compliance + AP. | As-built |
| D10 | **Transfers** | Two-phase `StockTransfer` `DRAFT→IN_TRANSIT→RECEIVED|CANCELLED`: dispatch creates `TRANSFER_OUT` at source, receipt creates `TRANSFER_IN` at destination; batch-aware; in-transit owns the stock between phases. Lock warehouses in a **deterministic order** (by id) to avoid deadlocks. | Models real shipping latency and shrinkage in transit; ordered locking prevents cross-transfer deadlock. | As-built (states) + New (lock ordering) |
| D11 | **Adjustments** | `StockAdjustment` + lines with `AdjustmentReason` and an **approval workflow** (`is_approved`/`approved_by_id`); each approved line emits an `ADJUSTMENT_ADD/REMOVE` movement. | Manual corrections need reason codes and sign-off for shrinkage control. | As-built |
| D12 | **Damage** | Dedicated `DamagedStock` (separate from generic adjustments) with incident date, photo evidence, loss value; linked to the generated adjustment and a `DAMAGED` movement. | Insurance/compliance need a first-class damage record, not a generic note. | As-built |
| D13 | **Reorder level** | `reorder_point` / `reorder_quantity` / `minimum_stock` on `InventoryItem`. A scheduled **reorder suggestion engine** (Celery Beat, `bulk` queue) scans items where `on_hand + on_order ≤ reorder_point` and emits **draft POs / suggestions** grouped by supplier — never auto-submits. | Automates replenishment while keeping a human approval gate. | As-built (fields) + New (engine) |
| D14 | **Alerts** | `InventoryAlert` types low/out/expiry/expired/damaged; **partial-unique constraint prevents duplicate open alerts**; low/out evaluated synchronously `on_commit` after each movement; expiry evaluated by a scheduled sweep; auto-resolve when condition clears. Delivery (email/SMS/push) is handed to the `notifications` context. | Idempotent, low-noise alerting; separation of detection vs delivery. | As-built (detection) + New (notifications wiring) |
| D15 | **Reservation** | `quantity_reserved` reserved by open orders (optional, behind a feature flag); reduces `quantity_available` without a movement until settle. | Prevents overselling scarce retail goods; off by default for kitchens. | New (deferred, flagged) |
| D16 | **Reconciliation** | Nightly Celery job asserts `Σ StockMovement.quantity == InventoryItem.quantity_on_hand` per item and `Σ batch movements == Batch.quantity`; discrepancies raise an alert + audit entry. | Detects drift between ledger and projection early. | **New** |
| D17 | **Idempotency** | Receipts, consumption, and transfer phases are keyed by `(reference_type, reference_id, phase)`; replaying an event or retrying a task never double-applies. | Outbox delivery is at-least-once; financial writes must be exactly-once in effect. | **New** |

---

## Consequences

### What becomes easier
- **Auditing & reporting.** Any balance is explainable as a sum of documented
  movements; COGS, valuation, shrinkage, and food-cost are direct ledger queries.
- **Cross-context decoupling.** `ordering` knows nothing about stock; it just
  emits an event. Inventory, reporting, and notifications subscribe independently.
- **Correct concurrency.** A single locked item row per change makes the hot path
  race-free without table-level locks.
- **Compliance.** Damage, expiry write-offs, and stocktakes are first-class,
  defensible records.

### What becomes harder
- **Eventual consistency on sales.** Stock reflects a sale only after the
  consumption event is processed; dashboards may briefly lag, and stock can go
  negative under `ALLOW_NEGATIVE`. Requires clear UX ("pending consumption") and
  the reconciliation job (D16).
- **Operational surface.** New Celery Beat jobs (reorder, expiry sweep,
  reconciliation) and outbox handlers to monitor; dead-letter handling matters.
- **Write amplification.** Two writes per change (movement + projection) and
  ledger growth — needs **table partitioning** of `stock_movement` by month and
  an archival policy.
- **Idempotency discipline.** Every event-driven write must carry an idempotency
  key; getting this wrong double-counts stock.

### What we'll need to revisit
- **FIFO costing** per tenant if finance requires cost-layer accuracy (D2).
- **Reservation** semantics if retail/packaged-goods oversell becomes real (D15).
- **Event sourcing / WMS extraction** (Option C) only when inventory is split
  into its own service at much higher scale.
- **Negative-stock defaults** per product type once real kitchen data is in.

---

## Action Items

> Design/specification follow-ups. **No implementation in this ADR.**

1. [ ] Ratify D1–D5, D8–D12, D14 as the accepted baseline (already coded; review
       against this ADR and add the reconciliation invariant).
2. [ ] Specify **Recipe/BOM** models (`Recipe`, `RecipeComponent`), versioning
       rules, and food-cost calculation (D7).
3. [ ] Define the **`OrderSettled` domain event** contract (payload: order id,
       line items with product/variant/qty, branch/warehouse resolution) and the
       inventory consumption handler (D6, D17).
4. [ ] Decide **negative-stock policy** storage (per-tenant + per-product-type
       override) and surface it in settings/feature flags (D6).
5. [ ] Specify the **reorder suggestion engine** (schedule, supplier grouping,
       draft-PO output, approval gate) (D13).
6. [ ] Specify the **expiry sweep** and **nightly reconciliation** Celery Beat
       jobs, including alert/audit outputs (D5, D14, D16).
7. [ ] Plan **`stock_movement` partitioning** (monthly range) and archival before
       first production load.
8. [ ] Define **warehouse lock-ordering** rule for transfers to prevent deadlock
       (D10).
9. [ ] Wire alert **delivery** through the `notifications` context (D14).
10. [ ] Add the **branch FK** migration when the `restaurant`/branch module
        promotes `branch_id` soft refs to real FKs (PROJECT_CONTEXT §7.6).

---

## Appendix: Requirement → Decision traceability

| Requirement | Covered by |
|-------------|-----------|
| Warehouse | D1, D10 |
| Stock | D1, D2, D3, D16 |
| Purchase | D8, D9 |
| Supplier | D9 |
| Transfers | D10 |
| Batch | D4 |
| Expiry | D5, D14 |
| Stock Adjustment | D11 |
| Damage | D12 |
| Consumption | D6, D17 |
| Recipe | D7 |
| Reorder Level | D13 |
| Alerts | D14, D16 |
