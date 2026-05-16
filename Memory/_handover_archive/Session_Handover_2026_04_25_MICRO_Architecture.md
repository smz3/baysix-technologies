# Session Handover — 2026-04-25 (AMENDED)
## MICRO Tab: Bloomberg ASKB Architecture for APAC Equities

**Session type:** Architecture deep-dive + engineering plan finalization
**Amended:** 2026-04-25 — Antigravity (Claude Opus 4.6) architecture review applied
**Next session:** Build Phase 1 (Quantitative Screener Terminal)
**Plan file:** `C:\Users\User\.claude\plans\session-summary-sigma-quant-curious-toast.md`

---

## What Was Decided This Session

### The Big Picture
Building a Bloomberg ASKB equivalent for APAC equities (KLSE focus) inside the existing
sigma-quant Intelligence Centre. The MICRO tab under `/intelligence` becomes a
Senior Research Analyst terminal — type a company or natural language question,
get a structured research report covering 7 non-negotiables.

### Key Architectural Decisions (All Settled)

| Decision | Choice | Amendment |
|----------|--------|-----------|
| AI agents (scoring/research) | Gemini 2.0 Flash (free, 1M context) | — |
| AI agents (intent/technical) | Groq llama3-8b (existing, fast) | — |
| PDF text extraction (Phase 2) | ~~pdfplumber~~ → pdfplumber + **langextract** (Google) | CHANGED — langextract adds LLM-powered structured extraction with source grounding on top of pdfplumber raw text. |
| Document vector store | Qdrant sigma_micro (new collection, same 384-dim as sigma_market) | — |
| Structured data store | Supabase (already configured) | — |
| RAG for financial statements | YES — section-chunked (512 tokens), not full document | — |
| Output UX | ~~Progressive SSE streaming~~ → **Parallel independent fetch** | CHANGED — SSE unreliable on Cloudflare Pages. |
| Fundamentals Source | yfinance → **FMP + Alpha Vantage + Bursa RSS** | **NEW** — FMP for 5yr history, Alpha Vantage for sentiment, Bursa RSS for real-time APAC disclosures. |
| Charting Library | Static Images → **TradingView Lightweight Charts** | **NEW** — Interactive, high-fidelity technical analysis in the browser. |
| NASA EONET | **Integrated** | Already live in sigma-research pipelines. |
| Supabase auth model | ~~Service role key on edge~~ → **Anon key + RLS policies** | — |
| NotebookLM | NOT used — we build the same thing via Gemini API | — |
| Google Data Agent Kit | NOT used — overkill for 50 KLSE companies | — |
| LangGraph | Available in requirements.txt, not needed for Phase 1 sequential pipeline | — |

### Gemini Already Integrated
`brief/route.ts` already uses Gemini 1.5 Flash as PRIMARY (Groq is fallback).
Existing env var: `GOOGLE_GENERATIVE_AI_API_KEY` — reuse this in all new routes.

> **⚠️ ENV VAR FIX:** The original plan said `GEMINI_API_KEY`. The codebase uses
> `GOOGLE_GENERATIVE_AI_API_KEY` in `brief/route.ts:79` and `macro-analysis/route.ts:71`.
> Use `GOOGLE_GENERATIVE_AI_API_KEY` consistently. Do NOT introduce a second name.

---

## Existing Infrastructure (Do Not Rebuild)

Everything below is LIVE in sigma-research:

| Component | File | Notes |
|-----------|------|-------|
| Qdrant cloud | `pipelines/store/qdrant_store.py` | sigma_market collection, 245 docs |
| Embedder | `pipelines/embed/embedder.py` | all-MiniLM-L6-v2, 384-dim |
| Ingest pipeline | `pipelines/ingest/` | FRED, yfinance, CCXT, RSS |
| FastAPI search server | `pipelines/server.py` | POST /search, port 8080 |
| Frontend proxy | `sigma-quant/src/app/api/intelligence/search/route.ts` | proxies to Python server |

**What's missing (to build):**
- `pipelines/ingest/pdf_ingest.py` — PDF extraction pipeline
- `sigma_micro` Qdrant collection — company filings
- All `/api/micro/` routes — directory exists but empty
- All MICRO UI components — stub at IntelligenceClient.tsx:256

---

