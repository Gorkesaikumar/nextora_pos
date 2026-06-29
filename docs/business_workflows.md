# Nextora POS: Enterprise Business Workflow & BPMN Documentation

This document acts as the definitive blueprint for the business domain architecture of Nextora POS. It defines the core end-to-end workflows of the modular monolith system, mapping them to system boundaries, role permissions, domain events, notifications, audit trails, and strict business rules.

---

## Architecture Context & Multi-Tenant Blueprint
All workflows in Nextora POS operate under a **shared-database, shared-schema multi-tenant model**, where isolation is enforced natively at the database layer via PostgreSQL Row-Level Security (RLS). Every tenant-owned row includes a `tenant_id` linked to the central `tenants.Tenant` model.
- **Tenant Scope**: A context manager `tenant_scope(tenant_id)` binds the active tenant for asynchronous operations (e.g., Celery tasks, webhook processing).
- **Audit Logs**: The system records every mutating operation in an append-only, tenant-scoped audit ledger (`audit.AuditLog`).

---

## Business Workflows Catalog

### 1. Restaurant Registration
* **Description**: A new restaurant signs up on the Nextora POS landing page, provisioning their dedicated tenant account and initial company owner credentials.
* **Pool/Lanes**:
  - `Tenant Admin` (Actor)
  - `Nextora Web App` (Frontend UI)
  - `Identity Context` (Backend User/Membership/RBAC management)
  - `Tenants Context` (Backend Tenant lifecycle management)
  - `Billing Context` (Backend Entitlements/SaaS lifecycle)

#### BPMN-style Flow
```
[Start: Admin Registration Request]
   │
   ▼
[Task: Admin Submits Form] (Email, Business Name, Subdomain Slug, Password)
   │
   ▼
[Exclusive Gateway: Slug Available?]
   ├── No  ──► [End: Error - Subdomain Unavailable]
   └── Yes ──► [Task: Create Tenant & TenantDomain] (Status: trialing)
                 │
                 ▼
               [Task: Generate Default RBAC Roles] (Company Owner, Cashier, Waiter, KDS, etc.)
                 │
                 ▼
               [Task: Create User & Assign 'Company Owner' Membership]
                 │
                 ▼
               [Task: Initialize Free Trial Subscription] (Billing Context)
                 │
                 ▼
               [Parallel Gateway]
                 ├── Flow 1 ──► [Task: Write Initial Audit Trail Log]
                 └── Flow 2 ──► [Task: Queue Celery welcome/verify email]
                                       │
                                       ▼
                                [End: Registration Completed]
```

* **Actors**: Tenant Admin (Restaurant Owner)
* **Preconditions**:
  - Email has not been registered in the identity database.
  - Requested tenant subdomain/slug is unique and not reserved.
* **Main Flow**:
  1. Actor submits the registration form with email, password, company name, and preferred subdomain.
  2. The system checks email and subdomain uniqueness.
  3. The system generates a new `Tenant` record with `status='trialing'` and links a corresponding `TenantDomain` record.
  4. The system provisions the standard 9 role templates (`company_owner`, `branch_manager`, `cashier`, `kitchen_staff`, `waiter`, `inventory_manager`, `accountant`, `support`, `super_admin`) for the new tenant.
  5. The system creates the `User` record with Argon2 hashing and assigns a `Membership` mapping the user to the new tenant with the `company_owner` role.
  6. The system triggers the creation of a trial `Subscription` under the default free tier plan.
  7. A verification token Celery task is scheduled, and a welcome email is sent.
* **Alternate Flows**:
  - *SaaS Landing Portal vs Support Onboarding*: If created by support, the support actor bypasses domain availability verification as they can override restrictions manually.
* **Error Flows**:
  - *Domain Collision*: Subdomain is already taken; form is returned to the user with validation error `uq_tenant_domain`.
  - *Verification Email Failed*: SMTP fails; the user account is created but is flagged as unverified. The UI prompts for resending verification upon login.
* **Events**:
  - `TenantCreated` (contains `tenant_id`, `owner_email`, `domain`)
  - `UserRegistered` (contains `user_id`, `email`)
* **Business Rules**:
  - Subdomains must match `^[a-z0-9-]+$` and be at least 3 characters.
  - Tenant default status must be `trialing`.
  - Membership of the creator must be `company_owner` at the root tenant level (no location restriction).
* **Required Permissions**: Public (No authentication required to register)
* **Audit Events**:
  - `TENANT_CREATED` (Tenant ID, Domain)
  - `USER_MEMBERSHIP_ASSIGNED` (User ID, Role ID)
* **Notifications**: Welcome email containing the email verification link.

---

### 2. Subscription Purchase
* **Description**: A restaurant upgrades from trial to paid, or renews their existing subscription by selecting a billing plan and executing payment.
* **Pool/Lanes**:
  - `Company Owner` (Actor)
  - `Billing Context` (Backend SaaS Billing engine)
  - `Razorpay SDK / Gateway` (External Payment Service)
  - `Tenants Context` (SaaS status modifier)

#### BPMN-style Flow
```
[Start: Upgrade/Renewal Requested]
   │
   ▼
[Task: Select Plan & Billing Interval] (Monthly / Annually)
   │
   ▼
[Task: Create Pending Invoice & Sequence Lock]
   │
   ▼
[Task: Initialize Razorpay Checkout Order]
   │
   ▼
[Intermediate Catch: Webhook / Callback from Razorpay]
   │
   ▼
[Exclusive Gateway: Payment Successful?]
   ├── No  ──► [Task: Mark Invoice Past Due] ──► [End: Payment Failed]
   └── Yes ──► [Task: Mark Invoice Paid & Stamped]
                 │
                 ▼
               [Task: Transition Subscription State to Active]
                 │
                 ▼
               [Task: Refresh Tenant Limits / Entitlements]
                 │
                 ▼
               [End: Subscription Active]
```

* **Actors**: Company Owner
* **Preconditions**:
  - Tenant account is not suspended.
  - Selected Plan and PlanPrice are active in the global plan catalog.
* **Main Flow**:
  1. Actor navigates to billing panel and selects a subscription plan.
  2. Billing context lock ensures a single active/pending subscription per tenant.
  3. System creates a `SubscriptionInvoice` using the atomic `BillingSequence` generator to avoid invoice number gaps.
  4. System initiates the external gateway session (Razorpay order).
  5. Actor completes checkout via the frontend.
  6. Razorpay fires a verified webhook `payment.captured` or user redirects back to callback.
  7. System marks the invoice as Paid, generates the `SubscriptionPayment` record, updates the `Subscription` object state to `active`, and sets the billing cycle dates.
* **Alternate Flows**:
  - *Auto-renewal*: Celery Beat hourly task detects subscriptions close to renewal, attempts automatic charge via stored payment token. If successful, renews subscription and generates invoices automatically.
* **Error Flows**:
  - *Payment Decline / Insufficient Funds*: Razorpay fails. Invoice transitions to `past_due`. The system enters a grace period. If grace period (e.g. 7 days) expires, the system triggers the subscription to `expired` and blocks write access via middleware check.
