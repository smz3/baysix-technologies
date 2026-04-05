# Baysix Technologies — Master Build Plan
**Version:** 3.0
**Date:** 2026-04-04
**Author:** Chief of Staff (Antigravity)
**Status:** ACTIVE — supersedes BAYSIX_BUILD_PLAN_v2.md entirely

---

## 0. Do Not Start Building Until You Have Read This Entire Document

This is the single source of truth. Do not reference v2 or the architecture discussion files.
Read sections 0–5 before touching any code.

**Who:** Syafiq M. Zin — solo founder, AI Quantitative Developer, Kuala Lumpur
**What:** Baysix Technologies — AI-native systematic trading platform
**Why:** Dual purpose — (1) live trading operation across three asset classes, (2) professional showcase for AI Quant Developer roles

---

## 1. Brand & Naming Convention (FINAL)

| Name | What It Is |
|---|---|
| **Baysix** | The software product. The platform. What the world sees. |
| **Sigma** | The proprietary trading strategy engine inside Baysix. B2B zones + SAMTC. |
| **sigma_core** | The compiled `.pyd` binary. The sealed mathematical heart of the Sigma engine. |

**Tagline:** *"Baysix — Powered by the Sigma Strategy Engine"*

**Naming rules:**
- All user-facing text, UI labels, and public documentation use "Baysix"
- "Sigma" appears as the strategy name within Baysix (e.g. "Sigma Engine", "Sigma Zones")
- `sigma_core` is internal only — never mentioned publicly, never in LLM context
- Repos: `baysix` (frontend), `baysix-backend` (FastAPI + LangGraph), `sigma-brain` (HQ, stays private)
- Old name `sigma-quant` is retired. The repo stays live during parallel build (Option C), then archived.

---

## 2. Hardware & Infrastructure Constraints

| Component | Spec | Implication |
|---|---|---|
| CPU | Intel i7-7700 @ 3.6GHz, 4 cores / 8 threads | No heavy parallel compute |
| RAM | 40GB | Supports large in-memory datasets |
| GPU | NVIDIA RTX 3060 Ti — 8GB VRAM | Gemma 3 9B Q4 fits (~6-7GB). Cannot run inference + GPU training simultaneously. |
| OS | Windows 10 Home | Ollama native (not Docker). MT5 native. |
| Budget | $0 cloud spend | Supabase free, Groq free, Gemini free, OCI Always Free |
| Storage | Standard SSD | Qdrant + model artifacts on OCI (~200GB free on OCI ARM) |

**GPU rule:** Cannot run Ollama inference AND LSTM/LoRA training simultaneously on the RTX 3060 Ti. All ML GPU training runs in scheduled windows when Ollama is idle. This is enforced by the scheduler.

---

## 3. Current State of Each Project

| Project | Status | Action |
|---|---|---|
| sigma-quant | Live at syafiqmzin-sigma-quant.pages.dev. Clean. | Keep running in parallel. Archive after Baysix Tier 0 launches. |
| sigma-brain | Pushed to GitHub (private). HQ. | Stays as-is. Source of truth for memory, agents, PRD. |
| sigma_core | ✅ COMPLETE — compiled `.pyd` binary | Sealed. Never touched again unless B2B math changes. |
| sigma-research | LangGraph skeleton (5 nodes, stubs only) | Superseded by `baysix-backend`. Do not build on it further. |
| sigma-crypto | Exists, not actively developed | Absorbed into Hyperliquid adapter in baysix-backend. |
| sigma-mt5 | MQL5 EA in live deployment | Continues as-is. Polls Supabase for signals. |
| baysix (frontend) | Does not exist yet | New Next.js 15 repo. Build this. |
| baysix-backend | Does not exist yet | New Python repo. FastAPI + LangGraph. Build this. |

---

## 4. Full Architecture

### 4.1 The Three Departments

