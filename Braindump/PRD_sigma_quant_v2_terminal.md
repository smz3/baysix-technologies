# PRD: Sigma Quant v2.0 — Terminal Rebuild

**Date:** 2026-04-02
**Author:** Chief of Staff (AI)
**Status:** APPROVED — Sprint Active
**Target:** Job application portfolio for AI Quant Developer + AI Market Analyst roles

---

## 1. Vision

Transform sigma-quant from a static backtest viewer into a **live operational trading terminal** that demonstrates:
- Real-time multi-asset market monitoring (Market Analyst JD)
- AI agent orchestration and system architecture (AI Quant Developer JD)
- Quantitative strategy testing and research capability (Both JDs)

---

## 2. Page Architecture (4 pages, 1 new default)

### 2a. INTELLIGENCE (New Default `/`)
**Purpose:** Mini Bloomberg terminal — the hero page recruiters see first.

**Layout — 3 horizontal zones:**

```
Zone 1: MARKET DATA (top)
┌──────────────────────────────────┬──────────────────────────┐
│ MAIN CHART                       │ RIGHT PANEL              │
│ TradingView candlestick chart    │ ┌──────────────────────┐ │
│ (lightweight-charts library)     │ │ WATCHLIST             │ │
│                                  │ │ 8 rows: symbol,      │ │
│ Tab bar: SPX BTC GOLD DXY ETH   │ │ price, change%,      │ │
│ SOL US10Y VIX                    │ │ mini sparkline        │ │
│                                  │ ├──────────────────────┤ │
│ Height: 420px                    │ │ AI REGIME             │ │
│ Background: #09090B              │ │ Badge + confidence    │ │
│                                  │ │ Narrative (2 lines)   │ │
│                                  │ │ Risk multiplier bar   │ │
│                                  │ │ "Run Analysis" btn    │ │
│                                  │ └──────────────────────┘ │
└──────────────────────────────────┴──────────────────────────┘

Zone 2: AGENT ORCHESTRATION (bottom)
┌──────────────────────┬──────────────────────────────────────┐
│ AGENT NETWORK        │ SWARM TERMINAL                       │
│ SVG: 6 nodes in      │ (existing SwarmTerminal.tsx,          │
│ hexagonal layout     │  moved from Dashboard)                │
│                      │                                       │
│ Each node: icon,     │ Terminal log feed with agent-coded    │
│ agent name, status   │ entries, auto-scroll, timestamps      │
│ dot                  │                                       │
│                      │                                       │
│ Connecting lines     │ Height: 300px                         │
│ with pulse animation │                                       │
│ (CSS keyframes)      │                                       │
│                      │                                       │
│ Width: 360px fixed   │                                       │
└──────────────────────┴──────────────────────────────────────┘
```

**Data sources:**
- `/api/market-data` — existing (prices + 24h change)
- `/api/market-data/ohlc` — NEW (OHLC candles for chart)
- `/api/macro-analysis` — existing (Groq regime classification)
- SwarmTerminal mock pipeline — existing (no API needed)

**Key interactions:**
- Click watchlist row → main chart switches to that asset
- Click "Run Analysis" → Groq macro classification runs
- Agent nodes pulse when corresponding SwarmTerminal log appears

### 2b. BACKTEST (Moved from `/` to `/backtest`)
**Purpose:** Existing backtest command center — no changes to content.

**Changes:**
- Route moves from `/` to `/backtest`
- Remove SwarmTerminal (moved to Intelligence)
- Rename in sidebar: "DASHBOARD" → "BACKTEST"

### 2c. OPERATIONS (Replaces Architecture at `/operations`)
**Purpose:** Paperclip-inspired task management and agent operations dashboard.

**Layout:**

```
Zone 1: OPS HERO STATS (top bar)
┌─────────────┬─────────────┬─────────────┬─────────────────┐
│ Active Tasks │ Completed   │ Active      │ Total API Cost  │
│     12       │    847      │ Agents: 6   │    $4.23        │
└─────────────┴─────────────┴─────────────┴─────────────────┘

Zone 2: MAIN CONTENT (two columns)
┌────────────────────────────────┬───────────────────────────┐
│ TASK BOARD                     │ AGENT ROSTER              │
│ 3 columns (not draggable):     │ 6 cards (monochrome):     │
│                                │                           │
│ BACKLOG | IN PROGRESS | DONE   │ CIO                       │
│                                │ Quant Researcher          │
│ Each card: title, agent badge, │ Quant Developer           │
│ priority pill, timestamp       │ Quant Trader              │
│                                │ Risk Manager              │
│ Data: paperclip_tasks table    │ Memory Curator            │
│ (Supabase)                     │                           │
│                                │ Each: name, role, status  │
│ Empty state if no tasks:       │ dot, task count           │
│ "No tasks in queue"            │                           │
└────────────────────────────────┴───────────────────────────┘

Zone 3: ACTIVITY FEED (full width)
┌─────────────────────────────────────────────────────────────┐
│ Agent activity log (agent_activity table)                     │
│ Each row: timestamp, agent badge, task description, cost     │
│ Chronological, newest first, max 50 entries                  │
└─────────────────────────────────────────────────────────────┘

Zone 4: PIPELINE + GATES (compact, full width)
┌─────────────────────────────────────────────────────────────┐
│ Existing pipeline flow (compact) + quality gates banner      │
└─────────────────────────────────────────────────────────────┘
```