* **Events**:
  - `SubscriptionUpgraded` (contains `tenant_id`, `plan_id`, `invoice_id`)
  - `SubscriptionPaymentSucceeded` (contains `invoice_id`, `amount`, `transaction_id`)
* **Business Rules**:
  - Only one active subscription allowed per tenant.
  - Pricing decimals must carry currency and match `PlanPrice` records.
  - Sequence generation must be strictly atomic (`SELECT FOR UPDATE` on `BillingSequence`).
* **Required Permissions**: `billing.manage`
* **Audit Events**:
  - `SUBSCRIPTION_MODIFIED` (Subscription ID, previous state, new state)
  - `INVOICE_SETTLED` (Invoice ID, total amount paid)
* **Notifications**: Subscription invoice email with PDF copy.

---

### 3. Restaurant Onboarding
* **Description**: A newly registered tenant fills out core business parameters, initializes tax metrics, and configures base operational rules.
* **Pool/Lanes**:
  - `Company Owner` (Actor)
  - `Catalog Context` (GST rates and menu categories configuration)
  - `Inventory Context` (Default warehouse/stock allocations)
  - `Tenants Context` (Timezone/Currency configuration)

#### BPMN-style Flow
```
[Start: First Login / Setup Wizard]
   │
   ▼
[Task: Define Localization Rules] (Timezone, Base Currency, Decimal Precision)
   │
   ▼
[Task: Seed Default Tax Classes] (e.g., GST 5%, GST 18%, Exempt)
   │
   ▼
[Task: Initialize Root Warehouse / Storage Location]
   │
   ▼
[Task: Seed Sample Category Tree]
   │
   ▼
[End: Tenant Setup Completed]
```

* **Actors**: Company Owner
* **Preconditions**:
  - Tenant is registered and has status `trialing` or `active`.
* **Main Flow**:
  1. Actor inputs localization metadata (timezone, local currency code, decimal rounding rules).
  2. System persists configuration directly on the `Tenant` instance.
  3. System provisions default `TaxClass` structures (e.g., standard SGST/CGST rates for POS operations).
  4. System auto-provisions a default root `Warehouse` (e.g., "Main Kitchen / Main Store") to facilitate initial stock loading.
  5. Onboarding wizard creates a core root `Category` to allow immediate menu builder catalog configuration.
* **Alternate Flows**:
  - *Data Import*: Tenant imports pre-existing menus/inventories using the CSV import utility.
* **Error Flows**:
  - *Unsupported Currency/Timezone*: Invalid format rejects model validation; forms return errors to user without saving.
* **Events**:
  - `OnboardingCompleted` (contains `tenant_id`, `setup_timestamp`)
* **Business Rules**:
  - Active currency must match payment gateway options.
  - Soft-deletable entities must start in an un-deleted state.
* **Required Permissions**: `tenants.manage`
* **Audit Events**:
  - `TENANT_METADATA_UPDATED` (Fields updated)
  - `WAREHOUSE_PROVISIONED` (Warehouse ID)
* **Notifications**: Setup walkthrough dashboard prompt.

---

### 4. Branch Setup
* **Description**: An enterprise tenant adds a new geographical retail outlet, sets up printers, and configures local kitchen routing targets.
* **Pool/Lanes**:
  - `Company Owner` / `Branch Manager` (Actor)
  - `Tenants Context` (Branch validation)
  - `Catalog Context` (Printer/KitchenStation setup)
  - `Identity Context` (Staff location allocation)

#### BPMN-style Flow
```
[Start: Setup New Branch]
   │
   ▼
[Task: Submit Branch Parameters] (Name, Physical Address, Tax Reg ID)
   │
   ▼
[Exclusive Gateway: Subscription Limit Exceeded?]
   ├── Yes ──► [End: Error - Upgrade Plan Required]
   └── No  ──► [Task: Save Branch Model] (Persists UUID location)
                 │
                 ▼
               [Task: Register POS Printers & Kitchen Stations]
                 │
                 ▼
               [Task: Assign Staff Membership to Branch]
                 │
                 ▼
               [End: Branch Setup Success]
```

* **Actors**: Company Owner, Branch Manager
* **Preconditions**:
  - Subscription limits have not been exceeded (branches allocation check).
* **Main Flow**:
  1. Actor initiates branch registration with name, street, phone, and local tax identifiers.
  2. System reads active subscription entitlement limits via the entitlements service.
  3. System creates a `Branch` (Location representation).
  4. Actor registers network IP printers and defines `KitchenStation` structures (e.g., "Cold Station", "Grill Station").
  5. Actor maps staff members to the branch via localized memberships.
* **Alternate Flows**:
  - *Multi-Branch Shared Inventory*: Mapping the branch to use an existing central warehouse rather than generating a new local warehouse.
* **Error Flows**:
  - *Entitlement Check Fails*: A `SubscriptionLimitExceeded` error is raised. UI redirects to Plan Upgrade page.
* **Events**:
  - `BranchCreated` (contains `tenant_id`, `branch_id`)
  - `KitchenStationRegistered` (contains `branch_id`, `station_id`)
* **Business Rules**:
  - Branch location UUIDs must remain unique across the tenant scope.
  - Tax Registration must follow the host nation format (e.g., GSTIN format check for India operations).
* **Required Permissions**: `branches.manage`
* **Audit Events**:
  - `BRANCH_ADDED` (Branch ID, Address)
  - `PRINTER_CONFIGURED` (Printer IP, Branch ID)
* **Notifications**: Branch activation notification to designated branch manager.

---

### 5. Product Creation
* **Description**: A restaurant manager builds out the menu catalog by configuring categories, products, prices, variants, tax classes, and modifiers.
* **Pool/Lanes**:
  - `Branch Manager` / `Inventory Manager` (Actor)
  - `Catalog Context` (Backend Menu inventory engine)

#### BPMN-style Flow
```
[Start: Add Menu Product]
   │
   ▼
[Task: Define Category & Product Name]
   │
   ▼
[Task: Assign Tax Class] (Link SGST/CGST/IGST tax rates)
   │
   ▼
[Task: Define Variants & Base Cost/Sell Price]
   │
   ▼
[Task: Link Modifier Groups & Modifiers] (e.g., Extra Cheese)
   │
   ▼
[Task: Generate Barcode / SKU]
   │
   ▼
[End: Product Catalog Entry Created]
```

* **Actors**: Branch Manager, Inventory Manager
* **Preconditions**:
  - Target parent `Category` exists.
  - Target `TaxClass` is active.
* **Main Flow**:
  1. Actor details product attributes: name, description, category, and base pricing structures.
  2. Actor links the product to a specific `TaxClass`.
  3. Actor adds variants (e.g., "Regular", "Large") with differential pricing matrices.
  4. Actor maps modifiers (e.g., extra sauces or toppings).
  5. System computes default GST distributions (CGST, SGST, IGST mapping rules).
  6. System generates unique barcodes/SKUs for the items.