```
┌──────────────────────────────────────────────────────────────────┐
│  FLOOR 3 — LEARNING LAB                                          │
│  Zone outcomes → Feature vectors → XGBoost → Better sizing      │
│  LSTM classifies regime → feeds zone scorer                      │
│  Gemma LoRA fine-tuned on Sigma zone reasoning (Phase 8+)        │
├──────────────────────────────────────────────────────────────────┤
│  FLOOR 2 — RESEARCH DESK                                         │
│  8 AI agents running on schedule + events                        │
│  Macro regime → Instrument selection → Risk posture              │
│  Bull/Bear debate → CIO synthesis → Daily Brief published        │
├──────────────────────────────────────────────────────────────────┤
│  FLOOR 1 — TRADING DESK                                          │
│  Sigma zones detected → ML-scored → Risk-sized → Executed        │
│  MT5 (Forex/Gold) + Hyperliquid (Crypto) + IBKR (Equities)      │
│  LangGraph writes signals. Brokers read signals. Never direct.   │
└──────────────────────────────────────────────────────────────────┘
```

### 4.2 System Architecture Diagram

```
YOUR LOCAL MACHINE (Windows)
├── MT5 EA (MQL5) — polls Supabase trading_signals, executes Forex/XAUUSD
├── IBKR TWS — equities execution (or IBKR Client Portal API on OCI later)
├── Ollama — Gemma 3 9B Q4, native install, GPU inference
└── sigma_core.pyd — sealed binary, called by MT5 EA and local scripts only

OCI ARM (Always Free — Ubuntu 22.04, always-on)
└── docker-compose.yml:
    ├── fastapi          (port 8000, internal only — never public)
    ├── qdrant           (port 6333, internal only — vector search)
    ├── hyperliquid-adapter  (crypto perps execution, polls Supabase)
    └── ibkr-adapter     (equities, if using Client Portal API)

SUPABASE (Cloud — free tier, universal bus)
├── trading_signals     (broker adapters poll this)
├── zone_outcomes       (the data flywheel — most important table)
├── model_versions      (XGBoost + LSTM artifacts and metrics)
├── agent_logs          (every agent input/output)
├── research_cycles     (cycle history, trigger type, status)
├── sector_state        (current regime, active focus instruments)
├── checkpoints         (LangGraph PostgresSaver writes here)
├── daily_brief         (CIO daily output — publicly readable)
└── public_regime_state (VIEW — computed, anon-readable, no sensitive data)

CLOUDFLARE PAGES (Free CDN)
└── Baysix Next.js 15 frontend
```

### 4.3 LLM Routing (Final)

| Agent | Model | Hosting | Reason |
|---|---|---|---|
| Data Agent | No LLM | — | Pure data fetching |
| Macro Researcher | Gemma 3 9B Q4 | Ollama (local) | Structured JSON, private, free |
| Micro Researcher | Gemma 3 9B Q4 | Ollama (local) | Zone probability estimation |
| Sentiment Agent | Gemma 3 2B Q4 | Ollama (local) | Simple classification |
| Risk Manager | Gemma 3 9B Q4 | Ollama (local) | Rule-based + narrative |
| P&L Attribution | Gemma 3 9B Q4 | Ollama (local) | Structured daily report |
| Equity Researcher | Gemini Flash | Cloud API | Long PDF context (10-K, transcripts) |
| Peer Reviewer | Groq Llama 3.3 70B | Cloud API | Strongest free reasoning model |
| CIO Synthesizer | Groq Llama 3.3 70B | Cloud API | Highest-stakes decision, low frequency |

**Local-first principle:** ~80% of agent calls go to local Gemma 3. Cloud only for highest-stakes reasoning. Ollama must be running on local machine when research cycles trigger.

**Note on model naming:** Use `gemma3:9b` in Ollama until Gemma 4 is confirmed available. Check with `ollama search gemma` when setting up.

### 4.4 Multi-Broker Architecture