## Two-Pipeline Architecture (AMENDED)

### Pipeline 1 — Structured Analysis (Phase 1, fast path ~5-6s)
Triggered by: "analyze MAYBANK", "analyze CIMB.KL"

```
Client enters "analyze MAYBANK"
    → Client fires 4 parallel requests:
    │
    ├─ GET /api/micro/company   → reads Supabase fundamentals_snapshots
    │                             (pre-populated by scheduled Python job)
    │                             → returns immediately (< 500ms)
    │
    ├─ POST /api/micro/score    → reads snapshot from Supabase
    │                             → Gemini scores 7 criteria
    │                             → writes ai_scores, returns (~4s)
    │
    ├─ POST /api/micro/research → reads snapshot + scores
    │                             → Gemini writes thesis (~5s)
    │
    └─ POST /api/micro/technical → Yahoo Finance chart API (lightweight)
                                   → Groq TA analysis (~3s)

Total: ~5-6s (parallelized) vs 15s (serial SSE)
Each panel renders independently as its fetch resolves.
```

> **WHY NOT SSE:** Cloudflare Pages Workers buffer responses, making SSE events
> arrive in batches rather than progressively. Parallel independent fetch gives the
> same visual effect (panels appearing one by one) with no buffering issues.

### Pipeline 2 — Deep Query / Natural Language (Phase 2, ~20-30s)
Triggered by: "why did MAYBANK's NIM compress?", "what did management say about..."

```
Groq intent extraction: { ticker, metric, period, question_type }
    → PARALLEL:
    │  ├─ Supabase: fetch fundamentals for ticker/period
    │  ├─ Qdrant sigma_micro: semantic search, filter by ticker+year
    │  │    → 8-10 relevant filing chunks (~10k tokens)
    │  └─ Qdrant sigma_market: recent news for ticker
    │       → 3-5 news items
    → Gemini synthesis: answer + citations (source, section, year, page)
    → Render: ANSWER panel with inline [1][2][3] citation references
```

---

## The 7 Non-Negotiables — Data Mapping

| Criterion | Phase 1 (Multi-Source) | Phase 2 (Annual Report) |
|-----------|------------------------|------------------------|
| Quality of Earnings | FMP: `operatingMargins`, `netIncomeToCommon` | MD&A: revenue recognition, one-off items |
| Growth Potential | FMP: `revenueGrowth`, `earningsGrowth` | Business Review: strategic outlook |
| Valuation | FMP: `trailingPE`, `forwardPE`, `priceToBook` | Financial Highlights |
| Balance Sheet | FMP: `debtToEquity`, `currentRatio` | Balance sheet notes |
| Cash Flow | FMP: `freeCashflow`, `operatingCashflow` | Cash flow statement notes |
| Management Quality | Alpha Vantage: Sentiment Analysis **(PROXY)** | MD&A + Chairman's Statement **(REAL)** |
| Product Differentiation | Bursa RSS: Disclosure Type Analysis **(PROXY)** | Business Review: competitive position **(REAL)** |
| Technical Analysis | TradingView Lightweight Charts (Interactive) | N/A |
| Risk Events | NASA EONET (Live feed) | N/A |

Phase 1 UI shows `QUANT PROXY` label on Management + Product Moat scores — honest about data source.

---

## Supabase Tables to Create

```sql
fundamentals_snapshots  -- Yahoo Finance quantitative data
ai_scores               -- Gemini scoring results (linked to snapshot)
watchlist               -- User-saved companies
company_filing_sections -- PDF extracted sections (Phase 2)
```

Full schema in plan file: `C:\Users\User\.claude\plans\session-summary-sigma-quant-curious-toast.md`

---

## API Routes to Build (AMENDED)

