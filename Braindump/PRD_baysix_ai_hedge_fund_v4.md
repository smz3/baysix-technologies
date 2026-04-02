# PRD v4: Baysix — Agentic Systematic Trading Platform

**Status:** APPROVED  
**Date:** 2026-04-01  
**Supersedes:** v3.0  
**Author:** Chief of Staff

---

## 0. The Job — Why This System Exists

This system is being built to win the following role:

> **AI Quantitative Developer**
> Build and iterate AI/ML models to predict stock and crypto price movements.
> Develop quantitative trading strategies using Python.
> Analyse daily P&L — what made money, what lost money, and why.
> Monitor market-moving news (macro, Trump, crypto schemes, sentiment) and model its impact.
> Build web scrapers and data pipelines using AI tools.
> Use and guide others on AI tools (ChatGPT, Cursor, etc.)
> Comfortable building with AI — not just using it.
> Familiar with LLMs, AI coding tools, and prompt engineering.

**This platform is not a demo. It is a live, running production system that directly satisfies every line of that job description.**

| # | Job Requirement | How Baysix Delivers It |
|---|---|---|
| 1 | AI/ML models to predict price movements | XGBoost Zone Scorer + LSTM Regime Classifier trained on live B2B zone outcomes |
| 2 | Quantitative strategies in Python | `sigma_core` B2B detection engine (Cython-compiled) + SAMTC consensus |
| 3 | Analyse daily P&L — what made/lost money, why | **P&L Attribution Agent** — automated daily report mapping outcomes to zone quality + macro regime |
| 4 | Monitor macro/news/sentiment, model its impact | **Macro Researcher Agent** — FRED + NLP news pipeline → regime state machine |
| 5 | Build web scrapers and data pipelines | **Data Agent** — CCXT, yfinance, FRED, NLP news scraper, all orchestrated via LangGraph |
| 6 | Use and guide AI tools | LangGraph multi-agent orchestration with Groq + Gemini — this IS the architecture |
| 7 | Comfortable building with AI, not just using it | Autonomous research loops, self-improving ML models, zero human-in-loop on research cycles |
| 8 | Trading knowledge expected | 7-year backtested B2B strategy, live MT5 and Crypto deployment |
| 9 | LLMs, prompt engineering | Structured JSON agent protocols — Groq for speed, Gemini for large-context synthesis |

---

## 1. Core Philosophy

**The AI does not discover strategies. It learns to deploy one strategy better.**

Baysix operates on a single proprietary edge: **B2B Zone Detection** (`sigma_core`). The AI Swarm's job is to:
- Learn *which regimes* produce the highest-quality B2B setups
- Learn *which instruments* have the most reliable B2B edge
- Score individual zones before risking capital
- Attribute P&L back to zone quality scores to close the learning loop

Two layers that never blur:

| Layer | What It Does |
|---|---|
| **Deterministic Algo Layer** | Detects B2B zones, sizes positions, routes orders — sealed in `.pyd` binary |
| **AI Reasoning Layer** | Learns when/where the edge works, scores zones, attributes P&L |

---

## 2. The Unified Platform: sigma-quant

**Everything surfaces through sigma-quant** — a single Next.js + Supabase web app.

A recruiter, portfolio manager, or the user themselves visits sigma-quant and sees:
- **Swarm Terminal** — live agent research run logs (already built)
- **P&L Dashboard** — real-time performance by instrument and strategy version
- **Zone Quality Board** — ML model scores and prediction accuracy
- **Research Reports** — auto-generated macro synthesis and validation results
- **Backtest vs Live Overlay** — statistical validation (permutation/bootstrap)

---

## 3. Architecture

