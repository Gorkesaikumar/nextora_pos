# ADR-0002: Customer Domain Architecture

**Status:** Proposed
**Date:** 2026-06-27
**Deciders:** Platform Architecture, Backend Lead, Product (CRM/Loyalty), Finance/Compliance (wallet = money), Legal/DPO (PII)
**Context (bounded context):** `src/contexts/customers`
**Related:** ADR-0001 (Inventory — ledger + outbox patterns reused here), PROJECT_CONTEXT §5 (`ordering`, `billing`), §10 item 6 (outbox/events). Catalog/Inventory established the transactional-outbox pattern.

---

## Context

Nextora POS needs a **customer/CRM domain** for multi-tenant restaurants spanning
identity, money-like balances, and engagement: customer profiles (incl. GST
B2B customers), loyalty points, prepaid **wallet**, **store credit / outstanding**
(accounts receivable), purchase history, automatic **offers**, **coupons**,
paid **membership**, and **referral**. Scale targets per PROJECT_CONTEXT: 10k+
tenants, 100k concurrent users, millions of transactions.

### What already exists (as-built)

A `customers` context is scaffolded with: `Customer` (phone-per-tenant identity,
GSTIN/legal_name, loyalty tier/points, `wallet_balance`, `credit_limit`,
`outstanding_credit`), immutable sub-ledgers (`PointsLedger`, `WalletTransaction`,
`CreditLedger`), and `Coupon`. Services mutate the denormalised balance under
`SELECT … FOR UPDATE` and append a ledger row. This ADR **ratifies** the
ledger-backed approach and **resolves the open decisions** (purchase history,
offers, membership, referral) while fixing concrete weaknesses in the as-built
code (see "Known weaknesses").

### Forces at play

- **Some of these balances are money.** The wallet is a **real liability** (the
  restaurant owes the customer); store credit is a **receivable**. Errors are
  financial, not cosmetic — they demand exactly-once posting, reconciliation,
  audit, and (for the wallet) regulatory awareness.
- **At-sale vs post-sale.** Coupons/offers/wallet/credit must be validated and
  applied **synchronously** while a bill is being built (they change the amount
  due). Loyalty earning, purchase-history, referral rewards and credit-settlement
  posting happen **after** the sale and must not block the POS.
- **Bounded-context isolation.** The customer domain must not hard-FK into
  `ordering`/`billing`. Purchase history must be derived without querying another
  context's tables.
- **PII & compliance.** Customer rows hold personal data (name, phone, email,
  GSTIN). Privacy law (retention, erasure) and — for stored-value wallets — RBI
  PPI rules are in scope.
- **Engagement is rule-driven and tenant-specific.** Earn rates, tier thresholds,
  offer rules, membership benefits must be **DB-driven config, never hardcoded**
  (the as-built loyalty tiers are hardcoded — a violation to fix).

### Constraints

- Python 3.12 / Django 5 / DRF / PostgreSQL / Redis / Celery.
- Money is `Decimal(12,2)`; every owned row extends `TenantAwareModel` (tenant
  scope + RLS, UUID PK, audit, soft delete). Cross-context refs are soft UUIDs.
- Reuse the **transactional outbox** (`shared.infrastructure.events`) and the
  payment **gateway ports/adapters** already built in `billing`.

### Known weaknesses in the as-built code (to fix here)

1. **Hardcoded loyalty thresholds** (500/2000/5000) and implicit earn rules in
   `services.adjust_points` — violates the "no hardcoded business rules" rule.
2. **Coupon redemption is not atomic** — `validate_coupon` checks `current_uses`
   but nothing increments it transactionally; no per-customer cap → over-redemption
   under concurrency.
3. **No idempotency** on order-driven effects — a redelivered/retried order event
   would double-credit points, double-charge credit, or double-spend wallet.
4. **No reconciliation** of `wallet_balance`/`outstanding_credit` against their
   ledgers.
5. `validate_coupon` uses `all_objects` with an explicit `tenant_id` filter,
   side-stepping the tenant-scoped manager (smell).

---

## Decision

Model the Customer Domain as **two layers inside the `customers` context**:

1. **Value accounts (financial) — ledger-backed.** Wallet, store credit, and
   loyalty points are each an **immutable ledger** as the source of truth, with a
   denormalised balance on `Customer` as a reconcilable projection, mutated under
   a per-customer row lock. All order-driven postings are **exactly-once**
   (idempotency key), **audited**, and **reconciled** nightly. This mirrors the
   inventory ledger (ADR-0001).