* **Alternate Flows**:
  - *Bulk CSV Import*: Import via spreadsheet streaming service, executing cycle guards to verify category tree loop safety.
* **Error Flows**:
  - *Duplicate SKU*: Save triggers validation error `uq_product_sku`. UI displays warning to change code.
  - *Cyclic Category Loop*: Category parent is set to its own subcategory; catalog cycle guard throws validation exception.
* **Events**:
  - `ProductCreated` (contains `product_id`, `sku`, `sell_price`)
  - `CatalogUpdated` (triggers cache invalidation signal for POS terminals)
* **Business Rules**:
  - Selling price cannot be zero unless flagged as free modifier.
  - SKU and Barcodes must be unique per tenant (reusable only after soft deletion).
* **Required Permissions**: `catalog.manage`
* **Audit Events**:
  - `PRODUCT_CREATED` (Product ID, Name, Selling Price)
  - `MODIFIER_GROUP_LINKED` (Product ID, Modifier Group ID)
* **Notifications**: Product update push signal to active cashier POS clients.

---

### 6. Inventory Purchase
* **Description**: Purchasing managers register suppliers, raise Purchase Orders (POs) for raw stock ingredients, and submit them for managerial approval.
* **Pool/Lanes**:
  - `Inventory Manager` (Actor)
  - `Branch Manager` / `Approver` (Actor)
  - `Inventory Context` (Supplier/PO management)

#### BPMN-style Flow
```
[Start: Purchase Order Required]
   │
   ▼
[Task: Select Supplier & Define Warehouse Target]
   │
   ▼
[Task: Compose Purchase Order Line Items] (Raw Items, Unit Costs, Order Qty)
   │
   ▼
[Task: Submit Purchase Order for Review]
   │
   ▼
[Exclusive Gateway: Total Value > Approval Limit?]
   ├── No  ──► [Task: Auto-Approve PO]
   └── Yes ──► [Task: Await Manager Approval] (Status: pending_approval)
                 │
                 ▼
               [Task: Manager Approves PO] (Status: approved)
                 │
                 ▼
               [Task: Transmit PO to Supplier]
                 │
                 ▼
               [End: Purchase Order Dispatched]
```

* **Actors**: Inventory Manager, Branch Manager
* **Preconditions**:
  - Selected `Supplier` is active.
  - Target stock `Warehouse` exists.
* **Main Flow**:
  1. Inventory Manager registers/selects a `Supplier`.
  2. Inventory Manager initiates a `PurchaseOrder` mapping line items (e.g. cheese blocks, flour bags), indicating order quantities and negotiated unit cost prices.
  3. System computes projected totals and checks manager approval hierarchies.
  4. If within auto-limits, status shifts directly to `approved`. Otherwise, it remains `pending_approval` until signed off by the Branch Manager.
  5. The PO status transitions to `ordered` upon manual download or automated supplier email dispatch.
* **Alternate Flows**:
  - *Direct PO*: Raising an emergency PO directly, bypassing approval structures if flagged by the Company Owner.
* **Error Flows**:
  - *PO Rejected*: Manager rejects the PO. Status transitions to `rejected` with reasons logged in audit trail.
* **Events**:
  - `PurchaseOrderCreated` (contains `po_id`, `supplier_id`)
  - `PurchaseOrderApproved` (contains `po_id`, `approver_id`)
* **Business Rules**:
  - Total PO cost calculations must use `Decimal` values.
  - PO lines must only contain inventory items active on the system.
* **Required Permissions**: `inventory.po_manage`
* **Audit Events**:
  - `PURCHASE_ORDER_SUBMITTED` (PO ID, Grand Total)
  - `PURCHASE_ORDER_APPROVED` (PO ID, Actor ID)
* **Notifications**: Approval request alert sent to Branch Manager; purchase order PDF sent to supplier.

---

### 7. Stock Update
* **Description**: Raw inventory arrives at the kitchen dock. Staff inspect the order, record the actual received quantities, allocate batch numbers, and verify stock updates.
* **Pool/Lanes**:
  - `Inventory Staff` (Actor)
  - `Inventory Context` (Stock adjustment, movements, and batches)
  - `Audit Context` (Log tracking)

#### BPMN-style Flow
```
[Start: Delivery Truck Arrives at Dock]
   │
   ▼
[Task: Inspect Goods & Check against PO]
   │
   ▼
[Task: Input Received Quantities in System]
   │
   ▼
[Task: Assign Batch Numbers, Manufacturing & Expiry Dates]
   │
   ▼
[Task: Calculate Cost Variance] (PO Price vs Invoice Price)
   │
   ▼
[Parallel Gateway]
   ├── Flow 1 ──► [Task: Update InventoryItem Stock Levels]
   ├── Flow 2 ──► [Task: Write StockMovement Transaction Journal]
   └── Flow 3 ──► [Task: Close/Partially Close Original Purchase Order]
                       │
                       ▼
                 [End: Stock Levels Updated]
```

* **Actors**: Inventory Staff, Inventory Manager
* **Preconditions**:
  - Purchase Order status is `ordered` or `partially_received`.
* **Main Flow**:
  1. Actor reviews the physical cargo shipment against the PO.
  2. Actor logs in to the system, enters received quantities, and assigns corresponding `Batch` numbers (with manufacturing and expiry dates).
  3. System calculates cost variances (real cost vs PO forecast).
  4. System updates the absolute `quantity_on_hand` on `Item` records via database transactions.
  5. System records `StockMovement` logs tracing types as `RECEIPT` with source links to the PO.
  6. PO status is set to `received` (or `partially_received` if outstanding balances remain).
* **Alternate Flows**:
  - *Direct Stock Receipt*: If stocking items without a formal pre-configured PO (e.g. direct store purchases), staff create a direct `StockMovement` entry using type `RECEIPT`.
* **Error Flows**:
  - *Expired Batches*: Expiry date entered is prior to current date. System rejects the transaction with a validation error.
* **Events**:
  - `StockReceived` (contains `movement_id`, `item_id`, `qty_received`)
  - `StockAlertTriggered` (fired if receipt fails to push items above minimum thresholds)
* **Business Rules**:
  - Database updates must lock target rows (`select_for_update`) to prevent concurrent race conditions during stock incrementing.
  - Expired inventory cannot be received.
* **Required Permissions**: `inventory.receive`
* **Audit Events**:
  - `STOCK_INCREMENTED` (Item ID, Batch ID, Quantity)
  - `PO_STATE_TRANSITION` (PO ID, Previous Status, New Status)
* **Notifications**: Alert sent if incoming item quantities differ significantly from original PO requests.

---

### 8. Customer Registration
* **Description**: A guest registers at the POS terminal, enrolling in the loyalty program and initiating an active store credit / prepaid wallet account.
* **Pool/Lanes**:
  - `Cashier` / `Customer App` (Actor)
  - `Customers Context` (CRM, Loyalty, and Ledger database)