```
LangGraph (OCI) → writes to Supabase trading_signals
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
    MT5 EA polls   Hyperliquid   IBKR adapter
    (local machine) adapter polls  polls
    Forex/XAUUSD    (OCI ARM)     (local/OCI)
                    Crypto perps   Equities
```

**Signal routing logic — instrument → broker mapping:**
- `XAUUSD`, `EURUSD`, `GBPUSD`, `USDJPY`, `[Forex pairs]` → MT5
- `BTC-PERP`, `ETH-PERP`, `SOL-PERP`, `[crypto perps]` → Hyperliquid
- `AAPL`, `NVDA`, `SPY`, `QQQ`, `[equity tickers]` → IBKR

**Non-negotiable rule:** LangGraph never calls broker APIs directly. It writes a signal record to Supabase. Each broker adapter is an independent service that reads from Supabase and writes its outcome back. This decouples execution from orchestration — one broker failing does not affect the others.

**IBKR:** Start with paper trading account (free, full API). Use Client Portal REST API (no TWS GUI needed) on OCI ARM when ready.

**Hyperliquid:** Python SDK (`hyperliquid-python-sdk`). Authentication via wallet private key. Runs on OCI ARM, always-on.

### 4.5 Docker Placement

```
LOCAL MACHINE (Windows) → NO Docker
├── Ollama: native install (GPU passthrough via Docker+WSL2 is slower and fragile)
├── MT5: native Windows app
├── IBKR TWS: native Windows app (if not using Client Portal API)
└── Python training scripts: run natively

OCI ARM (Linux) → YES Docker
└── docker-compose.yml manages four services:
    ├── fastapi (baysix-backend)
    ├── qdrant
    ├── hyperliquid-adapter
    └── ibkr-adapter (optional, if using Client Portal API)
    All with restart: always — auto-recover on OCI reboot
```

### 4.6 ML Training Architecture

| Model | Purpose | Trains On | Inference On | Trigger |
|---|---|---|---|---|
| **XGBoost Zone Scorer** | Score zone quality given current regime | OCI ARM (CPU — fast enough) | OCI ARM | Auto Sunday 2am + manual |
| **LSTM Regime Classifier** | Classify macro regime from time-series | Local machine (RTX 3060 Ti) | OCI ARM (artifact loaded) | Manual via Baysix Command |
| **Gemma 3 LoRA Fine-Tune** | Reason about Sigma zones with domain knowledge | Local machine (Unsloth + QLoRA) | Local Ollama (replaces base model) | Phase 8+ only |

**All training artifacts write to Supabase Storage immediately upon completion. Baysix frontend reads from Supabase. You always see results in the UI regardless of where training ran.**

**Deployment gate:** XGBoost model must pass permutation test (p < 0.05) before it is marked `deployed=true` in `model_versions`. The system rejects models that do not beat random chance.

### 4.7 Research Cycle — Three-Trigger Model

```
Trigger       When                              What Runs
─────────     ──────────────────────────────    ──────────────────────────────────
Scheduled     Market open (9am ET)              Full macro + micro cycle
              Every 4h during market hours      Watchlist refresh + regime check
              Market close                      P&L attribution cycle
              Sunday 2am                        XGBoost retraining job

Event-Driven  VIX > 25                          Risk-Off emergency protocol
              NFP / CPI / FOMC release          Macro event deep-dive
              Earnings surprise ≥ 5%            Equity researcher triggered
              New Sigma zone detected           Zone Inspector + XGBoost scoring
              Kill switch breached              Risk Manager emergency cycle

On-Demand     User triggers via Baysix UI       Any agent, any scope
```

---

## 5. The Data Flywheel (Most Important Component)

This is the mechanism that makes Baysix get smarter with every trade. Build this before any UI, before most agents.

