# Forge Design Token — Naming Convention & Reference

## Token Anatomy

```
--forge-{category}-{variant}-{modifier}
   │       │          │         │
   │       │          │         └── state, scale step, or mode qualifier
   │       │          └──────────── semantic name within the category
   │       └─────────────────────── design category
   └─────────────────────────────── system prefix (always "forge")
```

### Rules
1. Always lowercase, always hyphenated — never camelCase, never underscores.
2. The `forge-` prefix is mandatory on every token — prevents collisions with any third-party library.
3. `primitive-` tokens are raw hex values and are never referenced in components directly.
4. All component usage references semantic tokens only.

---

## Category Reference

| Category | Prefix | Examples |
|---|---|---|
| Color — brand | `--forge-color-brand-` | `brand-default`, `brand-hover`, `brand-pressed`, `brand-subtle` |
| Color — semantic | `--forge-color-{state}-` | `success-default`, `warning-subtle`, `danger-text`, `info-border` |
| Color — surface | `--forge-color-surface-` | `surface-ground`, `surface-base`, `surface-raised`, `surface-overlay` |
| Color — text | `--forge-color-text-` | `text-primary`, `text-body`, `text-secondary`, `text-disabled` |
| Color — border | `--forge-color-border-` | `border-default`, `border-strong`, `border-focus`, `border-danger` |
| Color — icon | `--forge-color-icon-` | `icon-primary`, `icon-brand`, `icon-success` |
| Color — data | `--forge-color-data-` | `data-1` through `data-6` |
| Color — primitive | `--forge-primitive-` | `primitive-indigo-500`, `primitive-neutral-800` |
| Typography — size | `--forge-type-size-` | `type-size-body`, `type-size-display`, `type-size-caption` |
| Typography — weight | `--forge-type-weight-` | `type-weight-regular`, `type-weight-semibold`, `type-weight-bold` |
| Typography — leading | `--forge-type-leading-` | `type-leading-body`, `type-leading-tight`, `type-leading-caption` |
| Typography — tracking | `--forge-type-tracking-` | `type-tracking-tight`, `type-tracking-normal`, `type-tracking-wide` |
| Spacing | `--forge-space-` | `space-1` (4px), `space-2` (8px) … `space-20` (80px) |
| Density | `--forge-density-` | `density-compact-card`, `density-standard-list-v` |
| Radius | `--forge-radius-` | `radius-sharp` (4px), `radius-card` (8px), `radius-pill` |
| Border width | `--forge-border-width-` | `border-width-hairline`, `border-width-thick`, `border-width-focus` |
| Border composite | `--forge-border-` | `border-default`, `border-danger`, `border-focus` |
| Shadow | `--forge-shadow-` | `shadow-none`, `shadow-ring`, `shadow-overlay`, `shadow-toast` |
| Focus | `--forge-focus-` | `focus-ring-width`, `focus-ring-color`, `focus-outline` |
| Opacity | `--forge-opacity-` | `opacity-disabled`, `opacity-scrim`, `opacity-muted` |
| Motion — duration | `--forge-duration-` | `duration-fast`, `duration-standard`, `duration-moderate` |
| Motion — easing | `--forge-ease-` | `ease-default`, `ease-out`, `ease-spring` |
| Motion — transition | `--forge-transition-` | `transition-fast`, `transition-standard` |
| Z-index | `--forge-z-` | `z-sticky`, `z-dropdown`, `z-modal`, `z-toast` |
| Zone dimensions | `--forge-zone-` | `zone-top-rail-height`, `zone-module-rail-width` |
| Container | `--forge-container-` | `container-xs`, `container-xl` |
| Icon size | `--forge-icon-` | `icon-sm` (16px), `icon-md` (20px), `icon-lg` (24px) |
| Breakpoint | `--forge-bp-` | `bp-sm` (640px), `bp-md` (768px), `bp-xl` (1280px) |
| Skeleton | `--forge-skeleton-` | `skeleton-base`, `skeleton-highlight`, `skeleton-gradient` |

---

## Scale Modifier Conventions

### Numeric scale steps
Used for palette primitives and spacing:
`50, 100, 150, 200, 300, 400, 500, 600, 700, 800, 900`

### Named size steps
Used for type scale, icons, and radii:
`xs, sm, md, lg, xl, 2xl`

### State modifiers
Applied to interactive component tokens:
`default, hover, pressed, focus, disabled, loading, error, success`

### Mode modifiers
`on-brand` — for content sitting on a brand-colored surface  
`on-dark`  — for content sitting on a dark surface  
`subtle`   — reduced-intensity background variant of a semantic color  
`text`     — text-specific variant of a semantic color (optimised contrast)  
`border`   — border-specific variant of a semantic color  
`on`       — foreground color for content on a semantic surface  

---

## Tailwind Class Naming

Tailwind classes map directly to token families:

| Token family | Tailwind class pattern | Example |
|---|---|---|
| `--forge-color-brand-default` | `bg-brand`, `text-brand`, `border-brand` | `<button class="bg-brand text-brand-on-brand">` |
| `--forge-color-surface-raised` | `bg-surface-raised` | `<div class="bg-surface-raised">` |
| `--forge-color-text-secondary` | `text-text-secondary` | `<span class="text-text-secondary">` |
| `--forge-color-success-DEFAULT` | `bg-success`, `text-success` | `<span class="text-success">` |
| `--forge-color-success-subtle` | `bg-success-subtle` | `<div class="bg-success-subtle">` |
| `--forge-color-border-default` | `border-border` | `<div class="border border-border">` |
| `--forge-radius-card` | `rounded-card` | `<div class="rounded-card">` |
| `--forge-radius-pill` | `rounded-pill` | `<button class="rounded-pill">` |
| `--forge-shadow-overlay` | `shadow-overlay` | `<div class="shadow-overlay">` |
| `--forge-duration-standard` | `duration-standard` | `<div class="transition duration-standard">` |
| `z-modal` | `z-modal` | `<div class="z-modal">` |
| `icon-md` | `.icon-md` utility | `<svg class="icon-md">` |
| `tabular-nums` | `.tabular-nums` utility | `<span class="tabular-nums">` |

---

## Color Token Decision Tree

```
Is the color for an interactive element (button, link, checkbox)?
  YES → use brand-* tokens
  NO  →
    Is it communicating a state (paid, pending, void, error)?
      YES → use semantic-* tokens (success/warning/danger/info)
      NO  →
        Is it text?
          YES → use text-* tokens (primary/body/secondary/tertiary/disabled)
          NO  →
            Is it a surface/background?
              YES → use surface-* tokens (ground/base/raised/overlay)
              NO  →
                Is it a border or divider?
                  YES → use border-* tokens
                  NO  →
                    Is it an icon?
                      YES → use icon-* tokens
                      NO  → use data-* tokens for charts only
```

---

## Dark Mode Implementation

Dark mode is activated by adding `data-theme="dark"` to the `<html>` element or a top-level container.

```html
<!-- Light (default) -->
<html>

<!-- Dark -->
<html data-theme="dark">
```

All semantic tokens automatically switch to dark mode values via the `[data-theme="dark"]` CSS selector in `tokens.css`. No component-level dark mode logic is needed.

**Rule E3 from DESIGN-nextora.md:** Mode switching is instant (`duration-instant`, 0ms). No transition animation between modes.

```js
// Toggle dark mode — instant, no animation
document.documentElement.setAttribute('data-theme', 'dark');
document.documentElement.removeAttribute('data-theme'); // back to light
```

---

## Density Mode Implementation

Density mode is set via a `data-density` attribute on the workspace container.

```html
<div data-density="compact">   <!-- POS terminal, cashier screen  -->
<div data-density="standard">  <!-- Manager back-office, dashboard -->
<div data-density="comfortable"> <!-- Settings, onboarding pages   -->
```

Components read the correct spacing from CSS custom property inheritance:

```css
[data-density="compact"]     { --local-card-pad: var(--forge-density-compact-card);   }
[data-density="standard"]    { --local-card-pad: var(--forge-density-standard-card);  }
[data-density="comfortable"] { --local-card-pad: var(--forge-density-comfort-card);   }
```

---

## Token Files

| File | Purpose |
|---|---|
| [`tokens.css`](./tokens.css) | CSS Custom Properties — all tokens, light + dark mode |
| [`tailwind.config.js`](./tailwind.config.js) | Tailwind v3 theme — mirrors tokens.css exactly |
| [`NAMING.md`](./NAMING.md) | This file — naming convention and reference |

---

## Prohibited Patterns

| Pattern | Why Prohibited | Correct Alternative |
|---|---|---|
| Hardcoded hex (`#4F6EF7`) in component styles | Breaks dark mode, breaks theming | `var(--forge-color-brand-default)` |
| Hardcoded px (`padding: 13px`) | Not on 4px grid | `var(--forge-space-3)` (12px) or `var(--forge-space-4)` (16px) |
| Using a primitive token in a component (`var(--forge-primitive-indigo-500)`) | Bypasses semantic layer | `var(--forge-color-brand-default)` |
| Using `semantic-success` for brand moments | Green means "operational success" only | `var(--forge-color-brand-default)` |
| Using `brand-default` for a status badge | Brand blue means "interactive" only | `var(--forge-color-info-default)` |
| Font size not in the 8-step scale | Breaks typographic rhythm | Nearest scale step |
| Font weight 500 | Explicitly absent from Forge | Use 400 (regular) or 600 (semibold) |
| `border-radius` not in the 3-radius grammar | Breaks shape language | `radius-sharp`, `radius-card`, or `radius-pill` |
| `box-shadow` on a card or button | Shadows reserved for overlays | Remove shadow; use border or surface step |
| `transition` longer than 220ms on a primary POS action | Slows operator workflow | `duration-standard` (150ms) or `duration-fast` (80ms) |