```
┌──────────────────────────────────────────────────────┐
│               sigma-quant (Next.js + Supabase)       │  ← Unified Showcase
│   Swarm Terminal │ P&L Dashboard │ Research Reports  │
└──────────────────────┬───────────────────────────────┘
                       │  Supabase (IPC + State Store + ML results)
┌──────────────────────▼───────────────────────────────┐
│           LangGraph Orchestrator (LOCAL → OCI later) │  ← sigma-research
│                                                       │
│  [Data Agent] → [Zone Inspector] → [Macro Research]  │
│  → [Statistical Researcher] → [ML Trainer]           │
│  → [P&L Attribution] → [Risk Manager] → [CIO]       │
└──────┬────────────────────────────┬──────────────────┘
       │ sigma_core .pyd (sealed)   │ trading_context.json → Supabase
┌──────▼──────────┐       ┌─────────▼──────────────────┐
│  sigma-crypto   │       │   sigma-mt5 (Broker VPS)   │
│  Binance Perps  │       │   MT5 EA polls Supabase    │
└─────────────────┘       └────────────────────────────┘
              Future: sigma-equities (IBKR Paper)
```

---

## 4. Infrastructure

| Component | Technology | Status | Cost |
|---|---|---|---|
| **Showcase / IPC Bus** | Supabase (existing sigma-quant project) | ✅ Active | Free |
| **Orchestrator** | Local machine (Python process) → migrate to OCI ARM later | Phase 0: Local | Free |
| **LLM — Speed** | Groq `llama-3.3-70b-versatile` | Placeholder key | Free tier |
| **LLM — Context** | Google Gemini 1.5 Flash | Placeholder key | Free tier |
| **Data** | FRED, yfinance, CCXT | Placeholder FRED key | Free |
| **Sealed Core** | `sigma_core` `.pyd` binary (CPython 3.13, AMD64) | ✅ Compiled | N/A |
| **Forex Execution** | MT5 EA on Broker VPS | Existing | Free |
| **Crypto Execution** | sigma-crypto → Binance API | Existing | Free |

> **OCI ARM Note:** Oracle Cloud ARM will be set up in a later phase. The LangGraph orchestrator runs locally first. The Supabase IPC layer means the MT5 EA and sigma-quant dashboard work regardless of where the orchestrator runs.

### Environment Variables (`.env` — placeholder format)
```env
# LLM Providers
GROQ_API_KEY=your_groq_key_here
GEMINI_API_KEY=your_gemini_key_here

# Data APIs
FRED_API_KEY=your_fred_key_here

# Supabase (reuse from sigma-quant)
NEXT_PUBLIC_SUPABASE_URL=existing_url
SUPABASE_SERVICE_ROLE_KEY=existing_key
```

---

## 5. The Two-Phase Learning System

### Phase A — Statistical Learning (Immediate)
No ML models yet. Pure statistical conditioning:
- Track every B2B zone outcome: T1 hit? T2? T3? Invalidated? Age at invalidation?
- Condition win rates on: timeframe, instrument, regime, macro state
- Output: **live regime-conditioned hit-rate tables** powering the CIO's sizing decisions

### Phase B — ML Layer (Progressive, built on Phase A data)

| Model | Input Features | Output | Job Req |
|---|---|---|---|
| **XGBoost Zone Scorer** | Zone geometry + macro context + sentiment | Quality score 0–1 | Req #1 |
| **LSTM Regime Classifier** | Multi-timeframe macro time series | Regime label + confidence | Req #1 |
| **NLP Sentiment Scorer** | News headlines (FRED text, crypto Twitter, Trump) | Sentiment score | Req #4 |
| **Online Learner** | Streaming zone outcomes | Continuous model updates | Req #7 |

**The Learning Loop:**
```
sigma_core detects zone
→ Feature vector extracted (TF, direction, macro regime, sentiment, zone age)
→ Zone deployed with base sizing × XGBoost quality score
→ Outcome tracked (T1/T2/T3/invalidated) → written to Supabase
→ P&L Attribution Agent explains daily results
→ XGBoost retrained weekly on accumulated outcome DB
→ Model improves → better zone selection next cycle
```

---

## 6. Agent Swarm