```
1. sigma_core detects B2B zone
2. Zone Inspector records feature vector immediately to zone_outcomes:
   {zone_id, instrument, timeframe, direction, zone_age, touch_count,
    atr_ratio, session, macro_regime_at_entry, sentiment_score,
    ml_confidence_at_entry, entry_price, status: "open"}
3. XGBoost scores the zone → confidence written to trading_signals
4. Risk Manager applies sizing: confidence × base_size
5. Broker adapter executes
6. Zone resolves → outcome written:
   {status: "closed", outcome: "T1_hit|T2_hit|invalidated|stopped",
    r_multiple, exit_price, duration_bars, slippage}
7. Sunday 2am: XGBoost retrains on all outcomes
8. Permutation test runs → must pass p < 0.05
9. New model artifact → Supabase Storage
10. FastAPI loads new model → next zone scored with improved version
```

**This loop never stops. Every trade makes the system smarter.**

---

## 6. Database Schema (Design in Full at Phase 0)

```sql
-- THE FLYWHEEL (most important)
zone_outcomes (
    id uuid PRIMARY KEY,
    zone_id text NOT NULL,
    instrument text NOT NULL,
    timeframe text NOT NULL,
    direction text NOT NULL,          -- 'long' | 'short'
    zone_age integer,                 -- bars since zone formed
    touch_count integer,
    atr_ratio numeric,                -- zone_size / ATR
    session text,                     -- 'london' | 'ny' | 'asia'
    macro_regime_at_entry text,       -- 'risk_on' | 'risk_off' | ...
    sentiment_score numeric,
    ml_confidence_at_entry numeric,
    entry_price numeric,
    exit_price numeric,
    outcome text,                     -- 'T1_hit' | 'T2_hit' | 'stopped' | 'invalidated'
    r_multiple numeric,
    duration_bars integer,
    slippage numeric,
    broker text,                      -- 'mt5' | 'hyperliquid' | 'ibkr'
    opened_at timestamptz,
    closed_at timestamptz
)

-- SIGNAL BUS
trading_signals (
    id uuid PRIMARY KEY,
    instrument text NOT NULL,
    broker text NOT NULL,
    direction text NOT NULL,
    size numeric NOT NULL,
    stop numeric NOT NULL,
    target_1 numeric NOT NULL,
    target_2 numeric,
    ml_confidence numeric,
    regime_at_signal text,
    sigma_zone_id text,
    status text DEFAULT 'pending',    -- 'pending' | 'filled' | 'rejected' | 'cancelled'
    created_at timestamptz DEFAULT now(),
    filled_at timestamptz,
    fill_price numeric
)

-- ML MODEL REGISTRY
model_versions (
    id uuid PRIMARY KEY,
    model_type text NOT NULL,         -- 'xgboost_zone_scorer' | 'lstm_regime'
    version integer NOT NULL,
    trained_at timestamptz NOT NULL,
    training_samples integer,
    accuracy numeric,
    permutation_p_value numeric,
    deployed boolean DEFAULT false,
    artifact_path text,               -- Supabase Storage path
    feature_importances jsonb
)

-- AGENT INTELLIGENCE
agent_logs (
    id uuid PRIMARY KEY,
    cycle_id uuid,
    agent_name text NOT NULL,
    model_used text,
    input_summary text,
    output jsonb,
    tokens_used integer,
    latency_ms integer,
    created_at timestamptz DEFAULT now()
)

research_cycles (
    id uuid PRIMARY KEY,
    trigger_type text NOT NULL,       -- 'scheduled' | 'event' | 'on_demand'
    trigger_reason text,
    status text DEFAULT 'running',    -- 'running' | 'completed' | 'failed'
    started_at timestamptz DEFAULT now(),
    completed_at timestamptz
)

-- MARKET STATE
sector_state (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    macro_regime text NOT NULL,
    regime_confidence numeric,
    active_focus text[],              -- ['XAUUSD', 'BTC-PERP', 'NVDA']
    sector_rotation text,
    bull_thesis text,
    bear_thesis text,
    cio_verdict text,
    updated_at timestamptz DEFAULT now()
)

-- PUBLIC SHOWCASE (read-only view — anon role can SELECT)
CREATE VIEW public_regime_state AS
    SELECT macro_regime, regime_confidence, active_focus, updated_at
    FROM sector_state
    ORDER BY updated_at DESC
    LIMIT 1;

-- DAILY BRIEF (public — CIO output)
daily_brief (
    id uuid PRIMARY KEY,
    brief_date date NOT NULL UNIQUE,
    regime text,
    bull_case text,
    bear_case text,
    cio_verdict text,
    active_focus text[],
    published_at timestamptz DEFAULT now()
)
```

