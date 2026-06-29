---
version: "1.0"
name: Nextora Design Language
codename: "Forge"
description: >
  An original design language for Nextora POS — a multi-tenant restaurant SaaS platform.
  Forge is built for people who work, not people who browse. Every decision prioritises
  clarity, speed, and trust over decoration, atmosphere, and novelty.
  Professional without being sterile. Minimal without being sparse. Fast without being terse.
---

# Nextora Design Language — Forge

> **Codename:** Forge  
> **Version:** 1.0  
> **Platform:** Restaurant SaaS POS — Web, Tablet, Touch Terminal  
> **Modes:** Light · Dark  
> **Audience:** Cashiers · Waiters · Kitchen Staff · Branch Managers · Company Owners · Platform Admins  

---

## Part I — Brand Philosophy

### The Core Premise

Nextora POS is not a product people choose to use. It is a product they *must* use — under shift pressure, in loud environments, hundreds of times a day. A cashier completing their fortieth order at 1 PM on a Saturday does not need inspiration. They need certainty.

**The Forge design language is built on one conviction:**

> Every second a staff member spends looking at the interface is a second stolen from the customer.

This is not a negative statement. It is an engineering target. The interface succeeds when it becomes invisible — when actions are so obvious, layouts so familiar, and feedback so instant that the operator stops thinking about the software and thinks only about the task.

### The Three Foundational Truths

**1. Operators are experts, not users.**  
A cashier who has been using the POS for two weeks has built deep muscle memory. The design must reward that muscle memory — never surprise the operator with layout shifts, reordered actions, or inconsistent placement. Consistency is the highest form of respect for the operator's time.

**2. Trust is communicated through precision.**  
A restaurant operator is handling real money, real orders, real customers. The interface must convey financial precision: numbers are always clearly formatted, states are always explicitly labelled, and destructive actions always require confirmation. No ambiguity. No approximation. No soft language where hard language is needed.

**3. Speed is a feature, not a side-effect.**  
Every component in the Forge system is designed to minimise the number of interactions required to complete a task. The fastest path to completion is the default path. Anything that slows an operator — an extra confirmation step, an unclear button label, a modal that blocks workflow — is a design defect.

### Brand Character

| Dimension | Nextora Forge |
|---|---|
| Personality | Authoritative, efficient, trustworthy |
| Tone | Direct, precise, never condescending |
| Feeling | A well-calibrated instrument |
| NOT | Playful, decorative, trendy, atmospheric |
| Closest analogy | A Bloomberg Terminal that a non-expert can master in two days |

### What Forge Is Not

- **Not a marketing interface.** There are no hero tiles, no full-bleed photography, no editorial paragraphs.
- **Not a consumer app.** There are no onboarding flows triggered on every visit, no gamification, no celebration animations beyond the minimum necessary confirmation feedback.
- **Not a dashboard tool.** Although Nextora includes reporting dashboards, even those are operational — built for decisions, not contemplation.
- **Not Apple.** The Forge language draws lessons from Apple's discipline and restraint, but applies them to an entirely different context, at an entirely different density, for an entirely different human moment.

---

## Part II — Visual Language

### The Visual Model: Zones, Not Pages

Forge does not think in pages. It thinks in **zones**. A POS screen is a persistent composition of simultaneous zones, each with a defined role. Unlike a marketing page, zones do not stack and scroll — they coexist and communicate.

```
┌─────────────────────────────────────────────────────────────────┐
│  TOP RAIL  — Tenant identity · Branch · User · Clock · Alerts   │  44px
├───────────────┬─────────────────────────────┬───────────────────┤
│               │                             │                   │
│  MODULE       │   WORKSPACE                 │  CONTEXT          │
│  RAIL         │                             │  PANEL            │
│               │   (changes per module)      │  (order summary,  │
│  64px wide    │                             │   active table,   │
│               │                             │   payment state)  │
│               │                             │                   │
├───────────────┴─────────────────────────────┴───────────────────┤
│  STATUS RAIL  — Kitchen alerts · Active orders · Shift info     │  32px
└─────────────────────────────────────────────────────────────────┘
```

**Zone definitions:**

| Zone | Purpose | Width / Height | Behaviour |
|---|---|---|---|
| Top Rail | Tenant context, clock, notifications, user | 44px fixed height | Always present; never collapsed |
| Module Rail | Primary navigation between modules | 64px fixed width | Always present on desktop; bottom bar on tablet portrait |
| Workspace | Primary task area; changes per module | Remaining width | Scrollable vertically; never horizontally |
| Context Panel | Persistent order/state context | 320–380px fixed width | Collapsible on small screens; always present on POS terminal |
| Status Rail | Real-time operational signals | 32px fixed height | Always present; dismissible alerts only |

### Surface Hierarchy

Forge defines four surface levels. Every element lives on exactly one surface level. Surface level communicates position in the visual stack without decorative shadows.

