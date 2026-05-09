# OpenBB Integration Plan — MICRO Tab (Bloomberg ASKB for Retail)
**Date:** 2026-04-27  
**Status:** Approved, ready to build  
**Scope:** Wire the sigma-quant MICRO tab to real KLSE fundamentals data via OpenBB

---

## What Is OpenBB?

OpenBB is an open-source financial data platform ("connect once, consume everywhere"). It wraps 100+ data providers (yfinance, FMP, Intrinio, Polygon, etc.) behind a single unified Python SDK and REST API.

**Key for us:**
- Ships a production-ready **MCP server** (`openbb-mcp-server`) — Claude can query KLSE data directly in dev sessions
- Python SDK replaces the need for separate fmp_ingest.py + alpha_vantage_ingest.py scripts
- KLSE coverage via `.KL` suffix (e.g., `MAYBANK.KL`) using yfinance provider — free, no API key
- FMP provider adds deeper fundamentals (250 req/day free tier)
- Self-hosted, AGPL license — $0 for the platform itself

**GitHub:** https://github.com/OpenBB-finance/OpenBB  
**MCP docs:** https://docs.openbb.co/odp/python/extensions/interface/openbb-mcp

---

## Current MICRO Tab State

| Component | Status |
|-----------|--------|
| UI components (MicroTerminal, MicroAgent, MicroThesis, MicroSearch) | Complete — mock data only |
| API routes (`src/app/api/micro/`) | Empty — none built yet |
| Supabase schema | None yet |
| Data pipeline | None yet |

---

## OpenBB Data Coverage for the 7 Non-Negotiables

| Criterion | OpenBB Endpoint | Provider |
|-----------|----------------|----------|
| Quality of Earnings | `equity.fundamental.income` + `equity.fundamental.metrics` | yfinance / fmp |
| Growth Potential | `equity.fundamental.income_growth` | yfinance / fmp |
| Valuation | `equity.fundamental.multiples` / `equity.fundamental.ratios` | yfinance / fmp |
| Balance Sheet | `equity.fundamental.balance` + `equity.fundamental.metrics` | yfinance / fmp |
| Cash Flow | `equity.fundamental.cash` + `equity.fundamental.metrics` | yfinance / fmp |
| Management Quality | `equity.fundamental.management` (proxy — names/comp only) | fmp |
| Product Differentiation | `equity.fundamental.revenue_per_segment` (proxy) | fmp |
| Technical (price history) | `equity.price.historical` | yfinance |

**KLSE note:** yfinance covers large-cap Bursa stocks (MAYBANK, CIMB, TENAGA, PBBANK, IHH, MAXIS, AXIATA). Free, no API key required.

---

## Architecture

```
[OpenBB MCP Server] ← Claude Code dev sessions query KLSE data directly (local)
        |
[OpenBB Python SDK] → sigma-research pipeline → Supabase fundamentals_snapshots
                                                        |
                                          sigma-quant Cloudflare Edge API routes
                                                        |
                                            MICRO Tab Frontend (React)
                                            Gemini scores + thesis on top
```

---

## Phase 0 — OpenBB MCP Server Setup (30 min)

Claude Code gets live KLSE data access in every dev session. No sigma-quant code changes needed.

**Install:**
```bash
pip install openbb openbb-yfinance openbb-fmp openbb-mcp-server
```

**Test KLSE data:**
```python
from openbb import obb
metrics = obb.equity.fundamental.metrics("MAYBANK.KL", provider="yfinance").to_df()
price = obb.equity.price.historical("MAYBANK.KL", provider="yfinance", interval="1d")
```

**Add to `.claude/settings.json`:**
```json
{
  "mcpServers": {
    "openbb": {
      "command": "openbb-mcp",
      "args": ["--transport", "stdio"]
    }
  }
}
```

**Validate:** New Claude session should see `equity_fundamental_metrics` MCP tool.

---

## Phase 1 — Python SDK Pipeline (1 day)

Replaces the 3 separate ingestion scripts from the original handover plan.

### Supabase Schema
**File:** `sigma-quant/supabase/migrations/001_micro_schema.sql`

