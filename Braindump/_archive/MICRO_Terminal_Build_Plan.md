# MICRO Terminal — Full Build Plan
**Date:** 2026-04-27  
**Status:** Phase 1 Complete — Phase 2 (AI Pipeline) Next  
**App:** sigma-quant Intelligence Centre → `/intelligence` → MICRO tab  
**Goal:** Bloomberg ASKB equivalent for KLSE + Global equities — type a ticker, get a structured analyst research report

---

## Current Architecture

```
[User types ticker]
        │
MicroTerminal.tsx (orchestrator)
        │
        ├── GET /api/micro/company?ticker=X  → Supabase fundamentals_snapshots
        │                                      → returns: fundamentals, statements, currency
        │
        ├── GET /api/micro/estimates?ticker=X → FMP API (live)
        │                                       → returns: analyst consensus, target price
        │
        ├── GET /api/micro/ownership?ticker=X → FMP API (live)
        │                                       → returns: insider trades, institutional holders
        │
        └── GET /api/micro/watchlist          → Supabase watchlist table
                                               → returns: saved tickers with live fundamentals
```

### Data Source Chain
```
yfinance (Python) → openbb_fundamentals_ingest.py → Supabase (fundamentals_snapshots)
                                                            │
                                                   sigma-quant edge routes
                                                            │
                                                   MICRO Tab (React)
```

---

## Phase 1 — Foundation & Data Quality ✅ COMPLETE

**Completed 2026-04-27. Build passes, zero TS errors.**

### What Was Fixed

| Issue | Fix Applied |
|-------|-------------|
| "RM MILLIONS" hardcoded for ALL tickers | Dynamic `{state.displayUnit} MILLIONS` based on currency |
| "RM RM 2.1B" double prefix on FCF | FCF now pre-formatted in route, rendered directly |
| `$` on estimates target price (wrong for KLSE) | Dynamic `{state.displayUnit}` |
| `$M` on insider trade values (wrong for KLSE) | Dynamic `{state.displayUnit}M` |
| `investorName` showed CIK numbers (US SEC ID) | Fixed field mapping → `investor.holder` (institution name) |
| `change_pct` hardcoded to `None` in ingest | Fixed → `info.get('regularMarketChangePercent')` |
| `fcf` always returned `null` from company route | Fixed → reads `free_cashflow` flat column |
| Watchlist: 15 hardcoded fake tickers | Replaced → live Supabase `watchlist` table |
| Watchlist: no click-to-analyze | Fixed → `onSearch(ticker)` prop wired |
| MAYBANK mock state loaded on tab open | Removed → initial state is empty/idle |
| MicroThesis.tsx was dead code | Integrated → now renders in CHART tab of MicroResearch |
| TradingView script in MicroResearch duplicated | Removed → MicroThesis owns TradingView |

### New Files Created (Phase 1)

| File | Purpose |
|------|---------|
| `src/app/api/micro/watchlist/route.ts` | GET / POST / DELETE watchlist (Supabase CRUD) |
| `supabase/migrations/20260427_micro_schema_patch.sql` | Adds `currency`, `display_unit`, `free_cashflow` columns |

### Files Modified (Phase 1)

| File | Change |
|------|--------|
| `sigma-research/pipelines/ingest/openbb_fundamentals_ingest.py` | Add `currency`, `display_unit`, `change_pct`, `free_cashflow` fields |
| `src/app/api/micro/company/route.ts` | Return `currency`, `displayUnit`, formatted FCF |
| `src/app/api/micro/ownership/route.ts` | Fix `investorName` field mapping |
| `src/components/intelligence/micro/MicroTypes.ts` | Add `currency`, `displayUnit` to `MicroFundamentals` + `MicroState` |
| `src/components/intelligence/micro/MicroTerminal.tsx` | Remove MAYBANK mock, add `normalizeTicker()`, clean `handleSearch` |
| `src/components/intelligence/micro/MicroWatchlist.tsx` | Full rewrite → live Supabase data + click-to-analyze |
| `src/components/intelligence/micro/MicroSearch.tsx` | Fix FCF double-RM prefix |
| `src/components/intelligence/micro/MicroStatements.tsx` | Dynamic currency labels (statements header + insider column) |
| `src/components/intelligence/micro/MicroResearch.tsx` | Import MicroThesis, replace CHART tab inline code |

### SQL Migration — Run in Supabase

**File:** `supabase/migrations/20260427_micro_schema_patch.sql`

