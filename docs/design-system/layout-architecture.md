# Nextora POS — Frontend Layout Architecture

> **Purpose:** the canonical spec for **how Forge's zones compose into actual
> screens** across the product (POS, Dashboard, Settings, Reports, Auth, Print,
> Invoice) plus the cross-layout chrome (Sidebar, Header, Footer, Content Area,
> Quick Search, Notifications) and the **responsive behavior** of each.
> **Scope:** specification only — no markup, no components, no implementation.
> **Anchored to:** [DESIGN-nextora.md](../../DESIGN-nextora.md) (Forge),
> [design-system/tokens/tailwind.config.js](../../design-system/tokens/tailwind.config.js),
> `design-system/tokens/tokens.css`, and [docs/design-system/component-inventory.md](component-inventory.md).
> Last updated: 2026-06-27.

---

## 0. Foundations the layouts depend on

These come from Forge and the token system — restated here so every layout entry
can reference them by token name, not by repeated rules.

### 0.1 Zones (Forge §II.1)
A screen is a composition of **persistent zones**, not a stack of pages:

| Zone | Token (height/width) | Role |
|---|---|---|
| Top Rail | `--forge-zone-top-rail-height` = 44px | Tenant/branch · clock · search · notifications · user |
| Module Rail | `--forge-zone-module-rail-width` = 64px (220px expanded) | Primary nav (RBAC-filtered) |
| Workspace | remaining width | The current module's task surface |
| Context Panel | `--forge-zone-context-panel` = 340px (380 lg / 300 sm) | Persistent secondary context (e.g. order summary) |
| Status Rail | `--forge-zone-status-rail-height` = 32px | Real-time signals (KOT, shift, sync) |

**Surfaces (§II.2):** Ground (page) · Base (zones) · Raised (cards/inputs) · Overlay
(modal/dropdown) · Toast. No element skips a level.

**Radii (§II.4):** `sharp` 4px (data/status) · `card` 8px (containers) · `pill`
9999px (primary actions / search).

### 0.2 Density modes (Forge §IV)
- **Compact** — POS terminal, KDS, cashier order list.
- **Standard** — manager dashboard, settings, catalog back-office.
- **Comfortable** — subscription/onboarding/help.
Every layout below declares which density it uses.

### 0.3 Breakpoints (tokens.css / tailwind)
`sm 640 · md 768 · lg 1024 · xl 1280 · 2xl 1440 · 3xl 1920`.
Rules from Forge Appendix A: **below `md`** Module Rail becomes bottom tab bar,
Context Panel becomes a pull-up sheet; **below `sm`** single column, all panels
are full-screen drawers.

### 0.4 Z-index ladder (tailwind.zIndex)
`base 0 · raised 1 · sticky 10 · dropdown 100 · overlay 200 · modal 300 · toast
400 · tooltip 500`. Layouts must respect this — e.g. a sticky toolbar never
covers a dropdown.

### 0.5 Motion budget (§VII)
No animation in a primary POS flow exceeds `motion-moderate` (220 ms). All
layouts disable non-essential motion under `prefers-reduced-motion`. Mode switch
is instant (Rule E3). **Motion Freeze Zones** apply during payment, order
submit, print: the whole layout stills.

### 0.6 Cross-cutting layout rules
1. **Zone consistency** — primary action **top-right of workspace** or right
   side of Context Panel (Forge C1). Layouts never move it.
2. **One scroll axis per region** — Workspace scrolls vertically; rails and
   context panel scroll independently; **no horizontal page scroll, ever.**
3. **Reserve space for async** — Skeleton matches final size; never reflow when
   data arrives.
4. **RBAC-aware rendering** — modules the user can't access are hidden from the
   Sidebar/Module Rail; soft-locked controls show a reason.
5. **Theme-token only** — no hard-coded color or spacing; light/dark/white-label
   theming flows through `data-theme` on `<html>`.
6. **i18n / RTL** — every layout mirrors; Module Rail stays on the "leading"
   side, Context Panel on the "trailing" side.

---

## 1. Cross-layout chrome (used by multiple layouts)

These are layout regions, not components — the component inventory defines
buttons/menus/etc.; this section defines **how a region is composed and where
it lives**.

