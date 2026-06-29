# Nextora POS — Component Inventory (Design System Spec)

> **Purpose:** the canonical catalog of UI components for the Nextora POS web/admin
> surfaces. This is a **specification**, not code — it defines what each component
> *is*, its variants/sizes/states, and its accessibility, keyboard, and usage
> contract. Implementation (Django templates / web POS) follows this spec.
> **Scope:** multi-tenant, **white-label** (themeable via tokens), **RBAC-aware**
> (permission-gated UI), POS-grade (fast, keyboard-first, dense).
> Last updated: 2026-06-27.

---

## 0. Foundations (shared vocabulary)

These apply to every component unless overridden in its entry — defined once here
to avoid repetition.

### 0.1 Size scale
`xs · sm · md · lg · xl`. **`md` is the default.** POS terminals default to a
**compact density**; back-office/admin defaults to **comfortable**. Density is a
global setting, not a per-component prop.

### 0.2 Intent / variant palette
Semantic intents map to theme tokens (never hard-coded colors — white-label safe):
`primary · secondary · tertiary/ghost · danger · success · warning · info · neutral`.

### 0.3 State vocabulary
`default · hover · focus-visible · active/pressed · selected · disabled ·
read-only · loading · error · success · indeterminate`. Not every component has
all states; each entry lists the ones it supports.

### 0.4 Accessibility baseline (every component)
- **Contrast:** text ≥ 4.5:1, large text/UI/icon ≥ 3:1 (WCAG AA).
- **Focus:** a visible `focus-visible` ring on every interactive element; never
  remove focus outlines. Focus order follows reading order.
- **Target size:** interactive targets ≥ 24×24 px (≥ 44×44 px on touch POS).
- **Motion:** honor `prefers-reduced-motion` — disable non-essential animation.
- **Color independence:** never convey meaning by color alone (pair with icon/text).
- **Labels:** every control has an accessible name (visible label, `aria-label`,
  or `aria-labelledby`). Icon-only controls require an `aria-label`.
- **i18n / RTL:** all components mirror in RTL; text never truncated without a
  tooltip/title; support locale number/currency/date formatting.
- **Live regions:** async status (toasts, validation, loading) announced via
  `aria-live` (`polite` for info, `assertive` for errors).

### 0.5 Keyboard baseline (every component)
- `Tab` / `Shift+Tab` move between components (roving `tabindex` *within* composite
  widgets so they are a single tab stop).
- `Enter` activates the default action; `Space` toggles/activates buttons & checkboxes.
- `Esc` closes the nearest dismissible layer (popover → dropdown → modal).
- Composite widgets use **arrow keys** internally (see each entry).
- No keyboard trap except modal/drawer (intentional focus trap while open).

### 0.6 RBAC & data-state conventions
- Controls the user lacks permission for are **disabled with a reason tooltip** or
  hidden — see **Permission Denied** for the page-level pattern.
- Every data surface (table, list, card grid) must define its **loading
  (skeleton)**, **empty**, and **error** states — see those entries.

---

## 1. Actions & Inputs

### 1.1 Button
- **Purpose:** trigger an action or submit.
- **Variants:** primary, secondary, tertiary/ghost, danger, success, link, icon-only;
  modifier: full-width.
- **Sizes:** sm / md / lg (xs for dense toolbars; xl for primary POS tender keys).
- **States:** default, hover, focus-visible, active, disabled, **loading** (spinner +
  `aria-busy`, label retained, width locked to avoid reflow).
- **Accessibility:** native `button` semantics; `disabled` (not just styled);
  icon-only needs `aria-label`; toggle buttons use `aria-pressed`; a button that
  opens a layer uses `aria-expanded` + `aria-haspopup`.
- **Keyboard:** `Enter`/`Space` activate; not a tab stop when disabled.
- **Usage:** **Do** keep one primary action per view; use danger for destructive
  acts + confirm. **Don't** use a button for navigation (use a link), nest
  interactive elements, or disable without a reason.

### 1.2 Input (text / number / currency / textarea)
- **Purpose:** free-form single- or multi-line entry.
- **Variants:** text, number, currency (locale + symbol, right-aligned), password
  (reveal toggle), textarea, with leading/trailing icon or addon, clearable.
- **Sizes:** sm / md / lg.
- **States:** default, focus, filled, disabled, read-only, **error** (message +
  `aria-invalid`), success, loading (async validation).