```sql
ALTER TABLE fundamentals_snapshots
  ADD COLUMN IF NOT EXISTS currency TEXT DEFAULT 'USD',
  ADD COLUMN IF NOT EXISTS display_unit TEXT DEFAULT '$',
  ADD COLUMN IF NOT EXISTS free_cashflow NUMERIC;

CREATE POLICY IF NOT EXISTS "public write scores" ON ai_scores FOR INSERT WITH CHECK (true);
```

Run this in the Supabase SQL Editor before re-ingesting.

### Re-Run Ingest After Schema Patch

```bash
cd workspace/sigma-research
python pipelines/ingest/openbb_fundamentals_ingest.py
```

Tickers: MAYBANK.KL, CIMB.KL, PBBANK.KL, IHH.KL, TENAGA.KL, MAXIS.KL, AXIATA.KL, GENT.KL, AAPL, MSFT, GOOGL

---

## Phase 2 — AI Scoring & Research Pipeline 🔜 NEXT SESSION

**Estimate: 1 day**

Build the 3 missing AI-powered routes. These give the MICRO terminal its intelligence layer.

### Route 1: `/api/micro/score` (POST `{ticker}`)

- Read `fundamentals_snapshots` from Supabase for the ticker
- Build a structured prompt from all fundamentals data
- Call **Gemini 2.0 Flash** (`GOOGLE_GENERATIVE_AI_API_KEY` — already configured)
- Score 7 criteria on a 0-10 scale:
  1. Earnings Quality
  2. Growth Potential
  3. Valuation
  4. Balance Sheet
  5. Cash Flow
  6. Management Quality (proxy via margins + coverage ratios)
  7. Product Moat (proxy via gross margin trend)
- Compute `composite` as weighted average
- Write result to `ai_scores` table
- Return `MicroScores`

**Copy Gemini call pattern from:** `src/app/api/intelligence/brief/route.ts`

### Route 2: `/api/micro/research` (POST `{ticker}`)

- Read `fundamentals_snapshots` + latest `ai_scores` for ticker from Supabase
- Call **Gemini 2.0 Flash** for a 200-word investment thesis
- Structure: summary sentence → key strengths → key risks → outlook
- Return `{thesis: string}`
- MicroThesis.tsx will display this below the TradingView chart (already wired)

### Route 3: `/api/micro/technical` (GET `?ticker=X`)

- Fetch 6-month daily OHLCV from Yahoo Finance public `/v8/finance/chart/` endpoint
- Copy pattern from `src/app/api/market-data/route.ts`
- Pass last 20 candles to **Groq llama3-8b** (`GROQ_API_KEY` — already configured)
- Copy Groq call pattern from `src/app/api/macro-analysis/route.ts`
- Return `{trend: 'BULLISH'|'BEARISH'|'NEUTRAL', rsi: string, summary: string}`

### Updated MicroTerminal Orchestration (Phase 2)

```ts
async function handleSearch(rawTicker: string) {
    const t = normalizeTicker(rawTicker)
    // Step 1: Get fundamentals fast
    const company = await fetch(`/api/micro/company?ticker=${t}`).then(r => r.json())
    setState({ ...company, status: 'analyzing' })

    // Step 2: Fire AI routes in parallel
    const [scoreRes, researchRes, technicalRes] = await Promise.allSettled([
        fetch('/api/micro/score', { method: 'POST', body: JSON.stringify({ ticker: t }) }).then(r => r.json()),
        fetch('/api/micro/research', { method: 'POST', body: JSON.stringify({ ticker: t }) }).then(r => r.json()),
        fetch(`/api/micro/technical?ticker=${t}`).then(r => r.json()),
    ])

    // Each panel updates independently as it resolves
    if (scoreRes.status === 'fulfilled') setState(prev => ({ ...prev, scores: scoreRes.value }))
    if (researchRes.status === 'fulfilled') setState(prev => ({ ...prev, thesis: researchRes.value.thesis }))
    setState(prev => ({ ...prev, status: 'complete' }))
}
```

### Add "Add to Watchlist" Button

After analysis completes in `MicroSearchHeader.tsx`:
```tsx
{state.status === 'complete' && state.ticker && (
    <button onClick={() => addToWatchlist(state.ticker!)}>
        + ADD TO WATCHLIST
    </button>
)}
```

Call `POST /api/micro/watchlist { ticker }` then refresh watchlist.

---

## Phase 3 — Document Intelligence 🔮 FUTURE (2 weeks)

Build natural language Q&A from actual Bursa Malaysia annual reports.

### Pipeline