**RLS Rules:**
- `anon` role: SELECT on `public_regime_state` and `daily_brief` only
- `authenticated` role: SELECT on all tables except `trading_signals` (write-sensitive)
- `admin` role (your UID): full access to everything
- Service role (FastAPI): full access via service key, never exposed to frontend

**Keep-alive (prevent Supabase project pausing):**
```sql
-- Run once in Supabase SQL editor to set up
SELECT cron.schedule('keep-alive', '0 9 */3 * *', 'SELECT 1');
```

---

## 7. The Baysix Frontend — Five Pages

### Access Model (Three Tiers)

| Tier | Who | Pages |
|---|---|---|
| **Public (no auth)** | Anyone — employers, recruiters, the world | Home, Research Hub, Daily Brief |
| **Authenticated** | Invited viewers (recruiter, PM with a login you create) | + Intelligence, Sigma Engine, Operations |
| **Admin** | You only (Supabase admin UID claim) | + Command (triggers, kill switch, training controls) |

### The Five Pages

| Route | Name | Tier | What It Shows |
|---|---|---|---|
| `/` | **Home** | Public | Baysix brand, tagline, live regime badge (from `public_regime_state`), CTA to Research Hub and Terminal |
| `/research` | **Research Hub** | Public | SAMTC paper, backtest methodology, validated results (Sharpe, Calmar, WFO explanation), Sigma strategy overview, system architecture diagram |
| `/daily` | **Daily Brief** | Public | CIO's daily market brief — auto-published each morning by research cycle |
| `/intelligence` | **Intelligence Terminal** | Auth | Live candlestick chart, multi-asset watchlist, full regime panel, Bull/Bear debate cards, CIO narrative, live agent feed |
| `/sigma` | **Sigma Engine** | Auth | Active zones, ML confidence scores, zone outcome history, regime-conditioned edge stats |
| `/lab` | **Learning Lab** | Auth | XGBoost metrics, feature importances, LSTM accuracy, model version history, zone outcome equity curve |
| `/operations` | **Operations** | Auth | Agent swarm live status, research cycle history, system health, Supabase realtime feed |
| `/command` | **Command** | Admin | Agent trigger panel, kill switch, retraining buttons, broker adapter status, raw P&L attribution |

---

## 8. Zero-Cost Production Stack

| Layer | Technology | Cost | Notes |
|---|---|---|---|
| Frontend hosting | Cloudflare Pages | $0 | Next.js 15, global CDN |
| Database | Supabase free tier | $0 | PostgreSQL + Realtime + Auth + RLS + Edge Functions |
| Vector DB | Qdrant (Docker on OCI) | $0 | Persistent volume on OCI storage |
| Python server | OCI ARM Always Free | $0 | 4 OCPUs, 24GB RAM, 200GB storage, forever |
| Local LLM | Ollama native (Windows) | $0 | Gemma 3 9B Q4 on RTX 3060 Ti |
| Cloud LLM (fast) | Groq free tier | $0 | Llama 3.3 70B, 30 req/min |
| Cloud LLM (context) | Gemini Flash free | $0 | 1M tokens/day, long PDF context |
| Economic data | FRED API | $0 | Unlimited |
| Equity data | yfinance | $0 | Unlimited |
| Crypto data | CCXT + Hyperliquid SDK | $0 | Free market data |
| Document parsing | Docling (pip library) | $0 | IBM open source, financial PDF parsing |
| CI/CD | GitHub Actions | $0 | 2000 min/month free |

**Total monthly cost: $0.00**