- **Accessibility:** always a `<label>` tied via `for`/`id`; help text & error
  linked via `aria-describedby`; `aria-invalid="true"` on error; required marked
  with text + `aria-required` (not asterisk alone); currency announces the unit.
- **Keyboard:** standard text editing; number supports `↑/↓` step; `Esc` clears if
  clearable; `Enter` submits within a single-field form.
- **Usage:** **Do** validate on blur, surface errors inline below the field, keep
  labels visible (not placeholder-as-label). **Don't** rely on placeholder for
  instructions, block paste, or auto-format destructively while typing.

### 1.3 Select (single / multi)
- **Purpose:** choose from a known list.
- **Variants:** single, multi (chips/tags), grouped options, with icons/descriptions,
  async-loaded, creatable; combine with **Search** for typeahead.
- **Sizes:** sm / md / lg.
- **States:** default, open, focus, selected, disabled, read-only, loading, error,
  empty-options.
- **Accessibility:** WAI-ARIA combobox/listbox pattern — trigger `role=combobox`
  with `aria-expanded`, `aria-controls`; list `role=listbox`; options `role=option`
  with `aria-selected`; active option tracked via `aria-activedescendant`. Multi
  announces selection count.
- **Keyboard:** `Enter`/`Space`/`↓` open; `↑/↓` move active option; `Home/End`
  first/last; typeahead jumps to match; `Enter` selects; `Esc` closes; multi uses
  `Space` to toggle, `Backspace` removes last chip.
- **Usage:** **Do** use Select for 5–20 options, virtualize long lists, show the
  empty-options state. **Don't** use a select for < 4 mutually exclusive options
  (use radio/segmented) or for free text.

### 1.4 Search
- **Purpose:** query/filter a dataset or global entities (products, customers, orders).
- **Variants:** inline filter, global (command-palette style), with scope selector,
  with recent/suggestions dropdown, with result-count.
- **Sizes:** sm / md / lg.
- **States:** idle, typing (debounced), loading, results, **no-results** (empty
  state), error, cleared.
- **Accessibility:** `role=searchbox` or combobox when it shows a suggestion list;
  results region is `aria-live=polite` with a count ("12 results"); the input has a
  clear control with `aria-label`.
- **Keyboard:** focus shortcut (e.g. `/` or `Ctrl/Cmd+K` for global); `↑/↓` through
  suggestions; `Enter` selects/submits; `Esc` clears then closes.
- **Usage:** **Do** debounce (~250 ms), preserve query in URL where shareable, show
  loading + no-results explicitly. **Don't** search on every keystroke without
  debounce or hide the clear affordance.

### 1.5 Dropdown (menu)
- **Purpose:** a list of **actions** or navigation triggered from a control.
- **Variants:** action menu, context menu (right-click), split-button menu, nested
  submenus, with icons/shortcuts/dividers/destructive items.
- **Sizes:** sm / md (menus rarely need lg).
- **States:** closed, open, item hover/focus, item disabled, danger item, checked
  item (menu-item-checkbox/radio).
- **Accessibility:** trigger `aria-haspopup=menu` + `aria-expanded`; container
  `role=menu`; items `role=menuitem` (or `menuitemcheckbox/radio`); focus moves
  into the menu on open and returns to trigger on close.
- **Keyboard:** `Enter`/`Space`/`↓` open; `↑/↓` move; `→/←` open/close submenu;
  `Home/End`; typeahead; `Esc` closes & restores focus; `Tab` closes the menu.
- **Usage:** **Do** group related actions, mark destructive items, show shortcuts.
  **Don't** put form inputs inside a menu (use a popover/dialog), or exceed ~7 top
  items without grouping.

### 1.6 Date Picker
- **Purpose:** pick a date, date-time, or range.
- **Variants:** single date, range, date-time, with presets (Today/This week/Last 30
  days), inline vs popover, min/max bounds, disabled dates.
- **Sizes:** sm / md / lg (input); calendar panel fixed.
- **States:** default, open, focus, selected, in-range, range-endpoints, today,
  disabled-date, out-of-bounds, error, read-only.
- **Accessibility:** text input is the source of truth (typed entry allowed +
  parsed); calendar is a `grid` with `role=gridcell`; selected = `aria-selected`,
  disabled = `aria-disabled`; month/year have a labeled live region announcing the
  focused date; respects locale first-day-of-week.
