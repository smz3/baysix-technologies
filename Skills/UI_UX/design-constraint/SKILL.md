---
name: design-constraint
description: >
  Baysix design system constraints. Enforce these rules on every frontend, dashboard,
  chart, UI component, or landing page built for the Baysix hedge fund. Triggers on any
  UI/UX task — overrides generic AI design defaults with finance-grade, quant-appropriate
  standards. Works alongside ui-ux-pro-max (for palette/style lookup) and design-system
  (for token architecture). Compatible with Claude, Gemini, Cursor, Copilot, or any agent
  that reads the Skills/ directory.
---

# Baysix Design Constraint — Finance-Grade UI Standard

Enforce this on every UI task. No exceptions. The goal: no AI slop. Every interface must
look like it was built by a quant team that takes precision seriously — not a generic SaaS
template.

---

## 1. Stack — Non-Negotiable

| Layer | Choice | Reason |
|-------|--------|--------|
| Components | shadcn/ui | Production-quality, accessible, unstyled base |
| Styling | Tailwind CSS | Constraint-based, no creative drift |
| Charts | Recharts or TradingView Lightweight Charts | Finance-first, performance-safe |
| Icons | Lucide React only | Consistent stroke weight, no emoji |
| Fonts | Inter (UI) + JetBrains Mono (data/code) | Legibility at small sizes, tabular nums |

Do not reach for random component libraries, CSS frameworks, or icon sets outside this list.

---

## 2. Color System

### Dark Mode First (Primary)
Baysix interfaces default to dark mode. Finance professionals monitor screens for hours —
dark mode reduces fatigue and makes data stand out.

```css
/* Primitives */
--color-bg-base:       #0A0B0D;   /* near-black, not pure black */
--color-bg-surface:    #111318;   /* card / panel */
--color-bg-elevated:   #1A1D26;   /* modal / popover */
--color-border:        #1E2330;   /* subtle dividers */
--color-border-strong: #2A3045;   /* active borders */

/* Text */
--color-text-primary:  #E8EAF0;   /* main content */
--color-text-muted:    #6B7280;   /* labels, secondary */
--color-text-inverse:  #0A0B0D;   /* on bright backgrounds */

/* Brand */
--color-brand:         #3B82F6;   /* Baysix blue — trust, precision */
--color-brand-muted:   #1D3461;   /* hover states, rings */

/* Semantic — Finance */
--color-profit:        #22C55E;   /* green — gains, positive delta */
--color-loss:          #EF4444;   /* red — drawdown, negative delta */
--color-neutral:       #94A3B8;   /* flat, unchanged */
--color-warning:       #F59E0B;   /* alerts, kill switch proximity */
--color-critical:      #DC2626;   /* kill switch triggered, breach */

/* Chart lines */
--color-chart-1:       #3B82F6;   /* primary series */
--color-chart-2:       #8B5CF6;   /* secondary series */
--color-chart-3:       #06B6D4;   /* tertiary series */
--color-chart-4:       #F59E0B;   /* benchmark / comparison */
```