| Agent | Satisfies Job Req | Key Tools | Output |
|---|---|---|---|
| **Data Agent** | #5 (data pipelines) | CCXT, yfinance, FRED, BeautifulSoup/Playwright | Raw OHLCV + macro + news state |
| **Zone Inspector** | #2 (quant strategy) | `sigma_core.b2b` (sealed .pyd) | Active zone snapshot per instrument |
| **Macro Researcher** | #4 (macro/news monitoring) | FRED API + Gemini Flash NLP | `regime`, `yield_curve`, `macro_narrative` |
| **Sentiment Agent** | #4 (sentiment modelling) | News scraper + Groq NLP | `sentiment_score`, `risk_events` |
| **Statistical Researcher** | #1 (ML models) | Supabase zone DB + pandas/scipy | `regime_hit_rates`, `instrument_rankings` |
| **ML Trainer** | #1 (AI/ML models) | XGBoost, sklearn, optuna | Updated model artifact + validation metrics |
| **P&L Attribution Agent** | #3 (daily P&L analysis) | Supabase trade log + Groq | `pnl_report.md` — what won, lost, why |
| **Risk Manager** | #3 (risk awareness) | Supabase exposure + correlation | Modified `max_risk_pct`, `kill_switch` flag |
| **CIO (Synthesizer)** | #6 (AI orchestration) | Groq structured JSON | `trading_context.json` → Supabase |
| **Validator** | #2 (strategy validation) | scipy permutation/bootstrap | `validation_report.md` |

---

## 7. Execution Layer

### MT5 — Forex (sigma-mt5)
- EA polls Supabase every 15 min for `trading_context.json`
- Applies `instrument_rankings` (block/allow pairs)
- Applies `max_risk_pct` multiplier (0.5x → 1.5x)
- Hard kill: 5% daily drawdown, 15% monthly
- **Dead Man's Switch:** Context > 24h old → auto-drop to 0.5x sizing

### Crypto — Binance Perps (sigma-crypto)
- Python calls Binance API directly using `sigma_core.b2b` for zones
- Same `trading_context.json` overlay applied

### US Equities (Phase 8 — Future)
- IBKR TWS API, paper trading first
- B2B zones on daily/weekly equity charts
- Regime gate: only active in confirmed trending regime

---

## 8. Risk & Governance

1. **No LLM Execution rule** — LLMs generate context, never call broker APIs
2. **Two kill switches** — Local EA hard limits + AI `kill_switch` flag
3. **Sealed core rule** — `sigma_core` source never enters an LLM context window
4. **ML gate rule** — No model version deployed without passing permutation test (p < 0.05)
5. **Sizing cap** — AI multiplier bounded 0.5x → 1.5x of base math-fixed risk
6. **Full audit trail** — Every agent decision logged to Supabase, visible in sigma-quant

---

## 9. Development Roadmap

| Phase | Deliverable | Status | Satisfies Job |
|---|---|---|---|
| **Phase 1** | `sigma_core` compiled to `.pyd` binary | ✅ DONE | #2 |
| **Phase 0** | LangGraph skeleton, API clients, Supabase schema, `.env` placeholders | **NEXT** | #6, #9 |
| **Phase 2** | Data Agent + Zone Inspector + Supabase zone outcome tracking | HIGH | #2, #5 |
| **Phase 3** | Macro Researcher + Sentiment Agent + P&L Attribution | HIGH | #3, #4 |
| **Phase 4** | Statistical Researcher + regime hit-rate tables | HIGH | #1 |
| **Phase 5** | XGBoost Zone Scorer v1 (Phase B begins) | HIGH | #1 |
| **Phase 6** | MT5 + Crypto execution via Supabase trading_context | HIGH | #2 |
| **Phase 7** | Validator agent — permutation/bootstrap CI | MEDIUM | #2 |
| **Phase 8** | LSTM Regime Classifier + online learning | MEDIUM | #1 |
| **Phase 9** | sigma-equities paper trading (US Equities, IBKR) | LOW | #1, #2 |
| **Phase 10** | sigma-quant full dashboard — all panels wired | MEDIUM | Showcase |
| **Phase 11** | OCI ARM migration of orchestrator | LOW | Infrastructure |