### 1.1 Sidebar (Module Rail + optional expanded drawer)
- **Position / size:** leading edge, full height between Top Rail and Status
  Rail. Collapsed `64px`, expanded `220px` (`max-w-module-rail-open`).
- **Surface:** `surface-sidebar`. Hairline border on the trailing edge using
  `border-default`. No shadow (Forge A4).
- **Composition (top→bottom):** tenant/branch glyph · module items (icon + label
  when expanded) · divider · pinned items (favorites, recents) · footer slot
  (collapse toggle, theme toggle, user mini-menu on mobile).
- **States:** collapsed (icons + tooltips on hover/focus), expanded, item
  hover/focus, **active item** (`aria-current=page`, left accent rail using
  `brand-default`), badge/count, **disabled/locked** (no permission — soft lock
  with reason tooltip per the Component Inventory's Permission Denied entry).
- **Behavior:**
  - **RBAC filter:** items the user lacks permission for are **hidden**, not
    disabled (Forge C1 + permission rules from component spec §6.4).
  - **Persistent collapsed state** per user.
  - **Two nesting levels max**; deeper levels open a flyout submenu (not nested
    rails — Forge A6 forbids secondary global nav).
  - **Skip link** to main content placed before the rail in DOM order.
- **Responsive:**
  - `≥ lg`: collapsed by default, manual expand (toggle in footer).
  - `md`: collapsed only (icons + tooltips).
  - `< md`: becomes a **bottom tab bar** (5 items max, overflow to "More" sheet).
  - `< sm`: bottom tab bar shrinks to 4; "More" drawer becomes full-screen.
- **Used by:** Dashboard · POS · Settings · Reports.
- **Not present in:** Authentication · Print · Invoice.

### 1.2 Header (Top Rail)
- **Position / size:** top edge, full width, **44px** (`zone-top-rail`).
- **Surface:** `surface-header`. Hairline bottom border. **Frosted** when content
  scrolls under it (`backdrop-filter: blur(20px) saturate(180%)` via `.frosted`
  utility) — never a shadow.
- **Composition (leading → trailing):**
  1. Module Rail handoff (brand glyph in compact view).
  2. **Breadcrumb** slot (Dashboard/Settings/Reports) or **Context Strip** slot
     (POS: branch · order # · table).
  3. **Spacer.**
  4. **Quick Search** (see §1.5).
  5. **Status cluster:** branch/shift indicator · sync/offline indicator.
  6. **Notifications** bell (count badge, see §1.6).
  7. **Theme toggle** (light/dark — instant, no transition).
  8. **User menu** (avatar/initials, dropdown per Component Inventory).
- **Sticky:** yes, on every layout that has it.
- **Keyboard:** logical tab order leading → trailing; global search shortcut
  `Ctrl/Cmd+K` or `/` focuses the search; `g + n` opens notifications.
- **Responsive:**
  - `≥ lg`: full composition.
  - `md`: search collapses to icon (opens overlay), branch label truncates.
  - `< md`: only brand glyph · search icon · notifications · user; breadcrumb
    moves into the content area as a one-line strip.
- **Used by:** Dashboard · POS · Settings · Reports.
- **Not present in:** Authentication · Print · Invoice.

### 1.3 Footer (Status Rail + Page Footer)
Forge has **two** footer concepts and they must not be confused:
- **Status Rail (32px, persistent):** live operational signals — open KOTs,
  active orders count, shift open/close, last sync, app version. Used by **POS**
  (always) and **Dashboard** (when an operational shift is active). Dismissible
  alerts only; no action that takes the user out of the current task.
- **Page Footer (Settings/Reports/Auth only):** non-sticky, comfortable density,
  contains version · legal links · support contact · current tenant. Never
  contains primary actions.
- **Not present in:** Print · Invoice (they use their own document footer — see
  §2.6 / §2.7).

### 1.4 Content Area (Workspace)
- **Position:** between Sidebar, Header, Context Panel, Status Rail.
- **Surface:** `surface-base`. Cards/lists inside use `surface-raised`.
- **Padding:** density-driven — Compact `p-4` · Standard `p-6` · Comfortable
  `p-8` (tokens `space-4/6/8`).
- **Scroll:** vertical only. The workspace owns the scrollbar; rails and
  context panel are independently scrollable.
- **Composition pattern:** every workspace declares three slots —
  1. **Workspace Header** (in-flow, not the Top Rail): page title + primary
     action top-right (Forge C1), optional filter strip / tabs underneath.
  2. **Main region** (cards, lists, tables, etc.).
  3. **Workspace Footer** (optional, sticky): bulk actions or pagination.
- **Data-state contract:** every workspace must define its **Loading
  (skeleton) · Empty · Error · Permission Denied** states (see component
  inventory §6) — not optional.
- **No horizontal overflow:** if content can't fit, it virtualizes, paginates,
  or moves into the Context Panel — never adds a page horizontal scrollbar.

### 1.5 Quick Search
Two distinct modes — the Forge interaction spec separates them deliberately.

**A. Global Quick Search (in Top Rail, back-office layouts only).**
- **Surface:** `surface-overlay` for the result panel; trigger uses `pill` radius.
- **Trigger:** `Ctrl/Cmd+K` or `/`; click/focus on the Top Rail input.
- **Composition:** command-palette overlay — **Scopes** (Orders / Customers /
  Products / Settings / Help) as chips at the top; recent + suggested below;
  results group by entity; arrow keys move within results; `Enter` opens; `Esc`
  closes and restores focus to the trigger.
- **Latency:** ~250 ms debounce; live result count announced (`aria-live=polite`).
- **Permission scoping:** scopes the user can't read are hidden.
- **Layouts:** Dashboard · Settings · Reports.

**B. Contextual Search (inline at top of a list, POS + within workspaces).**
- This is the Forge canonical "search is contextual" pattern (§VIII / Rule C5):
  search is **always at the top of the list it filters**, never duplicated into
  the Top Rail. Filters in place; result count displayed ("12 of 47 products").
- **Used by:** POS product browser, KDS ticket filter, any data table.

**Rule:** the **Top Rail Quick Search never exists on the POS layout** — POS
operators search in context, not globally.

### 1.6 Notifications
Two surfaces:

**A. Notification Center** (panel, opened from Top Rail bell).
- **Layer:** dropdown (`z-index: dropdown`), `surface-overlay`, `radius-card`,
  `shadow-overlay`.
- **Composition:** tabs `Inbox · Mentions · System`; each item shows icon +
  title + relative time + entity link; mark-all-read action top-right of panel.
- **Live updates:** server-sent updates push into the panel; unread count on
  the bell uses a count badge (capped "99+"); panel itself does not auto-open.
- **Keyboard:** bell `Enter` opens; `↑/↓` within list; `Enter` opens item; `e`
  marks read; `Esc` closes and returns focus.
- **Empty / error:** standard empty state ("All caught up"); error with retry.

**B. Toasts** (transient).
- **Region:** top-right desktop / bottom-center POS terminal / bottom mobile.
- **z-index:** `toast` (400), above modals.
- **Behavior:** auto-dismiss success at ~4–6 s; **errors and any toast with an
  Undo action never auto-dismiss** (Component Inventory §4.2); pause on
  hover/focus.
- **Live region:** `aria-live=polite` for info/success, `assertive` for errors.

**Operational signals do NOT go in toasts.** Kitchen "new KOT" alerts live in
the Status Rail; long-running task progress lives in a Notification Center item
with progress; only **outcome-of-an-action** belongs in a toast.

---

## 2. Layouts

Each entry below specifies: **zones used · composition · density · scroll
model · header/footer treatment · data-states · responsive behavior · print
mode (if any) · keyboard map**.

### 2.1 Dashboard Layout

**Purpose:** at-a-glance overview for managers/owners — KPIs, charts, recent
activity. **The default landing for manager/owner roles.**

- **Zones:** Top Rail · Sidebar · Workspace · *(Status Rail when a shift is
  active — otherwise hidden)* · *(no Context Panel)*.
- **Density:** Standard.
- **Workspace composition:**
  1. **Greeting strip** (1 line): "Good evening, {name} — {branch}"; primary
     action top-right (e.g. "New Order" deep-link to POS) per Forge C1.
  2. **KPI row:** 4–6 Metric Cards in a responsive grid:
     `grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-6`,
     `gap-4` (Compact KPI density rule from §III.3: ≥ 6 KPI cards above the fold
     at 768 px height).
  3. **Primary chart row:** one full-width line/area chart (revenue today vs
     prior) using `data-1`/`data-2`; with **table fallback toggle** per the
     chart accessibility rule.
  4. **Two-up row:** Top items chart + Top branches chart.
  5. **Recent activity:** Timeline of orders/payments/voids (Component
     Inventory §2.5), with "View all" → Reports.
- **Data-states:** every card/chart has skeleton, empty ("No data for this
  period"), error (with retry + correlation id), permission-denied (hidden
  cards for permissions user lacks).
- **Scroll:** workspace vertical; KPI row sticky-on-scroll **never** (avoid
  duplicate stickies under Top Rail).
- **Responsive:**
  - `xl`: 6-col KPI grid; charts side-by-side.
  - `lg`: 4-col KPI; charts stack at 1024 px.
  - `md`: 2-col KPI; all charts full width; sidebar collapsed.
  - `< md`: 1-col KPI; bottom tab bar nav; date range moves into a sheet.
- **Keyboard:** `Ctrl/Cmd+K` global search; `g h` jump to Dashboard; `r`
  refresh; `d` open date range; `←/→` within a chart move the focused datapoint.

### 2.2 Authentication Layout

**Purpose:** sign-in, MFA, password reset, tenant selection on multi-tenant
membership, first-run / SSO callback.

- **Zones:** **none of the operational zones.** No Sidebar, no Top Rail, no
  Status Rail, no Context Panel. The layout is **self-contained** — to ensure
  no chrome implies the user has any session yet.
- **Density:** Comfortable (this is one of Forge's permitted Comfortable
  surfaces — onboarding-class).
- **Composition:**
  - Full-height `surface-ground` with a **centered card** on `surface-raised`,
    `radius-card`, `shadow-overlay` (Auth is the rare non-chrome case where
    elevation reinforces "this is the only thing").
  - Card max width `xs` (480 px), padding `space-8` (32 px).
  - Brand glyph (top of card), title, optional sub-text, single column form,
    primary action button full-width.
  - Footer line under the card: locale switcher · "Need help?" · version. No
    Status Rail.
- **Flows in this layout:** Sign in · MFA challenge · Forgot password · Reset
  password · Tenant picker (when the user has multiple memberships — list of
  tenants as cards) · SSO redirect/callback state · Account-locked / suspended
  errors.
- **Data-states:** loading (button spinner) · invalid credentials (error under
  form, `role=alert`, focus to summary) · rate-limited · account locked
  (full-card empty/error variant with recovery CTA).
- **Responsive:**
  - `≥ md`: centered card.
  - `< md`: card fills width with `space-4` side padding; brand glyph + title at
    top, form below; full-width primary button stays at the bottom safe-area.
- **Keyboard:** `Tab` order = email → password → reveal → remember → submit →
  forgot link; `Enter` submits; MFA digits autoadvance; `Esc` is a no-op (no
  modal to close).
- **Security/UX:** never leak tenant existence ("Invalid credentials" is
  generic); MFA codes use one-time-code semantics (autofill).

### 2.3 POS Layout

**Purpose:** the primary cashier/waiter terminal — **the most performance- and
ergonomics-critical layout** in the product. Default for cashier/waiter roles.

- **Zones:** Top Rail · Module Rail (collapsed) · Workspace · **Context Panel
  (always present)** · Status Rail.
- **Density:** Compact (the canonical Forge Compact surface).
- **Workspace composition (cashier mode):**
  - **Workspace Header strip (in-flow):** order type chips (Dine-in · Takeaway
    · Delivery) + table selector + order # + customer chip + **contextual
    search** for products (Component Inventory §1.4 / Forge C5).
  - **Main region:** **Quick Key Grid** (Forge §VIII pattern) of product tiles
    — responsive 4–8 columns based on viewport, `radius-card`, image · name
    (`type-body-strong`) · price (`type-caption`); category tabs above the grid.
  - Primary action (`Pay`) is rendered in the **Context Panel** (right side),
    not in the Workspace Header — Forge C1 places it on the right side of the
    Context Panel for POS.
- **Context Panel composition (right side, 340 px, 380 lg, 300 sm):**
  - Order header (table/order #, customer chip).
  - **Order line list** — scrollable, sticky header, each line with name +
    qty stepper + price; modifiers indented.
  - Bill summary block (subtotal · discounts · tax · round-off · total) in
    `type-display` for the total, `tabular-nums` for every number (Rule B3).
  - **Primary action button (Pay)** docked at the bottom of the panel — `pill`
    radius, full width, `48px` height (touch-pref), keyboard `P`.
  - **Secondary actions** above Pay: Discount · Hold · Split · KOT.
- **Status Rail (bottom):** open KOTs count · printer status · sync status ·
  shift state · keyboard-shortcut hint (`?` opens shortcuts panel).
- **Scroll model:** **Workspace and Context Panel scroll independently.** The
  product grid scrolls; the order list scrolls; the Pay button and bill summary
  remain visible at all times.
- **Modes within POS:** New Order (default) · Open Orders · Split · Refund ·
  KDS (full-screen variant — Context Panel becomes ticket detail). Mode
  transitions never relayout the rails.
- **Motion freeze:** during `Pay → process → print`, the whole layout stills
  (Forge §VII Freeze Zones).
- **Data-states:** product grid skeleton on first load; empty search ("No
  products match — clear search"); offline indicator pinned to Status Rail with
  recovery action.
- **Responsive:**
  - `≥ xl` (terminal): full 3-zone layout (Module Rail + Workspace +
    Context Panel + Status Rail).
  - `lg`: Module Rail collapses to 64 px; Context Panel stays.
  - `md`: Context Panel becomes a **pull-up sheet** triggered by a sticky
    bottom-edge "Cart (3) · ₹450" pill; Module Rail collapsed.
  - `< md`: Module Rail becomes bottom tab bar; Context Panel = full-screen
    drawer; product grid switches to 2-column.
- **Keyboard map:** `N` new order · `P` pay · `D` discount · `H` hold · `K`
  KOT · `V` void (two-tap Destructive Action Protocol) · `/` search products ·
  `↑/↓` move active line in order list · `+/-` adjust focused-line qty · `Esc`
  dismiss sheet/cancel split · `?` shortcuts.

### 2.4 Settings Layout

**Purpose:** back-office configuration — tenant, branches, users/RBAC,
catalog, inventory, billing, integrations, devices, printer/KOT routing.

- **Zones:** Top Rail · Sidebar (full nav, expanded by default at `xl+`) ·
  Workspace with **internal two-pane pattern** · Page Footer · no Status Rail
  · no Context Panel.
- **Density:** Standard.
- **Workspace composition (two-pane, master/detail):**
  - **Left pane (sticky, 240 px on `xl+`):** vertical tab list of settings
    sections (Tenant · Branches · Roles & Permissions · Catalog · Inventory ·
    Billing · Devices · Integrations · API keys · Audit log). RBAC-filtered.
    Component Inventory §3.4 (Vertical Tabs) pattern.
  - **Right pane (Workspace):** active section content.
    - **Section header** with title + description + primary action top-right
      ("Add branch", "New role"…).
    - **Filter strip** if section is a list.
    - **Sectioned form** OR **table** OR **card grid** per section.
- **Form patterns:** Component Inventory §1.7. Long forms use a **sticky save
  bar** docked to the bottom of the Workspace (unsaved-changes guard on
  navigation). Sectioned forms keep an in-page mini-TOC at the top of the
  Workspace.
- **Detail editing:** opens in a **Drawer** (Component Inventory §4.4, non-modal
  on `xl+` so the list stays visible; modal on `< lg`).
- **Page Footer:** version · "Documentation" · current tenant · region —
  comfortable, non-sticky, end of Workspace scroll.
- **Data-states:** lists use skeleton rows · "First time here" onboarding
  empty-state (e.g. "Add your first branch"); per-section permission denied
  shown as the right pane (left pane already hides forbidden tabs).
- **Responsive:**
  - `≥ xl`: two-pane in-Workspace.
  - `lg`: left pane collapses to a horizontal tab strip above the right pane.
  - `md`: as `lg`; sidebar collapsed.
  - `< md`: settings tabs become an Accordion list; opening a section is a full
    page; "back" returns to the tab list; bottom tab bar nav.
- **Keyboard:** `g s` jump to Settings; `j/k` within the section tab list;
  `Enter` open; `Ctrl/Cmd+S` save form; `Esc` close drawer (with unsaved guard).

### 2.5 Reports Layout

**Purpose:** dashboards and detailed reporting — sales, items, taxes,
discounts, shifts, audit. Read-heavy, export-heavy.

- **Zones:** Top Rail · Sidebar · Workspace · Page Footer · no Status Rail · no
  Context Panel.
- **Density:** Standard (charts) / Compact (data tables).
- **Workspace composition:**
  - **Filter Bar** (sticky just under Top Rail, height `space-12` = 48 px,
    `surface-base` with hairline border, **not** frosted): Date range picker ·
    Branch picker · Channel · Compare-vs · "Export" menu (CSV / XLSX / PDF) ·
    "Save view" — primary "Run" implicit (filters auto-apply with debounce).
  - **Tabs** (Reports → Sales · Items · Tax · Payments · Discounts · Shifts ·
    Audit) — Component Inventory §3.4.
  - **Report body:** mix of Statistics Cards (KPI strip) + 1–2 large charts +
    one data Table with virtualization for > 1k rows. Each chart offers the
    accessibility table fallback.
  - **Drill-through:** clicking a chart point opens a **Drawer** (modal on
    mobile) with the underlying rows; never navigates away from the report.
- **Page Footer:** "Data freshness: as of {timestamp}" · export history link ·
  legal.
- **Data-states:** skeleton charts/tables; empty ("No data for this period —
  try a wider range"); error (retry + correlation id); partial/estimated
  badge when a backend warns the data is mid-roll-up.
- **Responsive:**
  - `≥ 2xl`: KPI strip 6-up, charts 2-up, table full width below.
  - `xl`: KPI 4-up, charts 1-up.
  - `lg`: KPI 2-up; filter bar wraps to two rows.
  - `md`: filter bar collapses to a Drawer; sticky "Filters (3)" pill.
  - `< md`: tables become **card lists** (one card per row, key columns only);
    bottom tab bar nav; "Export" lives in a sheet.
- **Print:** every report supports **Print View** (see §2.6) — header summary +
  applied filters + chart snapshot (rasterized at print time) + full table.
- **Keyboard:** `g r` Reports; `f` focus filters; `Ctrl/Cmd+E` export menu; `T`
  toggle "View as table" on a focused chart; `Ctrl/Cmd+P` print view.

### 2.6 Print Layout

**Purpose:** generic print surface for back-office documents (reports,
statements, ledger exports). **Distinct from the Invoice/Thermal layout (§2.7)**
which targets thermal printers.

- **Zones:** **none.** No Sidebar, Top Rail, Status Rail, Context Panel,
  Footer chrome. The entire `@media print` style strips zone chrome.
- **Surface:** `surface-raised` on white paper background (force `data-theme`
  to light when printing, regardless of operator mode).
- **Page model:** A4 portrait default; A4 landscape opt-in (wide tables);
  margins **20 mm top/bottom · 16 mm sides** (Forge spacing-derived). Page
  break controls: `page-break-inside: avoid` on table rows, statistics cards,
  and chart blocks; `page-break-after: always` between major sections.
- **Document header (every page):** tenant logo · tenant legal name · branch ·
  document title · generated-at timestamp · prepared-by user · page **N of M**.
  Repeats on every page (`<thead>`-like behavior for non-table content).
- **Document body:** the printable view of the source layout (Report / Statement
  / Audit). Charts rasterize at print time with their **table fallback also
  included** for accessibility.
- **Document footer:** filter summary (so the print is self-describing) ·
  watermark when applicable ("DRAFT" / "REPRINT") · correlation id ·
  confidentiality line.
- **Typography:** body `12pt` (smaller than screen body 15px because print DPI
  is higher); headings keep proportional scale; **all numbers tabular**;
  monospace for IDs.
- **Color:** colors map to print-safe equivalents; dark mode is disabled in
  print; data-family colors switch to **pattern-distinguishable** variants for
  monochrome printers.
- **Motion:** none (print is static).
- **Responsive:** N/A (page-size driven). Preview view shows the same layout on
  screen at A4 ratio, scrollable page-by-page.

### 2.7 Invoice Layout

**Purpose:** thermal printer receipts (POS) **and** A4/A5 tax invoices (GST,
B2B). Two related but distinct render modes.

#### A. Thermal Receipt (POS, 58 mm / 80 mm rolls)
- **Zones:** none.
- **Width model:** **monospace-first**, fixed character columns (`32` cols for
  58 mm; `42–48` cols for 80 mm). Layout is line-by-line, not box-based; tokens
  here are character widths, not pixels.
- **Composition (top→bottom):** tenant logo (optional, monochrome) · tenant
  name centered (`type-body-strong`) · branch address (caption) · GSTIN ·
  divider line (`─`) · invoice # + date + cashier · order # + table/channel ·
  itemized lines (qty · name · price, right-aligned price column) · modifiers
  indented · divider · subtotal · discount · CGST/SGST or IGST · service charge
  · round-off · **TOTAL** (emphasized) · payment lines (mode · amount · ref) ·
  divider · footer message (thank-you / return policy) · QR (UPI / invoice
  link) · barcode (order #) · feedback URL · sliced cut marker.
- **Typography:** system monospace; total uses double-height escape sequence
  when supported by the driver.
- **Locale:** numbers, dates, currency localized; for India: words form of
  total in `caption` ("Rupees Five Hundred Only").
- **Reprint marker:** "REPRINT" line at top with original print timestamp.
- **Driver integration:** layout produces an **ESC/POS-compatible sequence**;
  fallback to PDF for non-thermal devices.
- **Motion freeze:** during print, the POS layout enters Freeze Zone.

#### B. A4/A5 Tax Invoice (GST, B2B)
- **Zones:** none.
- **Page model:** A4 portrait by default; A5 portrait for half-page invoices.
- **Composition (top→bottom):**
  1. **Header:** "TAX INVOICE" title centered (or "BILL OF SUPPLY" when not
     applicable); invoice #, date, place-of-supply, due date.
  2. **Two-column party block:** Seller (tenant legal name, address, GSTIN,
     PAN, state) | Buyer (customer legal name, address, GSTIN, state code from
     Customer Domain `state_code` — see ADR-0002 §D1).
  3. **Itemized table:** S.No · Description · HSN/SAC · Qty · Unit · Rate ·
     Discount · Taxable Value · CGST (rate/amount) · SGST (rate/amount) **or**
     IGST (rate/amount) — IGST when buyer state ≠ seller state (place-of-supply
     rule). All numeric columns right-aligned, `tabular-nums`.
  4. **Totals block (right side):** Taxable value · CGST · SGST · IGST · Cess ·
     Round-off · **Grand Total**. Amount-in-words below.
  5. **Payment & terms block:** bank details · UPI VPA · QR · terms & conditions.
  6. **Signature block:** "For {Tenant}" · authorized signatory line.
- **Print-only chrome:** "Original for Recipient / Duplicate for Transporter /
  Triplicate for Supplier" tag in the corner per GST conventions.
- **Accessibility (for PDF/email render):** real table semantics, tagged PDF,
  alt text for QR (URL).
- **i18n:** numbers in Indian numbering system (`1,23,456.00`) when locale is
  `en-IN`; dates `DD-MM-YYYY` for India by default.

---

## 3. Layout × chrome matrix (quick reference)

| Layout | Sidebar | Top Rail | Status Rail | Context Panel | Page Footer | Density |
|---|---|---|---|---|---|---|
| Dashboard | ✓ | ✓ | optional (shift) | ✗ | ✗ | Standard |
| Authentication | ✗ | ✗ | ✗ | ✗ | minimal | Comfortable |
| POS | ✓ (collapsed) | ✓ (no Quick Search) | ✓ | ✓ (always) | ✗ | Compact |
| Settings | ✓ (expanded) | ✓ | ✗ | ✗ | ✓ | Standard |
| Reports | ✓ | ✓ | ✗ | ✗ (Drawer for detail) | ✓ | Standard |
| Print | ✗ | ✗ | ✗ | ✗ | document footer | print-only |
| Invoice | ✗ | ✗ | ✗ | ✗ | document footer | print/PDF |

---

## 4. Responsive Behavior (consolidated)

The per-layout sections above specify exact reflows. This section consolidates
the platform-wide rules.

### 4.1 Breakpoint reflow rules
| Breakpoint | Module Rail | Context Panel | Top Rail | Tables |
|---|---|---|---|---|
| `≥ 2xl` (1440+) | expanded | full (380 px) | full | wide grid |
| `xl` (1280) | collapsed (manual expand) | full (340 px) | full | full |
| `lg` (1024) | collapsed | full | full | full |
| `md` (768) | collapsed | **pull-up sheet** | search collapses to icon | tables OK, fewer cols |
| `sm` (640) | **bottom tab bar** | **full-screen drawer** | brand · search-icon · bell · user | tables become **card lists** |
| `< sm` (mobile phone) | bottom tab bar (4) | full-screen drawer | as above | card lists only |

### 4.2 Universal responsive rules
- **No horizontal scroll, ever.** Content reflows, virtualizes, or moves to a
  drawer.
- **Touch-target minimum 44 px below `md`, 48 px on POS terminals** (Forge
  §IX.3).
- **The primary action never disappears under reflow** — it docks (bottom of
  Context Panel sheet, bottom safe-area in mobile drawer) and remains within
  thumb reach.
- **Status Rail collapses last.** On `< sm` it becomes a single chip ("3 KOTs ·
  Synced 12s ago") at the bottom; tap expands to a sheet.
- **Sidebar↔Bottom Tab transition:** the active item carries across; tab bar
  shows 4–5 top modules, "More" opens a sheet with the full list.
- **Modal vs Drawer:** modals stay centered up to `lg`; below `md`, modals
  become full-screen drawers with a back affordance and a docked primary
  action.
- **Toasts:** top-right on desktop; bottom-center on POS terminal; bottom on
  mobile (above safe area + above bottom tab bar).
- **Density auto-shift:** moving from Standard layouts onto a touch terminal
  (`> 1280` width + coarse pointer) auto-bumps to Compact density. The user
  can override per device.
- **Frosted Top Rail** only on `≥ md` (older mobile browsers degrade —
  fall back to solid `surface-header`).
- **Print/Invoice** are unaffected by screen breakpoints (page-size driven).

### 4.3 Orientation & input
- **Coarse pointer (touch):** hover states removed; press-confirm scale(0.97);
  drag is supplementary only (Forge §VIII Context A).
- **Fine pointer (mouse):** hover states enabled; right-click context menus for
  power users (Reports/Settings only — never in POS).
- **Keyboard-only:** every layout passes a keyboard-only smoke test (no
  pointer); a visible focus ring is present on every interactive element.

### 4.4 Reduced motion
Under `prefers-reduced-motion`:
- Press-confirm scale removed.
- Sheet/drawer slide-ins replaced with instant opacity transitions.
- Skeleton shimmer becomes a static pulse (per tokens.css §10).
- Mode-switch stays instant.

---

## 5. Acceptance checklist (per layout, before ship)

Adapted from Forge Appendix B; a layout (not just a component) must pass:

- [ ] Zones, surfaces, radii use **tokens only** (no hard-coded px/hex/colors).
- [ ] **Primary action top-right of workspace or Context Panel** (Forge C1).
- [ ] All four data-states designed: **Skeleton · Empty · Error · Permission
      Denied**.
- [ ] Responsive reflow specified for `sm · md · lg · xl · 2xl`.
- [ ] Light & dark mode parity (Forge E1); no pure black/white surfaces.
- [ ] Keyboard map documented + global shortcut (`?` panel) includes the
      layout's shortcuts.
- [ ] **Focus order** matches visual reading order; visible focus on every
      interactive element.
- [ ] **RBAC** behavior: hidden vs soft-locked items have explicit treatment.
- [ ] **No horizontal scroll**; vertical scroll lives on a single region.
- [ ] **i18n / RTL** mirror verified; numbers/dates/currency formatted per
      locale.
- [ ] Motion budget respected; Freeze Zones (payment/submit/print) verified.
- [ ] Print/Invoice layouts: A4 + thermal page breaks tested; tagged PDF for
      accessibility; reprint marker present.

---

## 6. Cross-references

- **Design language:** [DESIGN-nextora.md](../../DESIGN-nextora.md) — zones,
  surfaces, density, motion, interaction laws.
- **Tokens:** `design-system/tokens/tokens.css`,
  [design-system/tokens/tailwind.config.js](../../design-system/tokens/tailwind.config.js).
- **Components used by these layouts:**
  [docs/design-system/component-inventory.md](component-inventory.md).
- **Domain context for Invoice §2.7B (state_code / GST split):**
  [docs/adr/ADR-0002-customer-domain-architecture.md](../adr/ADR-0002-customer-domain-architecture.md).