---

## 9. Build Phases

### Phase 0 — Foundation (Build First. Everything Depends on This.)

- [ ] Create `baysix-backend` Python repo (FastAPI + LangGraph)
- [ ] Push `sigma-research` to private GitHub (it only exists locally — risk)
- [ ] FastAPI skeleton: `main.py`, `/health`, `/trigger`, `/agents`, CORS config
- [ ] LangGraph `PostgresSaver` checkpointer wired to Supabase direct DB URL
  - `pip install langgraph-checkpoint-postgres` (separate package — verify before wiring)
  - Use direct PostgreSQL connection string, NOT the REST API URL
- [ ] Supabase schema applied (all tables from Section 6 — design in full now, not phase by phase)
- [ ] `.env` structure locked: `SUPABASE_DB_URL`, `GROQ_API_KEY`, `GEMINI_API_KEY`, `SUPABASE_SERVICE_KEY`
- [ ] `docker-compose.yml` written for OCI: fastapi + qdrant + hyperliquid-adapter
- [ ] Supabase keep-alive cron job set up
- [ ] End-to-end smoke test: `/trigger` → LangGraph cycle → checkpoint written to Supabase ✅

### Phase 1 — sigma_core ✅ DONE

### Phase 2 — The Data Flywheel (Build Before Any Agent Logic)

- [ ] Zone outcome auto-writer: every Sigma zone that fires writes feature vector to `zone_outcomes`
- [ ] Zone outcome resolver: at trade close, writes outcome + R-multiple automatically
- [ ] This runs silently from day one, accumulating training data
- [ ] Validate: after 10 trades, confirm all records are clean and complete
- [ ] Data Agent: FRED, yfinance, CCXT pulls → structured Supabase tables
- [ ] Sector state updater: XLK/XLE/XLF relative strength → `sector_state` table

### Phase 3 — Research Agents

- [ ] Macro Researcher: Gemma 3 9B local via Ollama, structured JSON regime output
- [ ] Bull Agent + Bear Agent nodes in LangGraph (sequential first, parallel optimization later)
- [ ] Sentiment Agent: news scraper + Gemma 3 2B classifier
- [ ] Micro Researcher: zone quality in current regime
- [ ] Risk Manager: drawdown check, kill switch logic
- [ ] Peer Reviewer: Groq 70B validates research before CIO
- [ ] CIO Synthesizer: Groq 70B adjudicates, produces daily brief
- [ ] APScheduler: three-trigger model wired (scheduled + event-driven + on-demand)
- [ ] Daily brief auto-published to Supabase `daily_brief` table each morning

### Phase 4 — Equity Researcher Agent

- [ ] IBKR paper account set up, Client Portal API credentials obtained
- [ ] SEC EDGAR API integration (edgartools or direct API)
- [ ] Docling PDF parser: earnings call transcripts, 10-K, FOMC minutes → text chunks
- [ ] Chunks embedded via sentence-transformers → Qdrant ingestion
- [ ] Equity Researcher agent: queries Qdrant + runs DCF on parsed financials
- [ ] Cross-references Sigma zones on equity charts with fundamental signals

### Phase 5 — XGBoost Zone Scorer v1

- [ ] Requires Phase 2 data (minimum 200 zone records to start, 500 for production)
- [ ] Feature engineering from `zone_outcomes` table
- [ ] XGBoost training pipeline (runs on OCI ARM, CPU only)
- [ ] Permutation test gate (p < 0.05 required for deployment)
- [ ] Model artifact → Supabase Storage
- [ ] ML confidence score injected into `trading_signals` at zone detection

### Phase 6 — LSTM Regime Classifier

- [ ] Multi-timeframe macro time-series features (DXY, VIX, yield curve, credit spreads)
- [ ] LSTM training pipeline on local machine (RTX 3060 Ti, run when Ollama idle)
- [ ] Regime label added as additional feature to XGBoost zone scorer
- [ ] Inference runs on OCI ARM (loaded from Supabase Storage artifact)