#### BPMN-style Flow
```
[Start: Register New Guest]
   │
   ▼
[Task: Submit Customer Contact Details] (Name, Phone, Email)
   │
   ▼
[Task: Create Customer Account Profile]
   │
   ▼
[Parallel Gateway]
   ├── Flow 1 ──► [Task: Enroll in LoyaltyProgram] (Initial Tier: Bronze/Base)
   └── Flow 2 ──► [Task: Initialize Prepaid Wallet Account] (Balance: 0.00)
                       │
                       ▼
                 [End: Customer Enrolled]
```

* **Actors**: Cashier, Customer
* **Preconditions**:
  - Phone number/email must be unique within the tenant bounds.
* **Main Flow**:
  1. Cashier enters customer name, phone number, and optional email on the POS.
  2. System checks duplication constraints.
  3. System creates a `Customer` profile record.
  4. System automatically instantiates a default `LoyaltyProgram` membership (setting tier to baseline Bronze/Standard).
  5. System provisions a `WalletTransaction` tracking system (setting starting balance to 0.00).
* **Alternate Flows**:
  - *Bulk Customer Import*: Importing legacy loyalty tables via CSV structures during system migration.
* **Error Flows**:
  - *Phone Number Exists*: System flags duplicate numbers. Cashier is prompted to search for the existing record instead.
* **Events**:
  - `CustomerRegistered` (contains `customer_id`, `loyalty_membership_id`)
* **Business Rules**:
  - Phone numbers must be normalized before validation (e.g. removal of special characters and addition of country codes).
  - Multi-tenant partitioning must ensure customers from Tenant A are completely hidden from Tenant B.
* **Required Permissions**: `customers.manage`
* **Audit Events**:
  - `CUSTOMER_CRM_CREATED` (Customer ID, Name, Phone)
  - `LOYALTY_TIER_ASSIGNED` (Customer ID, Tier Name)
* **Notifications**: SMS confirmation sent to customer welcoming them to the loyalty program.

---

### 9. Table Reservation
* **Description**: Customers reserve tables. Hosts verify availability on the floor plan, allocate layout targets, and manage arrival states.
* **Pool/Lanes**:
  - `Host / Cashier` (Actor)
  - `Restaurant Context` (Table layouts, reservation constraints)
  - `Notifications Context` (SMS/Email dispatch)

#### BPMN-style Flow
```
[Start: Reservation Inquiry]
   │
   ▼
[Task: Query Table Layout Availability by Date, Time & Cover Size]
   │
   ▼
[Exclusive Gateway: Suitable Table Available?]
   ├── No  ──► [Task: Add Guest to Waitlist] ──► [End: Waitlisted]
   └── Yes ──► [Task: Hold Table Layout Targets]
                 │
                 ▼
               [Task: Create Reservation Record] (Status: confirmed)
                 │
                 ▼
               [Task: Dispatch Confirmation Alert]
                 │
                 ▼
               [Intermediate Event: Customer Arrives]
                 │
                 ▼
               [Task: Update Table Status to Seated]
                 │
                 ▼
               [End: Reservation Completed]
```

* **Actors**: Host, Customer
* **Preconditions**:
  - The requested time slot falls within the restaurant's active hours.
* **Main Flow**:
  1. Host checks grid availability on the terminal visual floor layout.
  2. Host registers customer details, guest size (covers), and desired booking slot.
  3. System queries table capacities.
  4. Host selects an available table; system locks the slot and creates a `Reservation` record with status `confirmed`.
  5. The system triggers a confirmation SMS to the customer.
  6. Upon arrival, the host marks the guest as `seated`, updating table status in real-time.
* **Alternate Flows**:
  - *Waitlist Registration*: If fully booked, the guest is added to the Waitlist queue. If a cancellation occurs, the system alerts the host to seat the waitlisted customer.
* **Error Flows**:
  - *Double Booking Collision*: Two staff members select the same table simultaneously. The database throws a transaction lock exception; the second attempt is rejected, prompting the host to select a different table.
* **Events**:
  - `ReservationConfirmed` (contains `reservation_id`, `table_id`, `arrival_time`)
  - `TableSeated` (contains `table_id`, `order_id`)
* **Business Rules**:
  - Table selection capacity must be equal to or greater than the requested covers count.
  - Reservations expire if the customer does not arrive within a grace period (e.g. 15 minutes).
* **Required Permissions**: `restaurant.reserve`
* **Audit Events**:
  - `RESERVATION_CREATED` (Reservation ID, Table Number, Covers)
  - `RESERVATION_CANCELLED` (Reservation ID, Reason)
* **Notifications**: Confirmation SMS with booking details; cancellation alert.

---

### 10. Dine-In Order
* **Description**: Waiters open a new order for seated table guests, select items with custom modifiers, send tickets to the kitchen, and track the table through service.
* **Pool/Lanes**:
  - `Waiter` (Actor)
  - `Ordering Context` (Order processing, bills, KOT generation)
  - `Catalog Context` (Menu validation)
  - `Kitchen Station / KDS` (Preparation visual boards)

#### BPMN-style Flow
```
[Start: Table Guest Seats]
   │
   ▼
[Task: Waiter Opens New Order] (Links Table & Waiter ID)
   │
   ▼
[Task: Select Menu Items & Modifiers]
   │
   ▼
[Task: Validate Stock Levels] (Confirm ingredients/preps are available)
   │
   ▼
[Task: Send to Kitchen]
   │
   ▼
[Task: System Generates KOT & Routes to Stations] (Hot Kitchen, Bar, Grill)
   │
   ▼
[Task: Waiter Delivers Food & Bumps KDS Status] (Status: served)
   │
   ▼
[End: Order Active on Table]
```

* **Actors**: Waiter, Cashier
* **Preconditions**:
  - The assigned table is marked as occupied.
* **Main Flow**:
  1. Waiter selects an active table on the POS and clicks "New Order".
  2. Waiter inputs menu items and options (e.g., "Medium Rare Steaks" with "Extra Gravy").
  3. Waiter clicks "Send to Kitchen".
  4. System runs validation, reserves inventory items, and generates a Kitchen Order Ticket (KOT).
  5. KOT is sent to active KDS displays or physical thermal printers based on the routing configuration.
  6. The order status transitions to `preparing`.
  7. Food is prepared, served, and marked as `served` on the waiter's terminal.
* **Alternate Flows**:
  - *Split/Merge Orders*: Guests want to pay separately. Waiter selects items and triggers `split_order` service. This creates two distinct order UUIDs linked to the same table.
* **Error Flows**:
  - *Item Out-of-Stock*: Ingredient counts fall below threshold limits. POS prevents order submission, forcing the waiter to remove or substitute the item.
* **Events**:
  - `OrderCreated` (contains `order_id`, `table_id`)
  - `KOTGenerated` (contains `kot_id`, `items_list`)
* **Business Rules**:
  - Order numbers must follow a sequential pattern that resets daily.
  - Multi-tenant protection must ensure that orders are isolated at the database level.
