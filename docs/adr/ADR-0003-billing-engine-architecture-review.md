# Enterprise Architecture Review Board (EARB)
## Technical Review Report: Nextora POS Billing Engine Architecture (ADR-0003)

**Review Date:** 2026-06-27  
**Review Board:** Enterprise Architecture Review Board (EARB)  
**Target Context:** `src/contexts/ordering`  
**Documents Evaluated:** [ADR-0003: POS Billing Engine Architecture](file:///d:/NEXTORA_POS/docs/adr/ADR-0003-billing-engine-architecture.md)

---

## Executive Summary

The EARB has completed an architectural audit of the proposed **POS Billing Engine Architecture**. The design demonstrates a solid understanding of the domain, particularly in its use of pure domain models for financial calculations, double-payment prevention via idempotency constraints, and RLS multi-tenant database isolation.

However, several critical gaps have been identified that pose risks to the system's **financial correctness, performance scaling, concurrency throughput, and offline data consistency**. 

This report challenges specific areas of the proposed architecture and recommends concrete improvements to ensure the platform can scale to 100,000+ concurrent terminals.

---

## Detailed Architectural Challenges

### 1. Financial Correctness
* **The Back-Calculation Rounding Problem:** The ADR describes forward calculations (subtotal $\rightarrow$ discount $\rightarrow$ tax). However, in many jurisdictions, menu prices are presented to consumers as **tax-inclusive**. When calculating the taxable base, the system must perform back-calculation:
  $$\text{Taxable Base} = \frac{\text{Inclusive Price}}{1 + \text{Tax Rate}}$$
  If a restaurant sells an item for ₹100.00 at an 18% GST rate:
  $$\text{Taxable Base} = \frac{100}{1.18} \approx 84.7457627...$$
  Rounding this to `Decimal(12,2)` yields ₹84.75, which results in a computed tax of ₹15.25 (totaling ₹100.00). However, if a customer buys 100 units of this item, rounding the unit base first ($84.75 \times 100 = 8475.00$) versus calculating on the total batch ($8474.58$) introduces a ₹0.42 variance.
* **Tip Revenue Recognition Risk:** Mixing tips directly into the payment total without separating them at the database layer can cause the system to misclassify tips as restaurant revenue. This can lead to compliance issues regarding sales tax (GST/VAT) reporting.

---

### 2. Concurrency Bottleneck (DailyCounter Sequence Lock)
* **The Serial Write Bottleneck:** Using `SELECT ... FOR UPDATE` on the `DailyCounter` table to guarantee gapless invoice numbering creates a significant database bottleneck:
  ```sql
  SELECT last_number FROM daily_counter 
  WHERE tenant_id = %s AND location_id = %s AND scope = 'invoice' AND date = %s 
  FOR UPDATE;
  ```
  This row lock forces a single-threaded write bottleneck for all cashiers checkout transactions in a specific branch. If a high-volume branch has 15 POS terminals checking out guests at peak hours, the database will experience transaction delays and lock waits.

---

### 3. Tax Calculations & Compliance
* **Place of Supply (POS) Fallback Rules:** For inter-state transactions (IGST) vs. intra-state transactions (CGST + SGST), the system requires the customer's tax state. If a cashier processes a transaction without entering customer details, the system lacks a fallback rule.
* **Line-Level vs. Bill-Level Tax Rounding:** Laws in different regions require rounding taxes at different stages. For example, India's GST regulations allow rounding to the nearest rupee at the invoice summary level, whereas other jurisdictions require rounding at the line item level. The engine must support both configurations dynamically.

---

### 4. Refund Logic & Discount Clawbacks
* **Refund of Proportionally Discounted Orders:** If an order has a flat order-level discount applied (e.g. ₹50 off ₹500), returning a single item requires clawing back the correct portion of the discount. If the refunded amount is calculated using the original item price, the customer will be over-refunded.
* **Loyalty Points Deficit Handling:** When a guest returns an item, the system should claw back the loyalty points earned on that purchase. If the customer has already spent those points, the system must have a strategy for handling a negative points balance or deducting the value of the points from the refund.

---

### 5. Duplicate Payments & Webhook Race Conditions
* **Webhook vs. Callback API Races:** For card and UPI payments, the external gateway (e.g. Razorpay) sends a webhook notification. At the same time, the POS client sends a frontend redirect callback to mark the transaction as paid. If both processes run concurrently, they can cause a race condition, leading to double-allocation of loyalty points or stock deductions.

---

### 6. Invoice Numbering & Operating Business Dates
* **Midnight Date Crossovers:** If a shift starts at 8:00 PM on Friday and ends at 3:00 AM on Saturday, using the system wall-clock date (`date = timezone.now().date()`) will split the shift's transactions across two different dates in the `DailyCounter` table. This complicates financial reconciliation for the shift.

---

### 7. Performance & Data Storage Scale
* **Write Amplification on Billed Orders:** Storing full snapshots of item names, variants, modifiers, and tax details on every single order item record prevents changes to the menu catalog from altering historical sales records. However, this design increases database storage requirements. At a scale of millions of invoices, it will lead to database performance degradation.

---

### 8. Disaster Recovery & Offline Synchronization Conflicts
* **The "Void-Modify" Split Brain:** During an internet outage, a manager voids an order on a local POS client. Meanwhile, on the active cloud database, a cashier has already settled the order. When the connection is restored, the sync engine faces a conflict: an order that is marked as `voided` offline and `paid` online.

---

## Recommendations for Improvement

The EARB recommends the following updates to the Billing Engine architecture before starting implementation:

### 1. Financial Math
* **Adopt Unit Back-Calculation Standards:** Always store unit prices, line discounts, and taxable amounts with 4 decimal places (`Decimal(12,4)`) during calculation. Round the final values to 2 decimal places (`Decimal(12,2)`) only at the invoice summary level.
* **Explicit Liability Mapping for Tips:** Map tips to a dedicated `tips_collected` balance field in the database. This separates tips from the taxable invoice subtotal and records them as a non-revenue liability.

### 2. High-Throughput Sequence Allocation
* **Decouple Settlement from Invoice Numbering:** To eliminate the database write bottleneck on the `DailyCounter` table:
  1. Cashiers settle transactions using a unique, transient order reference ID.
  2. The POS client prints a customer receipt immediately using this transaction reference.
  3. The system assigns the formal tax invoice number asynchronously using a background worker queue (e.g., Celery). This shifts sequence generation out of the user-facing checkout transaction.

### 3. Operating Business Dates
* **Use Business Dates for Sequences:** Instead of using the server's timezone date for the `DailyCounter` key, use the active **Business Date** linked to the branch's open shift. This ensures all transactions in a single shift are grouped under the same date, regardless of midnight crossovers.

### 4. Refund Calculations
* **Enforce Net-of-Discount Refund Calculations:** Ensure that the refund service calculates values using the net taxable base of the item after applying all proportional discounts:
  $$\text{Refund Value}_i = \text{Item Price}_i - \text{Allocated Line Discount}_i$$

### 5. Webhook and Callback Synchronization
* **Database Row Locking for Payments:** Enforce a database lock on the parent order before processing any payment status updates. Use the payment's `idempotency_key` as a lock key in Redis to prevent concurrent processing of webhooks and client callbacks.

### 6. Database Storage Optimization
* **Implement Database Partitioning:** Partition the `order`, `order_item`, and `tax_invoice` tables by year or quarter. Move closed invoices older than 90 days to a read-only historical archive database to keep the active database small and fast.

### 7. Offline Sync Conflict Resolution
* **Implement Strict Business Rules for Offline Conflicts:** Establish clear rules for resolving offline sync conflicts:
  1. Paid transactions are immutable. If an order is marked as `paid` on the server, reject any offline modification events for that order.
  2. Create a compensating transaction (e.g., a stock adjustment or credit note) to reconcile any variances caused by rejected offline modifications.