### Phase 7 — P&L Attribution Agent

- [ ] Daily report: maps trade outcomes → regime → zone score → sizing decision
- [ ] Every trade gets a `logic_trace` entry (explainability / audit trail)
- [ ] Regime-conditioned hit-rate tables per instrument
- [ ] SQL joins across `zone_outcomes`, `trading_signals`, `sector_state`

### Phase 8 — Baysix Frontend (Build Last — The UI Has Real Data By Now)

- [ ] Create `baysix` Next.js 15 repo
- [ ] Supabase Auth set up: three-tier access model (public, authenticated, admin)
- [ ] Home page: brand, live regime badge from `public_regime_state`, CTA
- [ ] Research Hub: static SAMTC paper, methodology, validated backtest results
- [ ] Daily Brief: auto-renders from `daily_brief` Supabase table
- [ ] Intelligence Terminal: lightweight-charts candlestick, watchlist, regime panel, CIO narrative
- [ ] Sigma Engine: active zones, ML scores, outcome history
- [ ] Learning Lab: XGBoost metrics, feature importances, model versions
- [ ] Operations: agent swarm live feed via Supabase Realtime
- [ ] Command: trigger panel (admin only), kill switch, training buttons

### Phase 9 — Gemma 3 LoRA Fine-Tuning

- [ ] Requires Phase 2 data: 500+ zone outcomes with reasoning traces
- [ ] Fine-tuning dataset: zone context → quality reasoning → outcome
- [ ] Training via Unsloth + QLoRA (8GB VRAM compatible, RTX 3060 Ti)
- [ ] Fine-tuned model replaces base Gemma 3 9B in Macro + Micro agents

### Phase 10 — OCI ARM Migration (If Local Machine Becomes Limiting)

- [ ] FastAPI + LangGraph already in Docker on OCI from Phase 0
- [ ] Ollama inference: evaluate NIM (NVIDIA Inference Microservices) as Ollama replacement for faster CUDA optimization
- [ ] Supabase IPC bus means MT5 + frontend work regardless of where orchestrator runs

---

## 10. Key Design Principles (Non-Negotiable)

1. **The AI does not discover strategies. It learns to deploy one strategy better.**
   B2B zones are the edge. AI learns when, where, and how hard to deploy that edge.

2. **No LLM execution rule.** LLMs write to Supabase. Broker adapters read from Supabase. LLMs never call broker APIs.

3. **Build the flywheel before the agents.** Zone outcome tracking starts at Phase 2. The ML models are useless without data.

4. **Build the UI last.** By Phase 8, the system has real data, real agent outputs, real history. The UI is a window into a running system, not a mockup.

5. **Sealed core rule.** `sigma_core` source is never in any LLM context, any repo README, any public surface.

6. **PostgresSaver from Phase 0.** Cannot be retrofitted. Wire it before writing any agent node logic.

7. **RAG for text, SQL for numbers.** Qdrant is for news, research papers, alpha memos. `zone_outcomes`, prices, OHLCV — those go through Supabase SQL queries.

8. **Local-first LLM.** Route to Gemma 3 local before cloud. Cloud only for peer review and CIO synthesis.

9. **ML gate rule.** No model version deploys without permutation test p < 0.05. Enforced in code, not in process.

10. **Two kill switches always.** EA hard stop (local, MT5 side) + `kill_switch` flag in Supabase (AI side). Either one stops everything.

---

## 11. What NOT to Do

- ❌ Do NOT run Docker on your local Windows machine (GPU passthrough via WSL2 is fragile)
- ❌ Do NOT use RAG for numerical or structured data (zone outcomes, prices, win rates → SQL)
- ❌ Do NOT build the frontend before the backend has real data
- ❌ Do NOT deploy an XGBoost model that fails the permutation test
- ❌ Do NOT run Ollama inference and GPU training simultaneously (8GB VRAM)
- ❌ Do NOT expose FastAPI directly to the internet (always behind Supabase Edge Functions or OCI firewall)
- ❌ Do NOT reference sigma_core in any LLM prompt or public documentation
- ❌ Do NOT push to GitHub without verifying .env files are in .gitignore
- ❌ Do NOT build baysix-platform and sigma-quant as separate apps (they are now one: Baysix)
- ❌ Do NOT add RAGFlow — use Docling (pip library, no Docker container needed)