* **Required Permissions**: `ordering.create`
* **Audit Events**:
  - `ORDER_OPENED` (Order ID, Table ID)
  - `KOT_SENT_TO_KITCHEN` (KOT ID, Items Count)
* **Notifications**: KDS sound chime alerting kitchen staff to new orders.

---

### 11. Takeaway Order
* **Description**: A guest places an order at the front counter. The cashier collects payment immediately, submits the items to the kitchen, and dispatches the order when ready.
* **Pool/Lanes**:
  - `Cashier` (Actor)
  - `Ordering Context` (Menu, Order, KOT routing, Payment calculations)
  - `Kitchen Station` (Visual prep display)

#### BPMN-style Flow
```
[Start: Customer walks up to Counter]
   │
   ▼
[Task: Input Takeaway Order Items]
   │
   ▼
[Task: Collect Upfront Payment] (Cash, Card, or UPI)
   │
   ▼
[Task: Generate Order, Invoice & Receipt] (Order Status: paid)
   │
   ▼
[Task: Dispatch KOT to Kitchen]
   │
   ▼
[Task: Kitchen Prepares & Bumps Order]
   │
   ▼
[Task: Handover Food to Customer]
   │
   ▼
[End: Order Closed]
```

* **Actors**: Cashier, Kitchen Staff
* **Preconditions**:
  - POS terminal is logged in and the cash drawer session is open.
* **Main Flow**:
  1. Cashier creates a new order, flagging the service type as `takeaway`.
  2. Cashier inputs the items and modifiers.
  3. Cashier collects upfront payment.
  4. System processes payment and generates a paid invoice.
  5. System generates the KOT and routes it to the kitchen display.
  6. Cashier hands a printed receipt with a queue number to the customer.
  7. When the kitchen bumps the order as ready, the cashier calls the queue number and dispatches the food.
* **Alternate Flows**:
  - *Pay Later*: If configured, takeaway orders can be sent to the kitchen before payment is collected. The order is then settled at pickup.
* **Error Flows**:
  - *Payment Processing Fails*: Card terminal declines transaction. Cashier cancels checkout and selects an alternative payment method (e.g. Cash) or voids the pending order.
* **Events**:
  - `TakeawayOrderPlaced` (contains `order_id`, `queue_number`)
  - `TakeawayOrderDispatched` (contains `order_id`)
* **Business Rules**:
  - Takeaway queue numbers must reset to 1 at the start of each day.
  - Tax calculation must use localized takeaway tax rules (e.g., exclusion of service charges).
* **Required Permissions**: `ordering.takeaway`
* **Audit Events**:
  - `TAKEAWAY_ORDER_PAID` (Order ID, Payment Method)
  - `TAKEAWAY_DISPATCHED` (Order ID, Queue Number)
* **Notifications**: Queue notification chime when the order is ready.

---

### 12. Online Order (Aggregator Integration)
* **Description**: Online ordering platforms (e.g., third-party aggregators or direct consumer web portals) transmit orders directly to the restaurant's POS system.
* **Pool/Lanes**:
  - `Third-Party Aggregator` (External API webhook)
  - `POS Webhook Gateway` (API authentication layer)
  - `Ordering Context` (Auto-acceptance & order creation)
  - `Kitchen Station` (Preparation routing)

#### BPMN-style Flow
```
[Start: Online Order Event Received]
   │
   ▼
[Task: Authenticate Aggregator Signature & Payload]
   │
   ▼
[Task: Validate Menu Item Availability & Operating Hours]
   │
   ▼
[Exclusive Gateway: Accept Automatically?]
   ├── No  ──► [Task: Route to Cashier Review Queue] ──► [Task: Cashier Accepts]
   └── Yes ──► [Task: Auto-Accept Order]
                 │
                 ▼
               [Task: Create Order & Map External Payment ID]
                 │
                 ▼
               [Task: Generate KOT & Print Delivery Slips]
                 │
                 ▼
               [Task: Await Delivery Rider Assignment]
                 │
                 ▼
               [End: Order Ready for Pickup]
```

* **Actors**: Cashier, Third-Party Delivery Rider
* **Preconditions**:
  - Tenant API keys and webhooks are active.
  - POS system is online.
* **Main Flow**:
  1. Aggregator API posts an order payload to Nextora.
  2. Gateway authenticates the request using HMAC signatures.
  3. System matches aggregator menu IDs with Nextora catalog catalog mappings.
  4. If menu items are available, system auto-accepts the order.
  5. System generates the order, routes KOT items to target kitchen prep stations, and prints a delivery slip.
  6. The delivery driver is notified when the order is bumped as ready.
* **Alternate Flows**:
  - *Manual Review Queue*: If configured, online orders route to a review list on the POS terminal. The cashier must manually click "Accept" to route the order to the kitchen.
* **Error Flows**:
  - *Item Out-of-Stock*: If an item is unavailable, the webhook returns a cancellation response. The aggregator notifies the customer, and the order is voided.
* **Events**:
  - `OnlineOrderReceived` (contains `external_order_id`, `aggregator_name`)
  - `OnlineOrderAccepted` (contains `order_id`, `est_prep_time`)
* **Business Rules**:
  - Online orders must handle specific tax mappings (e.g. aggregator-invoiced tax collections).
  - Auto-accept features are automatically disabled if the kitchen queue latency exceeds threshold limits (e.g. 45 minutes).
* **Required Permissions**: `ordering.api_write`
* **Audit Events**:
  - `ONLINE_ORDER_INTEGRATION_SUCCESS` (External ID, Source)
  - `ONLINE_ORDER_AUTO_REJECTED` (Reason, Target items)
* **Notifications**: POS notification popup alerting staff to a new incoming online order.

---

### 13. Kitchen Workflow
* **Description**: Kitchen staff manage orders via the Kitchen Display System (KDS). They track preparation stages and mark orders as ready for service.
* **Pool/Lanes**:
  - `Kitchen Staff` (Actor)
  - `KDS Terminal` (Visual status board)
  - `Ordering Context` (Kitchen ticket state engine)

#### BPMN-style Flow
```
[Start: KOT Routed to KDS Display]
   │
   ▼
[Task: Order Appears on KDS Screen] (Sorted by prep time / priority)
   │
   ▼
[Task: Kitchen Staff clicks 'Start Cooking'] (Status transitions to 'cooking')
   │
   ▼
[Task: Food Prepared & Plated]
   │
   ▼
[Task: Staff clicks 'Bump / Ready' on KDS]
   │
   ▼
[Parallel Gateway]
   ├── Flow 1 ──► [Task: Update OrderItem State to 'Ready']
   ├── Flow 2 ──► [Task: Trigger Waiter Alert Notification]
   └── Flow 3 ──► [Task: Increment KDS prep performance stats]
                       │
                       ▼
                 [End: Food Ready at Pass]
```

* **Actors**: Kitchen Staff (Chef, Line Cook), Waiter
* **Preconditions**:
  - An active KOT has been generated by the POS system.