- **Keyboard:** in grid: `←/→` day, `↑/↓` week, `PageUp/PageDown` month,
  `Shift+PageUp/Down` year, `Home/End` week start/end, `Enter/Space` select, `Esc`
  close. Range: select start then end; `Esc` cancels in-progress range.
- **Usage:** **Do** allow typed input with format hint, show presets for analytics
  ranges, localize. **Don't** force calendar-only entry, or use for unknown/very
  distant dates (use typed input).

### 1.7 Forms
- **Purpose:** compose inputs into a validated submission unit.
- **Variants:** single-column (default), sectioned, wizard/multi-step, inline
  (filters), modal form; with sticky action bar.
- **Sizes:** field density follows global density.
- **States:** pristine, dirty, validating, **invalid** (summary + per-field),
  submitting (disable submit + spinner), success, server-error, unsaved-changes
  guard.
- **Accessibility:** group related fields in `fieldset`/`legend`; an error
  **summary** at top (`role=alert`, focus moved to it) listing links to fields;
  per-field errors via `aria-describedby` + `aria-invalid`; required communicated
  in text; submit is a real submit button (Enter submits).
- **Keyboard:** `Tab` order matches visual order; `Enter` submits from any text
  field (single primary); steps in a wizard are reachable; `Esc` prompts on unsaved.
- **Usage:** **Do** validate on blur + on submit, keep labels top-aligned for scan
  speed, preserve input on error, confirm-before-leave when dirty. **Don't** clear
  the form on validation error, validate aggressively on first keystroke, or use
  placeholder as the only label.

---

## 2. Data Display

### 2.1 Table (data grid)
- **Purpose:** dense, sortable, comparable rows of records.
- **Variants:** basic, sortable, selectable (checkbox column), expandable rows,
  sticky header/column, editable cells, grouped/tree, with row actions, virtualized,
  density toggle (comfortable/compact), with toolbar (search/filters/bulk actions).
- **Sizes:** row height via density; column widths resizable.
- **States:** loading (**skeleton rows**), empty (**empty state**), error (**error
  state**), no-permission (column/row gated), sorted (asc/desc), filtered, selected
  rows, row hover, sticky-shadow, pagination/loading-more.