**Data sources:**
- `paperclip_tasks` table (Supabase) — already typed in database.ts
- `agent_activity` table (Supabase) — already typed in database.ts
- Static agent roster data (existing from Architecture page)

### 2d. RESEARCH → STRATEGY EXPLORER (`/research`)
**Purpose:** Interactive strategy research and backtest comparison.

**Layout:**

```
Zone 1: PAGE HEADER + MASTER PAPER (keep existing featured card)

Zone 2: STRATEGY EXPLORER (new)
┌────────────────────────────────┬───────────────────────────┐
│ CONTROLS                       │ COMPARISON TABLE          │
│                                │                           │
│ Environment multi-select       │ Side-by-side metrics:     │
│ (checkboxes for each backtest  │ Net P&L, Win Rate,        │
│ environment from Supabase)     │ Sharpe, Max DD, Avg R,    │
│                                │ Profit Factor, Total Trds │
│ Max 3 environments selected    │                           │
│                                │ Color-coded: best = green │
│                                │                           │
└────────────────────────────────┴───────────────────────────┘

Zone 3: EQUITY CURVE OVERLAY (full width)
┌─────────────────────────────────────────────────────────────┐
│ Overlaid equity curves for all selected environments         │
│ Different colors per environment (silver, blue, green)       │
│ Using existing EquityCurve component adapted for multi-line  │
└─────────────────────────────────────────────────────────────┘

Zone 4: FORENSIC AUDIT CARDS (keep existing 4 cards)
```

**Data sources:**
- `getAllBacktests()` — existing
- `getTradesByBacktest()` — existing (called per selected environment)
- `calculateMetrics()` — existing
- `calculateEquityCurve()` — existing

---

## 3. Design System (No Changes)

All new components follow existing tokens:
- Glass: `rgba(24,24,27,0.7)` + `backdrop-blur(55px)` + shadow
- Base: `#09090B`, Surface: `#18181B`, Elevated: `#0F0F11`
- Text: Primary `#FAFAFA`, Secondary `#A1A1AA`, Muted `#71717A`
- Semantic: Win `#22C55E`, Loss `#EF4444`, Neutral `#3B82F6`
- Monochrome card treatment: `border-subtle`, `text-silver` icons
- Fonts: Inter (sans), JetBrains Mono (mono)
- No rainbow per-card coloring

---

## 4. New Component Inventory

| Component | Page | Complexity | Notes |
|-----------|------|-----------|-------|
| `TradingViewChart.tsx` | Intelligence | L | `lightweight-charts` wrapper, useRef+useEffect pattern |
| `CompactWatchlist.tsx` | Intelligence | M | Slim 8-row ticker list, click to change chart |
| `CompactRegime.tsx` | Intelligence | S | Condensed AI regime panel for sidebar |
| `AgentNetwork.tsx` | Intelligence | M | SVG with 6 nodes + CSS pulse animations |
| `IntelligenceTerminal.tsx` | Intelligence | S | Page layout wiring existing + new components |
| `TaskBoard.tsx` | Operations | M | 3-column kanban from paperclip_tasks |
| `AgentRoster.tsx` | Operations | S | 6 cards with status + task count |
| `ActivityFeed.tsx` | Operations | S | Chronological agent_activity log |
| `OpsHeroStats.tsx` | Operations | S | 4 stat cells for task/agent metrics |
| `StrategyExplorer.tsx` | Research | M | Multi-select + comparison table |
| `EquityCurveOverlay.tsx` | Research | M | Multi-series equity chart |

**Modified existing files:**
- `Sidebar.tsx` — Update nav items and routes
- `page.tsx` (root `/`) — Swap from Dashboard to Intelligence
- `DashboardClient.tsx` — Remove SwarmTerminal import
- `globals.css` — Add pulse animation keyframes

**New API route:**
- `/api/market-data/ohlc/route.ts` — OHLC candle proxy

---

## 5. Sidebar Navigation (Updated)

| Order | Label | Route | Icon |
|-------|-------|-------|------|
| 1 | INTELLIGENCE | `/` | Radar |
| 2 | BACKTEST | `/backtest` | LayoutDashboard |
| 3 | OPERATIONS | `/operations` | Network |
| 4 | RESEARCH HUB | `/research` | Library |
| 5 | GITHUB | (external) | Github |

---

## 6. Risk & Constraints

- **OHLC API route:** Yahoo Finance chart endpoint may have intermittent issues. Graceful fallback: show "No chart data" message, watchlist still works.
- **lightweight-charts:** Not a React component — requires manual DOM management via useRef/useEffect and cleanup on unmount. Memory leak risk if not disposed properly.
- **Supabase tables may be empty:** All Operations page queries need empty-state handling.
- **No real drag-and-drop:** Kanban columns are static CSS grid, not interactive. This is acceptable for a portfolio demo.
- **Agent node animation:** Keep simple (CSS-only pulse on connecting lines). No canvas/WebGL — adds complexity without ROI.