| Level | Name | Light Token | Dark Token | Use |
|---|---|---|---|---|
| 0 | Ground | `surface-ground` | `surface-ground-dark` | Page background, behind all zones |
| 1 | Base | `surface-base` | `surface-base-dark` | Main workspace, module rail, context panel |
| 2 | Raised | `surface-raised` | `surface-raised-dark` | Cards, list rows, input fields |
| 3 | Overlay | `surface-overlay` | `surface-overlay-dark` | Modals, dropdowns, floating panels |
| 4 | Toast | `surface-toast` | `surface-toast-dark` | Notification toasts (highest layer) |

No element skips a level. A card (Level 2) never sits directly on Ground (Level 0) without a Base (Level 1) surface underneath.

### Depth Without Shadows

Forge communicates depth through **surface colour steps**, not drop shadows. Shadows are reserved for overlay-level elements (modals, dropdowns) only — and even then, a single, calibrated shadow token is used. This keeps the interface clean, removes visual noise, and ensures depth signals are always meaningful.

```
Ground → Base: 4-step lightness difference (light) / 6-step lightness difference (dark)
Base → Raised: 3-step lightness difference
Raised → Overlay: shadow-overlay token (the only shadow)
```

### Shape Grammar

Forge uses three border radius values. No intermediate values are ever invented.

| Token | Value | Use |
|---|---|---|
| `radius-sharp` | 4px | Data table rows, status badges, input fields, compact chips |
| `radius-card` | 8px | Cards, panels, dropdowns, modal bodies |
| `radius-pill` | 9999px | Primary action buttons, search inputs, quantity steppers |

**Rule:** Radius communicates interaction type.
- `radius-sharp` → data and status
- `radius-card` → container and panel
- `radius-pill` → primary action

Never use `radius-pill` on a passive container. Never use `radius-sharp` on a primary button.

---

## Part III — Design Principles

These are the eight principles that govern every design decision in the Forge system. When two options conflict, the principle higher on this list takes precedence.

### Principle 1 — Clarity Over Cleverness

If a design decision requires explanation, it is wrong. Labels are complete words. Icons are always accompanied by labels in primary navigation. Abbreviations are used only when universally understood (GST, UPI, KDS). Status is communicated with colour + icon + text — never colour alone.

### Principle 2 — Consistency Earns Speed

An operator learns the interface once and then operates from memory. Every module follows the same structural pattern: list on the left, detail on the right, actions in the same position. The primary action is always in the same position (top-right of a workspace, or right side of the context panel). Moving anything breaks trained memory.

### Principle 3 — Density is a Feature

Operational software must show more information in less space than consumer software. Forge achieves comfortable density — not aggressive compression — through a calibrated type scale, precise spacing tokens, and components designed to carry multiple data fields without feeling crowded. A cashier should see at least 8 line items without scrolling. A manager's dashboard should show 6 KPI cards above the fold.

### Principle 4 — State is Always Explicit

Every interactive element communicates its current state through its visual form. There is no state ambiguity in Forge:
- Is this button loading? → show a spinner inside the button
- Is this order paid? → show a green "Paid" badge, not just a green dot
- Is this field in error? → show an error border + error message text
- Is this action destructive? → show the destructive variant (red) and require a second confirmation

### Principle 5 — Touch and Keyboard are Equal Citizens

No workflow requires a mouse. Every workflow that can be completed by touch can be completed by keyboard. Tab order follows visual reading order. Keyboard shortcuts exist for every primary action and are discoverable through a persistent shortcut reference panel. Touch targets are never smaller than 44×44px.

### Principle 6 — Feedback is Instant

Every action receives feedback within one frame (16ms). Long-running operations show a progress indicator within 100ms of initiation. Completed operations show a success confirmation. Failed operations show an error with a recovery path — never a dead end. The operator is never left wondering whether their action registered.

### Principle 7 — The Default Path is the Fast Path

The most common workflow for any role is the default state. A cashier opens the POS and is in New Order mode. A kitchen staff member opens the KDS and sees live tickets. The manager opens the dashboard. No one has to navigate to their primary task — they land on it.

### Principle 8 — Modes Coexist, Never Conflict

Dark mode and light mode are full implementations of the Forge language — not inverted screenshots. Every component, every surface, every semantic colour has a deliberate dark-mode counterpart. No component is permitted in the system without both light and dark specifications.

---

## Part IV — Spacing Philosophy

### The Base Unit

**All spacing in Forge is a multiple of 4px.** The 4px base unit was chosen (rather than the common 8px) to allow fine-grained density control at the compact end of the scale without resorting to arbitrary values.

Structural layout (zone widths, rail heights, card sizes) snaps to 8px multiples. Typographic adjustments and component-internal padding may use 4px multiples.

### Spacing Token Scale

| Token | Value | Use |
|---|---|---|
| `space-1` | 4px | Icon-to-label gaps, tight inline spacing |
| `space-2` | 8px | Internal chip padding, tight list item vertical padding |
| `space-3` | 12px | Standard list item vertical padding, input internal padding |
| `space-4` | 16px | Card internal padding (compact), form field gap |
| `space-5` | 20px | Card internal padding (standard), section gap |
| `space-6` | 24px | Card internal padding (comfortable), modal padding |
| `space-8` | 32px | Between card groups, panel internal sections |
| `space-10` | 40px | Zone padding (workspace top/bottom) |
| `space-12` | 48px | Modal top padding, back-office page top margin |
| `space-16` | 64px | Back-office section separation |
| `space-20` | 80px | Reserved for marketing/onboarding pages only |

