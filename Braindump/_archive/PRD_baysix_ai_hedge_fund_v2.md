# PRD: Baysix AI-Native Hedge Fund — Full Architecture Build
### Version 2.0 | Updated 2026-03-26 | Supersedes v1.0 (2026-03-12)

---

## What Changed from v1

| Area | v1 (2026-03-12) | v2 (2026-03-26) |
|------|-----------------|-----------------|
| Strategy identity | SAMTC (crypto) and B2B EA (MT5) treated as separate | **Unified: B2B Zone Detection is THE core strategy**, deployed to multiple platforms |
| Live trading | Not mentioned | **XAUUSD live on MT5** (Just Markets, semi-automated) |
| Target platforms | Crypto only, MT5 "pending" | MT5 (live) → IBKR (backtest/paper) → any platform |
| Backtest engine | Extend sigma-crypto only | **Instrument-agnostic B2B backtester** across all markets |
| sigma-quant role | "Add research report viewer" | **Full employer showcase** — agents, performance, research, architecture |
| Primary goal | Portfolio piece for jobs | **Dual: help live trading AND portfolio piece** |
| Architecture model | Three layers (research/backtest/execution) | **Four pillars** (Brain/Research/Strategy/Showcase) |

---

## Context

Baysix is an AI-native mini hedge fund with a dual purpose:
1. **Operational tool** — AI research agents that improve the founder's live XAUUSD trading decisions daily
2. **Portfolio piece** — demonstrates production-grade multi-agent AI systems for quant researcher / AI agent builder job applications

**Current state (2026-03-26):**
- Founder is live trading XAUUSD on MT5 via Just Markets (A/B book broker), semi-automated using B2B zone concepts
- sigma-crypto has a validated backtester with strong OOS results (Sharpe 1.16, Payoff 1.65, Skew 3.43)
- sigma-mt5 has V5.0 EA with pending cluster fix
- sigma-quant has 35+ forensic components deployed on Cloudflare
- sigma-brain has 11 agent definitions but agents lack data pipelines and tools
- Budget: $100/mo (Claude Code Pro). Everything else free/open-source.
- Hardware: RTX 3060+ (8GB+ VRAM), Windows 10

**The core insight**: B2B Zone Detection is one strategy applied to many markets. SAMTC is the research paper name. The MT5 EA is a deployment target. sigma-crypto's backtester is another. They share the same edge.

**Key principle:** Claude Code remains the sole orchestrator. NO LangGraph/CrewAI. sigma-research provides Python tools that Claude Code agents invoke.

---

## Four-Pillar Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    BAYSIX AI HEDGE FUND                      │
├──────────┬──────────────┬──────────────┬────────────────────┤
│  BRAIN   │  RESEARCH    │  STRATEGY    │  SHOWCASE          │
│          │              │              │                    │
│ sigma-   │ sigma-       │ sigma-crypto │ sigma-quant        │
│ brain    │ research     │ sigma-mt5    │                    │
│          │              │              │                    │
│ Claude   │ Data pipes   │ B2B Zone     │ Next.js dashboard  │
│ Code     │ Vector mem   │ Detection    │ for employers      │
│ agents   │ Local LLMs   │ Engine       │                    │
│ memory   │ Analysis     │ Backtesting  │ Agent activity     │
│ skills   │ Citations    │ Execution    │ Performance        │
│ delega-  │ Reports      │              │ Research reports   │
│ tion     │              │ MT5 (live)   │ Architecture viz   │
│          │              │ IBKR (paper) │ Risk dashboard     │
│          │              │ Crypto       │                    │
└──────────┴──────────────┴──────────────┴────────────────────┘

