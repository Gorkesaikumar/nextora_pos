/**
 * ============================================================
 *  NEXTORA POS — FORGE DESIGN TOKEN SYSTEM
 *  Tailwind CSS v3 Theme Configuration
 *  Version: 1.0  |  Codename: Forge
 *
 *  This file is the single source of truth for Tailwind.
 *  All values mirror tokens.css exactly.
 *  Usage: extend the default Tailwind theme — do not replace.
 *
 *  Naming convention in Tailwind classes:
 *    bg-forge-{token}     → background
 *    text-forge-{token}   → text color
 *    border-forge-{token} → border color
 *    shadow-forge-{token} → shadow
 *    rounded-forge-{token}→ border radius
 *    spacing maps to p-*, m-*, gap-* etc.
 * ============================================================
 */

const defaultTheme = require('tailwindcss/defaultTheme');

/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/**/*.{js,ts,jsx,tsx,vue,html}',
    './index.html',
  ],

  /**
   * Dark mode via data attribute: data-theme="dark"
   * Applied on <html> or top-level container.
   * Instant switch (no transition) — Rule E3 from DESIGN-nextora.md
   */
  darkMode: ['class', '[data-theme="dark"]'],

  theme: {
    /**
     * ── SCREENS / BREAKPOINTS ────────────────────────────────
     * Mirrors --forge-bp-* tokens in tokens.css
     */
    screens: {
      sm:  '640px',   /* large phone / small tablet         */
      md:  '768px',   /* tablet portrait                    */
      lg:  '1024px',  /* tablet landscape / small desktop   */
      xl:  '1280px',  /* standard desktop POS terminal      */
      '2xl': '1440px',/* large desktop / wide terminal      */
      '3xl': '1920px',/* extra wide — reporting dashboards  */
    },

    /**
     * ── SPACING ──────────────────────────────────────────────
     * Base unit: 4px (0.25rem)
     * All structural layout snaps to 8px (2 units) multiples.
     * Mirrors --forge-space-* tokens.
     */
    spacing: {
      px:  '1px',
      0:   '0px',
      1:   '0.25rem',   /*  4px */
      2:   '0.5rem',    /*  8px */
      3:   '0.75rem',   /* 12px */
      4:   '1rem',      /* 16px */
      5:   '1.25rem',   /* 20px */
      6:   '1.5rem',    /* 24px */
      7:   '1.75rem',   /* 28px */
      8:   '2rem',      /* 32px */
      9:   '2.25rem',   /* 36px */
      10:  '2.5rem',    /* 40px */
      11:  '2.75rem',   /* 44px — touch target min  */
      12:  '3rem',      /* 48px — touch target pref */
      14:  '3.5rem',    /* 56px */
      16:  '4rem',      /* 64px */
      20:  '5rem',      /* 80px — marketing only    */
      24:  '6rem',      /* 96px */
      32:  '8rem',      /* 128px */
      40:  '10rem',     /* 160px */
      48:  '12rem',     /* 192px */
      64:  '16rem',     /* 256px */
    },

    /**
     * ── BORDER RADIUS ────────────────────────────────────────
     * Three semantic radii + none.
     * Mirrors --forge-radius-* tokens.
     * Rule: radius communicates interaction type.
     *   sharp → data / status
     *   card  → container / panel
     *   pill  → primary action
     */
    borderRadius: {
      none:  '0px',
      sharp: '0.25rem',  /*  4px — badges, inputs, data rows */
      card:  '0.5rem',   /*  8px — cards, panels, modals     */
      lg:    '0.75rem',  /* 12px — larger containers         */
      pill:  '9999px',   /* pill — buttons, chips, search    */
      full:  '9999px',   /* circle — icon buttons            */
    },

    extend: {
      /**
       * ── COLORS ─────────────────────────────────────────────
       * All colors reference CSS custom properties so that
       * dark mode tokens apply automatically via [data-theme="dark"].
       *
       * Palette families:
       *   brand     → interactive signal (Forge Indigo)
       *   semantic  → operational state (success/warning/danger/info)
       *   surface   → layout surfaces (ground/base/raised/overlay/toast)
       *   text      → typography hierarchy
       *   border    → all border/divider colors
       *   icon      → icon fill/stroke colors
       *   data      → chart / graph series colors
       *   primitive → raw hex palette (rarely used directly)
       */
      colors: {

        /* ── BRAND ────────────────────────────────── */
        brand: {
          DEFAULT:   'var(--forge-color-brand-default)',
          hover:     'var(--forge-color-brand-hover)',
          pressed:   'var(--forge-color-brand-pressed)',
          subtle:    'var(--forge-color-brand-subtle)',
          'on-brand':'var(--forge-color-brand-on-brand)',
          'focus-ring': 'var(--forge-color-brand-focus-ring)',
          'on-dark': 'var(--forge-color-brand-on-dark)',
        },

        /* ── SEMANTIC — SUCCESS ───────────────────── */
        success: {
          DEFAULT: 'var(--forge-color-success-default)',
          subtle:  'var(--forge-color-success-subtle)',
          text:    'var(--forge-color-success-text)',
          border:  'var(--forge-color-success-border)',
          on:      'var(--forge-color-success-on)',
        },

        /* ── SEMANTIC — WARNING ───────────────────── */
        warning: {
          DEFAULT: 'var(--forge-color-warning-default)',
          subtle:  'var(--forge-color-warning-subtle)',
          text:    'var(--forge-color-warning-text)',
          border:  'var(--forge-color-warning-border)',
          on:      'var(--forge-color-warning-on)',
        },

        /* ── SEMANTIC — DANGER ────────────────────── */
        danger: {
          DEFAULT: 'var(--forge-color-danger-default)',
          subtle:  'var(--forge-color-danger-subtle)',
          text:    'var(--forge-color-danger-text)',
          border:  'var(--forge-color-danger-border)',
          on:      'var(--forge-color-danger-on)',
        },

        /* ── SEMANTIC — INFO ──────────────────────── */
        info: {
          DEFAULT: 'var(--forge-color-info-default)',
          subtle:  'var(--forge-color-info-subtle)',
          text:    'var(--forge-color-info-text)',
          border:  'var(--forge-color-info-border)',
          on:      'var(--forge-color-info-on)',
        },

        /* ── SURFACE ──────────────────────────────── */
        surface: {
          ground:     'var(--forge-color-surface-ground)',
          base:       'var(--forge-color-surface-base)',
          raised:     'var(--forge-color-surface-raised)',
          overlay:    'var(--forge-color-surface-overlay)',
          toast:      'var(--forge-color-surface-toast)',
          'toast-fg': 'var(--forge-color-surface-toast-fg)',
          sidebar:    'var(--forge-color-surface-sidebar)',
          header:     'var(--forge-color-surface-header)',
          kbd:        'var(--forge-color-surface-kbd)',
          code:       'var(--forge-color-surface-code)',
          selection:  'var(--forge-color-surface-selection)',
          'row-hover':    'var(--forge-color-surface-row-hover)',
          'row-selected': 'var(--forge-color-surface-row-selected)',
          'row-danger':   'var(--forge-color-surface-row-danger)',
        },

        /* ── TEXT ─────────────────────────────────── */
        text: {
          primary:     'var(--forge-color-text-primary)',
          body:        'var(--forge-color-text-body)',
          secondary:   'var(--forge-color-text-secondary)',
          tertiary:    'var(--forge-color-text-tertiary)',
          placeholder: 'var(--forge-color-text-placeholder)',
          disabled:    'var(--forge-color-text-disabled)',
          'on-dark':   'var(--forge-color-text-on-dark)',
          inverse:     'var(--forge-color-text-inverse)',
        },

        /* ── BORDER ───────────────────────────────── */
        border: {
          strong:   'var(--forge-color-border-strong)',
          DEFAULT:  'var(--forge-color-border-default)',
          subtle:   'var(--forge-color-border-subtle)',
          disabled: 'var(--forge-color-border-disabled)',
          focus:    'var(--forge-color-border-focus)',
          danger:   'var(--forge-color-border-danger)',
          success:  'var(--forge-color-border-success)',
          warning:  'var(--forge-color-border-warning)',
        },

        /* ── ICON ─────────────────────────────────── */
        icon: {
          primary:   'var(--forge-color-icon-primary)',
          secondary: 'var(--forge-color-icon-secondary)',
          tertiary:  'var(--forge-color-icon-tertiary)',
          disabled:  'var(--forge-color-icon-disabled)',
          'on-brand':'var(--forge-color-icon-on-brand)',
          brand:     'var(--forge-color-icon-brand)',
          success:   'var(--forge-color-icon-success)',
          warning:   'var(--forge-color-icon-warning)',
          danger:    'var(--forge-color-icon-danger)',
          info:      'var(--forge-color-icon-info)',
        },

        /* ── DATA / CHART SERIES ──────────────────── */
        data: {
          1: 'var(--forge-color-data-1)',
          2: 'var(--forge-color-data-2)',
          3: 'var(--forge-color-data-3)',
          4: 'var(--forge-color-data-4)',
          5: 'var(--forge-color-data-5)',
          6: 'var(--forge-color-data-6)',
        },

        /* ── PRIMITIVE INDIGO (raw scale) ─────────── */
        indigo: {
          50:  '#EEF1FE',
          100: '#D5DCFD',
          200: '#ABBAFB',
          300: '#8097F8',
          400: '#6580F9',
          500: '#4F6EF7',
          600: '#3D5CE5',
          700: '#2E4DD4',
          800: '#2040B0',
          900: '#152E8A',
        },

        /* ── PRIMITIVE NEUTRAL ────────────────────── */
        neutral: {
          0:   '#FFFFFF',
          50:  '#F8F8F8',
          100: '#F2F2F2',
          150: '#EBEBEB',
          200: '#E0E0E0',
          300: '#CBCBCB',
          400: '#A8A8A8',
          500: '#848484',
          600: '#5C5C5C',
          700: '#3D3D3D',
          800: '#252525',
          900: '#141414',
        },

        /* ── DARK NEUTRAL ─────────────────────────── */
        'neutral-dark': {
          0:   '#1A1A1C',
          50:  '#212124',
          100: '#2A2A2E',
          150: '#313136',
          200: '#3C3C42',
          300: '#4F4F57',
          400: '#6B6B75',
          500: '#8C8C98',
          600: '#ABABBA',
          700: '#C8C8D8',
          800: '#E0E0EE',
          900: '#F0F0F8',
        },
      },

      /**
       * ── TYPOGRAPHY ───────────────────────────────────────
       * fontFamily, fontSize, fontWeight, lineHeight,
       * letterSpacing all mirror tokens.css Section 4.
       */
      fontFamily: {
        sans: [
          'Inter',
          ...defaultTheme.fontFamily.sans,
        ],
        mono: [
          'ui-monospace',
          'Cascadia Code',
          'Fira Code',
          'JetBrains Mono',
          'Consolas',
          ...defaultTheme.fontFamily.mono,
        ],
      },

      fontSize: {
        /* 8-step Forge scale */
        'micro':   ['0.6875rem', { lineHeight: '1.27', letterSpacing: '0.02em'  }], /* 11px */
        'caption': ['0.8125rem', { lineHeight: '1.38', letterSpacing: '0.01em'  }], /* 13px */
        'body':    ['0.9375rem', { lineHeight: '1.47', letterSpacing: '0'        }], /* 15px */
        'body-lg': ['1rem',      { lineHeight: '1.47', letterSpacing: '0'        }], /* 16px */
        'h3':      ['0.9375rem', { lineHeight: '1.33', letterSpacing: '0'        }], /* 15px */
        'h2':      ['1.125rem',  { lineHeight: '1.22', letterSpacing: '-0.015em' }], /* 18px */
        'h1':      ['1.375rem',  { lineHeight: '1.18', letterSpacing: '-0.02em'  }], /* 22px */
        'display': ['1.75rem',   { lineHeight: '1.14', letterSpacing: '-0.03em'  }], /* 28px */
      },

      fontWeight: {
        regular:  '400',
        semibold: '600',
        bold:     '700',
        /* Note: 500 is intentionally absent (Forge Rule B2) */
      },

      letterSpacing: {
        tight:   '-0.03em',
        snug:    '-0.015em',
        normal:  '0em',
        wide:    '0.01em',
        wider:   '0.02em',
        widest:  '0.06em',
      },

      lineHeight: {
        tight:   '1.14',
        snug:    '1.22',
        normal:  '1.33',
        body:    '1.47',
        relaxed: '1.60',
        caption: '1.38',
        micro:   '1.27',
        none:    '1.00',
      },

      /**
       * ── SHADOWS ──────────────────────────────────────────
       * Forge uses ONE shadow for overlay-level surfaces.
       * Cards, buttons, and list rows NEVER use shadows.
       */
      boxShadow: {
        none:    'none',
        ring:    'var(--forge-shadow-ring)',
        overlay: 'var(--forge-shadow-overlay)',
        toast:   'var(--forge-shadow-toast)',
        focus:   'var(--forge-shadow-focus-ring)',
      },

      /**
       * ── BORDER WIDTH ─────────────────────────────────────
       */
      borderWidth: {
        DEFAULT:  '1px',
        0:        '0px',
        hairline: '1px',
        medium:   '1.5px',
        thick:    '2px',
        focus:    '2px',
      },

      /**
       * ── OPACITY ──────────────────────────────────────────
       */
      opacity: {
        0:        '0',
        disabled: '0.40',
        overlay:  '0.50',
        scrim:    '0.60',
        muted:    '0.72',
        subtle:   '0.85',
        100:      '1',
      },

      /**
       * ── Z-INDEX ──────────────────────────────────────────
       */
      zIndex: {
        below:     '-1',
        base:      '0',
        raised:    '1',
        sticky:    '10',
        dropdown:  '100',
        overlay:   '200',
        modal:     '300',
        toast:     '400',
        tooltip:   '500',
        debug:     '9999',
      },

      /**
       * ── TRANSITION DURATION ──────────────────────────────
       */
      transitionDuration: {
        instant:   '0ms',
        fast:      '80ms',
        standard:  '150ms',
        moderate:  '220ms',
        deliberate:'300ms',
        slow:      '500ms',
      },

      /**
       * ── TRANSITION TIMING FUNCTION ───────────────────────
       */
      transitionTimingFunction: {
        DEFAULT:   'cubic-bezier(0, 0, 0.2, 1)',
        'in':      'cubic-bezier(0.4, 0, 1, 1)',
        'out':     'cubic-bezier(0, 0, 0.2, 1)',
        'in-out':  'cubic-bezier(0.4, 0, 0.2, 1)',
        spring:    'cubic-bezier(0.34, 1.56, 0.64, 1)',
        sharp:     'cubic-bezier(0.4, 0, 0.6, 1)',
      },

      /**
       * ── ANIMATION ────────────────────────────────────────
       */
      keyframes: {
        'forge-fade-in': {
          from: { opacity: '0' },
          to:   { opacity: '1' },
        },
        'forge-fade-out': {
          from: { opacity: '1' },
          to:   { opacity: '0' },
        },
        'forge-slide-in-top': {
          from: { opacity: '0', transform: 'translateY(-8px)' },
          to:   { opacity: '1', transform: 'translateY(0)'    },
        },
        'forge-slide-in-bottom': {
          from: { opacity: '0', transform: 'translateY(8px)' },
          to:   { opacity: '1', transform: 'translateY(0)'   },
        },
        'forge-slide-in-right': {
          from: { opacity: '0', transform: 'translateX(16px)' },
          to:   { opacity: '1', transform: 'translateX(0)'    },
        },
        'forge-slide-in-left': {
          from: { opacity: '0', transform: 'translateX(-16px)' },
          to:   { opacity: '1', transform: 'translateX(0)'     },
        },
        'forge-scale-in': {
          from: { opacity: '0', transform: 'scale(0.95)' },
          to:   { opacity: '1', transform: 'scale(1)'    },
        },
        'forge-shake': {
          '0%':   { transform: 'translateX(0)'    },
          '15%':  { transform: 'translateX(-4px)' },
          '30%':  { transform: 'translateX(4px)'  },
          '45%':  { transform: 'translateX(-3px)' },
          '60%':  { transform: 'translateX(3px)'  },
          '75%':  { transform: 'translateX(-2px)' },
          '90%':  { transform: 'translateX(2px)'  },
          '100%': { transform: 'translateX(0)'    },
        },
        'forge-shimmer': {
          '0%':   { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition:  '200% 0' },
        },
        'forge-spin': {
          from: { transform: 'rotate(0deg)'   },
          to:   { transform: 'rotate(360deg)' },
        },
        'forge-pulse': {
          '0%, 100%': { opacity: '1'    },
          '50%':       { opacity: '0.45' },
        },
      },

      animation: {
        'fade-in':        'forge-fade-in var(--forge-duration-standard, 150ms) ease-out',
        'fade-out':       'forge-fade-out var(--forge-duration-standard, 150ms) ease-in',
        'slide-in-top':   'forge-slide-in-top var(--forge-duration-moderate, 220ms) ease-out',
        'slide-in-bottom':'forge-slide-in-bottom var(--forge-duration-moderate, 220ms) ease-out',
        'slide-in-right': 'forge-slide-in-right var(--forge-duration-moderate, 220ms) ease-out',
        'slide-in-left':  'forge-slide-in-left var(--forge-duration-moderate, 220ms) ease-out',
        'scale-in':       'forge-scale-in var(--forge-duration-deliberate, 300ms) ease-out',
        'shake':          'forge-shake 300ms ease-in-out',
        'shimmer':        'forge-shimmer 1.5s ease-in-out infinite',
        'spin-slow':      'forge-spin 1s linear infinite',
        'pulse-subtle':   'forge-pulse 2s ease-in-out infinite',
      },

      /**
       * ── CONTAINER WIDTHS ─────────────────────────────────
       */
      maxWidth: {
        'prose':  '65ch',
        'xs':     '480px',
        'sm':     '640px',
        'md':     '768px',
        'lg':     '1024px',
        'xl':     '1280px',
        '2xl':    '1440px',
        '3xl':    '1920px',
        /* POS zone widths */
        'context-panel':    '340px',
        'context-panel-lg': '380px',
        'context-panel-sm': '300px',
        'module-rail':      '64px',
        'module-rail-open': '220px',
      },

      minWidth: {
        'touch':  '44px',
        'touch-pref': '48px',
        'icon-target': '44px',
      },

      minHeight: {
        'touch':      '44px',
        'touch-pref': '48px',
        'top-rail':   '44px',
        'status-rail':'32px',
      },

      height: {
        'top-rail':    '44px',
        'status-rail': '32px',
        'module-rail': '64px',
        'touch':       '44px',
        'touch-pref':  '48px',
      },

      width: {
        'module-rail':      '64px',
        'module-rail-open': '220px',
        'context-panel':    '340px',
        'icon-xs':  '12px',
        'icon-sm':  '16px',
        'icon-md':  '20px',
        'icon-lg':  '24px',
        'icon-xl':  '32px',
        'icon-2xl': '48px',
      },

      /**
       * ── BACKDROP BLUR ────────────────────────────────────
       */
      backdropBlur: {
        frosted: '20px',
      },

      backdropSaturate: {
        frosted: '180%',
      },
    },
  },

  /**
   * ── PLUGINS ──────────────────────────────────────────────
   */
  plugins: [
    /**
     * Forge utilities plugin
     * Adds custom utility classes that can't be expressed
     * through theme extension alone.
     */
    function ({ addUtilities, addBase, theme }) {

      /* Tabular numbers utility — financial values */
      addUtilities({
        '.tabular-nums': {
          'font-variant-numeric': 'tabular-nums',
          'font-feature-settings': '"tnum" on, "lnum" on',
        },
        '.proportional-nums': {
          'font-variant-numeric': 'proportional-nums',
        },
        '.slashed-zero': {
          'font-variant-numeric': 'slashed-zero',
        },
      });

      /* Forge font feature sets */
      addUtilities({
        '.font-features-default': {
          'font-feature-settings': '"ss03" on, "cv11" on',
        },
        '.font-features-tabular': {
          'font-feature-settings': '"tnum" on, "ss03" on',
        },
      });

      /* Skeleton shimmer surface */
      addUtilities({
        '.skeleton': {
          'background': 'var(--forge-skeleton-gradient)',
          'background-size': '200% 100%',
          'animation': 'forge-shimmer 1.5s ease-in-out infinite',
          'border-radius': 'var(--forge-radius-sharp)',
        },
      });

      /* Frosted glass surface */
      addUtilities({
        '.frosted': {
          'backdrop-filter': 'blur(20px) saturate(180%)',
          '-webkit-backdrop-filter': 'blur(20px) saturate(180%)',
          'background-color': 'var(--forge-color-surface-overlay)',
          'opacity': 'var(--forge-opacity-frosted-light)',
        },
        '.frosted-dark': {
          'backdrop-filter': 'blur(20px) saturate(180%)',
          '-webkit-backdrop-filter': 'blur(20px) saturate(180%)',
          'background-color': 'var(--forge-color-surface-overlay)',
          'opacity': 'var(--forge-opacity-frosted-dark)',
        },
      });

      /* Press confirm — universal tactile interaction */
      addUtilities({
        '.press-confirm': {
          'transition': 'transform 80ms ease-in-out',
          '&:active': {
            'transform': 'scale(0.97)',
          },
        },
        '@media (prefers-reduced-motion: reduce)': {
          '.press-confirm': {
            'transition': 'none',
            '&:active': {
              'transform': 'none',
            },
          },
        },
      });

      /* Forge focus ring — consistent across all components */
      addUtilities({
        '.forge-focus': {
          'outline': '2px solid var(--forge-color-brand-focus-ring)',
          'outline-offset': '2px',
        },
        '.forge-focus-inset': {
          'outline': '2px solid var(--forge-color-brand-focus-ring)',
          'outline-offset': '-2px',
        },
      });

      /* Disabled state */
      addUtilities({
        '.disabled-state': {
          'opacity': '0.40',
          'pointer-events': 'none',
          'cursor': 'not-allowed',
        },
      });

      /* Zone layout helpers */
      addUtilities({
        '.zone-top-rail': {
          'height': 'var(--forge-zone-top-rail-height, 44px)',
          'min-height': 'var(--forge-zone-top-rail-height, 44px)',
        },
        '.zone-status-rail': {
          'height': 'var(--forge-zone-status-rail-height, 32px)',
          'min-height': 'var(--forge-zone-status-rail-height, 32px)',
        },
        '.zone-module-rail': {
          'width': 'var(--forge-zone-module-rail-width, 64px)',
          'min-width': 'var(--forge-zone-module-rail-width, 64px)',
        },
        '.zone-context-panel': {
          'width': 'var(--forge-zone-context-panel, 340px)',
          'min-width': 'var(--forge-zone-context-panel, 340px)',
        },
      });

      /* Icon sizing */
      addUtilities({
        '.icon-xs':  { 'width': '12px', 'height': '12px', 'flex-shrink': '0' },
        '.icon-sm':  { 'width': '16px', 'height': '16px', 'flex-shrink': '0' },
        '.icon-md':  { 'width': '20px', 'height': '20px', 'flex-shrink': '0' },
        '.icon-lg':  { 'width': '24px', 'height': '24px', 'flex-shrink': '0' },
        '.icon-xl':  { 'width': '32px', 'height': '32px', 'flex-shrink': '0' },
        '.icon-2xl': { 'width': '48px', 'height': '48px', 'flex-shrink': '0' },
      });

      /* Text truncation helpers */
      addUtilities({
        '.truncate-1': {
          'overflow': 'hidden',
          'display': '-webkit-box',
          '-webkit-line-clamp': '1',
          '-webkit-box-orient': 'vertical',
        },
        '.truncate-2': {
          'overflow': 'hidden',
          'display': '-webkit-box',
          '-webkit-line-clamp': '2',
          '-webkit-box-orient': 'vertical',
        },
        '.truncate-3': {
          'overflow': 'hidden',
          'display': '-webkit-box',
          '-webkit-line-clamp': '3',
          '-webkit-box-orient': 'vertical',
        },
      });

      /* Base styles */
      addBase({
        'html': {
          'font-family': [
            'Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont',
            '"Segoe UI"', 'sans-serif',
          ].join(', '),
          'font-size': '16px',
          'font-feature-settings': '"ss03" on, "cv11" on',
          '-webkit-font-smoothing': 'antialiased',
          '-moz-osx-font-smoothing': 'grayscale',
          'text-rendering': 'optimizeLegibility',
          'color': 'var(--forge-color-text-body)',
          'background-color': 'var(--forge-color-surface-ground)',
          'accent-color': 'var(--forge-color-brand-default)',
        },
        '::selection': {
          'background-color': 'var(--forge-color-surface-selection)',
          'color': 'var(--forge-color-text-primary)',
        },
        ':focus-visible': {
          'outline': '2px solid var(--forge-color-brand-focus-ring)',
          'outline-offset': '2px',
        },
        '*, *::before, *::after': {
          'box-sizing': 'border-box',
        },
      });
    },
  ],
};