```sql
CREATE TABLE fundamentals_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticker TEXT NOT NULL,
    company_name TEXT,
    exchange TEXT,
    sector TEXT,
    price NUMERIC,
    change_pct NUMERIC,
    pe_ratio NUMERIC, fwd_pe NUMERIC, pb_ratio NUMERIC, ev_ebitda NUMERIC,
    rev_growth NUMERIC, eps_growth NUMERIC,
    gross_margin NUMERIC, op_margin NUMERIC, net_margin NUMERIC, roe NUMERIC,
    debt_to_equity NUMERIC, current_ratio NUMERIC,
    free_cashflow NUMERIC, operating_cashflow NUMERIC,
    data_source TEXT DEFAULT 'openbb_yfinance',
    fetched_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(ticker)
);

CREATE TABLE ai_scores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    snapshot_id UUID REFERENCES fundamentals_snapshots(id),
    ticker TEXT NOT NULL,
    earnings_quality NUMERIC, growth NUMERIC, valuation NUMERIC,
    balance_sheet NUMERIC, cash_flow NUMERIC, management NUMERIC,
    moat NUMERIC, composite NUMERIC,
    scored_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE watchlist (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticker TEXT NOT NULL,
    added_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(ticker)
);

-- RLS (anon key for edge routes, service role for Python pipeline)
ALTER TABLE fundamentals_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_scores ENABLE ROW LEVEL SECURITY;
ALTER TABLE watchlist ENABLE ROW LEVEL SECURITY;
CREATE POLICY "public read fundamentals" ON fundamentals_snapshots FOR SELECT USING (true);
CREATE POLICY "public read scores" ON ai_scores FOR SELECT USING (true);
CREATE POLICY "public read watchlist" ON watchlist FOR SELECT USING (true);
CREATE POLICY "public write watchlist" ON watchlist FOR ALL USING (true);
CREATE POLICY "public write scores" ON ai_scores FOR INSERT USING (true);
```

### Ingest Script
**File:** `sigma-research/pipelines/ingest/openbb_fundamentals_ingest.py`

```python
from openbb import obb
from supabase import create_client
import os

TICKERS = [
    "MAYBANK.KL", "CIMB.KL", "TENAGA.KL", "PBBANK.KL",
    "IHH.KL", "MAXIS.KL", "AXIATA.KL", "DIGI.KL"
]

def fetch_and_store(ticker: str, supabase):
    metrics = obb.equity.fundamental.metrics(ticker, provider="yfinance").to_df()
    quote   = obb.equity.price.quote(ticker, provider="yfinance").to_df()
    profile = obb.equity.profile(ticker, provider="yfinance").to_df()

    row = {
        "ticker": ticker,
        "company_name": profile["name"].iloc[0] if not profile.empty else ticker,
        "exchange": "KLSE",
        "sector": profile.get("sector", [None])[0],
        "price": quote["last_price"].iloc[0] if not quote.empty else None,
        "change_pct": quote["change_percent"].iloc[0] if not quote.empty else None,
        "pe_ratio": metrics.get("pe_ratio", [None])[0],
        "fwd_pe": metrics.get("forward_pe", [None])[0],
        "pb_ratio": metrics.get("price_to_book", [None])[0],
        "ev_ebitda": metrics.get("ev_to_ebitda", [None])[0],
        "rev_growth": metrics.get("revenue_growth", [None])[0],
        "eps_growth": metrics.get("eps_growth", [None])[0],
        "gross_margin": metrics.get("gross_profit_margin", [None])[0],
        "op_margin": metrics.get("operating_profit_margin", [None])[0],
        "roe": metrics.get("return_on_equity", [None])[0],
        "debt_to_equity": metrics.get("debt_to_equity", [None])[0],
        "current_ratio": metrics.get("current_ratio", [None])[0],
        "free_cashflow": metrics.get("free_cash_flow", [None])[0],
        "data_source": "openbb_yfinance"
    }
    supabase.table("fundamentals_snapshots").upsert(row, on_conflict="ticker").execute()
    print(f"✓ {ticker}")

if __name__ == "__main__":
    sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])
    for t in TICKERS:
        try:
            fetch_and_store(t, sb)
        except Exception as e:
            print(f"✗ {t}: {e}")
```