Data flow:
Sources → sigma-research pipelines → Parquet/Qdrant →
Agents analyze → Mathematician validates → Peer-reviewer gates →
CIO decides → Reports generated → sigma-quant displays →
Employer sees everything
```

### Pillar Responsibilities

| Pillar | Project | What It Does | Path |
|--------|---------|-------------|------|
| **Brain** | sigma-brain | Orchestration, agent definitions, memory, skills, delegation | `C:\Users\User\Desktop\sigma-brain` |
| **Research** | sigma-research | Data pipelines, analysis (macro/micro/risk), vector memory, local LLMs, citations, reports | `C:\Users\User\Desktop\sigma-research` (NEW) |
| **Strategy** | sigma-crypto, sigma-mt5 | B2B zone detection engine, backtesting, live execution | `C:\Users\User\Desktop\sigma-crypto`, `sigma-mt5` |
| **Showcase** | sigma-quant | Employer-facing web dashboard — everything visible | `C:\Users\User\Desktop\sigma-quant` |
| (Support) | sigma-linkedin | AI content manager for LinkedIn portfolio posts | `C:\Users\User\Desktop\sigma-linkedin` |

---

## The Unified Strategy: B2B Zone Detection

SAMTC (State Aware Multi Temporal Consensus) is the **research paper name** for the B2B Zone Detection strategy. The core logic is the same across all markets:

1. Detect supply/demand zones (B2B: base-to-base structural zones)
2. Multi-timeframe consensus (higher TF zones validated by lower TF entry signals)
3. State-aware filtering (regime detection gates which trades are taken)

### Deployment Targets

```
B2B Zone Detection Engine (shared Python core)
    ├── MT5 (XAUUSD live today, FX pairs, metals)
    │   └── via sigma-mt5 EA + signal bridge
    ├── Crypto (BTC/ETH/SOL perpetuals)
    │   └── via sigma-crypto backtester/execution
    ├── IBKR (equities, futures, options — paper trade first)
    │   └── via ib_insync API
    └── Future platforms as needed
```

**Current live instrument:** XAUUSD on MT5 (Just Markets, semi-automated)
**Backtest validated:** BTCUSDT (sigma-crypto, OOS Sharpe 1.16)
**Next targets:** EURUSD, GBPUSD, US30, sector ETFs — determined by backtesting B2B zones across instruments

---

## Research Philosophy (Hybrid — Three Legends)

1. **Ray Dalio layer (Macro Regime)** — Economic machine model (growth/inflation/liquidity) determines the regime. Top-level filter that gates everything below. *"If you don't understand the macro environment, you're flying blind."*

2. **Point72 layer (Sector/Instrument Selection)** — Within the regime, fundamental + quantitative analysis selects which asset classes and instruments have edge. Deep micro analysis with macro awareness. *"The edge is in the details."*

3. **Paul Tudor Jones layer (Risk Management)** — Obsessive risk management on every position. Position sizing, stop placement, correlation risk, drawdown limits. *"Losers average losers."*

---

## Part 1: sigma-research — The Research Engine

**Location:** `C:\Users\User\Desktop\sigma-research\` + junction at `workspace/sigma-research/`

```
sigma-research/
├── CLAUDE.md                     # Project instructions
├── requirements.txt              # All Python deps
├── .env.example                  # Required API keys template
├── .gitignore
├── config/
│   └── data_sources.yaml         # API endpoints, refresh schedules, symbols
├── data/
│   ├── pipelines/
│   │   ├── __init__.py
│   │   ├── fred_fetcher.py       # DXY, 10Y yield, CPI, PMI, M2, NFP, GDP
│   │   ├── yahoo_finance.py      # SPX, VIX, Gold, BTC, bonds, sector ETFs
│   │   ├── sec_edgar.py          # 10-K, 10-Q, 8-K filings (equities)
│   │   ├── crypto_data.py        # Funding rates, open interest, liquidations
│   │   ├── fixed_income.py       # Treasury yields, credit spreads, TED spread
│   │   ├── fx_data.py            # Major pairs, carry trade data, CoT reports
│   │   ├── commodities_data.py   # WTI, Gold, Copper, Ag seasonality
│   │   ├── news_fetcher.py       # Tavily free tier (1000/mo) + RSS fallback
│   │   ├── sentiment_data.py     # Fear & Greed, Google Trends, Reddit
│   │   └── openbb_bridge.py      # OpenBB SDK for unified market data
│   ├── raw/                      # Fetched data (parquet/json)
│   ├── processed/                # Cleaned, feature-engineered
│   └── cache/                    # requests-cache to avoid re-fetching
├── memory/
│   ├── __init__.py
│   ├── vector_store.py           # Qdrant CRUD wrapper
│   ├── embedder.py               # sentence-transformers (local, no API)
│   ├── citation_tracker.py       # CitationRecord for every claim
│   └── research_index.py         # Index all past research into Qdrant
├── analysis/
│   ├── macro/                    # DALIO LAYER
│   │   ├── regime_detector.py    # Economic machine: growth/inflation/liquidity state
│   │   ├── economic_calendar.py  # FOMC, CPI, NFP, ECB, BOJ schedule + impact
│   │   ├── cross_asset.py        # Rolling correlation matrix: all asset classes
│   │   ├── yield_curve.py        # Inversion detection, term premium, rate trajectory
│   │   └── liquidity_monitor.py  # M2, Fed balance sheet, TGA, RRP
│   ├── micro/                    # POINT72 LAYER
│   │   ├── zone_statistics.py    # B2B zone hit rates, touch depth, entry precision
│   │   ├── trade_forensics.py    # Post-mortem from trade logs
│   │   ├── equity_analyzer.py    # DCF, earnings, peer comp (from SEC filings)
│   │   ├── fx_analyzer.py        # Carry trade scoring, PPP, CoT positioning
│   │   ├── fi_analyzer.py        # Duration risk, credit spread analysis
│   │   ├── commodity_analyzer.py # Supply/demand, seasonality, inventory
│   │   └── signal_attribution.py # Which signals → which P&L
│   ├── risk/                     # PTJ LAYER
│   │   ├── position_sizer.py     # Kelly criterion, volatility-adjusted sizing
│   │   ├── correlation_risk.py   # Portfolio correlation, concentration limits
│   │   ├── drawdown_monitor.py   # Real-time DD tracking, kill switch triggers
│   │   └── scenario_stress.py    # What-if scenarios (rate shock, crash, etc.)
│   ├── sentiment/
│   │   ├── news_scorer.py        # Ollama classifies headlines: bull/bear/neutral
│   │   ├── fear_greed.py         # alternative.me API
│   │   └── social_pulse.py       # pytrends + Reddit sentiment
│   └── anti_hallucination.py     # Multi-source verification engine
├── b2b/                          # SHARED B2B ZONE DETECTION (NEW in v2)
│   ├── __init__.py
│   ├── zone_detector.py          # Instrument-agnostic B2B zone detection
│   ├── mtf_consensus.py          # Multi-timeframe consensus logic
│   └── backtester.py             # Unified backtester for any OHLCV data
├── reports/
│   ├── generator.py              # Jinja2 + WeasyPrint → PDF
│   ├── templates/                # Morning brief, research memo, forensic
│   └── output/                   # Generated PDFs
├── llm/
│   ├── __init__.py
│   ├── router.py                 # Claude (deep reasoning) vs Ollama (throughput)
│   ├── ollama_client.py          # localhost:11434 interface
│   └── prompts/                  # System prompts per analysis type
├── scripts/
│   ├── daily_macro_brief.py      # Morning macro scan (all macro pipelines)
│   ├── research_pipeline.py      # Full end-to-end research runner
│   └── ingest_past_research.py   # One-time: index existing papers into Qdrant
└── tests/
    ├── __init__.py
    └── test_pipelines.py