### Contextual Spacing Models

Forge defines three density modes. Every surface explicitly declares which density mode it uses.

**Compact** — POS terminal, cashier workspace, kitchen display, order list  
Internal card padding: `space-3` (12px)  
List item vertical padding: `space-2` (8px) top + `space-2` (8px) bottom  
Section gap: `space-4` (16px)  
Minimum viable density: 8 list items visible without scrolling on a 768px-height screen.

**Standard** — Manager dashboard, branch settings, product catalog back-office  
Internal card padding: `space-5` (20px)  
List item vertical padding: `space-3` (12px) top + `space-3` (12px) bottom  
Section gap: `space-6` (24px)  
Minimum viable density: 5 cards visible above the fold on a 768px-height screen.

**Comfortable** — Subscription management, onboarding wizard, help pages  
Internal card padding: `space-6` (24px)  
List item vertical padding: `space-4` (16px) top + `space-4` (16px) bottom  
Section gap: `space-8` (32px)

### The Non-Negotiable Clearances

These minimum clearances are inviolable regardless of density mode:

- Touch target minimum: 44×44px (48×48px preferred for terminal screens)
- Text-to-edge minimum: `space-3` (12px) — text never bleeds to a container edge
- Icon-to-label gap: `space-1` (4px) — icons and their labels are always adjacent
- Status badge clearance: `space-2` (8px) from adjacent text
- Input label-to-field gap: `space-1` (4px)
- Between stacked input fields: `space-4` (16px)
- Primary button bottom clearance from screen edge: `space-4` (16px) minimum

---

## Part V — Color Philosophy

### The Forge Color Model

The Forge color system has four distinct families. Every color in the system belongs to exactly one family. Colors from different families are never used interchangeably.

```
┌─────────────────────────────────────────────────────────────┐
│  BRAND FAMILY      — The single interactive color           │
│  SEMANTIC FAMILY   — Operational state communication        │
│  NEUTRAL FAMILY    — All surfaces, borders, text            │
│  DATA FAMILY       — Chart, graph, and metric colors        │
└─────────────────────────────────────────────────────────────┘
```

### Brand Family — The Interactive Signal

One color signals "this responds to your input." One color only. The brand interactive color is **Forge Indigo** — a blue with enough violet warmth to feel modern and trustworthy, not corporate-cold.

**Brand Indigo** anchors the entire interactive vocabulary. It appears on:
- All primary buttons
- All text links
- All focus rings
- All selected states (chips, tabs, checkboxes, radio buttons)
- Active navigation item indicators

It never appears as:
- A background surface (unless it is the button fill itself)
- A status indicator (green/amber/red handle status)
- A decorative element

**Light Mode Brand Tokens:**
| Token | Hex | Use |
|---|---|---|
| `brand-default` | #4F6EF7 | Default interactive elements |
| `brand-hover` | #3D5CE5 | Hover state (desktop) |
| `brand-pressed` | #2E4DD4 | Active/pressed state |
| `brand-subtle` | #EEF1FE | Selected row backgrounds, chip fill on selection |
| `brand-on-brand` | #FFFFFF | Text and icons on brand-colored surfaces |
| `brand-focus-ring` | #4F6EF7 | 2px focus ring, 2px offset |
| `brand-on-dark` | #7B96FF | Brand blue adjusted for dark surfaces (WCAG AA) |

**Dark Mode counterparts use the same token names; values shift toward higher luminance to maintain contrast ratios.**

### Semantic Family — Operational State

Semantic colors communicate state, not brand. They are used exclusively in their defined contexts. Using a semantic color outside its context is a system violation.

| State | Name | Light Hex | Dark Hex | Use |
|---|---|---|---|---|
| Success | `semantic-success` | #16A34A | #4ADE80 | Paid, completed, in stock, approved |
| Success subtle | `semantic-success-subtle` | #DCFCE7 | #14532D | Success badge background, success row tint |
| Warning | `semantic-warning` | #D97706 | #FCD34D | Pending, low stock, awaiting confirmation |
| Warning subtle | `semantic-warning-subtle` | #FEF3C7 | #451A03 | Warning badge background |
| Danger | `semantic-danger` | #DC2626 | #F87171 | Void, refund, out of stock, overdue, delete |
| Danger subtle | `semantic-danger-subtle` | #FEE2E2 | #450A0A | Danger badge background, destructive row tint |
| Info | `semantic-info` | #0284C7 | #38BDF8 | Informational, in-progress, neutral status |
| Info subtle | `semantic-info-subtle` | #E0F2FE | #0C4A6E | Info badge background |

**Critical Rule:** Color alone never communicates state. Every semantic color usage is paired with:
1. A text label (e.g., "Paid", "Void", "Low Stock")
2. An icon (e.g., ✓ for success, ✕ for danger, ⚠ for warning)

This ensures the interface is fully accessible to colour-blind operators.

### Neutral Family — Surface and Text

The neutral family forms the visual substrate of the entire interface. It is a calibrated 12-step grayscale with warm undertones (not cold blue-gray, not yellow — warm but neutral).

