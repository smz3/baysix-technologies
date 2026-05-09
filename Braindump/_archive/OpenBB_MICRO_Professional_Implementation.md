# OpenBB MICRO Professional Implementation Plan

**Date:** 2026-04-27  
**Status:** Strategic Blueprint  
**Objective:** Evolve the MICRO tab into a Bloomberg-grade Equity Research Terminal using the OpenBB ODP v4 platform.

---

## 1. UI/UX Architecture: The "Double-Decker" Center Column

We are moving away from a single-panel view to a stacked dual-panel architecture in the center column (`workspace/sigma-quant/src/components/intelligence/micro/MicroResearch.tsx`).

### A. Top Panel: VISUALS.HUB
A high-fidelity visualization area for trends, segments, and transcripts.
- **Navigation:** Top-level tabs `[CHART]` | `[SEGMENTS]` | `[VALUATION]` | `[ESTIMATES]` | `[TRANSCRIPT]`
- **Components:**
    - **CHART**: Advanced TradingView Candlestick Widget.
    - **SEGMENTS**: 2D Bar Charts for Revenue by Geography and Revenue by Business Line.
    - **VALUATION**: Time-series charts of Forward P/E, EV/EBITDA, and P/B multiples.
    - **ESTIMATES**: Consensus ratings (Buy/Hold/Sell) and Analyst Price Target vs. Spot.
    - **TRANSCRIPT**: AI-parsed earnings call highlights and sentiment heatmaps.

### B. Bottom Panel: STATEMENTS.ENGINE
A dedicated workspace for raw data exploration and professional ownership analysis.
- **Navigation:** Contextual Dropdowns and Sub-tabs.
- **Core Controls:**
    - **Statement Dropdown:** `[INCOME STATEMENT ▼]` | `[BALANCE SHEET ▼]` | `[CASH FLOW ▼]`
    - **Time Toggles:** `[ FY ]` `[ QTR ]` `[ TTM ]`
- **Sub-Tabs (Bottom):** `[DATA.GRID]` | `[INSIDER]` | `[OWNERSHIP]` | `[FILINGS]` | `[PEERS]` | `[QUANT.DNA]`
    - *Note:* `[QUANT.DNA]` in MICRO is for asset-level diagnostics (Sharpe, Vol, VaR). Strategy-level modelling is moved to the dedicated `QUANT.LAB` tab.

---

## 2. Professional Feature Roadmap (OpenBB Mapping)

### Phase 1: Core Fundamentals & Ownership
- **Income Statement:** `obb.equity.fundamental.income`
- **Balance Sheet:** `obb.equity.fundamental.balance`
- **Cash Flow:** `obb.equity.fundamental.cash`
- **Insider Trading:** `obb.equity.ownership.insider_trading`
- **Institutional Ownership:** `obb.equity.ownership.institutional`

### Phase 2: Estimates & Segment Analysis
- **Analyst Consensus:** `obb.equity.estimates.consensus`
- **Price Targets:** `obb.equity.estimates.price_target`
- **Revenue Segments:** `obb.equity.fundamental.revenue_per_segment`
- **Revenue Geo:** `obb.equity.fundamental.revenue_per_geography`

### Phase 3: Documents & Quantitative Diagnostics
- **SEC Filings:** `obb.equity.fundamental.filings`
- **Quant Diagnostics:** `obb.quantitative.diagnostics` (VaR, Sharpe, Volatility)
- **Factor Exposure:** `obb.equity.fundamental.famafrench` (Fama-French 3-Factor model)

---

## 3. Design Standard: "SIGMA STANDARD V2"

Strict adherence to the Emerald/Black aesthetic verified from production:
- **Palette:** 
    - Background: `#000000` (Pure Black)
    - Accents: `#10b981` (Emerald-500)
    - Borders: `border-emerald-500/10` (Subtle tint)
- **Typography:** 
    - All-caps `font-mono` for headers and labels.
    - `text-[9px]` for secondary data, `text-[11px]` for primary.
    - `tracking-[0.2em]` for all uppercase labels.
- **Interactions:**
    - Active tabs: `border-b-2 border-emerald-500` + `bg-emerald-500/5`.
    - Hover: `bg-emerald-500/10` on rows and buttons.

---

## 4. Technical Execution Plan

### A. Frontend Components (New Structure)
1. `MicroTerminal.tsx`: Main flex layout.
2. `MicroAgent.tsx`: Sidebar workflow/chat.
3. `MicroResearch.tsx`: The "Double-Decker" center column (VisualsHub + StatementsEngine).
4. `MicroScreener.tsx`: Right sidebar with Watchlist and 7 Non-Negotiable scores.

### B. API Routes (`/api/micro/*`)
- `/company`: Fetch fundamentals snapshots from Supabase.
- `/ownership`: Fetch insider/institutional data.
- `/estimates`: Fetch analyst consensus and targets.
- `/score`: Gemini scoring agent for the 7 non-negotiables.

### C. Data Ingestion (`sigma-research`)
- `openbb_fundamentals_ingest.py`: Unified script using OpenBB Python SDK to populate Supabase.
- Scheduled via Cron or manual trigger for KLSE/Global tickers.

---

## 5. Verification Checklist

- [ ] OpenBB Python SDK can fetch `MAYBANK.KL` income statement with 5 years history.
- [ ] Supabase table `fundamentals_snapshots` updated to handle JSONB for multi-year arrays.
- [ ] `VisualsHub` sub-tabs switch content without layout shift.
- [ ] `StatementsEngine` dropdown correctly updates the data grid.
- [ ] Emerald/Black aesthetic matches the Intelligence Terminal live deployment.