```

### Python Dependencies (all free)

```
# Data fetching
fredapi             # FRED API (free with registration)
yfinance            # Yahoo Finance (free, no key)
ccxt                # Exchange data (Binance, etc.)
openbb              # Unified market data SDK (200+ sources, free tier)
edgartools           # SEC EDGAR parser (free, government data)

# Vector memory
qdrant-client       # Vector DB client (localhost:6333)
sentence-transformers  # Local embeddings (all-MiniLM-L6-v2, 80MB)

# Local LLM
ollama              # Local LLM client (localhost:11434)

# Data processing
pandas              # DataFrames
numpy               # Numerics
scipy               # Statistics

# Reports
weasyprint          # HTML → PDF
jinja2              # Templates

# Utilities
pydantic            # Structured schemas
python-dotenv       # .env management
requests-cache      # Avoid duplicate API calls
PyYAML              # Config files
pytrends            # Google Trends (free)
asyncpraw           # Reddit API (free)

# Testing
pytest              # Test framework
```

---

## Part 2: sigma-quant — The Employer Showcase

sigma-quant already has 35+ forensic components, equity curves, trade tables, and SAMTC protocol audit. It needs to evolve from "crypto backtest viewer" to **"full AI hedge fund showcase."**

### Current State (Next.js 16, Supabase, Cloudflare)
- 5 routes: `/`, `/research`, `/research/view/[slug]`, `/research/[slug]`
- 28 forensic audit components
- Reads from Supabase: `trades`, `b2b_zones`, `strategy` tables
- Only shows sigma-crypto backtest data

### What Employers Need to See

**1. The AI agents working** — who analyzed what, delegation chain, cited findings
- New page: `/agents` — real-time agent activity feed
- Shows: which agent ran, what data it fetched, what it concluded, citations used
- Visualizes the multi-agent delegation flow (Chief of Staff → quant-researcher → macro + micro → mathematician → peer-reviewer → CIO)

**2. Multi-instrument performance** — prove the strategy works across markets
- New page: `/portfolio` — aggregated view across all instruments
- Multi-instrument equity curves (XAUUSD, BTCUSDT, EURUSD, etc.)
- Allocation pie chart, correlation heatmap
- Benchmark comparison (vs SPX, vs Gold buy-and-hold)
- Sharpe, Sortino, Calmar, max DD per instrument and portfolio-level

**3. Research reports** — show the analysis quality
- Enhanced `/research` — display AI-generated research reports (morning briefs, research memos)
- PDF viewer for generated reports
- Citation trail visible (every claim linked to source data)

**4. Architecture & system design** — show technical depth
- New page: `/architecture` — interactive system diagram
- Four-pillar visualization
- Tech stack overview
- Agent roster with roles and delegation flow

**5. Risk dashboard** — show institutional-grade risk management
- New component section on main dashboard
- Portfolio-level VaR, correlation risk, drawdown tracking
- Kill switch status, position sizing methodology

### Data Flow: sigma-research → Supabase → sigma-quant

New Supabase tables needed:
- `research_reports` — generated reports (regime classifications, morning briefs)
- `agent_activity` — agent execution logs (who, when, what, result)
- `macro_regimes` — regime classification history
- `backtest_results` — multi-instrument backtest results
- `portfolio_state` — aggregated portfolio metrics

---

## Part 3: Open-Source Stack

### INSTALL (all free, all local)

| Tool | Why This One | Replaces |
|------|-------------|----------|
| **OpenBB SDK** | 200+ data sources, Python native. Free tier sufficient. | Building 10 separate fetchers |
| **Qdrant** (localhost:6333) | Single Windows .exe, no Docker. MIT license. 1GB = 100K vectors. | Chroma (Docker), Pinecone ($70/mo) |
| **Ollama** (localhost:11434) | One-click GPU-accelerated. Model management built-in. | OpenAI API ($50-200/mo) |
| **sentence-transformers** | all-MiniLM-L6-v2: 80MB, 10ms/embed, CPU. No API cost. | OpenAI Embeddings |
| **WeasyPrint** | HTML/CSS → professional PDF. Jinja2 templates. | ReportLab, LaTeX |
| **edgartools** | Best Python SEC EDGAR client. XBRL parsing. Free. | sec-api.io ($$$) |
| **IBKR API** (ib_insync) | Backtesting + paper trading on equities/futures/options. Free with account. | Alpaca (limited), TD Ameritrade (deprecated) |

### STUDY (reference architectures)

| Repo | What We Learn |
|------|--------------|
| virattt/ai-hedge-fund | Agent prompt patterns, risk manager tools |
| assafelovic/gpt-researcher | Multi-step research methodology |
| stanford-oval/storm | Multi-perspective research generation |
| langchain-ai/langgraph | State machine patterns (study, don't install) |

### REJECTED

| Tool | Why Not |
|------|---------|
| Kafka | Single laptop. File-based pipelines sufficient. |
| Kubernetes | No cluster. |
| Airflow | Windows Task Scheduler for daily briefs. |
| LangGraph/CrewAI | Claude Code IS the orchestrator. No second layer. |

---

## Part 4: Citation & Anti-Hallucination System

### CitationRecord Schema
```python
class CitationRecord(BaseModel):
    claim: str              # "DXY is at 103.2, ranging since Feb"
    source_name: str        # "FRED", "SEC EDGAR", "Binance API"
    source_url: str         # Direct URL to data
    retrieval_date: str     # When fetched
    data_date: str          # What date the data represents
    value: Any              # Actual data point
    confidence: float       # 0.0-1.0
    verified_by: list[str]  # Which agents verified