```
Bursa Malaysia PDF → pdfplumber (raw text) → langextract (Google, structured extraction)
    → Section chunking (512 tokens)
    → all-MiniLM-L6-v2 embedder (existing in sigma-research)
    → Qdrant sigma_micro collection (NEW — same infra as sigma_market)
```

### New Files

| File | Purpose |
|------|---------|
| `sigma-research/pipelines/ingest/pdf_ingest.py` | PDF extraction + embed + upsert to Qdrant |
| `sigma-research/scripts/ingest_filing.py` | CLI tool: `python ingest_filing.py MAYBANK_2024.pdf` |
| `sigma-quant/src/app/api/micro/query/route.ts` | NL Q&A: Qdrant RAG + Gemini synthesis + citations |

### Query Types (Phase 3)

```
"why did MAYBANK's NIM compress in Q3 2024?"
→ Groq intent extraction: { ticker: 'MAYBANK', metric: 'NIM', period: 'Q3 2024' }
→ PARALLEL: Supabase fundamentals + Qdrant sigma_micro (filing chunks) + Qdrant sigma_market (news)
→ Gemini synthesis: answer + [1][2][3] citation references
```

---

## Phase 4 — Professional UX Upgrades 🔮 FUTURE

- **VALUATION tab:** Time-series P/E, EV/EBITDA, P/B charts from FMP historical multiples
- **SEGMENTS tab:** Revenue by geography/business line from FMP (requires FMP Pro tier)
- **TRANSCRIPT tab:** Earnings call highlights — source TBD (possibly Alpha Vantage premium)
- **Pre-earnings briefing:** Automated 1-page brief on upcoming earnings
- **Sector scan:** `scan BANKING KLSE` → ranks all banking stocks by composite score
- **QUANT.DNA sub-tab:** Sharpe, VaR, volatility for the stock as an asset

---

## Data Coverage Summary

| Data Type | Source | Coverage | Status |
|-----------|--------|----------|--------|
| Income Statement (5yr) | yfinance | KLSE + Global | ✅ Live |
| Balance Sheet (5yr) | yfinance | KLSE + Global | ✅ Live |
| Cash Flow (5yr) | yfinance | KLSE + Global | ✅ Live |
| Metrics (P/E, P/B, ROE, etc.) | yfinance | KLSE + Global | ✅ Live |
| Price / Change % | yfinance | KLSE + Global | ✅ Fixed |
| Free Cash Flow | yfinance | KLSE + Global | ✅ Fixed |
| Currency (MYR/USD/SGD) | yfinance | KLSE + Global | ✅ Fixed |
| Analyst Consensus | FMP Free | Global only | ✅ Live |
| Price Targets | FMP Free | Global only | ✅ Live |
| Insider Trading | FMP Free | Global only | ✅ Live |
| Institutional Ownership | FMP Free | Global only | ✅ Fixed |
| Revenue by Segment | FMP Pro | Not included | 🔜 Phase 4 |
| AI Scores (7 criteria) | Gemini | Any ticker | 🔜 Phase 2 |
| Investment Thesis | Gemini | Any ticker | 🔜 Phase 2 |
| Technical Analysis | Groq | Any ticker | 🔜 Phase 2 |
| Annual Report Q&A | Gemini + Qdrant | Bursa Malaysia | 🔜 Phase 3 |

---

## Ticker Normalization Logic

```ts
const KLSE_KNOWN = new Set(['MAYBANK','CIMB','PBBANK','TENAGA','IHH','MAXIS','AXIATA','GENT',
  'HARTA','TOPGLOV','NESTLE','PETGAS','DIALOG','BIMB','AMMB','RHBBANK','HLBANK'])
const US_KNOWN = new Set(['AAPL','MSFT','GOOGL','AMZN','META','NVDA','TSLA','NFLX'])

function normalizeTicker(raw: string): string {
    const t = raw.trim().toUpperCase().replace(/\.KL$/, '')
    if (US_KNOWN.has(t)) return t
    if (KLSE_KNOWN.has(t)) return `${t}.KL`
    if (/^\d{4}$/.test(t)) return `${t}.KL`  // Bursa stock code
    return t
}
```

---

## Supabase Tables

### `fundamentals_snapshots` (Main data store)
```
ticker (UNIQUE) | company_name | exchange | sector | currency | display_unit
pe_ratio | fwd_pe | pb_ratio | ev_ebitda | rev_growth | eps_growth
gross_margin | op_margin | roe | debt_to_equity | current_ratio
price | change_pct | free_cashflow
income_statement (JSONB) | balance_sheet (JSONB) | cash_flow (JSONB)
insider_trading (JSONB) | institutional_ownership (JSONB) | segment_data (JSONB)
data_source | fetched_at | updated_at
```