2. **Engagement (rule-driven) — config + event projections.** Offers, coupons,
   membership, referral and purchase-history are driven by **DB-stored rules**
   and **event-fed projections**. Purchase history is a **read model** populated
   from `ordering` events via the outbox — never a cross-context query.

3. **Integration split (the crux):**
   - **Synchronous at sale** (during billing): validate + apply coupon/offer,
     reserve/redeem wallet and store-credit tender, compute loyalty *accrual
     preview*. These change the amount due, so `ordering` calls published
     customer services in-transaction.
   - **Asynchronous post-sale** (via outbox events from `ordering`): award
     loyalty points, append the purchase-history projection, post credit
     settlement, grant referral rewards. Decoupled, idempotent, eventually
     consistent.

4. **Wallet stays closed-loop** (store credit only, no cash-out / P2P transfer)
   to remain outside RBI PPI licensing — a deliberate scope boundary (D2).

This is an **"accept the ledger spine, add the engagement layer, fix the
financial-integrity gaps"** decision.

---

## Options Considered

### Option A: Denormalised balances + ad-hoc services (current trajectory)

Keep mutable `wallet_balance`/`outstanding_credit`/`loyalty_points` on `Customer`
with thin services; ledgers as a side log; rules in code.

| Dimension | Assessment |
|-----------|------------|
| Complexity | Low |
| Cost | Low |
| Financial integrity | **Poor** — no reconciliation, no idempotency, hardcoded rules |
| Scalability | OK (single row lock) |
| Team familiarity | High |

**Pros:** Least work; already partly built.
**Cons:** Money handled without exactly-once or reconciliation; double-posting on
event redelivery; rules hardcoded (un-tenantable); no purchase history/offers/
membership/referral. Fails the financial and product bar.

### Option B: Ledger-backed value accounts + event-driven engagement (CHOSEN)

Immutable ledgers as truth + projected balances + outbox-fed projections; rules
in DB; sync-at-sale / async-post-sale split. Reuses the inventory pattern.

| Dimension | Assessment |
|-----------|------------|
| Complexity | Medium |
| Cost | Medium (ledger growth, projections, reconciliation jobs) |
| Financial integrity | **Strong** — exactly-once, reconcilable, audited |
| Scalability | High (per-customer lock; projections offload reads) |
| Team familiarity | High (mirrors `inventory`/`ordering`/`billing`) |

**Pros:** Auditable money; decoupled from `ordering`; tenant-configurable rules;
covers every requirement. Consistent with the rest of the platform.
**Cons:** More moving parts (projections, reconciliation, idempotency discipline);
eventual consistency for post-sale effects.

### Option C: Split contexts and/or external CRM/loyalty SaaS

Separate `loyalty`, `wallet/payments`, `crm` contexts now, or integrate a
third-party loyalty/CRM/wallet provider.

| Dimension | Assessment |
|-----------|------------|
| Complexity | High |
| Cost | High (integration/vendor, or premature service split) |
| Scalability | Very high |
| Team familiarity | Low |

**Pros:** Clean future extraction; offloads wallet/compliance to a licensed PPI
provider; best at extreme scale.
**Cons:** Premature for a modular monolith; vendor lock-in and data-residency/
multi-tenant friction; over-engineered for current scale. **Revisit specifically
for the wallet** if we ever allow cash-out (then a licensed PPI provider is the
right call) and for CRM if marketing automation outgrows us.

---

## Trade-off Analysis

- **A vs B — money demands a ledger.** Wallet and credit are balance-sheet items.
  A mutable counter cannot be reconciled or defended to an auditor, and without
  idempotency, at-least-once order events will double-post. The ledger's extra
  write + nightly reconciliation is the cost of correct money. Decisive.
- **B vs C — don't outsource/split prematurely**, with one carve-out: the
  **wallet's regulatory exposure**. By keeping the wallet **closed-loop** (spend
  only in-store, no withdrawal), we stay outside PPI licensing and can build it
  in-house (D2). If product ever wants cash-out, that single feature flips the
  build-vs-buy decision toward a licensed provider — so we isolate the wallet
  behind a port now to keep that option open.