* **Main Flow**:
  1. Kitchen ticket appears on the KDS display, color-coded by elapsed wait time.
  2. Kitchen Staff clicks "Prepare", changing item status to `cooking`.
  3. Kitchen Staff prepares the food items.
  4. Once plated, the staff member clicks "Bump", changing the status to `ready`.
  5. The system alerts the assigned waiter to collect and serve the order.
* **Alternate Flows**:
  - *Item Void/Cancellation*: If the front counter voids an item, it is instantly struck through on the KDS display.
* **Error Flows**:
  - *KDS Terminal Disconnect*: System loses connection. A fallback network print event is triggered, routing physical paper tickets to backup kitchen printers.
* **Events**:
  - `KOTItemStatusChanged` (contains `kot_item_id`, `new_status`)
  - `KOTAllItemsReady` (contains `kot_id`)
* **Business Rules**:
  - KDS monitors target preparation metrics (calculating duration between KOT creation and bump timestamps).
  - Voided items must be highlighted on the KDS screen with audible alerts.
* **Required Permissions**: `kds.view_bump`
* **Audit Events**:
  - `KITCHEN_PREP_STARTED` (KOT ID, Timestamp)
  - `KITCHEN_TICKET_BUMPED` (KOT ID, Total Preparation Time)
* **Notifications**: Push notifications to the waiter's terminal when food is ready at the kitchen pass.

---

### 14. Billing Workflow
* **Description**: Waiters request the final check for a table. The system calculates subtotals, applies discounts, computes tax distributions, and locks the invoice.
* **Pool/Lanes**:
  - `Waiter / Cashier` (Actor)
  - `Ordering Context` (POS billing engine, tax calculators, invoice sequencers)

#### BPMN-style Flow
```
[Start: Customer Requests Bill]
   │
   ▼
[Task: Query Order Details & Active Items]
   │
   ▼
[Task: Compute Subtotal & Proportional Item Discounts]
   │
   ▼
[Task: Apply Location-Based Taxes & Service Charges] (GST Calculations)
   │
   ▼
[Task: Apply Rounding Rules] (Round to nearest integer unit)
   │
   ▼
[Task: Lock Order State & Issue Pro-Forma Invoice]
   │
   ▼
[Task: Generate Sequential Invoice Number] (INV{YYMMDD}-{NNNN})
   │
   ▼
[End: Bill Printed & Presented]
```

* **Actors**: Waiter, Cashier
* **Preconditions**:
  - The order status is `active` and contains at least one non-voided item.
* **Main Flow**:
  1. Actor triggers the "Generate Bill" action for the order.
  2. System queries order items and calculates the subtotal.
  3. System applies any active manual or coupon discounts proportionally across order lines.
  4. System calculates localized taxes (CGST, SGST, IGST) using place-of-supply rules.
  5. System calculates optional service charges and applies currency rounding rules.
  6. System creates a `SubscriptionInvoice` using the atomic sequence generator to guarantee gapless daily invoice numbering.
  7. The system locks the order state to prevent any item modifications while payment is pending.
* **Alternate Flows**:
  - *Split Bill*: If guest requests a split bill, the system recalculates taxes and discounts proportionally across the newly created sub-orders.
* **Error Flows**:
  - *Concurrently Modified Order*: If a waiter tries to modify the order while the cashier is generating the bill, the transaction lock rejects the write operation.
* **Events**:
  - `BillCalculated` (contains `order_id`, `subtotal`, `tax_total`, `grand_total`)
  - `InvoiceGenerated` (contains `invoice_id`, `invoice_number`)
* **Business Rules**:
  - Invoice numbers must be sequential and contain no gaps.
  - Tax calculations must handle fractional values using `Decimal` arithmetic.
* **Required Permissions**: `ordering.bill`
* **Audit Events**:
  - `BILL_GENERATED` (Order ID, Invoice Number, Total)
  - `ORDER_LOCK_APPLIED` (Order ID)
* **Notifications**: Thermal print commands dispatched to table-side printers.

---

### 15. Payment Workflow
* **Description**: Cashiers collect payments for locked invoices using cash, card, UPI, prepaid wallets, or store credit.
* **Pool/Lanes**:
  - `Cashier` (Actor)
  - `Ordering Context` (Payment processing and reconciliation)
  - `Customers Context` (Prepaid wallets & store credits validations)
  - `External Card Machine / UPI Gateway` (Merchant API integrations)

#### BPMN-style Flow
```
[Start: Process Bill Payment]
   │
   ▼
[Task: Select Payment Mode] (Cash, Card, UPI, Customer Wallet, Store Credit)
   │
   ▼
[Exclusive Gateway: Mode Selected]
   ├── Wallet / Credit ──► [Task: Verify Balance & Debit Customer Ledger]
   ├── Card / UPI      ──► [Task: Initiate Terminal Checkout & Await API Success]
   └── Cash            ──► [Task: Record Cash Intake & Open Cash Drawer]
                                 │
                                 ▼
                     [Task: Save Payment Record]
                                 │
                                 ▼
                     [Exclusive Gateway: Bill Fully Settled?]
                        ├── No  ──► [Task: Await Next Split Payment Mode]
                        └── Yes ──► [Task: Transition Order Status to Paid]
                                      │
                                      ▼
                                    [Task: Release Table occupied status]
                                      │
                                      ▼
                                    [End: Invoice Settle Success]
```

* **Actors**: Cashier, Customer
* **Preconditions**:
  - The invoice state is locked and unpaid.
  - If using store credit/wallet, the customer profile must be linked to the order.
* **Main Flow**:
  1. Cashier prompts the customer for payment and selects the payment mode.
  2. If card/UPI is selected, the system triggers the integrated terminal API and awaits checkout completion.
  3. If wallet/credit is selected, the system checks customer balances and applies the debit transaction.
  4. System records the `Payment` transaction details.
  5. If the invoice is fully settled, the status transitions to `paid` and the system releases the table reservation lock.
* **Alternate Flows**:
  - *Split Payment*: Customer pays using a combination of payment modes (e.g. 50% Cash and 50% UPI). The system records separate payment records for each transaction.
* **Error Flows**:
  - *Insufficient Wallet Balance*: Wallet balance is less than required payment. System rejects transaction and prompts cashier to request another payment method.
* **Events**:
  - `PaymentCaptured` (contains `payment_id`, `invoice_id`, `amount`, `mode`)
  - `OrderSettled` (contains `order_id`)
* **Business Rules**:
  - Payments are processed inside database transactions to ensure database consistency.
  - Store credit options are only available for customers with approved credit terms.
* **Required Permissions**: `ordering.pay`
* **Audit Events**:
  - `PAYMENT_RECORDED` (Payment ID, Mode, Settle Amount)
  - `TABLE_VACATED` (Table ID, Order ID)
* **Notifications**: SMS receipt sent to customer; cash drawer alert tone.

---