### Rules
- Never use raw hex values in components — always reference semantic tokens
- Profit/loss colors must meet WCAG 4.5:1 contrast on dark backgrounds
- Do not use green/red for anything other than P&L — use blue for actions, amber for warnings
- Never use pure white (#FFFFFF) or pure black (#000000)

---

## 3. Typography

```css
/* Scale — use only these sizes */
--text-xs:   0.625rem;  /* 10px — table micro labels */
--text-sm:   0.75rem;   /* 12px — secondary data */
--text-base: 0.875rem;  /* 14px — body default (finance UIs run smaller) */
--text-md:   1rem;      /* 16px — section headers */
--text-lg:   1.25rem;   /* 20px — page titles */
--text-xl:   1.5rem;    /* 24px — hero metrics */
--text-2xl:  2rem;      /* 32px — KPI callouts only */

/* Weight */
--font-normal:   400;
--font-medium:   500;
--font-semibold: 600;
--font-bold:     700;   /* use sparingly — signals importance */
```

### Rules
- All numeric data (P&L, prices, percentages) → JetBrains Mono with `font-variant-numeric: tabular-nums`
- Body text minimum 14px — no smaller for readable data
- Line height minimum 1.5 for prose, 1.2 acceptable for dense data tables
- Do not mix font families beyond Inter + JetBrains Mono

---

## 4. Spacing System

Use Tailwind's 4px base grid only. No arbitrary values (`p-[13px]` is banned).

```
4px   → gap-1, p-1   (icon padding)
8px   → gap-2, p-2   (tight internal)
12px  → gap-3, p-3   (card internal)
16px  → gap-4, p-4   (standard)
24px  → gap-6, p-6   (section padding)
32px  → gap-8, p-8   (panel padding)
48px  → gap-12        (major sections)
```

---

## 5. Component Rules

### Cards / Panels
```
background: var(--color-bg-surface)
border: 1px solid var(--color-border)
border-radius: 8px          ← NOT 0, NOT 16px+
padding: 16px–24px
```
No drop shadows on dark mode — use border instead.

### Data Tables
- Alternating row: `bg-surface` / `bg-elevated`
- Sticky headers always
- Right-align all numeric columns
- Monospace font for all numbers
- Sort indicators visible, not hidden-on-hover
- No horizontal scrollbar on desktop (columns must fit)

### Charts
- Always include axis labels — never rely on tooltips alone
- Zero line marked when showing delta values
- Profit fill: `rgba(34, 197, 94, 0.1)` — subtle, not saturated
- Drawdown fill: `rgba(239, 68, 68, 0.1)`
- Grid lines: `var(--color-border)`, opacity 40%
- No chart animations on data update — instant refresh only
- Legend above chart, not below

### Buttons
```
Primary:   bg-brand text-white hover:bg-brand-muted
Secondary: bg-transparent border-border text-primary hover:bg-elevated
Danger:    bg-critical text-white — only for destructive / kill switch actions
```
- Minimum touch target: 36px height (desktop finance app, not mobile-first)
- No rounded-full buttons unless it's an icon-only action

### Status Badges
```
Profit / Active:  bg-profit/10 text-profit border-profit/30
Loss / Error:     bg-loss/10 text-loss border-loss/30
Warning:          bg-warning/10 text-warning border-warning/30
Neutral / Paused: bg-muted/10 text-muted border-muted/30
```

---

## 6. Layout Patterns

### Dashboard (primary pattern)
```
┌─────────────────────────────────────────┐
│  Sidebar (240px fixed) │  Main (flex-1) │
│  - Navigation          │  - Header bar  │
│  - Strategy selector   │  - KPI row     │
│  - Risk status         │  - Charts      │
│                        │  - Tables      │
└─────────────────────────────────────────┘
```
- Sidebar collapses to 64px icon-only on narrow screens
- KPI row: max 4 metrics across — do not cram 8 numbers into one row
- Charts take minimum 60% of content area height

### KPI Cards (top row)
Each card shows: metric name (muted, 12px) → value (bold, 24px) → delta (colored, 14px)
```
┌─────────────┐
│ Sharpe      │  ← label, text-muted, text-sm
│ 1.16        │  ← value, text-2xl, font-bold
│ ▲ +0.04     │  ← delta, text-profit or text-loss
└─────────────┘
```

---

## 7. Anti-Patterns — Never Do These

| Pattern | Why banned |
|---------|------------|
| Gradient hero sections | Looks like a marketing site, not a trading system |
| Animated counters on load | Distracting, slows perceived data trust |
| Card hover lift (`translateY`) | Fine for SaaS, wrong for data-dense finance UI |
| Pastel color palettes | Low contrast, illegible on monitors |
| Emoji in the UI | Unprofessional in a trading context |
| Rounded-full cards | Bento grid aesthetic — wrong category |
| Pure white backgrounds | Eye strain on monitors |
| Sans-serif numbers in tables | Misaligned columns, hard to scan |
| Decorative illustrations | No stock art, no blob shapes, no abstract graphics |
| Auto-play chart animations | Trust issue — looks like it's fabricating movement |
| More than 3 chart series without toggle | Spaghetti chart — always add show/hide controls |

---

## 8. How to Use This Skill With ui-ux-pro-max

When asked to build or design any UI:

1. **Read this file first** — apply these constraints as hard rules
2. **Then consult `Skills/ui-ux-pro-max/`** — use it to look up specific palettes, styles, or UX guidelines that fit within these constraints
3. **Finance-matching query**: when searching ui-ux-pro-max data, filter for `product type = Trading Platform` or `FinTech` first
4. **Design system tokens**: use `Skills/design-system/` for CSS variable architecture if building a full token system

The order of precedence: **design-constraint > ui-ux-pro-max > design-system**

---

## 9. Quick Reference — Tailwind Classes

```jsx
// Card
<div className="bg-[#111318] border border-[#1E2330] rounded-lg p-6">

// KPI value
<span className="text-2xl font-bold text-[#E8EAF0] font-mono tabular-nums">

// Profit delta
<span className="text-sm text-[#22C55E]">▲ +1.2%</span>

// Loss delta
<span className="text-sm text-[#EF4444]">▼ -0.8%</span>

// Status badge — active
<span className="text-xs px-2 py-0.5 rounded bg-green-500/10 text-green-400 border border-green-500/30">
  Active
</span>

// Table number cell
<td className="text-right font-mono tabular-nums text-sm text-[#E8EAF0]">
```