- **Sync vs async integration.** Applying a coupon/offer or spending wallet must
  be synchronous — it changes the bill — so `ordering` calls customer services
  inside the billing transaction (tight coupling accepted for correctness).
  Everything that *follows* a completed sale (earn points, history, referral
  reward, credit settlement) goes through the **outbox**, keeping the POS fast
  and the contexts decoupled, at the cost of brief eventual consistency. The
  reconciliation job is the safety net.
- **Offers vs Coupons — two mechanisms, one pipeline.** Offers are *automatic*
  (rule matches the cart), coupons are *explicit* (customer presents a code).
  They share a single deterministic **discount pipeline** (D13) so stacking and
  precedence are predictable rather than emergent.

---

## Component Decisions

"As-built" ratifies existing code; "New" is to design/add; "Fix" corrects an
as-built weakness.

| # | Area | Decision | Rationale | State |
|---|------|----------|-----------|-------|
| D1 | **Customer identity** | Natural key = `(tenant, phone)`; email/GSTIN optional. Provide an explicit **merge** operation (re-point ledgers/history, tombstone the dup) for duplicate profiles. | Phone is the POS lookup key; dedup is inevitable. | As-built (key) + New (merge) |
| D2 | **Wallet** | **Closed-loop stored value**: ledger-backed (`WalletTransaction` = truth, `wallet_balance` = projection), spend in-store only, **no cash-out / transfer**. Top-up via the existing `billing` gateway port. Exactly-once + audited. | Keeps us outside RBI PPI licensing while giving customers prepaid balance; real money ⇒ ledger. | As-built + Fix (idempotency, reconcile) |
| D3 | **Store credit / Outstanding** | AR ledger (`CreditLedger` = truth, `outstanding_credit` = projection); **credit-limit enforced under the customer row lock**; add **aging buckets** (0–30/31–60/61–90/90+) and statements. | Receivables need limit control + aging for collections. | As-built + New (aging/statements) |
| D4 | **Loyalty** | Points ledger (`PointsLedger`) + **DB-driven earn/burn rules and tier thresholds** per tenant (remove hardcoded 500/2000/5000), **point expiry**, and a tracked **points liability**. Tier recomputed from a config table. | "No hardcoded business rules"; points are a liability with expiry. | As-built (ledger) + **Fix** (config) |
| D5 | **Purchase History** | A **read-model projection** in the customer context, populated from `ordering` events (`OrderSettled`/`InvoiceIssued`) via the outbox; stores per-customer order/spend summaries + line rollups. Never queries `ordering` tables. | Decoupling + fast CRM reads; avoids cross-context joins. | **New** |
| D6 | **Offers** | **Automatic, rule-based** promotions (cart/item/tier/time-window/BOGO). Rules stored in DB; evaluated **synchronously at sale**; emit which offers applied. | Tenant-configurable promotions without code changes. | **New** |
| D7 | **Coupons** | Code-based; add a **`CouponRedemption` ledger** with **atomic claim** (lock + increment `current_uses` in one tx), **per-customer usage cap**, and validity/min-spend. Replace the non-atomic check. | Prevents over-redemption races; enables per-customer limits. | As-built (model) + **Fix** (atomic redemption) |
| D8 | **Membership** | **Paid program**: `MembershipPlan` (price, period, benefits) + `Membership` (customer subscription: active/expired, validity, auto-renew) billed through the **`billing` gateway port**. Distinct from earned loyalty tier (membership is bought; tier is earned). | Recurring paid perks are a separate concept from loyalty. | **New** |
| D9 | **Referral** | `ReferralCode` per customer + `Referral` attribution; reward granted **on a qualifying event** (referee's first settled order) via the outbox; **fraud guards** (self-referral, velocity, device/phone reuse). | Event-driven, abuse-resistant growth loop. | **New** |
| D10 | **Integration split** | **Sync at sale** (validate/apply coupon+offer, redeem wallet/credit tender) via published customer services called in the billing tx; **async post-sale** (earn points, history projection, credit settlement, referral reward) via outbox events from `ordering`. | Bill correctness needs sync; engagement effects can be eventual. | **New** |
| D11 | **Idempotency** | Every order-driven posting (points earn, wallet spend, credit charge/settle, referral reward) carries an **idempotency key** (order/line/event id) with a partial-unique guard on the relevant ledger. | At-least-once outbox delivery must not double-post money/points. | **New (Fix)** |
| D12 | **Reconciliation** | Nightly job asserts `Σ WalletTransaction == wallet_balance` and `Σ CreditLedger == outstanding_credit` (and points) per customer; discrepancies raise an alert + audit. | Detects projection drift in money balances early. | **New** |
| D13 | **Discount pipeline** | One deterministic order: **automatic offers → coupon → loyalty-points redemption → wallet/credit tender**, with explicit **stacking rules** (e.g. one coupon per bill; offers stack unless flagged exclusive). | Predictable, testable discounting instead of emergent behaviour. | **New** |
| D14 | **PII / privacy** | Treat contact fields as PII: encrypt-at-rest where warranted, define **retention**, and implement **right-to-erasure as anonymise-in-place** (tombstone PII, keep financial ledgers for audit). | Data-protection compliance without breaking financial records. | **New** |
| D15 | **Concurrency** | Per-customer `SELECT … FOR UPDATE` for all value-account mutations (as-built); accept hot-row serialisation per customer (acceptable — contention is per individual). | Correctness for money under concurrency. | As-built |

---

## Consequences

### What becomes easier
- **Defensible money.** Wallet liability and credit receivable are explainable as
  a sum of ledger entries; reconciliation catches drift.
- **Decoupling.** `ordering` emits events; loyalty, history, and referral react
  independently — and a future reporting/marketing context can subscribe too.
- **Tenant-configurable engagement.** Earn rates, tiers, offers, membership perks
  live in DB config, not code.
- **Predictable discounting.** A single pipeline makes promotions testable.

### What becomes harder
- **Eventual consistency post-sale.** Points/history/rewards land shortly *after*
  the bill; UX must show "pending" and the reconciliation job must run.
- **Operational surface.** New outbox handlers + Beat jobs (point expiry,
  membership renewal, reconciliation, statement generation) to monitor.
- **Idempotency discipline.** Every order-driven posting needs a key; mistakes
  double-credit money.
- **Compliance burden.** PII handling (erasure/retention) and the wallet's
  closed-loop boundary must be enforced and reviewed.

### What we'll need to revisit
- **Wallet cash-out / open-loop** → would require a **licensed PPI provider**
  (flip to Option C for the wallet only).
- **Marketing automation / segmentation at scale** → a dedicated CRM context or
  external platform.
- **Membership billing** overlaps `billing`'s subscription machinery — decide
  reuse vs a customer-specific lightweight version.
- **Points liability accounting** treatment with Finance (breakage, expiry).

---

## Action Items

> Design/specification follow-ups. **No implementation in this ADR.**

1. [ ] Ratify the ledger spine (wallet/credit/points) and add the **idempotency
       key + partial-unique** to each ledger (D2/D3/D4/D11).
2. [ ] **Fix loyalty config**: move earn rules + tier thresholds + expiry to a
       per-tenant config table; remove hardcoded values (D4).
3. [ ] **Fix coupon redemption**: `CouponRedemption` ledger + atomic claim +
       per-customer cap; retire the non-atomic `current_uses` check (D7).
4. [ ] Define the **`ordering` event contracts** the domain consumes
       (`OrderSettled`/`InvoiceIssued`: customer id, totals, lines, tender) (D5/D10).
5. [ ] Specify the **Purchase-History projection** (schema + handler) (D5).
6. [ ] Specify the **Offers rules model + evaluation** and the **discount
       pipeline / stacking** precedence (D6/D13).
7. [ ] Specify **Membership** (`MembershipPlan`/`Membership`) and its billing via
       the gateway port; relationship to loyalty tier (D8).
8. [ ] Specify **Referral** (codes, attribution, qualifying event, fraud guards)
       (D9).
9. [ ] Specify **aging buckets + statements** for outstanding credit (D3).
10. [ ] Specify the **nightly reconciliation** + **point-expiry** + **membership-
        renewal** Beat jobs (D12, D4, D8).
11. [ ] **PII plan**: classify fields, retention, anonymise-on-erasure flow;
        legal/DPO review (D14).
12. [ ] Plan **partitioning/archival** for the high-volume ledgers
        (wallet/points/history) before production load.

---

## Appendix: Requirement → Decision traceability

| Requirement | Covered by |
|-------------|-----------|
| Customer | D1, D14, D15 |
| Loyalty | D4, D11, D12 |
| Wallet | D2, D11, D12 |
| Credit | D3, D11 |
| Outstanding | D3, D12 |
| GST Customer | D1 (GSTIN/legal_name on profile) |
| Purchase History | D5, D10 |
| Offers | D6, D13 |
| Coupons | D7, D13 |
| Membership | D8 |
| Referral | D9 |