### 16. Refund Workflow
* **Description**: Managers process invoice refunds for returned items or billing errors, reversing loyalty points and updating inventory.
* **Pool/Lanes**:
  - `Branch Manager` (Actor)
  - `Ordering Context` (Invoice ledger and refund manager)
  - `Customers Context` (Points/Prepaid wallet ledger adjusters)
  - `Inventory Context` (Optional stock restock routines)

#### BPMN-style Flow
```
[Start: Refund Request Submitted]
   │
   ▼
[Task: Select Invoice & Identify Target Return Items]
   │
   ▼
[Task: Input Refund Reason & Verify Manager Credentials]
   │
   ▼
[Exclusive Gateway: Refund Amount Valid?]
   ├── No  ──► [End: Error - Amount exceeds invoice payment]
   └── Yes ──► [Task: Process Payment Gateway Reverse / Cash Release]
                 │
                 ▼
               [Task: Create Refund Transaction Record]
                 │
                 ▼
               [Parallel Gateway]
                 ├── Flow A ──► [Task: Deduct Earned Loyalty Points]
                 ├── Flow B ──► [Task: Return items to Inventory (Optional)]
                 └── Flow C ──► [Task: Mark Invoice as Refunded / Partially Refunded]
                                       │
                                       ▼
                                 [End: Refund Processed]
```

* **Actors**: Branch Manager, Cashier
* **Preconditions**:
  - Invoice status is `paid` or `partially_paid`.
  - Transaction date is within the allowed refund window (e.g. 30 days).
* **Main Flow**:
  1. Actor locates the original customer invoice in the system.
  2. Actor selects target items to refund and enters the refund reason.
  3. System validates that the refund amount does not exceed the paid amount.
  4. System processes the reverse payment through the payment gateway or opens the cash drawer for cash refunds.
  5. System records the refund transaction.
  6. System reverses any loyalty points earned on the original purchase.
  7. If items are restocked, the system increments inventory levels and writes a stock movement log.
* **Alternate Flows**:
  - *Store Credit Refund*: Customer receives store credit instead of cash/card refund. The system credits the customer's account balance.
* **Error Flows**:
  - *Refund Lockout*: Non-manager attempts to process a refund. The system blocks the action and requests manager override credentials.
* **Events**:
  - `RefundIssued` (contains `refund_id`, `invoice_id`, `amount`)
  - `InventoryRestocked` (contains `item_id`, `quantity`)
* **Business Rules**:
  - Refund transactions must lock the parent invoice to prevent concurrent refund attempts.
  - Loyalty point balances cannot drop below zero. If a point deduction results in a negative balance, the balance is set to zero.
* **Required Permissions**: `ordering.refund`
* **Audit Events**:
  - `REFUND_PROCESSED` (Refund ID, Invoice ID, Amount)
  - `INVENTORY_RESTOCK` (Item ID, Count)
* **Notifications**: Refund receipt email sent to customer.

---

### 17. Daily Closing (End of Day / Z-Report)
* **Description**: Managers reconcile POS terminals at the end of the day, record physical cash counts, verify payment gateway receipts, and close the trading day.
* **Pool/Lanes**:
  - `Branch Manager` (Actor)
  - `Ordering Context` (Sales totals, DailyCounter controller)
  - `Identity Context` (Active shift trackers)
  - `Audit Context` (EOD sign-off ledger)

#### BPMN-style Flow
```
[Start: Trigger EOD Closing Process]
   │
   ▼
[Task: Retrieve POS Transaction Totals by Mode] (Cash, Card, UPI, etc.)
   │
   ▼
[Task: Count Physical Drawer Cash & Input Totals]
   │
   ▼
[Task: Calculate Drawer Variance] (Expected Cash vs Actual Cash Count)
   │
   ▼
[Task: Lock Active Business Day Ledger] (Prevents subsequent transactions)
   │
   ▼
[Task: Reset Daily Invoice Sequence Counters] (DailyCounter reset)
   │
   ▼
[Task: Generate Z-Report Summary]
   │
   ▼
[End: End of Day Closed]
```

* **Actors**: Branch Manager, Cashier
* **Preconditions**:
  - All orders are closed (either paid, voided, or suspended).
  - Current time is outside peak service hours.
* **Main Flow**:
  1. Actor triggers the End of Day (EOD) process on the POS.
  2. System aggregates daily sales totals by payment mode.
  3. Cashier counts physical cash in the drawer and inputs the count.
  4. System calculates variances between expected and actual cash counts.
  5. System locks the trading day, preventing any new sales transactions from being recorded.
  6. System resets the daily invoice sequence counter.
  7. System generates the daily Z-Report, summarizing sales, taxes, discounts, and cash drawer variances.
* **Alternate Flows**:
  - *Automated Midnight Closing*: If managers forget to trigger EOD, the system auto-locks the day at a configured time (e.g. 03:00 AM) and sends a draft Z-report to the company owner.
* **Error Flows**:
  - *Pending Orders Block*: Open orders prevent EOD closing. System displays warnings; cashier must settle, split, or void open orders before proceeding.
* **Events**:
  - `DailyClosingCompleted` (contains `tenant_id`, `branch_id`, `closing_date`, `sales_total`)
* **Business Rules**:
  - EOD Z-Reports cannot be modified after generation.
  - Cash drawer variances exceeding tolerance thresholds (e.g., $10) are flagged for audit review.
* **Required Permissions**: `reports.eod_close`
* **Audit Events**:
  - `DAILY_CLOSING_ZREPORT` (Branch ID, Expected Cash, Actual Cash, Variance)
  - `SEQUENCE_COUNTER_RESET` (Daily key)
* **Notifications**: Daily Z-Report email summary sent to Company Owner.

---

### 18. Stock Adjustment
* **Description**: Inventory managers perform periodic physical stock counts, document count variances (due to waste, theft, or data entry errors), and log adjustments.
* **Pool/Lanes**:
  - `Inventory Manager` (Actor)
  - `Inventory Context` (Stock adjustment, movements, and alerts)

#### BPMN-style Flow
```
[Start: Physical Inventory Count Audit]
   │
   ▼
[Task: Input Counted Quantities for Target Items]
   │
   ▼
[Task: Calculate Adjustment Variance] (System Stock vs Counted Stock)
   │
   ▼
[Task: Input Adjustment Reason Code] (Spoilage, Theft, Count Discrepancy)
   │
   ▼
[Exclusive Gateway: Variance exceeds threshold limits?]
   ├── No  ──► [Task: Auto-Commit Stock Adjustment]
   └── Yes ──► [Task: Await Manager Approval & Sign-Off]
                 │
                 ▼
               [Task: Manager Approves Adjustment]
                 │
                 ▼
               [Parallel Gateway]
                 ├── Flow 1 ──► [Task: Update InventoryItem Qty on Hand]
                 └── Flow 2 ──► [Task: Write StockMovement Adjustment Journal]
                                       │
                                       ▼
                                 [End: Stock Adjustment Applied]
```

* **Actors**: Inventory Manager, Branch Manager
* **Preconditions**:
  - Inventory items are active.
  - Previous inventory periods are closed.