```

### Anti-Hallucination Protocol
1. **Source-First**: Agents fetch data BEFORE making claims
2. **Multi-Source**: Macro regime claims require 2+ independent sources agreeing
3. **Recency Check**: Macro data >7 days old flagged; micro >30 days flagged
4. **Mathematician Gate**: All statistical claims validated
5. **Cross-Model Check**: Critical claims re-evaluated by different LLM (Ollama vs Claude)

---

## Part 5: LLM Routing Strategy

| Task | Model | Cost |
|------|-------|------|
| Research orchestration, strategy analysis | Claude (via Claude Code Pro) | $100/mo (included) |
| News sentiment classification | Ollama: qwen2.5:7b (4.4GB) | Free |
| Document summarization (SEC filings) | Ollama: qwen2.5:7b | Free |
| Cross-check verification | Ollama: mistral:7b | Free |
| Embedding generation | sentence-transformers (CPU) | Free |
| Report writing | Claude (quality matters) | Included |

---

## Part 6: Agent System

### Core Agents (in sigma-brain)

| Agent | Role | Tools from sigma-research |
|-------|------|--------------------------|
| quant-researcher | Research director | Qdrant pre-search, spawns sub-agents |
| macro-researcher | Dalio layer — regime detection | daily_macro_brief.py, regime_detector.py, yield_curve.py, liquidity_monitor.py |
| micro-researcher | P72 layer — instrument analysis | zone_statistics.py, trade_forensics.py, fx_analyzer.py, commodity_analyzer.py |
| equity-researcher | P72 layer — SEC filings, DCF | sec_edgar.py, equity_analyzer.py |
| fixed-income-researcher | P72 layer — duration, credit | fixed_income.py, fi_analyzer.py, yield_curve.py |
| mathematician | Statistical validation gate | CSV parsing, significance tests |
| peer-reviewer | Research quality gate | Memory files, consistency checks |
| risk-manager | PTJ layer — risk enforcement | position_sizer.py, correlation_risk.py, drawdown_monitor.py |
| quant-developer | Code implementation | Worktree-based development |
| code-reviewer | Code quality gate | Git diff, pytest |
| cio | Strategic decision (final) | Memory + full research package |
| quant-trader | Read-only observer | Memory + trade logs |
| memory-curator | Writes Memory/*.md | Qdrant embedding after writes |
| research-data-agent | Shared data utility | All data/pipelines/* scripts |

### Quality Gates

- **Code gate**: ALL code must be APPROVED by code-reviewer before execution
- **Research gate**: ALL research must be APPROVED by peer-reviewer before reaching CIO
- **Risk gate**: ALL position sizing must be APPROVED by risk-manager

### Skills

| Skill | Command | What It Does |
|-------|---------|-------------|
| `/morning-brief` | daily_macro_brief.py | Regime + key levels + calendar + sentiment |
| `/run-research` | research_pipeline.py | Full pipeline: fetch → analyze → validate → review → report |
| `/ingest-research` | ingest_past_research.py | Index existing papers into Qdrant |
| `/run-backtest` | (existing) | Run SAMTC backtest |
| `/check-mt5-health` | (existing) | MT5 connection check |

---

## Part 7: Build Sequence (Updated for v2)

### Phase 1 — Foundation + Data Layer
*Data pipelines, vector memory, local LLMs, citations*

1. Create sigma-research project structure + CLAUDE.md + requirements.txt
2. Create workspace junction
3. Install all Python dependencies (venv)
4. Build core data pipelines: fred_fetcher.py, yahoo_finance.py, crypto_data.py
5. Build citation_tracker.py + anti-hallucination foundation
6. Install Qdrant binary + build vector_store.py + embedder.py
7. Build ollama_client.py + verify models
8. Run verification: fetch live data, embed memo, query by similarity

### Phase 2 — Macro Research + Morning Brief
*Directly helps live XAUUSD trading*

9. Build analysis/macro/ — regime_detector, yield_curve, liquidity_monitor, economic_calendar, cross_asset
10. Build daily_macro_brief.py script
11. Update macro-researcher AGENT.md with tools
12. Create /morning-brief skill
13. Test: /morning-brief → regime classification with citations

### Phase 3 — Remaining Pipelines + Micro Research
*Full multi-asset research capability*

14. Build remaining pipelines: sec_edgar, fixed_income, fx_data, commodities, news, sentiment, openbb_bridge
15. Build analysis/micro/ — zone_statistics, trade_forensics, fx_analyzer, commodity_analyzer, equity_analyzer
16. Build sentiment analysis: news_scorer (Ollama), fear_greed, social_pulse
17. Create equity-researcher, fixed-income-researcher, research-data-agent definitions
18. Create /run-research skill
19. Test: full multi-asset research question → specialized agents → math → peer review

### Phase 4 — Unified B2B Backtest Engine
*Test strategy across all instruments*

20. Extract B2B zone detection from sigma-crypto into sigma-research/b2b/
21. Build instrument-agnostic backtester (any OHLCV → B2B zones → results)
22. Backtest B2B zones on: XAUUSD, EURUSD, GBPUSD, USDJPY, US30, SPX, BTC, ETH, SOL
23. Build signal_attribution.py — which signals → which P&L
24. Comparative analysis: where is B2B edge strongest?
25. Test: unified backtest produces comparable results to sigma-crypto for same data

### Phase 5 — Risk Layer + Reports
*Professional output*

26. Build analysis/risk/ — position_sizer, correlation_risk, drawdown_monitor, scenario_stress
27. Build Jinja2 report templates (morning brief, research memo, forensic, monthly)
28. Build generator.py (WeasyPrint PDF)
29. Build research_pipeline.py (full end-to-end orchestrator)
30. Wire Qdrant into memory-curator workflow
31. Test: full pipeline → cited PDF with all three research layers

### Phase 6 — sigma-quant Showcase
*Everything visible to employers*

32. New Supabase tables: research_reports, agent_activity, macro_regimes, backtest_results, portfolio_state
33. New page: /portfolio — multi-instrument overview, allocation, benchmarks
34. New page: /agents — agent activity feed, delegation flow visualization
35. New page: /architecture — interactive system diagram
36. Enhanced /research — AI research reports viewer with citations
37. Macro regime widget + correlation heatmap on main dashboard
38. Test: employer can see agents working, performance, research, architecture

### Phase 7 — IBKR Integration
*Multi-platform proof*

39. IBKR API connection (ib_insync) for historical data
40. Route B2B signals to IBKR paper account
41. Equities/futures backtesting
42. Results flow to sigma-quant dashboard
43. Test: paper trade on IBKR, results visible on dashboard

### Phase 8 — Research Paper + Polish
*Job application ready*

44. Formalize B2B Zone Detection as academic-style quant research paper
45. Full demo flow: /morning-brief → research → backtest → dashboard → PDF
46. LinkedIn portfolio content via sigma-linkedin
47. Interview demo preparation (15-minute walkthrough)
48. Test: complete end-to-end demo with live data

---

## Part 8: Risk Rules (Non-Negotiable)

1. **Never authorize live trades without explicit human confirmation**
2. **Never push to git remotes without user approval**
3. **Never expose API keys** — read from .env, never print them
4. **Never delete files** without telling the user first
5. **Always report drawdown breaches** to risk-manager before proceeding
6. **Two-key rule**: Any live execution requires both AI assessment AND user confirmation
7. **Code gate**: No code runs without code-reviewer APPROVED verdict
8. **Research gate**: No research reaches CIO without peer-reviewer APPROVED verdict

---

## Part 9: Cost Analysis

### Monthly: $100-$105/month total
| Item | Cost |
|------|------|
| Claude Code Pro | $100 |
| FRED API | $0 (free) |
| OpenBB SDK | $0 (free tier) |
| Ollama + models | $0 (local, ~9GB disk) |
| Qdrant | $0 (local binary) |
| sentence-transformers | $0 (local) |
| yfinance | $0 |
| Supabase | $0 (free tier) |
| Cloudflare Pages | $0 |
| SEC EDGAR | $0 (government) |
| IBKR | $0 (paper trading free with account) |
| Tavily Search | $0 (1000 free/mo) |

### What This Replaces
Bloomberg Terminal ($24K/yr), OpenAI API ($50-200/mo), Pinecone ($70/mo), AWS ($50-200/mo)

---

## Part 10: Verification (End-to-End Tests)

1. **Data pipeline:** `python sigma-research/data/pipelines/fred_fetcher.py` → DXY parquet exists
2. **Local LLM:** `curl localhost:11434/api/generate` → Ollama responds with classification
3. **Vector memory:** Embed memo → query "SAMTC bear market" → retrieve relevant research
4. **Morning brief:** `/morning-brief` → regime classification with citations
5. **Multi-instrument backtest:** B2B zones tested on XAUUSD + BTCUSDT → comparable Sharpe
6. **Full pipeline:** Research question → macro + micro + math + peer review → cited PDF
7. **Anti-hallucination:** Every numeric claim traces to CitationRecord with source URL
8. **Showcase:** Employer visits sigma-quant → sees agents, performance, research, architecture
9. **Live integration:** Morning brief regime matches what's visible on MT5 charts