```
sigma-quant/src/app/api/micro/
├── company/route.ts      ← reads fundamentals_snapshots from Supabase (pre-populated)
├── score/route.ts        ← Gemini scoring agent (reads snapshot, writes ai_scores)
├── research/route.ts     ← Gemini research agent + thesis
├── technical/route.ts    ← Groq TA agent (Yahoo chart API for price history only)
└── watchlist/route.ts    ← Supabase CRUD (anon key + RLS)

NOTE: query/route.ts (SSE orchestrator) is REMOVED. Client calls above routes
independently and in parallel. No server-side orchestration needed.

sigma-research/ (Phase 1 addition):
├── pipelines/ingest/fmp_ingest.py            ← FMP API (Global Fundamentals) → Supabase
├── pipelines/ingest/alpha_vantage_ingest.py  ← Alpha Vantage (Sentiment/Macro) → Supabase
├── pipelines/ingest/bursa_ingest.py          ← Scrape Bursa Announcements (Local) → Supabase
└── pipelines/ingest/eonet_ingest.py          ← NASA EONET (Physical Risk) → Supabase

sigma-research/ (Phase 2):
├── pipelines/ingest/pdf_ingest.py    ← pdfplumber (raw text) + langextract (structured extraction) + embed + upsert
└── pipelines/server.py               ← extend: add POST /micro/search
```

---

## UI Design — MICRO Terminal