**requirements.txt additions:**
```
openbb>=4.0.0
openbb-yfinance>=1.0.0
openbb-fmp>=1.0.0
openbb-mcp-server>=0.1.0
```

---

## Phase 2 — Edge API Routes (1 day)

All in `sigma-quant/src/app/api/micro/`. Supabase client via `createServerClient()` from `src/lib/supabase.ts`.

| Route | Method | Logic |
|-------|--------|-------|
| `company/route.ts` | GET `?ticker=MAYBANK` | Normalize ticker → `.KL`, read `fundamentals_snapshots`, return MicroFundamentals |
| `score/route.ts` | POST `{ticker, fundamentals}` | Read snapshot → Gemini 2.0 Flash scores 7 criteria → write `ai_scores` → return MicroScores |
| `research/route.ts` | POST `{ticker, fundamentals, scores}` | Gemini thesis generation (200 words) → return `{thesis}` |
| `technical/route.ts` | GET `?ticker=MAYBANK` | Yahoo Finance 6-month OHLCV → Groq llama3 TA summary |
| `watchlist/route.ts` | GET / POST / DELETE | CRUD on `watchlist` table |

**Key env vars:** `GOOGLE_GENERATIVE_AI_API_KEY` (existing), `GROQ_API_KEY` (existing), `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`

---

## Phase 3 — Wire Frontend (1 day)

| Component | Change |
|-----------|--------|
| `MicroTerminal.tsx` | Lift state here, orchestrate 4 parallel fetches on search submit |
| `MicroSearch.tsx` | Call `/api/micro/company` + `/api/micro/score` + `/api/micro/research` in parallel |
| `MicroThesis.tsx` | Call `/api/micro/technical` on ticker change, populate TA summary below TradingView chart |
| `MicroAgent.tsx` | Show real fetch progress logs (Fetching data → Scoring → Synthesizing...) |

Orchestration pattern in MicroTerminal:
```typescript
async function analyze(rawTicker: string) {
    const t = normalizeTicker(rawTicker)  // "MAYBANK" → "MAYBANK.KL"
    setStatus('analyzing')
    const [company, scores, research, technical] = await Promise.allSettled([
        fetch(`/api/micro/company?ticker=${t}`).then(r => r.json()),
        fetch(`/api/micro/score`, { method: 'POST', body: JSON.stringify({ticker: t}) }).then(r => r.json()),
        fetch(`/api/micro/research`, { method: 'POST', body: JSON.stringify({ticker: t}) }).then(r => r.json()),
        fetch(`/api/micro/technical?ticker=${t}`).then(r => r.json()),
    ])
    // Populate state as each settles — panels render independently
    setStatus('complete')
}
```

---

## Verification Checklist

- [ ] Phase 0: `openbb-mcp` running, Claude session sees `equity_fundamental_metrics` tool, `MAYBANK.KL` returns real data
- [ ] Phase 1: `openbb_fundamentals_ingest.py` runs for 8 KLSE tickers, Supabase has non-null P/E / FCF / D/E rows
- [ ] Phase 2: `GET /api/micro/company?ticker=MAYBANK` → 200 with fundamentals JSON
- [ ] Phase 2: `POST /api/micro/score` → 7 scores returned by Gemini
- [ ] Phase 3: MICRO tab on production URL shows real analysis for MAYBANK within 6s

---

## Build Timeline

| Day | Deliverable |
|-----|-------------|
| 1 | Phase 0 — OpenBB MCP working locally, KLSE data validated |
| 2 | Phase 1 — Supabase schema live, ingest script populates 8 KLSE stocks |
| 3 | Phase 2 — 5 API routes built |
| 4-5 | Phase 3 — Frontend wired, end-to-end test on production |

---

## Notes

- **Playwright MCP** (currently downloading) — not needed for Phases 0-2, useful for Phase 3 UI testing
- **EODHD** — skip for now, validate free yfinance coverage first. Add later if KLSE fundamentals depth is insufficient for mid-caps
- **FMP free tier** — 250 req/day. Fine for 8-50 stocks fetched once/day
- **Phase 2 (PDF/document intelligence)** — unchanged from original handover plan. pdfplumber + langextract pipeline for Bursa Malaysia annual reports. Build after Phase 1 is live