- **Accessibility:** real table semantics (`table/thead/tbody/th[scope]`); sortable
  headers are buttons with `aria-sort`; selection checkboxes have labels ("Select
  row {name}"); row count and selection announced via live region; for virtualized
  grids use `role=grid` with `aria-rowcount/aria-rowindex`.
- **Keyboard:** `Tab` to controls; in grid mode arrow keys move cell focus,
  `Space` toggles row selection, `Shift+Click`/`Shift+↑↓` range select, `Enter`
  opens row; sort header `Enter/Space`.
- **Usage:** **Do** right-align numbers/currency, keep primary identifier first,
  paginate or virtualize > 100 rows, provide bulk-action affordances and an empty
  state. **Don't** put unrelated data in one mega-table, hide critical actions in
  overflow only, or reflow columns on every render.

### 2.2 Card
- **Purpose:** a self-contained content container/grouping.
- **Variants:** basic, with header/footer, media card, interactive/clickable, selectable,
  elevated vs outlined, list-item card.
- **Sizes:** padding via density; width is layout-driven (grid).
- **States:** default, hover (if interactive), focus, selected, disabled, loading
  (skeleton), error.
- **Accessibility:** a clickable card is **one** activatable element (wrap in a
  link/button or use a single primary action — avoid multiple nested click targets
  that confuse SR users); decorative media is `alt=""`.
- **Keyboard:** if interactive, focusable + `Enter/Space` activates the primary action.
- **Usage:** **Do** keep one primary action per card, use for grouping not for every
  element. **Don't** nest cards deeply or make the whole card *and* inner buttons
  separately clickable ("nested interactive" anti-pattern).

### 2.3 Statistics Card / Metric Card
- **Purpose:** surface a single KPI (Metric) or a small set of stats (Statistics).
  *Metric Card* = one number + delta/spark; *Statistics Card* = grouped metrics.
- **Variants:** value-only, value + delta (▲/▼ with % and color **+ icon/sign**),
  value + sparkline/mini-chart, with trend period selector, comparison vs previous.
- **Sizes:** sm (tile) / md / lg (hero metric).
- **States:** loading (skeleton number), empty ("—" / no data), error, stale (with
  "as of" timestamp), positive/negative/neutral delta.
- **Accessibility:** the number has a descriptive accessible name ("Today's revenue:
  ₹1,23,400, up 12% vs yesterday"); never signal up/down by color alone — include
  an arrow glyph and sign; sparkline has a text/`aria-label` summary or adjacent
  table.
- **Keyboard:** non-interactive by default; if the period selector or drill-through
  exists it follows Dropdown/Button rules.
- **Usage:** **Do** format currency/numbers per locale, show the comparison basis,
  keep one KPI per Metric Card. **Don't** cram 6 numbers into one tile or rely on
  red/green alone for direction.

### 2.4 Charts
- **Purpose:** visualize trends, distributions, comparisons (sales, items, hours).
- **Variants:** line, area, bar/column (stacked/grouped), pie/donut, sparkline,
  combo, heatmap; with legend, tooltip, axis labels, threshold/target lines.
- **Sizes:** sm (sparkline) / md (card) / lg (dashboard) / full.
- **States:** loading (skeleton), empty ("No data for this period"), error,
  partial/estimated, hover/focus datapoint, selected series, zoom/brush.
- **Accessibility:** charts are **not** purely visual — provide a text alternative:
  `role=img` + descriptive `aria-label`/summary, **and** an accessible data table
  fallback (toggle "View as table"); series distinguished by pattern/shape + label,
  not color alone; tooltips reachable by keyboard.
- **Keyboard:** focusable chart; `←/→` move between datapoints (announce value),
  `Tab` cycles series, `Enter` drills through; legend items toggle series with
  `Enter/Space`.
- **Usage:** **Do** label axes & units, start bar axes at zero, offer table view,
  limit to ~5–7 series. **Don't** use 3D/exploded pies, encode by color only, or
  truncate axes to exaggerate.

### 2.5 Timeline
- **Purpose:** chronological sequence of events (order lifecycle, audit trail, KOT).
- **Variants:** vertical (default), horizontal, alternating, with icons/status dots,
  grouped by day, with relative + absolute timestamps.
- **Sizes:** sm / md.
- **States:** default, current/active step, completed, pending, error/failed event,
  loading (skeleton), empty.
- **Accessibility:** ordered semantics (`ol/li`); each item exposes status as text
  (not just a colored dot); timestamps use `<time datetime>`; current step marked
  with `aria-current`.
- **Keyboard:** non-interactive items are static; interactive items (expandable)
  follow Accordion rules.
- **Usage:** **Do** show absolute time on hover/focus and relative inline, keep
  status text + icon. **Don't** convey state by dot color only or reverse chronology
  without a clear label.

### 2.6 Calendar
- **Purpose:** month/week/day view of dated entities (reservations, shifts, events).
- **Variants:** month, week, day, agenda/list; with events, all-day row, drag-to-create,
  resource columns (tables/staff).
- **Sizes:** responsive; compact month vs full week.
- **States:** today, selected day, event present, overlapping events, loading,
  empty, out-of-range/disabled day, drag/resize in progress.
- **Accessibility:** grid semantics (`role=grid`, gridcells); each day labeled with
  full date; events are list items within a cell with accessible names (title +
  time); announce view changes via live region.
- **Keyboard:** arrow keys move day focus; `PageUp/Down` month, `t` jump to today,
  `Enter` open day/event, view switch via buttons; events navigable via `Tab`.
- **Usage:** **Do** localize week start & formats, indicate today clearly, handle
  dense days with "+N more". **Don't** rely on color-only event categories.

### 2.7 Pagination
- **Purpose:** navigate paged result sets.
- **Variants:** numbered, prev/next only, load-more/infinite, page-size selector,
  "showing X–Y of Z", cursor-based (no total).
- **Sizes:** sm / md.
- **States:** default, current page (`aria-current=page`), disabled ends, loading
  (next page), single-page (hidden/disabled).
- **Accessibility:** wrap in `nav` with `aria-label="Pagination"`; current page
  `aria-current=page`; prev/next have labels and `aria-disabled` at bounds; result
  range announced.
- **Keyboard:** each control is a tab stop; `Enter/Space` activate; arrow keys
  optional within the control group.
- **Usage:** **Do** show total + range when known, keep page size persistent per
  user, prefer cursor pagination for huge/streaming sets. **Don't** reset to page 1
  on unrelated state changes or hide the control during loading (disable instead).

---

## 3. Navigation

### 3.1 Sidebar (primary nav)
- **Purpose:** primary app navigation, **RBAC-filtered** to permitted modules.
- **Variants:** expanded, collapsed (icons + tooltips), with sections/groups,
  nested/flyout submenus, with tenant/branch switcher, pinned/footer items, mobile
  off-canvas.
- **Sizes:** expanded / collapsed widths.
- **States:** active item (`aria-current=page`), hover, focus, expanded group,
  disabled/locked (no permission), badge/count on item, collapsed-with-tooltip.
- **Accessibility:** `nav` landmark with `aria-label`; current item `aria-current`;
  collapsible groups use `aria-expanded`; collapsed icon items expose names via
  tooltip **and** `aria-label`; off-canvas traps focus while open.
- **Keyboard:** `Tab`/arrows move between items; `Enter/Space` activate; submenus
  open with `→`/`Enter`, close with `←`/`Esc`; a skip-link bypasses nav to main.
- **Usage:** **Do** filter by permission, mark the active route, keep ≤ 2 nesting
  levels, persist collapsed state. **Don't** show modules the user can't access
  without a lock affordance, or bury frequent actions two levels deep.

### 3.2 Navbar (top bar)
- **Purpose:** global header — brand/tenant, global search, quick actions, notifications,
  user menu, branch/shift status.
- **Variants:** with global search, with notifications (badge), user/account dropdown,
  breadcrumb slot, contextual page actions, sticky.
- **Sizes:** standard height; compact on POS.
- **States:** default, scrolled (elevation), with unread badge, offline indicator,
  syncing.
- **Accessibility:** `banner` landmark; interactive clusters labeled; notification
  count announced; user menu follows Dropdown pattern.
- **Keyboard:** logical tab order (brand → search → actions → user); global search
  shortcut; menus per Dropdown.
- **Usage:** **Do** keep it stable across pages, surface offline/sync state, expose
  search shortcut. **Don't** overload with > ~5 clusters or duplicate sidebar nav.

### 3.3 Breadcrumb
- **Purpose:** show location in the hierarchy and allow upward navigation.
- **Variants:** with icons, with truncation/overflow ("…" menu) for deep paths,
  with current-page dropdown (siblings).
- **Sizes:** sm / md.
- **States:** default, current (last, non-link), truncated/overflow, loading.
- **Accessibility:** `nav` + `aria-label="Breadcrumb"`, ordered list; current item
  `aria-current=page` and not a link; separators are decorative (`aria-hidden`).
- **Keyboard:** links are tab stops; overflow menu follows Dropdown.
- **Usage:** **Do** reflect the actual hierarchy, keep the last crumb as plain text,
  collapse the middle on overflow. **Don't** use breadcrumbs as the only nav or list
  the page's own tabs as crumbs.

### 3.4 Tabs
- **Purpose:** switch between sibling views within the same context.
- **Variants:** horizontal (default), vertical, pill/segmented, with icons/badges/
  counts, scrollable/overflow, closable tabs.
- **Sizes:** sm / md / lg.
- **States:** selected (`aria-selected`), hover, focus, disabled, with badge,
  overflow-scrolled, lazy/loading panel.
- **Accessibility:** WAI-ARIA Tabs — `role=tablist`, `role=tab` (`aria-selected`,
  `aria-controls`), `role=tabpanel` (`aria-labelledby`); only the active tab is in
  the tab order (roving tabindex).
- **Keyboard:** `←/→` (horizontal) or `↑/↓` (vertical) move between tabs;
  `Home/End` first/last; activation either automatic (on focus) or manual
  (`Enter/Space`) — pick manual when panels are expensive to load.
- **Usage:** **Do** keep tab labels short, preserve panel state where sensible, use
  for peer content. **Don't** use tabs for a sequential flow (use a wizard) or nest
  tab bars.

---

## 4. Feedback & Overlays

### 4.1 Alert (inline banner)
- **Purpose:** persistent, contextual message tied to a region/page.
- **Variants:** info, success, warning, danger/error, neutral; with title, description,
  actions, dismissible, with icon.
- **Sizes:** sm / md.
- **States:** default, dismissible (with close), with action buttons, expanded/collapsed
  detail.
- **Accessibility:** informational alert `role=status`/`aria-live=polite`; urgent/
  error `role=alert`/`assertive`; intent conveyed by icon + text, not color alone;
  close button has `aria-label`.
- **Keyboard:** actions and close are tab stops; `Esc` does **not** dismiss inline
  alerts (they're persistent) unless explicitly dismissible.
- **Usage:** **Do** place near the relevant content, keep it until resolved, include
  a next action. **Don't** use an alert for transient confirmation (use Toast) or
  stack many alerts.

### 4.2 Toast (transient notification)
- **Purpose:** brief, transient feedback ("Saved", "Order sent").
- **Variants:** info, success, warning, error; with action (Undo), with progress,
  promise (loading→success/error), grouped/stacked.
- **Sizes:** single size; positioned region (e.g., top-right / bottom on POS).
- **States:** entering, visible, paused (on hover/focus), exiting, with-action,
  persistent-on-error.
- **Accessibility:** toast region is an `aria-live` container (`polite` for success/
  info, `assertive` for errors); auto-dismiss **pauses on hover/focus**; errors and
  any toast with an action should **not** auto-dismiss; never put the only copy of
  critical info in a toast.
- **Keyboard:** a shortcut moves focus into the toast region to reach actions; `Esc`
  dismisses the focused toast; actions are reachable.
- **Usage:** **Do** keep messages short, auto-dismiss success after ~4–6 s, keep
  errors/undo until acted on. **Don't** use toasts for required decisions, stack > 3,
  or convey errors that need resolution only via a toast.

### 4.3 Modal (dialog)
- **Purpose:** focused task or confirmation that interrupts the flow.
- **Variants:** standard, confirmation (danger), form modal, full-screen (mobile),
  scrollable body, with sticky footer actions.
- **Sizes:** sm / md / lg / xl / full.
- **States:** open, closing, loading (async submit), with unsaved-changes guard,
  nested (avoid; if needed, stack with care).
- **Accessibility:** `role=dialog` + `aria-modal=true`, labeled by title
  (`aria-labelledby`) and described by body (`aria-describedby`); **focus trap**
  while open; focus moves to the dialog (first focusable or heading) on open and
  **returns to the trigger** on close; background is inert.
- **Keyboard:** `Esc` closes (unless destructive/unsaved → confirm); `Tab` cycles
  within; `Enter` submits the primary action; focus cannot leave the dialog.
- **Usage:** **Do** keep one primary action, confirm destructive ops, guard unsaved
  changes, return focus on close. **Don't** use modals for long forms (use a page),
  stack multiple modals, or auto-open without user intent.

### 4.4 Drawer (sheet / off-canvas panel)
- **Purpose:** side/bottom panel for secondary tasks, details, or filters without
  full context switch.
- **Variants:** right (detail/edit), left (nav), bottom (mobile actions), sizes,
  modal vs non-modal (push), with sticky header/footer.
- **Sizes:** sm / md / lg / full-height.
- **States:** open, closing, modal (with scrim + focus trap) vs non-modal, loading,
  unsaved-changes guard.
- **Accessibility:** modal drawer = `role=dialog` + `aria-modal` + focus trap +
  return focus (same contract as Modal); non-modal drawer is a `complementary`
  region and must **not** trap focus.
- **Keyboard:** `Esc` closes a modal drawer; focus management mirrors Modal for the
  modal variant; non-modal drawer participates in normal tab order.
- **Usage:** **Do** use for record detail/edit alongside a list, keep the list
  context visible (non-modal) when helpful. **Don't** trap focus in a non-modal
  drawer or use a drawer where a modal's interruption is required.

### 4.5 Accordion
- **Purpose:** progressively disclose stacked sections to manage density.
- **Variants:** single-open vs multi-open, with icons/badges, bordered vs flush,
  nested.
- **Sizes:** sm / md.
- **States:** collapsed, expanded, focus, disabled, with content loading.
- **Accessibility:** each header is a `button` with `aria-expanded` and
  `aria-controls`; the panel is `region` `aria-labelledby` the header; heading level
  is correct for the page outline.
- **Keyboard:** `Enter/Space` toggle; `↑/↓` move between headers; `Home/End`
  first/last; optional `→/←` to expand/collapse.
- **Usage:** **Do** use for optional/secondary detail, keep important content open by
  default. **Don't** hide critical info or required form fields inside collapsed
  panels, or nest deeply.

---

## 5. Status & Labeling

### 5.1 Badge
- **Purpose:** small count or status indicator attached to another element.
- **Variants:** count (numeric, with "99+" cap), dot (presence/unread), status
  (intent color + label), standalone vs anchored to icon/avatar.
- **Sizes:** sm / md.
- **States:** default, max-capped, zero (hidden by default), intent variants.
- **Accessibility:** count badges expose meaning via accessible text ("3 unread
  notifications"), not just a number; dot-only badges need an `aria-label`; never
  color-only.
- **Keyboard:** non-interactive (decoration on an interactive host).
- **Usage:** **Do** cap large counts, hide at zero, pair with the host's label.
  **Don't** put actions in a badge or use it for long text (use a Tag/Chip).

### 5.2 Tag
- **Purpose:** label, categorize, or represent a removable selection (filters, multi-select).
- **Variants:** static label, removable (× ), selectable/toggle, with icon/avatar,
  color-coded category, input-tag (token).
- **Sizes:** sm / md.
- **States:** default, hover, focus, selected, removable, disabled, read-only.
- **Accessibility:** removable tag's × is a button with `aria-label="Remove {tag}"`;
  selectable tags expose pressed/selected state; category color paired with text.
- **Keyboard:** focusable when interactive; `Backspace/Delete` removes a focused
  removable tag; `Enter/Space` toggles a selectable tag.
- **Usage:** **Do** use for filters and multi-select tokens, keep labels short.
  **Don't** overload one element with many colored tags, or use a tag as a primary
  button.

### 5.3 Status Chip
- **Purpose:** communicate the **state of an entity** (order: Open/Paid/Void; payment:
  Pending/Settled; stock: In/Low/Out).
- **Variants:** solid, soft/subtle, outline; with leading status dot/icon; with
  optional tooltip for detail.
- **Sizes:** sm / md.
- **States:** maps to a **fixed domain status set** per entity; each status →
  intent token (e.g., success=Paid, warning=Low, danger=Void/Out, neutral=Draft).
- **Accessibility:** status text is always present (color/dot are reinforcement, never
  the sole signal); if truncated, full status in `title`/tooltip; consistent
  status→intent mapping across the app.
- **Keyboard:** non-interactive unless it opens a status menu (then Dropdown rules).
- **Usage:** **Do** keep one source-of-truth status vocabulary per entity, reuse the
  same color mapping everywhere. **Don't** invent ad-hoc statuses per screen or rely
  on color alone.

---

## 6. Data-State Patterns (whole-region states)

> Every data surface must implement these four; they are not optional decorations.

### 6.1 Loading Skeleton
- **Purpose:** placeholder mimicking content shape while data loads (perceived perf).
- **Variants:** text lines, card skeleton, table-row skeleton, chart skeleton, avatar/
  media block; shimmer vs static pulse.
- **Sizes:** matches the real content's footprint to avoid layout shift.
- **States:** animating, static (reduced-motion), timeout→error.
- **Accessibility:** container `aria-busy=true` and/or `role=status` with an
  off-screen "Loading…"; skeleton shapes are `aria-hidden`; **reserve final layout
  size** to prevent CLS; disable shimmer under `prefers-reduced-motion`.
- **Keyboard:** nothing focusable inside a skeleton.
- **Usage:** **Do** match the real structure, show after a short delay (~150–200 ms)
  to avoid flashing, cap duration then show error. **Don't** use a skeleton for < 300
  ms loads (flicker) or mismatch the real layout.

### 6.2 Empty State
- **Purpose:** communicate "nothing here yet" and guide the next action.
- **Variants:** first-use (onboarding CTA), no-results (after search/filter, with
  "clear filters"), cleared/all-done, no-permission-empty.
- **Sizes:** inline (in a card/table) vs full-page.
- **States:** first-use vs filtered-empty (different copy + actions).
- **Accessibility:** meaningful heading + description (announced); illustration is
  `aria-hidden`/decorative; the primary CTA is a real button/link.
- **Keyboard:** CTA is focusable and reachable.
- **Usage:** **Do** explain why it's empty and offer the next step (create / clear
  filters), differentiate first-use from no-results. **Don't** show a bare "No data"
  with no guidance or hide that filters are active.

### 6.3 Error State
- **Purpose:** communicate a failure to load/act and offer recovery.
- **Variants:** inline (region failed), full-page (route failed), partial (one widget),
  with retry, with details/support id, network/offline variant.
- **Sizes:** inline vs full-page.
- **States:** transient (retryable), persistent, offline, partial-data-with-warning.
- **Accessibility:** `role=alert` so it's announced; human-readable message + a
  **retry** action; include a correlation/support id as selectable text; never expose
  raw stack traces.
- **Keyboard:** retry/back actions focusable; focus moves to the error on appearance.
- **Usage:** **Do** offer retry, distinguish offline from server error, keep prior
  data visible when a refresh fails (stale-with-warning). **Don't** blame the user,
  show technical jargon, or silently fail.

### 6.4 Permission Denied
- **Purpose:** the RBAC-gated state when the user lacks rights for a route/action/field.
- **Variants:** page-level (403 route), section-level (panel hidden/locked),
  control-level (disabled control + reason tooltip), field-level (read-only/masked).
- **Sizes:** full-page vs inline lock.
- **States:** hard-denied (hidden), soft-denied (visible but locked with reason),
  request-access (CTA to ask an admin).
- **Accessibility:** locked controls use `aria-disabled` + a programmatic reason
  (`aria-describedby` → "Requires the Manage Catalog permission"); page-level denial
  is announced with a clear heading; don't leak existence of data the user can't see
  unless intended.
- **Keyboard:** a soft-locked control may remain focusable to expose its reason;
  request-access CTA is reachable.
- **Usage:** **Do** prefer hiding truly unauthorized modules (see Sidebar), use
  soft-lock + reason where discoverability helps, offer a request-access path.
  **Don't** show a broken/empty page, reveal restricted data, or disable silently
  with no explanation. Ties to RBAC `has_permission(user, code, tenant, location)`.

---

## 7. Cross-cutting usage rules (apply everywhere)

1. **Theme tokens only** — no hard-coded colors/spacing; white-label theming and
   dark mode come from tokens.
2. **One primary action** per view/card/modal; everything else is secondary/tertiary.
3. **Color is never the only signal** — always pair with text/icon/shape.
4. **Every async surface** declares loading + empty + error (+ permission) states.
5. **Keyboard-complete** — every action reachable and operable without a mouse;
   POS flows are keyboard/scanner-first.
6. **Focus is sacred** — visible focus, logical order, return focus after overlays.
7. **Respect density & locale** — compact on POS, comfortable in admin; localize
   numbers/currency/dates and mirror for RTL.
8. **RBAC-aware rendering** — gate actions/sections by permission, with a clear
   denied affordance.
9. **No layout shift** — reserve space for async content (skeletons match final size).
10. **Reduced motion** — gate non-essential animation behind `prefers-reduced-motion`.

---

## 8. Component index (quick reference)

| # | Component | Category | Key a11y pattern |
|---|-----------|----------|------------------|
| 1 | Button | Actions | native button, `aria-pressed`/`expanded` |
| 2 | Input | Inputs | label + `aria-describedby`/`invalid` |
| 3 | Select | Inputs | combobox/listbox + `activedescendant` |
| 4 | Search | Inputs | searchbox/combobox + live results |
| 5 | Dropdown | Actions | menu/menuitem + focus return |
| 6 | Date Picker | Inputs | grid + typed input |
| 7 | Forms | Inputs | fieldset + error summary `role=alert` |
| 8 | Table | Data | table semantics + `aria-sort` |
| 9 | Card | Data | single activatable target |
| 10 | Statistics/Metric Card | Data | descriptive value name, sign+icon |
| 11 | Charts | Data | `role=img` + table fallback |
| 12 | Timeline | Data | ordered list + `aria-current` |
| 13 | Calendar | Data | grid + labeled days |
| 14 | Pagination | Data | `nav` + `aria-current=page` |
| 15 | Sidebar | Nav | `nav` landmark + `aria-current` |
| 16 | Navbar | Nav | `banner` landmark |
| 17 | Breadcrumb | Nav | `nav` + ordered list + current |
| 18 | Tabs | Nav | tablist/tab/tabpanel + roving tabindex |
| 19 | Alert | Feedback | `role=status`/`alert` |
| 20 | Toast | Feedback | `aria-live`, pause-on-hover |
| 21 | Modal | Overlay | `role=dialog` `aria-modal` + trap |
| 22 | Drawer | Overlay | dialog (modal) / complementary (non-modal) |
| 23 | Accordion | Disclosure | button `aria-expanded` + region |
| 24 | Badge | Status | accessible text, not number-only |
| 25 | Tag | Status | removable × labeled button |
| 26 | Status Chip | Status | fixed status vocab + text |
| 27 | Loading Skeleton | Data-state | `aria-busy` + reserve size |
| 28 | Empty State | Data-state | heading + CTA, first-use vs no-results |
| 29 | Error State | Data-state | `role=alert` + retry + support id |
| 30 | Permission Denied | Data-state | `aria-disabled` + reason, RBAC-gated |