* **Main Flow**:
  1. Actor initiates a `StockAdjustment` sheet.
  2. Actor inputs counted quantities for target items.
  3. System calculates variances between recorded stock and counted stock.
  4. Actor selects adjustment reason codes (e.g., "Spoilage", "Theft", "Waste").
  5. If the adjustment value exceeds tolerance limits, the sheet is routed to the Branch Manager for approval.
  6. Upon approval, the system updates inventory levels and records stock movements.
* **Alternate Flows**:
  - *Cycle Counting*: Adjusting stock for a single category of items at a time, rather than a full warehouse count.
* **Error Flows**:
  - *Locked Adjustment*: Adjustment sheet is locked by another user. System blocks concurrent edits.
* **Events**:
  - `StockAdjustmentApplied` (contains `adjustment_id`, `items_adjusted_count`, `net_value_adjustment`)
* **Business Rules**:
  - Adjustments must lock target items to prevent race conditions with sales transactions.
  - Adjusted quantities can be positive or negative.
* **Required Permissions**: `inventory.adjust`
* **Audit Events**:
  - `STOCK_ADJUSTMENT_COMMITTED` (Adjustment ID, Total Variance Value)
  - `INVENTORY_COUNT_RECORDED` (Item ID, System Qty, Actual Qty)
* **Notifications**: Alert sent to Company Owner if adjustments indicate significant stock shrinkage.

---

### 19. Purchase Workflow (Supplier Invoice Matching)
* **Description**: Receivables clerks match incoming supplier invoices with original Purchase Orders and Goods Receipts (three-way match) before payment approval.
* **Pool/Lanes**:
  - `Receivables Clerk` / `Accountant` (Actor)
  - `Inventory Context` (Purchase order, receipts, and invoices matching)
  - `Billing / Accounts Context` (Accounts Payable logger)

#### BPMN-style Flow
```
[Start: Supplier Invoice Received]
   │
   ▼
[Task: Locate Associated Purchase Order & Goods Receipt]
   │
   ▼
[Task: Input Supplier Invoice Line Prices & Quantities]
   │
   ▼
[Task: Run Three-Way Match Verification] (Invoice vs PO vs Receipt)
   │
   ▼
[Exclusive Gateway: Match Discrepancy Found?]
   ├── Yes ──► [Task: Flag Invoice for Dispute Resolution] ──► [End: In Dispute]
   └── No  ──► [Task: Approve Supplier Invoice for Payment]
                 │
                 ▼
               [Task: Create Accounts Payable Record]
                 │
                 ▼
               [End: Approved for Payment]
```

* **Actors**: Receivables Clerk, Accountant
* **Preconditions**:
  - Purchase order exists and is marked as received or partially received.
* **Main Flow**:
  1. Actor receives the physical/digital supplier invoice.
  2. Actor locates the corresponding Purchase Order and Goods Receipt records in the system.
  3. Actor inputs the supplier invoice prices and quantities.
  4. System runs a three-way match, validating that the invoice matches both the PO and the Goods Receipt.
  5. If values match, the system approves the invoice and creates an Accounts Payable record.
* **Alternate Flows**:
  - *Two-way Match*: If a PO was not required (e.g. direct utility bills), the clerk matches the invoice directly against the service receipt.
* **Error Flows**:
  - *Discrepancy Exception*: Quantities or prices differ. System flags the invoice as `disputed` and alerts the purchasing manager to contact the supplier.
* **Events**:
  - `SupplierInvoiceMatched` (contains `invoice_id`, `po_id`, `amount_approved`)
* **Business Rules**:
  - Discrepancy tolerances are set at the tenant level (e.g., maximum 2% price variance).
  - Invoice numbers must be unique per supplier.
* **Required Permissions**: `inventory.invoice_match`
* **Audit Events**:
  - `SUPPLIER_INVOICE_APPROVED` (Supplier ID, Invoice ID, Match Result)
  - `DISPUTED_MATCH_LOCKED` (PO ID, Invoice ID)
* **Notifications**: Dispute alert sent to purchasing manager; payment approval notification sent to accounting.

---

### 20. Employee Shift Workflow
* **Description**: Staff members open and close cashier drawer shifts. They log active work sessions, record cash drops, and reconcile cash variances.
* **Pool/Lanes**:
  - `Cashier` / `Waiter` (Actor)
  - `Branch Manager` (Actor)
  - `Employees Context` (Shift records and sessions)
  - `Ordering Context` (Cash drawer registers tracking)

#### BPMN-style Flow
```
[Start: Shift Commences]
   │
   ▼
[Task: Staff Logs In & Opens Shift Session]
   │
   ▼
[Task: Input Starting Cash Drawer Float]
   │
   ▼
[Task: Execute POS Sales & Record Transactions]
   │
   ▼
[Task: Record Cash Drop (During Shift)] (Removes excess cash from drawer to safe)
   │
   ▼
[Task: Initiate Shift Closing]
   │
   ▼
[Task: Count Drawer Cash & Reconcile Sales]
   │
   ▼
[Exclusive Gateway: Shift Variance Detected?]
   ├── Yes ──► [Task: Flag Variance for Manager Review]
   └── No  ──► [Task: Close Shift Session]
                 │
                 ▼
               [End: Shift Completed]
```

* **Actors**: Cashier, Waiter, Branch Manager
* **Preconditions**:
  - Employee has an active membership with the target branch.
  - The previous shift on the selected terminal is closed.
* **Main Flow**:
  1. Cashier logs in to the POS and opens their shift.
  2. Cashier inputs the starting cash float.
  3. Cashier processes sales transactions during the shift.
  4. If cash in the drawer exceeds threshold limits, cashier performs a "Cash Drop" to transfer funds to the manager's safe.
  5. At the end of the shift, the cashier initiates the shift closing process.
  6. Cashier counts final cash in the drawer; system reconciles the count against expected totals.
  7. If no variance is found, the cashier closes the shift.
* **Alternate Flows**:
  - *Shift Handover*: Cashier hands the drawer over to the next shift cashier. The system performs an intermediate reconciliation without closing the trading day.
* **Error Flows**:
  - *Drawer Variance*: Count discrepancy detected. Cashier must enter a variance explanation. The shift is closed with a `variance_flag` and escalated to the manager.
* **Events**:
  - `ShiftOpened` (contains `shift_id`, `employee_id`, `start_float`)
  - `ShiftClosed` (contains `shift_id`, `end_float`, `variance`)
* **Business Rules**:
  - Only one active shift is allowed per employee at any given time.
  - Cash drops must be verified and signed off by the branch manager.
* **Required Permissions**: `employees.shifts_manage`
* **Audit Events**:
  - `SHIFT_OPENED` (Employee ID, Float Amount)
  - `CASH_DROP_RECORDED` (Employee ID, Drop Amount, Manager ID)
  - `SHIFT_CLOSED` (Employee ID, Sales Expected, Counted Cash, Variance)
* **Notifications**: SMS alert sent to Branch Manager if a shift variance exceeds set thresholds.