**Light Mode Neutrals:**
| Token | Hex | Use |
|---|---|---|
| `neutral-0` | #FFFFFF | Surface-raised, modal, input background |
| `neutral-50` | #F8F8F8 | Surface-base (main workspace) |
| `neutral-100` | #F2F2F2 | Surface-ground (page background) |
| `neutral-150` | #EBEBEB | Zone separators, hairline borders |
| `neutral-200` | #E0E0E0 | Input borders, card borders |
| `neutral-300` | #CBCBCB | Disabled input borders |
| `neutral-400` | #A8A8A8 | Placeholder text, muted icons |
| `neutral-500` | #848484 | Secondary text, captions |
| `neutral-600` | #5C5C5C | Body text (secondary) |
| `neutral-700` | #3D3D3D | Body text (primary) |
| `neutral-800` | #252525 | Headings, strong emphasis |
| `neutral-900` | #141414 | Highest contrast text |

**Dark Mode Neutrals (inverted, with warm dark undertone — not pure black):**
| Token | Hex | Use |
|---|---|---|
| `neutral-dark-0` | #1A1A1C | Surface-ground |
| `neutral-dark-50` | #212124 | Surface-base |
| `neutral-dark-100` | #2A2A2E | Surface-raised, cards |
| `neutral-dark-150` | #313136 | Zone separators, hairline borders |
| `neutral-dark-200` | #3C3C42 | Input borders, card borders |
| `neutral-dark-300` | #4F4F57 | Disabled borders |
| `neutral-dark-400` | #6B6B75 | Placeholder text, muted icons |
| `neutral-dark-500` | #8C8C98 | Secondary text |
| `neutral-dark-600` | #ABABBA | Body text (secondary) |
| `neutral-dark-700` | #C8C8D8 | Body text (primary) |
| `neutral-dark-800` | #E0E0EE | Headings |
| `neutral-dark-900` | #F0F0F8 | Highest contrast text |