The MICRO tab uses the EXACT same design language as the TERMINAL tab:
- 9px font-mono font-bold uppercase tracking-widest everywhere
- border-subtle panel separators (no rounded cards)
- Reuses existing `PanelHeader` component from TerminalView.tsx:33-44
- text-win (green #22C55E), text-loss (red), text-muted (grey)
- Progressive loading: each panel appears as its agent completes

### Layout Sketch (3-column grid)

```
┌─────────────────────────────────────────────────────────────────────────┐
│ SIGMA INTELLIGENCE   TERMINAL  ►MICRO◄  AI.DESK      STABLE-EXP 85%×1.0│
├─────────────────────────────────────────────────────────────────────────┤
│ BTC 94,200▲+1.2%  ETH 3,420▲  GOLD 3,350▲  SPY 560▲  DXY 103.2▼       │
├────────────────────┬────────────────────────────────────────────────────┤
│                    │ MAYBANK.KL  MALAYAN BANKING BERHAD  KLSE  BANKING  │
│  MICRO.SEARCH      │ RM 9.45  ▲ +0.08  (+0.85%)                        │
│  ──────────────    │ COMPOSITE:  ██████████░░░░░░  7.1/10   HOLD        │
│  SCORES             │  FUNDAMENTALS                │
│  ─────────────────  │  ──────────────────────────  │
│  EARN.QUALITY  8/10 │  P/E RATIO         12.1×     │
│  ██████████░░       │  FWD P/E           10.8×     │
│  ROE 11.2% PROXY    │  P/B RATIO          1.2×     │
│                     │  EV/EBITDA          8.4×     │
│  GROWTH        6/10 │  ──────────────────────────  │
│  ████████░░░░       │  REV GROWTH        +5.4%     │
│  EPS +3.2% YoY      │  EPS GROWTH        +3.2%     │
│                     │  GROSS MARGIN      42.1%     │
│  VALUATION     7/10 │  OP MARGIN         22.3%     │
│  █████████░░░       │  ROE               11.2%     │
│  P/E 12.1× FAIR     │  ──────────────────────────  │
│                     │  DEBT/EQUITY        0.85     │
│  BAL.SHEET     8/10 │  CURRENT RATIO      1.42     │
│  ██████████░░       │  FREE CASHFLOW    RM 2.1B    │
│  D/E 0.85 STRONG    ├──────────────────────────────┤
│                     │  THESIS                      │
│  CASH FLOW     7/10 │  ──────────────────────────  │
│  █████████░░░       │  MAYBANK is a high-quality   │
│  FCF RM 2.1B        │  ASEAN banking franchise     │
│                     │  trading at a discount to    │
│  MANAGEMENT    6/10 │  regional peers...           │
│  ████████░░░░       ├──────────────────────────────┤
│  AV SENTIMENT       │  TECHNICAL (TRADINGVIEW)     │
│                     │  ──────────────────────────  │
│  PRODUCT MOAT  6/10 │  [  TRADINGVIEW CHART HERE ] │
│  ████████░░░░       │  [  LIGHTWEIGHT WIDGET     ] │
│  BURSA DISCLOSURE   │                              │
│                     │  TREND: BULLISH  RSI: 58     │
│  COMPOSITE   7.1/10 │  SOURCE: FMP + ALPHA VANTAGE │
└────────────────────┴──────────────────────────────┘

Column 1 (fixed ~220px): MICRO.SEARCH — input bar + watchlist + query history
Column 2 (fixed ~280px): SCORES — 7 non-negotiables with ██░░ bars + source label
Column 3 (flex-1):        Top: FUNDAMENTALS (raw Yahoo Finance numbers)
                          Mid: THESIS (Gemini research narrative)
                          Bot: TECHNICAL (Groq TA analysis)
```

### Deep Query Mode (Phase 2 — same left sidebar, different right panel)

```
┌────────────────────┬──────────────────────────────────────────────────┐
│  MICRO.SEARCH      │  Q: why did MAYBANK's NIM compress in Q3 2024?   │
│  > why did         ├──────────────────────────────────────────────────┤
│    MAYBANK NIM     │  ANALYSIS                                        │
│    compress Q3?_   │                                                  │
│                    │  NIM compressed 7bps to 2.24% in Q3 2024.       │
│                    │  Primary driver: rising deposit costs as MAYBANK │
│                    │  repriced fixed deposits following BNM hold...   │
│                    │                                                  │
│                    │  ── SOURCES ──────────────────────────────────   │
│                    │  [1] Q3 2024 Quarterly Report — MD&A p.12       │
│                    │      "Net interest margin declined to 2.24%..."  │
│                    │  [2] Q3 2024 Earnings Commentary                │
│                    │      "The NIM pressure reflects our decision..." │
│                    │  [3] sigma_market: BNM Rate Decision Aug 2024   │
│                    │                                                  │
│                    │  MODEL: gemini-2.0-flash  CONFIDENCE: 88%       │
└────────────────────┴──────────────────────────────────────────────────┘
```

### Progressive Loading Sequence

```
0s   → User hits Enter
     → Company header strip appears (name + exchange)
     → Left sidebar shows "ANALYSING..."

2s   → FUNDAMENTALS panel fills (Yahoo Finance data arrives)
     → Raw numbers appear, source label: "YAHOO FINANCE"

6s   → SCORES panel fills (Gemini scoring completes)
     → Score bars animate left to right ░░░ → ████

11s  → THESIS panel fills (Research Agent completes)
     → Text appears in streaming chunks

14s  → TECHNICAL panel fills (Groq TA completes)
     → Structured table appears

15s  → Watchlist entry updates with new score
     → "─── ANALYSIS COMPLETE ───"

Loading state per panel:
│  SCORES               │
│  ── ANALYSING ──────  │  ← text-muted, subtle pulse opacity animation
```

---

## Phase Build Sequence

### Phase 1 — Quantitative Screener (START HERE)
**Estimate:** 5 days (adjusted from 3-4 after architecture review)
**Deliverable:** Full MICRO terminal working in production. Type "analyze X" → parallel-rendered structured report with 7 scores, fundamentals data, thesis, technical analysis.

Files to create (10 new, 1 edit — consolidated from original 13):

**Supabase:**
- `supabase/migrations/001_micro_schema.sql`

**API Routes (5 routes, NO SSE orchestrator):**
- `src/app/api/micro/company/route.ts` (reads Supabase, NOT Yahoo edge call)
- `src/app/api/micro/score/route.ts` (Gemini scoring)
- `src/app/api/micro/research/route.ts` (Gemini thesis)
- `src/app/api/micro/technical/route.ts` (Groq TA)
- `src/app/api/micro/watchlist/route.ts`

**UI Components (3 files, consolidated from 7):**
- `src/components/intelligence/micro/MicroTerminal.tsx` (main layout + orchestration + input)
- `src/components/intelligence/micro/MicroPanels.tsx` (Scores, Fundamentals, Thesis, Technical as named exports)
- `src/components/intelligence/micro/MicroTypes.ts` (shared types)

**Python Pipeline (4 new in sigma-research):**
- `sigma-research/pipelines/ingest/fmp_ingest.py` (FMP → Supabase)
- `sigma-research/pipelines/ingest/alpha_vantage_ingest.py` (Alpha Vantage → Supabase)
- `sigma-research/pipelines/ingest/bursa_ingest.py` (Bursa Scraper → Supabase)
- `sigma-research/pipelines/ingest/eonet_ingest.py` (NASA EONET → Supabase)

**Edit:**
- `src/components/intelligence/IntelligenceClient.tsx` line 256

### Phase 2 — Document Intelligence (AMENDED)
**Estimate:** 1-2 weeks after Phase 1
**Deliverable:** Agents read actual Bursa Malaysia annual reports. Deep NL Q&A with document citations.

**Document Processing Pipeline (two-stage):**
1. **pdfplumber** — raw text extraction from Bursa Malaysia annual report PDFs
2. **langextract** (Google, `pip install langextract`) — LLM-powered structured extraction
   with source grounding. Extracts financial entities (revenue, NIM, dividends, etc.)
   and maps each to exact character position in source text.
   Uses Gemini 2.5 Flash via `GOOGLE_GENERATIVE_AI_API_KEY` (same key as Phase 1).

New files:
- `sigma-research/pipelines/ingest/pdf_ingest.py` (pdfplumber → langextract → embed → Qdrant)
- `sigma-research/scripts/ingest_filing.py` (CLI tool)
- `sigma-quant/src/components/intelligence/micro/AnswerPanel.tsx` (added to MicroPanels.tsx)
Extend: `sigma-research/pipelines/server.py` (add /micro/search)
New Qdrant collection: `sigma_micro` (384-dim, same as sigma_market)
New Python dep: `langextract>=1.2.0` in requirements.txt

### Phase 3 — Workflow Automation
Pre-earnings briefing, post-earnings anomaly detection, sector comparison table.

### Phase 4 — MCP Exposure
Expose data as MCP tools so Claude Code can query financial data directly in sessions.

---

## Supported Query Syntax (Phase 1)

```
analyze MAYBANK          → single company, structured report
analyze MAYBANK.KL       → explicit KLSE ticker
analyze 1295             → Bursa stock code (convert to .KL)
watchlist                → show all saved companies
add MAYBANK              → add to watchlist
remove CIMB              → remove from watchlist
```

Phase 2 adds:
```
why did MAYBANK's NIM drop in Q3 2024?
what did management say about dividends?
compare MAYBANK vs CIMB fee income 3 years
pre-earnings MAYBANK
post-earnings MAYBANK Q2 2025
scan banking KLSE         → sector scan (Phase 1.5)
```

---

## Environment Variables Needed (AMENDED)

| Var | Where | Status |
|-----|-------|--------|
| `GOOGLE_GENERATIVE_AI_API_KEY` | Cloudflare Pages + .env | ALREADY EXISTS — reuse existing key |
| `GROQ_API_KEY` | Already configured | DONE |
| `NEXT_PUBLIC_SUPABASE_URL` | Already in supabase.ts | NEED to add to Cloudflare env |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Already in supabase.ts | NEED to add to Cloudflare env |
| ~~`SUPABASE_SERVICE_ROLE_KEY`~~ | ~~Edge routes~~ | REMOVED from edge — use anon key + RLS instead. Service role stays in sigma-research .env only for Python pipeline writes. |
| `QDRANT_URL` | sigma-research .env | DONE (cloud instance live) |
| `QDRANT_API_KEY` | sigma-research .env | DONE |
| `LANGEXTRACT_API_KEY` | sigma-research .env (Phase 2) | NEEDED — same Gemini key, aliased for langextract |

---

## Bloomberg ASKB vs What We're Building

| Bloomberg ASKB | Our Build | Gap |
|---------------|-----------|-----|
| "Why did margins contract?" → answer from 10-K + transcripts | Phase 2: same via Qdrant sigma_micro + Gemini | Need pdf_ingest.py |
| Pre-earnings prep automated | Phase 3 | After Phase 1+2 live |
| Nowcasting via alt data | Not in scope | Bloomberg pays $millions for this |
| Sentiment from thousands of articles | sigma_market already does this | DONE |
| Natural language to financial data | Phase 1 (structured) + Phase 2 (NL Q&A) | Partially done |
| Earnings call transcript analysis | Phase 2 (if transcripts downloaded) | Need transcript source |

We're building ~80% of ASKB functionality at $0/month (free tiers) vs ~$30k/year/user for Bloomberg.

---

## Files to Reference Next Session

| File | Why |
|------|-----|
| `sigma-quant/src/components/intelligence/IntelligenceClient.tsx:256` | Wire MicroTerminal here |
| `sigma-quant/src/components/intelligence/views/TerminalView.tsx:33-44` | PanelHeader component to reuse |
| `sigma-quant/src/app/api/macro-analysis/route.ts:82-98` | Groq API call pattern to copy |
| `sigma-quant/src/app/api/intelligence/brief/route.ts` | Gemini API call pattern (primary) |
| `sigma-quant/src/app/api/market-data/route.ts:34-56` | Yahoo Finance fetch pattern |
| `sigma-quant/src/lib/supabase.ts` | `createServerClient()` for all API routes |
| `sigma-research/pipelines/embed/embedder.py` | Reuse for Phase 2 PDF embedding |
| `sigma-research/pipelines/store/qdrant_store.py` | Reuse for Phase 2 sigma_micro upsert |
| `sigma-research/pipelines/server.py` | Extend for /micro/search endpoint |
| `C:\Users\User\.claude\plans\session-summary-sigma-quant-curious-toast.md` | Full plan with SQL schema |

---

## Open Questions / Decisions Already Made

All architecture decisions are settled. No open questions remain for Phase 1.

Phase 2 decision (settled): Document processing uses **pdfplumber + langextract** pipeline.
Priority sections for Bursa Malaysia annual reports: MD&A + Business Review.
These cover Management Quality and Product Differentiation — the two criteria
that Yahoo Finance cannot provide. langextract source grounding provides citation
traceability back to exact page/character positions.

---

## Session Notes

- User wanted production-grade, not a toy. Architecture is now production-grade.
- Went through 3 iterations: Groq-only → Gemini no-RAG → Gemini + section RAG (correct)
- RAG is necessary for multi-year multi-company natural language Q&A
- Kreuzberg explored but rejected for this layer — Python pdfplumber fits existing pipeline
- Google Data Agent Kit assessed — overkill for 50 KLSE companies, not used
- NotebookLM assessed — we're building the same capability via Gemini API directly
- Qdrant/embedding infrastructure already exists in sigma-research — not rebuilding it

---

## Antigravity Architecture Review (2026-04-25)

**Reviewer:** Antigravity (Claude Opus 4.6)
**Full report:** See `micro_architecture_review.md` in conversation artifacts.

### Critical Issues Fixed in This Amendment

1. **Yahoo Finance quoteSummary on edge** — blocked by Cloudflare IPs.
   → Fixed: Pre-fetch via Python pipeline (`fundamentals_ingest.py`) to Supabase.
   Edge routes read from DB only.

2. **SSE streaming on Cloudflare Pages** — Workers buffer responses.
   → Fixed: Replaced with parallel independent `fetch()` from client.
   Same progressive UX, more reliable.

3. **Wrong env var name** — plan said `GEMINI_API_KEY`, codebase uses `GOOGLE_GENERATIVE_AI_API_KEY`.
   → Fixed: Standardized to `GOOGLE_GENERATIVE_AI_API_KEY` throughout.

4. **Service role key on edge** — security risk for portfolio showcase.
   → Fixed: Use anon key + RLS on edge. Service role stays in Python pipeline only.

### Medium Risks Addressed

5. **In-memory cache doesn't work on Cloudflare** — each request may hit different isolate.
   → Mitigated: Cache in Supabase, not in module-level variables.

6. **Component over-fragmentation** — 7 component files consolidated to 3.
   → `MicroTerminal.tsx`, `MicroPanels.tsx`, `MicroTypes.ts`

7. **15s serial pipeline** — parallelized AI calls.
   → Expected latency: ~5-6s (all agents fire simultaneously after data arrives).

### Document Intelligence Pipeline (Phase 2 — NEW)

Original plan used pdfplumber alone. Amended to use **pdfplumber + langextract**:

```
Bursa Malaysia Annual Report (PDF)
    → pdfplumber: raw text extraction (tables, paragraphs)
    → langextract (Google): structured extraction via Gemini
       - Extracts: revenue, NIM, dividends, management commentary, risk factors
       - Source grounding: maps each extraction to char_interval in source
       - Few-shot examples define schema per document type
       - Parallel chunk processing for 100+ page documents
    → Section chunking (512 tokens) for RAG
    → Embed via all-MiniLM-L6-v2 (existing embedder)
    → Upsert to Qdrant sigma_micro collection
```

Key advantage: langextract source grounding enables the Phase 2 citation system
(`[1] Q3 2024 Quarterly Report — MD&A p.12`) with exact text provenance.