### `ai_scores` (Gemini output — Phase 2)
```
snapshot_id (FK) | ticker | earnings_quality | growth | valuation
balance_sheet | cash_flow | management | moat | composite | scored_at
```

### `watchlist` (User saved tickers)
```
ticker (UNIQUE) | added_at
```

---

## Environment Variables Required

| Variable | Where | Status |
|----------|-------|--------|
| `NEXT_PUBLIC_SUPABASE_URL` | Cloudflare Pages + `.env.local` | ✅ Configured |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Cloudflare Pages + `.env.local` | ✅ Configured |
| `SUPABASE_SERVICE_ROLE_KEY` | `.env.local` only (Python ingest) | ✅ Configured |
| `FMP_API_KEY` | Cloudflare Pages + `.env.local` | ✅ Configured |
| `GOOGLE_GENERATIVE_AI_API_KEY` | Cloudflare Pages + `.env.local` | ✅ Exists (used by brief route) |
| `GROQ_API_KEY` | Cloudflare Pages + `.env.local` | ✅ Configured |

---

## Verification Checklist — Phase 1

### After Running SQL Migration + Re-Ingest:
- [ ] `GET /api/micro/company?ticker=MAYBANK.KL` → `currency: 'MYR'`, `displayUnit: 'RM'`, `changePct` non-null
- [ ] `GET /api/micro/company?ticker=AAPL` → `currency: 'USD'`, `displayUnit: '$'`
- [ ] `GET /api/micro/watchlist` → returns Supabase rows (not error)

### UI Checks (local: http://localhost:3000/intelligence → MICRO tab):
- [ ] Tab opens to empty/idle state (no MAYBANK pre-loaded)
- [ ] Search "MAYBANK" → statements header shows "RM MILLIONS"
- [ ] Search "AAPL" → statements header shows "$ MILLIONS"
- [ ] FCF shows "RM 2.1B" for MAYBANK (not "RM RM 2.1B")
- [ ] FCF shows "$X.XB" for AAPL
- [ ] Estimates target price uses correct currency symbol
- [ ] Insider trades VALUE column uses correct currency symbol
- [ ] Ownership shows institution names (not 4-digit CIK numbers)
- [ ] Watchlist loads from Supabase on tab open (empty or real data)
- [ ] Click watchlist item → triggers search for that ticker
- [ ] CHART tab shows TradingView widget (via MicroThesis)
- [ ] CHART tab shows thesis placeholder text below chart

---

## File Map — MICRO System

```
sigma-quant/
├── src/
│   ├── app/api/micro/
│   │   ├── company/route.ts        ← Supabase fundamentals (FIXED)
│   │   ├── estimates/route.ts      ← FMP analyst consensus (existing)
│   │   ├── ownership/route.ts      ← FMP insider + institutional (FIXED)
│   │   ├── watchlist/route.ts      ← Supabase CRUD (NEW)
│   │   ├── score/route.ts          ← Gemini scoring (PHASE 2)
│   │   ├── research/route.ts       ← Gemini thesis (PHASE 2)
│   │   └── technical/route.ts      ← Groq TA (PHASE 2)
│   │
│   └── components/intelligence/micro/
│       ├── MicroTypes.ts           ← Shared interfaces (UPDATED)
│       ├── MicroTerminal.tsx       ← Root layout + orchestration (FIXED)
│       ├── MicroSearch.tsx         ← Search input + analyst panel (FIXED)
│       ├── MicroResearch.tsx       ← Visuals: Chart/Segments/Valuation/Estimates/Transcript (FIXED)
│       ├── MicroThesis.tsx         ← TradingView chart + thesis text (INTEGRATED)
│       ├── MicroStatements.tsx     ← Financial statements grid (FIXED)
│       ├── MicroWatchlist.tsx      ← Watchlist sidebar (REWRITTEN — live data)
│       └── MicroAgent.tsx          ← Agent workflow log + chat stub
│
└── supabase/migrations/
    ├── 20260427_micro_schema.sql       ← Original 3-table schema
    └── 20260427_micro_schema_patch.sql ← Adds currency, display_unit, free_cashflow (NEW)

sigma-research/
└── pipelines/ingest/
    └── openbb_fundamentals_ingest.py   ← yfinance ingest (FIXED — currency, change_pct, fcf)
```