**Why warm dark, not pure black:**  
Pure black backgrounds (#000000) on OLED displays can cause halation around high-contrast text, making it harder to read. The `neutral-dark-0` ground (#1A1A1C) is dark enough for true dark-mode depth while eliminating halation. It also aligns with the character of a professional instrument — not the void of a cinema screen.

### Data Family — Charts and Metrics

For reporting dashboards, data visualisations require colors that are:
- Distinguishable by color-blind users (deuteranopia and protanopia safe)
- Harmonious with the Forge brand palette
- Consistent across all chart types

| Token | Hex | Use |
|---|---|---|
| `data-1` | #4F6EF7 | Primary series (aligns with brand) |
| `data-2` | #E07B39 | Secondary series (warm contrast) |
| `data-3` | #2DB5A3 | Tertiary series (teal) |
| `data-4` | #9B6DDE | Quaternary series (violet) |
| `data-5` | #D4596A | Quinary series (rose) |
| `data-6` | #5BA85B | Sixth series (forest green) |

All six data colors pass WCAG AA contrast against both `neutral-50` (light) and `neutral-dark-50` (dark) backgrounds.

### Color Rules

1. **Brand colors are for interaction only.** Never use `brand-default` as a decorative background.
2. **Semantic colors are for state only.** Never use `semantic-success` for a brand moment.
3. **No gradients on surfaces.** Gradients may only appear on chart fills (area charts), using semi-transparent versions of data-family colors.
4. **No shadows on cards or buttons.** The shadow token (`shadow-overlay`) is used only for Level 3 Overlay surfaces.
5. **Contrast minimum:** All body text must achieve WCAG AA (4.5:1). Primary operational values (order totals, alert text) must achieve WCAG AAA (7:1).

---

## Part VI — Typography Philosophy

### The Typeface: Inter Variable

Forge uses **Inter Variable** as its sole typeface. Inter is selected because:
- Open-source, zero licensing risk, Google Fonts CDN availability
- Variable font enables the full weight axis (100–900) from a single file
- Superior legibility at 13–17px (the operational density range)
- Latin, Devanagari, and extended character set support (critical for Indian restaurant market)
- `font-feature-settings: "ss03"` produces a rounded 'a' that reduces sterility
- Negative letter-spacing at display sizes approximates the premium feel of proprietary display faces

**Font stack declaration:**
```
Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif
```

The system-ui fallback ensures native rendering on platforms where Inter has not yet loaded.

### The Type Scale — 8 Steps

Forge defines exactly 8 type scale steps. No intermediate sizes are ever invented. Each step has a defined role that cannot be substituted.

| Token | Size | Weight | Line Height | Letter Spacing | Role |
|---|---|---|---|---|---|
| `type-display` | 28px | 700 | 1.14 | -0.3px | Module page headings, metric totals in dashboard |
| `type-heading-1` | 22px | 600 | 1.18 | -0.2px | Panel headings, modal titles, section names |
| `type-heading-2` | 18px | 600 | 1.22 | -0.15px | Card headings, sub-section labels |
| `type-heading-3` | 15px | 600 | 1.33 | 0 | List group headers, column headers |
| `type-body` | 15px | 400 | 1.47 | 0 | Standard operational body text, list items |
| `type-body-strong` | 15px | 600 | 1.47 | 0 | Emphasised body text, prices, quantities |
| `type-caption` | 13px | 400 | 1.38 | 0.1px | Metadata, timestamps, secondary labels |
| `type-caption-strong` | 13px | 600 | 1.38 | 0.1px | Status badge labels, emphasised captions |
| `type-micro` | 11px | 400 | 1.27 | 0.2px | Fine print, keyboard shortcut labels, legal text |

### Typography Principles

**1. The weight ladder is 400 / 600 / 700 only.**  
Weight 500 is absent. Mid-weight text creates ambiguity between "is this body text or an emphasis?" Forge resolves ambiguity by requiring a deliberate choice: regular (400) or bold (600/700).

**2. Negative letter-spacing only on headings.**  
`type-display` and `type-heading-1` use negative letter-spacing. This creates the precise, tight character of a professional instrument at large sizes. Body and caption text never use negative tracking — at 13–15px, negative tracking impairs readability.

**3. Line height is tighter on headings, fuller on body.**  
Display and heading levels use 1.14–1.22 (compact heading rhythm). Body uses 1.47 (reading rhythm). Caption uses 1.38. This is not arbitrary — it reflects how the eye reads at each size.

**4. `type-body` is 15px, not 16px or 17px.**  
Apple runs body at 17px for editorial pace. Nextora POS runs body at 15px for operational density. At 17px, a cashier's order item list shows 7 items on a 600px-height workspace. At 15px, it shows 9 items. Two extra line items visible without scrolling is a meaningful productivity gain.

**5. Number formatting is always tabular.**  
All numeric values (prices, quantities, tax amounts, order counts) use `font-variant-numeric: tabular-nums`. This ensures columns of numbers align vertically, making comparisons and error-detection instant.

**6. The minimum rendered size is 11px (`type-micro`).**  
Nothing in the Forge system renders below 11px. Keyboard shortcut hints and legal fine print use `type-micro`. Any use case that would require sub-11px text must be solved through layout or information architecture, not font size reduction.

**7. Monospace for codes, IDs, and technical values.**  
Order numbers, invoice numbers, product SKUs, and API keys render in the system monospace font (`ui-monospace, "Cascadia Code", "Fira Code", monospace`). This distinguishes machine-readable identifiers from human-readable content and prevents character confusion (0 vs O, 1 vs l).

---

## Part VII — Motion Philosophy

### The Forge Motion Contract

Motion in Forge serves one of four purposes. If a motion does not serve one of these purposes, it does not exist in the system.

1. **Confirm** — An action registered and completed (button press, payment captured)
2. **Locate** — A new element arrived or moved (toast appeared, panel opened, focus shifted)
3. **Orient** — The user understands where they are in a flow (step transition, modal layering)
4. **Recover** — An error state is signalling attention (shake, pulse)

Decorative motion — animation that exists to delight, to fill time, or to demonstrate technical sophistication — is explicitly prohibited in Forge.

### Motion Token Scale

| Token | Duration | Easing | Use |
|---|---|---|---|
| `motion-instant` | 0ms | — | State changes that should feel instantaneous (tab selection, toggle) |
| `motion-fast` | 80ms | `ease-in-out` | Button press (scale), badge count change |
| `motion-standard` | 150ms | `ease-out` | Input focus ring, status badge change, chip selection |
| `motion-moderate` | 220ms | `ease-out` | Toast enter/exit, dropdown open/close, panel collapse |
| `motion-deliberate` | 300ms | `ease-in-out` | Modal open/close, page-level navigation, large panel state |
| `motion-slow` | 500ms | `ease-in-out` | Reserved — skeleton-to-content transition only |

**Rule:** No animation in a primary POS workflow may exceed `motion-moderate` (220ms). A cashier completing a payment should never wait for an animation.

### The Four System Motions

**1. The Press Confirm (all interactive elements)**  
`transform: scale(0.97)` on active/pressed state, returning to `scale(1.0)` on release.  
Duration: `motion-fast` (80ms) out, `motion-standard` (150ms) back.  
This single motion applies to every button, chip, card, and list row that responds to press. It is the tactile signal of the Forge system.

*Why 0.97 not 0.95:* Apple uses 0.95, which is noticeable on large marketing buttons. At Forge's compact component sizes (32–40px height buttons), 0.95 looks like a mechanical failure. 0.97 gives the tactile signal without visual alarm.

**2. The Focus Shift (keyboard navigation)**  
Focus ring: `2px solid brand-focus-ring`, `2px offset`.  
Transition: `motion-standard` (150ms) `ease-out`.  
The focus ring never teleports — it transitions smoothly to guide the eye across the interface.

**3. The Toast Entry (notifications)**  
Toast slides in from the top-right: `transform: translateY(-8px) → translateY(0)` + `opacity: 0 → 1`.  
Duration: `motion-moderate` (220ms) `ease-out`.  
Exit: `opacity: 1 → 0` + `motion-standard` (150ms).

**4. The Destructive Alert (error recovery)**  
A brief horizontal shake: `transform: translateX(-4px) → translateX(4px) → translateX(-2px) → translateX(0)`.  
Duration: 300ms total, 4 keyframes.  
Used when a destructive action is denied (insufficient permission), when a required field is missed, or when a payment fails.

### Motion Freeze Zones

During the following operations, **all non-essential animations are paused:**

- Payment capture in progress
- Order submission in progress
- Receipt printing in progress
- Any full-screen loading state

Motion during a financial transaction creates the impression of instability. The interface should feel completely still when money is moving.

---

## Part VIII — Interaction Philosophy

### The Interaction Model: Three Input Contexts

Forge operates across three primary input contexts simultaneously. Every component is designed for all three.

**Context A — Touch Terminal (Primary POS)**  
Hardware: 10–27" touchscreen. Input: fingers (may be gloved).  
Design implications: 48px minimum targets, generous padding, no hover states, drag interactions are supplementary not primary, all critical actions reachable with one hand from the dominant side of the screen.

**Context B — Keyboard (Back-Office, Manager)**  
Hardware: Desktop or laptop with external keyboard.  
Design implications: Full tab order, keyboard shortcuts for all primary actions, arrow-key navigation within lists and grids, Enter to confirm, Escape to cancel, no workflow that requires mouse.

**Context C — Mouse (Reporting, Admin)**  
Hardware: Desktop with mouse.  
Design implications: 32px minimum targets (relaxed from touch), hover states on all interactive elements, right-click context menus for power-user shortcuts.

### The Five Interaction Laws

**Law 1 — Primary actions are always in the same position.**  
The primary action for any workspace is always top-right of the workspace or right side of the Context Panel. An operator who has learned this pattern never searches for "the button." This spatial consistency is absolute — not a guideline.

**Law 2 — Destructive actions require double confirmation.**  
Any action that cannot be undone (void an order, process a refund, delete a product, remove a user) follows the Destructive Action Protocol:
1. First tap: button transitions to destructive state (semantic-danger fill, "Confirm Void?" label)
2. Three-second timeout: if no second tap, button resets to default
3. Second tap within timeout: action executes
4. Completion: toast confirms the destructive action completed

No modal dialog for destructive confirmation — it interrupts workflow. The two-tap button pattern is faster, less disruptive, and builds muscle memory for "I have to tap this twice."

**Law 3 — Every action has a keyboard equivalent.**  
Primary actions: single-key shortcut (e.g., `N` = New Order, `P` = Pay, `V` = Void).  
Secondary actions: modifier + key (e.g., `Ctrl+D` = Apply Discount, `Ctrl+S` = Split Bill).  
Shortcuts are visible in a persistent shortcut reference (triggered by `?` key) and in tooltip on hover (desktop only).

**Law 4 — Incomplete states are visible, never hidden.**  
An order with missing required fields (e.g., table number for dine-in) shows the incomplete indicator inline — never discovered at submission. A payment attempt on an order with zero items shows an error immediately, not after the cashier has entered payment details.

**Law 5 — Recovery is always one step.**  
Every error state offers a single, obvious recovery action. "Payment failed — Retry" not "An error occurred, please contact support." "Product not found — Clear search" not a dead empty state. The operator is never left at a dead end.

### Interaction Patterns

**The Quick Key Grid**  
For high-velocity cashier workflows, the product catalog exposes a Quick Key grid — a configurable grid of product tiles (4 to 8 columns depending on screen size) ordered by sales frequency. Quick Keys use `radius-card` (8px), a product image thumbnail, product name in `type-body-strong`, and price in `type-caption`. Tapping a Quick Key adds it to the order immediately. No confirmation required.

**The Modifier Sheet**  
When a product has required modifiers (size, spice level, cooking preference), tapping it opens a Modifier Sheet — a slide-up panel (mobile) or a context-anchored dropdown (desktop). Modifier options use the configurator chip pattern: `radius-pill`, `type-caption`, selection indicated by `brand-default` border + `brand-subtle` fill. Required modifier groups are visually grouped with `type-heading-3` group labels.

**The Quantity Stepper**  
Inline quantity control: `−` button · quantity value · `+` button. The stepper uses `radius-pill` on the whole assembly, with the quantity value in `type-body-strong` (tabular nums). Pressing `−` to reach zero transitions the button to a delete icon — tapping it once more shows the destructive state ("Remove item?"), requiring confirmation before the item is removed.

**The Payment Split**  
When splitting a bill, the Context Panel transforms into a Split Panel — a tabbed view showing each payer's portion. Each tab has a running total in `type-display`. Adding a payment to one payer's tab updates all totals in real time. The "Pay Full" button remains accessible via a "Merge" action if the cashier decides to cancel the split.

**The Contextual Search**  
Search is available in every list view. It is always positioned at the top of the list (not in the top rail — search is contextual to the current list, not global). The search input uses `radius-pill`, 44px height, an inline search icon on the left. Results filter inline without a page reload. No separate search results page exists — filtering happens in place.

---

## Part IX — Accessibility Philosophy

### The Forge Accessibility Contract

Accessibility in Forge is not a feature layer added after design. It is a design constraint applied from the first decision. The target compliance level is **WCAG 2.2 AA** for all POS terminal screens and **WCAG 2.2 AAA** for all text carrying financial values.

### The Seven Accessibility Foundations

**1. Color is never the sole differentiator.**  
Every status, state, or category communicated by color is also communicated by:
- A text label (primary)
- An icon (secondary)

An operator who cannot distinguish red from green can operate Nextora POS without any loss of functionality.

**2. Contrast is non-negotiable.**  
| Surface | Required Ratio | Standard |
|---|---|---|
| Body text on any surface | 4.5:1 minimum | WCAG AA |
| Financial values, alert text | 7:1 minimum | WCAG AAA |
| UI component borders | 3:1 minimum | WCAG AA (non-text) |
| Placeholder text | 3:1 minimum | WCAG AA (non-text) |

The Forge neutral scale is calibrated to guarantee these ratios in both light and dark mode at every surface level.

**3. Touch targets are generous.**  
- Minimum: 44×44px (WCAG 2.5.5 recommendation)
- Preferred: 48×48px for all POS terminal primary actions
- Spacing between adjacent targets: minimum 8px (`space-2`) to prevent mis-tap

**4. Focus is always visible.**  
The `brand-focus-ring` (2px solid, 2px offset) is visible on all surfaces in both light and dark mode. Focus ring contrast against background is always ≥ 3:1. The focus ring is never hidden, overridden, or reduced in size for aesthetic reasons.

**5. Screen reader support for back-office.**  
All icon-only buttons carry `aria-label`. All data tables carry `scope` headers. All status badges carry `role="status"` and `aria-live="polite"` where they update dynamically. All modal dialogs trap focus correctly and return focus on close. All form fields have associated labels (never placeholder-as-label).

**6. Motion respects the operator.**  
All animations respect the `prefers-reduced-motion` media query. When reduced motion is active:
- The Press Confirm scale(0.97) is removed
- Toast slides are replaced with instant opacity transitions
- Panel open/close transitions are reduced to 50ms opacity only
- No animations are eliminated entirely (state changes still need to be perceived) — only the motion component is removed, preserving the timing of state changes.

**7. Language is direct and literal.**  
Button labels are verbs: "Pay", "Void", "Add Item", "Apply Discount", "Print Receipt". Never "Submit", "Proceed", "Continue", or "OK" — these words carry no information about what will happen. Error messages name the problem and the solution: "Quantity cannot be zero — increase to at least 1" not "Invalid input."

---

## Part X — Consistency Rules

These rules are the constitutional layer of the Forge system. They exist to prevent the gradual erosion of system coherence as the product grows. Any design decision that violates a Consistency Rule requires explicit documentation of the exception and sign-off from the design lead.

### Rule Set A — Visual Consistency

**A1.** Every interactive element uses `brand-default` as its active/selected signal. No module invents a second interactive color.

**A2.** Border radius tokens are used exclusively. Radius values of 5px, 6px, 10px, 12px, 16px, or any value not defined in the radius token set are prohibited.

**A3.** Spacing values are multiples of 4px. Values of 5px, 6px, 7px, 9px, 10px, or any value not in the spacing token set are prohibited.

**A4.** Drop shadows appear only on Level 3 (Overlay) surfaces. Cards, buttons, input fields, list rows, and navigation elements never have drop shadows.

**A5.** Gradients are permitted only on chart area fills (50% opacity, data-family colors). Gradient backgrounds on any structural surface are prohibited.

**A6.** The module rail is the only global navigation. No secondary global navigation element is introduced inside the workspace. Navigation within a module uses tabs, breadcrumbs, or a top strip — never a nested sidebar.

### Rule Set B — Typography Consistency

**B1.** Font sizes are defined by the 8-step type scale. No font size outside this scale is used in any component.

**B2.** The weight ladder is 400 / 600 / 700. Weight 500 is not used. Weights below 400 are not used in any operational context.

**B3.** All monetary values and quantities use `font-variant-numeric: tabular-nums`. This rule applies universally — no exceptions for "small" numbers.

**B4.** All heading tokens use the Inter Variable font. No module may introduce a second display typeface for visual differentiation.

**B5.** Order numbers, invoice numbers, SKUs, and machine identifiers render in monospace. Human-readable content never renders in monospace.

### Rule Set C — Interaction Consistency

**C1.** The primary action is always top-right of the workspace or right side of the Context Panel. No exception.

**C2.** Destructive actions always follow the Two-Tap Confirmation Protocol. No destructive action bypasses this protocol, even for "quick" deletions.

**C3.** The Press Confirm (scale 0.97) applies to every interactive element. It is the universal tactile signal. No interactive element is exempt.

**C4.** Every keyboard shortcut is documented in the shortcut reference panel (triggered by `?`). No undocumented shortcut exists in production.

**C5.** Search is always contextual (within the current list) and never global (across all modules). The search field is always at the top of the list it filters, never in the top rail.

### Rule Set D — State Consistency

**D1.** Every component has explicit specifications for: default, hover (desktop), pressed, focused, disabled, loading, error, and success states. No component ships without all eight states designed.

**D2.** Loading states use skeleton screens (not spinners) for content that exceeds 300ms to load. Spinners are used only for action-in-progress (a button that has been tapped and is awaiting a response).

**D3.** Empty states always contain a title, a description of why it's empty, and a primary action to resolve the empty state. "No orders found" alone is insufficient. It must be paired with "No orders have been placed today" and a "New Order" action.

**D4.** Error states always contain the error in plain language, the cause if determinable, and a single recovery action. Generic error messages ("Something went wrong") are not permitted in production.

**D5.** Every list that can be searched also displays the result count when a search filter is active ("12 of 47 products").

### Rule Set E — Mode Consistency

**E1.** Every component is designed and documented for both light and dark mode simultaneously. A component submitted without both mode specifications is incomplete and cannot be shipped.

**E2.** Dark mode is not an inverted screenshot. Surface hierarchy, semantic colors, and focus rings are independently specified for dark mode. The dark mode neutral scale runs from #1A1A1C (ground) to #F0F0F8 (highest contrast text) — it never uses pure black (#000000) or pure white (#FFFFFF) as surface colors.

**E3.** Mode switching is instant (`motion-instant`, 0ms). There is no transition animation between light and dark mode. Fading between modes creates visual confusion and delays the perceived response.

**E4.** System mode preference (`prefers-color-scheme`) is respected by default. Operators may override to a fixed mode through user settings. The override is persisted per user, not per device.

---

## Appendix A — Token Summary Reference

### Surface Tokens

| Token | Light | Dark |
|---|---|---|
| `surface-ground` | neutral-100 | neutral-dark-0 |
| `surface-base` | neutral-50 | neutral-dark-50 |
| `surface-raised` | neutral-0 | neutral-dark-100 |
| `surface-overlay` | neutral-0 | neutral-dark-100 |
| `surface-toast` | neutral-800 (dark toast) | neutral-100 (light toast) |

### Elevation / Shadow Token

| Token | Value |
|---|---|
| `shadow-overlay` | `0 4px 16px rgba(0,0,0,0.12), 0 1px 4px rgba(0,0,0,0.08)` |

### Zone Dimension Tokens

| Token | Value |
|---|---|
| `zone-top-rail-height` | 44px |
| `zone-module-rail-width` | 64px |
| `zone-status-rail-height` | 32px |
| `zone-context-panel-width` | 340px |
| `zone-context-panel-width-lg` | 380px |

### Breakpoints

| Token | Value | Description |
|---|---|---|
| `bp-sm` | 640px | Small tablet / large phone |
| `bp-md` | 768px | Standard tablet portrait |
| `bp-lg` | 1024px | Tablet landscape / small desktop |
| `bp-xl` | 1280px | Standard desktop POS terminal |
| `bp-2xl` | 1440px | Large desktop / wide terminal |

Below `bp-md`: Module Rail becomes bottom tab bar; Context Panel collapses to a pull-up sheet.  
Below `bp-sm`: Single-column layout; all panels become full-screen drawers.

---

## Appendix B — Component Checklist

Every new component entering the Forge system must satisfy this checklist before it is considered complete:

- [ ] Light mode and dark mode specifications documented
- [ ] All 8 states documented (default, hover, pressed, focused, disabled, loading, error, success)
- [ ] Touch target ≥ 44×44px verified
- [ ] Keyboard interaction documented (tab, enter, escape, arrow keys where applicable)
- [ ] ARIA roles and attributes documented
- [ ] Color contrast verified at WCAG AA (body text) and AAA (financial values)
- [ ] Spacing uses only token values (no hardcoded px)
- [ ] Border radius uses only token values
- [ ] Font size uses only the 8-step type scale
- [ ] Press Confirm (scale 0.97) specified on all interactive states
- [ ] Focus ring (2px solid, 2px offset) specified
- [ ] Reduced-motion variant documented
- [ ] Compact, Standard, and Comfortable density variants specified (where applicable)
- [ ] Empty state designed (for any component that can have zero items)
- [ ] Error state designed (for any component that can receive invalid input)

---

## Appendix C — The Forge Design Manifesto

*For the designers and engineers building Nextora POS:*

The restaurant industry operates at a pace that most software designers never experience. A table turn at a busy restaurant means 45 minutes of service per cover. In that 45 minutes, a waiter takes an order on a POS, the kitchen receives a KDS ticket, food is prepared and delivered, a cashier processes a payment, and a receipt is printed. The software is touched dozens of times. Every friction point compounds.

We are building for the person taking orders at table 12 while table 8 is calling for the bill and table 3 just walked in. We are building for the manager checking his dashboard at 11 PM after a 14-hour shift, who needs to see one number — did today work?

We are not building a product showcase. We are not building a demo for an investor deck. We are building a tool that earns trust through daily reliability, that speeds through repetition, that never surprises the operator when they cannot afford a surprise.

The Forge language is our answer to that human reality.

Every pixel we do not add is a distraction we have removed.  
Every token we define is a decision made once, correctly, for everyone.  
Every principle we document is a fight we have won in advance.

Make it fast. Make it clear. Make it trustworthy. Make it invisible.

---

*Forge Design Language — Nextora POS — Version 1.0*  
*Generated from first principles with lessons drawn from the Apple Design Analysis review.*  
*This document is the source of truth for all visual and interaction decisions in the Nextora POS product.*