---

## 12. Immediate Next Actions (When Resuming)

**Step 1:** Verify environment
```powershell
docker --version        # should not be needed locally, but confirm OCI setup later
ollama --version
ollama list             # see what models are pulled
ollama pull gemma3:9b   # if not already pulled
```

**Step 2:** Get Supabase direct DB URL
- Supabase Dashboard → Settings → Database → Connection String → URI (NOT the pooler URL)
- Add to baysix-backend `.env` as `SUPABASE_DB_URL=postgresql://...`

**Step 3:** Apply Supabase schema
- Run all CREATE TABLE statements from Section 6 as a single migration
- Set up RLS policies
- Set up keep-alive cron job

**Step 4:** Create `baysix-backend` repo structure
```
baysix-backend/
├── main.py                 # FastAPI app
├── graph/
│   ├── builder.py          # LangGraph graph definition
│   └── state.py            # AgentState schema
├── agents/
│   ├── data_agent.py
│   ├── macro_researcher.py
│   ├── bull_agent.py
│   ├── bear_agent.py
│   ├── micro_researcher.py
│   ├── risk_manager.py
│   ├── peer_reviewer.py
│   └── cio_synthesizer.py
├── adapters/
│   ├── mt5_adapter.py      # polls Supabase, calls MT5 signals file
│   ├── hyperliquid.py      # polls Supabase, calls Hyperliquid SDK
│   └── ibkr.py             # polls Supabase, calls IBKR Client Portal API
├── ml/
│   ├── zone_scorer.py      # XGBoost training + inference
│   └── regime_classifier.py # LSTM training + inference
├── flywheel/
│   └── zone_tracker.py     # writes zone_outcomes records automatically
├── scheduler/
│   └── triggers.py         # APScheduler three-trigger setup
├── docker-compose.yml      # for OCI ARM deployment
├── Dockerfile
├── requirements.txt
└── .env.example
```

**Step 5:** Wire PostgresSaver checkpointer (verify exact import for installed LangGraph version first)
```bash
pip show langgraph
pip install langgraph-checkpoint-postgres
```

**Step 6:** Phase 0 smoke test — trigger a LangGraph cycle, confirm checkpoint writes to Supabase

---

## 13. Open Decisions (Resolved This Session)

| Decision | Resolution |
|---|---|
| One app or two | **ONE** — Baysix. sigma-quant runs in parallel (Option C) then archived. |
| Public vs private | Three-tier: Public (Home/Research/Daily Brief), Auth (Terminal/Sigma/Lab/Ops), Admin (Command) |
| Docker on local | **NO** — Ollama native on Windows. Docker only on OCI ARM. |
| RAGFlow | **REMOVED** — replaced by Docling Python library. Much lighter. |
| Redis/Celery | **REMOVED** — replaced by APScheduler in FastAPI + Supabase triggers. |
| Broker for crypto | **Hyperliquid** (not Binance) — decentralized, lower fees, on-chain transparency |
| Broker for equities | **IBKR** — paper account first, Client Portal API on OCI |
| Where XGBoost trains | **OCI ARM** (CPU is sufficient at this data scale) |
| Where LSTM trains | **Local machine** (RTX 3060 Ti), inference on OCI |
| UI build order | **Last** (Phase 8) — after backend has real data |
| Sigma/Baysix branding | **Baysix** is the product. **Sigma** is the strategy engine inside it. |

---

*This document is the single source of truth. v2 and all prior architecture discussion files are superseded.*
*Last updated: 2026-04-04 by Chief of Staff*
