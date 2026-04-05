# PRD: Baysix AI-Native Hedge Fund — Full Architecture Build
### Version 1.0 | Approved 2026-03-12

---

## Context

We're building Baysix, an AI-native hedge fund with three layers: **Research Department** (priority), **Backtest Engine**, and **Execution Engine**. The user is broke (Claude Code Pro $100/mo is the only budget) and needs this as a job portfolio piece for Quant Researcher + Multi AI Agent Builder roles.

**What already exists and works:**
- sigma-brain: 11 agents, 4 skills, memory system, workspace junctions, worktree protocol
- sigma-crypto: SAMTC V6.7 with 40x in-sample returns, vectorized backtester, BTCUSDT data
- sigma-mt5: MQL5 V5.0 B2B EA (pending cluster fix)
- sigma-quant: Next.js 16 dashboard with 35+ forensic components, deployed on Cloudflare
- sigma-linkedin: Content manager (functional, stale config)

**What's missing:** The agents have role definitions but NO actual data pipelines, NO vector memory, NO citation tracking, NO report generation, NO local LLM integration. We need to build the research infrastructure beneath the existing agent layer.

**Key principle:** Claude Code remains the orchestrator. We do NOT add LangGraph/CrewAI as a second orchestration layer. Instead, we build a `sigma-research` Python project that provides tools the existing Claude Code agents invoke.

**User hardware:** RTX 3060+ (8GB+ VRAM) — can run qwen2.5:7b and mistral:7b comfortably via Ollama.

**Asset class scope:** ALL — Crypto, Forex, Equities, Fixed Income, Commodities (full Point72-style coverage).

**Research philosophy:** Hybrid of three legends, with clear hierarchy:
1. **Ray Dalio layer (Macro Regime)** — Economic machine model determines the regime (risk-on/off, inflationary/deflationary, growth/contraction). This is the top-level filter that gates everything below.
2. **Point72 layer (Sector/Instrument Selection)** — Within the regime, fundamental + quantitative analysis selects which asset classes and instruments have edge. Deep micro analysis (earnings, filings, zone stats) with macro awareness.
3. **Paul Tudor Jones layer (Risk Management)** — Obsessive risk management on every position. Position sizing, stop placement, correlation risk, drawdown limits. "Losers average losers."

---

## Architecture Overview

```
sigma-brain (Chief of Staff — Claude Code orchestrator)
    ├── sigma-research (NEW — data pipelines, vector memory, reports, local LLM)
    ├── sigma-crypto   (SAMTC V6.7 backtester — extend with regime overlay)
    ├── sigma-mt5      (MQL5 EA — keep as-is, pending cluster fix)
    ├── sigma-quant    (Dashboard — add research report viewer)
    └── sigma-linkedin (Content — update stale config)
```

**Data flow:** Data Sources → sigma-research pipelines → Parquet/Qdrant → Agents analyze → Mathematician validates → Peer-reviewer gates → CIO decides → Reports generated → Dashboard displays

---

## Part 1: New Project — sigma-research

**Location:** `C:\Users\User\Desktop\sigma-research\` + junction at `workspace/sigma-research/`

```
sigma-research/
├── CLAUDE.md                     # Project instructions
├── requirements.txt              # All Python deps
├── config/
│   └── data_sources.yaml         # API endpoints, refresh schedules
├── data/
│   ├── pipelines/
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
│   ├── vector_store.py           # Qdrant CRUD wrapper
│   ├── embedder.py               # sentence-transformers (local, no API)
│   ├── citation_tracker.py       # CitationRecord for every claim
│   └── research_index.py         # Index all past research into Qdrant
├── analysis/
│   ├── macro/                    # DALIO LAYER — Regime Detection
│   │   ├── regime_detector.py    # Economic machine: growth/inflation/liquidity state
│   │   ├── economic_calendar.py  # FOMC, CPI, NFP, ECB, BOJ schedule + impact
│   │   ├── cross_asset.py        # Rolling correlation matrix: all asset classes
│   │   ├── yield_curve.py        # Inversion detection, term premium, rate trajectory
│   │   └── liquidity_monitor.py  # M2, Fed balance sheet, TGA, RRP
│   ├── micro/                    # POINT72 LAYER — Instrument Selection
│   │   ├── zone_statistics.py    # B2B zone hit rates, touch depth, entry precision
│   │   ├── trade_forensics.py    # Post-mortem from sigma-crypto trade logs
│   │   ├── equity_analyzer.py    # DCF, earnings, peer comp (from SEC filings)
│   │   ├── fx_analyzer.py        # Carry trade scoring, PPP, CoT positioning
│   │   ├── fi_analyzer.py        # Duration risk, credit spread analysis
│   │   ├── commodity_analyzer.py # Supply/demand, seasonality, inventory
│   │   └── signal_attribution.py # Which signals → which P&L
│   ├── risk/                     # PTJ LAYER — Risk Management
│   │   ├── position_sizer.py     # Kelly criterion, volatility-adjusted sizing
│   │   ├── correlation_risk.py   # Portfolio correlation, concentration limits
│   │   ├── drawdown_monitor.py   # Real-time DD tracking, kill switch triggers
│   │   └── scenario_stress.py    # What-if scenarios (rate shock, crash, etc.)
│   ├── sentiment/
│   │   ├── news_scorer.py        # Ollama classifies headlines: bull/bear/neutral
│   │   ├── fear_greed.py         # alternative.me API
│   │   └── social_pulse.py       # pytrends + Reddit sentiment
│   └── anti_hallucination.py     # Multi-source verification engine
├── reports/
│   ├── generator.py              # Jinja2 + WeasyPrint → PDF
│   ├── templates/                # Morning brief, research memo, forensic
│   └── output/                   # Generated PDFs
├── llm/
│   ├── router.py                 # Claude (deep reasoning) vs Ollama (throughput)
│   ├── ollama_client.py          # localhost:11434 interface
│   └── prompts/                  # System prompts per analysis type
├── scripts/
│   ├── daily_macro_brief.py      # Morning macro scan (all macro pipelines)
│   ├── research_pipeline.py      # Full end-to-end research runner
│   └── ingest_past_research.py   # One-time: index existing papers into Qdrant
└── tests/
```

### Key Python Dependencies (all free)
```
openbb              # Unified market data SDK (free tier)
fredapi             # FRED API (free with registration)
yfinance            # Yahoo Finance (free, no key)
edgartools           # SEC EDGAR parser (free, public data)
qdrant-client       # Vector DB client
sentence-transformers  # Local embeddings (all-MiniLM-L6-v2, 80MB)
ollama              # Local LLM client
weasyprint          # HTML → PDF report generation
jinja2              # Report templates
pytrends            # Google Trends (free)
asyncpraw           # Reddit API (free)
requests-cache      # Avoid duplicate API calls
pydantic            # Structured output schemas
python-dotenv       # .env management
```

---

## Part 2: Open-Source Stack (What to Install and Why)

### INSTALL (all free, all local)

| Tool | Why This One | Replaces |
|------|-------------|----------|
| **OpenBB SDK** (`pip install openbb`) | 200+ data sources, Python native. Covers FRED + equities + crypto + macro in one SDK. Free tier sufficient. | Building 6 separate custom fetchers |
| **Qdrant** (binary download, runs on localhost:6333) | Single Windows .exe, no Docker. MIT license. Metadata filtering. 1GB RAM for 100K vectors. | Chroma (needs Docker), Pinecone ($70/mo), Weaviate (Docker) |
| **Ollama** (Windows installer, localhost:11434) | One-click. GPU-accelerated on RTX. Model management built-in. | OpenAI API ($50-200/mo), HuggingFace Inference ($$$) |
| **sentence-transformers** (`pip install`) | `all-MiniLM-L6-v2`: 80MB, runs on CPU in 10ms/embed. No API cost. | OpenAI Embeddings ($0.13/M tokens), Cohere Embed ($$$) |
| **WeasyPrint** (`pip install`) | HTML/CSS → professional PDF. Jinja2 templates. Free. | ReportLab (complex API), LaTeX (overkill) |
| **edgartools** (`pip install`) | Best Python SEC EDGAR client. Parses XBRL, 10-K, 10-Q. Government data = free. | sec-api.io ($$$), manual scraping |

### STUDY BUT DON'T INSTALL (reference architectures)

| Repo | What We Learn |
|------|--------------|
| **virattt/ai-hedge-fund** | Agent prompt engineering patterns, risk manager tool definitions. Uses OpenAI ($$$) + LangGraph — conflicts with our Claude Code orchestrator. Study their AGENT prompts. |
| **assafelovic/gpt-researcher** | Multi-step research methodology: plan → search → extract → synthesize → report. Replicate the pattern, not the code. |
| **stanford-oval/storm** | Multi-perspective research generation. The concept is already in our pipeline (macro + micro + math = multiple perspectives). |
| **langchain-ai/langgraph** | State machine patterns for checkpointing. Study, don't add as dependency — we already have Claude Code agents. |

### REJECTED (and why)

| Tool | Why Not |
|------|---------|
| Kafka | Single laptop. Python queues or file-based pipelines are fine. |
| Kubernetes | No cluster to manage. Docker Compose if ever needed. |
| Airflow | APScheduler or Windows Task Scheduler for daily briefs. |
| TimescaleDB | Already have Supabase (Postgres) via sigma-quant. |
| Redis | `diskcache` or `requests-cache` is sufficient locally. |

---

## Part 3: Citation & Anti-Hallucination System

### CitationRecord Schema (in `sigma-research/memory/citation_tracker.py`)
```python
@dataclass
class CitationRecord:
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
3. **Recency Check**: Macro data >7 days old gets flagged, micro >30 days
4. **Mathematician Gate**: All statistical claims validated (existing agent)
5. **Cross-Model Check**: Critical claims re-evaluated by different LLM (Ollama vs Claude)

---

## Part 4: LLM Routing Strategy

| Task | Model | Cost |
|------|-------|------|
| Research orchestration, strategy analysis | Claude (via Claude Code Pro) | $100/mo (included) |
| News sentiment classification | Ollama: qwen2.5:7b (4.4GB, fits RTX) | Free |
| Document summarization (SEC filings) | Ollama: qwen2.5:7b | Free |
| Cross-check verification | Ollama: mistral:7b (different model) | Free |
| Embedding generation | sentence-transformers (CPU, 10ms/embed) | Free |
| Report writing | Claude (quality matters) | Included |

---

## Part 5: Agent Enhancements

### Existing AGENT.md Updates

**macro-researcher** — Add Dalio-layer tools:
- `python sigma-research/scripts/daily_macro_brief.py` → regime + indicators
- `python sigma-research/analysis/macro/regime_detector.py` → economic machine state
- `python sigma-research/analysis/macro/yield_curve.py` → rate trajectory
- Qdrant query: past research on similar macro conditions

**micro-researcher** — Add Point72-layer tools:
- `python sigma-research/analysis/micro/zone_statistics.py` → zone stats
- `python sigma-research/analysis/micro/equity_analyzer.py` → fundamentals
- `python sigma-research/analysis/micro/trade_forensics.py` → post-mortem

**risk-manager** — Add PTJ-layer tools:
- `python sigma-research/analysis/risk/position_sizer.py` → Kelly sizing
- `python sigma-research/analysis/risk/correlation_risk.py` → portfolio risk
- `python sigma-research/analysis/risk/drawdown_monitor.py` → DD tracking

**memory-curator** — Add Qdrant embedding step:
- After writing to Memory/*.md: `python sigma-research/memory/research_index.py --embed-latest`

**quant-researcher** — Add pre-research Qdrant query:
- Before spawning sub-agents: `python sigma-research/memory/vector_store.py --query "topic"`

### New AGENT.md Files (3)

**equity-researcher** (`.claude/agents/equity-researcher/AGENT.md`):
- SEC filing analysis, earnings, DCF modeling, peer benchmarking
- Tools: `sec_edgar.py`, `equity_analyzer.py`, OpenBB equities
- Spawned by quant-researcher for equity-specific deep dives

**fixed-income-researcher** (`.claude/agents/fixed-income-researcher/AGENT.md`):
- Duration risk, credit spreads, sovereign debt, yield curve positioning
- Tools: `fixed_income.py`, `fi_analyzer.py`, `yield_curve.py`
- Spawned by quant-researcher for FI-specific analysis

**research-data-agent** (`.claude/agents/research-data-agent/AGENT.md`):
- Shared data utility. Fetches and caches market data on demand.
- Tools: All `sigma-research/data/pipelines/*` scripts

---

## Part 6: New Skills

| Skill | Command | What It Does |
|-------|---------|-------------|
| `/morning-brief` | Runs `daily_macro_brief.py` | Regime classification + key levels + calendar + sentiment |
| `/run-research` | Runs `research_pipeline.py` with a question | Full pipeline: fetch → analyze → validate → review → report |
| `/ingest-research` | Runs `ingest_past_research.py` | One-time index of existing papers into Qdrant |

---

## Part 7: Files Summary

### New Files to Create
- `C:\Users\User\Desktop\sigma-research\` — entire project (see Part 1 structure)
- `sigma-brain/workspace/sigma-research/` — junction
- `.claude/agents/equity-researcher/AGENT.md` — SEC filings, earnings, DCF
- `.claude/agents/fixed-income-researcher/AGENT.md` — duration, credit, yields
- `.claude/agents/research-data-agent/AGENT.md` — shared data utility
- `.claude/skills/morning-brief/SKILL.md` — daily macro scan
- `.claude/skills/run-research/SKILL.md` — full pipeline runner
- `.claude/skills/ingest-research/SKILL.md` — Qdrant indexer

### Existing Files to Modify
| File | Change |
|------|--------|
| `sigma-brain/CLAUDE.md` | Add sigma-research to Project Map, add 3 new agents + 3 new skills, add hybrid philosophy section |
| `sigma-brain/.claude/settings.json` | Add `SIGMA_RESEARCH` env var |
| `.claude/agents/macro-researcher/AGENT.md` | Add Dalio-layer tool invocations |
| `.claude/agents/micro-researcher/AGENT.md` | Add Point72-layer tool invocations |
| `.claude/agents/risk-manager/AGENT.md` | Add PTJ-layer tool invocations |
| `.claude/agents/memory-curator/AGENT.md` | Add Qdrant embedding step |
| `.claude/agents/quant-researcher/AGENT.md` | Add pre-research Qdrant query + new sub-agent roster |

---

## Part 8: Build Sequence

### Phase 1 — Foundation + Data Layer (Week 1-2)
1. Create `sigma-research/` project structure + CLAUDE.md + requirements.txt + `__init__.py` files
2. Create workspace junction: `workspace/sigma-research/`
3. `pip install openbb fredapi yfinance edgartools qdrant-client sentence-transformers ollama weasyprint jinja2 pytrends requests-cache pydantic python-dotenv`
4. Build core data pipelines: `openbb_bridge.py`, `fred_fetcher.py`, `yahoo_finance.py`
5. Build asset-class pipelines: `crypto_data.py`, `fixed_income.py`, `fx_data.py`, `commodities_data.py`
6. Install Ollama + pull `qwen2.5:7b` (RTX 3060+ confirmed — 4.4GB fits comfortably)
7. Build `ollama_client.py` + `router.py`
8. Download Qdrant Windows binary, build `vector_store.py` + `embedder.py`
9. Run `ingest_past_research.py` to index existing sigma-crypto research papers into Qdrant
10. **Test:** Fetch live DXY + VIX + BTC funding + 10Y yield + Gold, embed a memo, retrieve by query

### Phase 2 — Dalio Layer: Macro Regime Engine (Week 3-4)
11. Build `regime_detector.py` — economic machine: growth x inflation x liquidity state matrix
12. Build `yield_curve.py` — inversion detection, term premium, rate trajectory
13. Build `liquidity_monitor.py` — M2, Fed balance sheet, TGA, RRP
14. Build `economic_calendar.py` — FOMC, CPI, NFP, ECB, BOJ with impact scoring
15. Build `cross_asset.py` — rolling correlation matrix across ALL asset classes
16. Build `citation_tracker.py` + `anti_hallucination.py`
17. Build `daily_macro_brief.py` script (chains all Dalio-layer analysis)
18. Update macro-researcher AGENT.md with tool invocations
19. Create `/morning-brief` skill
20. **Test:** `/morning-brief` → regime classification with citations covering all 5 asset classes

### Phase 3 — Point72 Layer: Instrument Analysis (Week 5-6)
21. Build `equity_analyzer.py` — DCF, earnings, peer comp from SEC EDGAR data
22. Build `sec_edgar.py` pipeline — ingest 10-K/10-Q filings
23. Build `fx_analyzer.py` — carry trade scoring, CoT positioning
24. Build `fi_analyzer.py` — duration risk, credit spread analysis
25. Build `commodity_analyzer.py` — supply/demand, seasonality
26. Build `zone_statistics.py` + `trade_forensics.py` (extends existing micro)
27. Build sentiment: `news_scorer.py` (Ollama), `fear_greed.py`, `social_pulse.py`
28. Create equity-researcher + fixed-income-researcher AGENT.md files
29. Update micro-researcher + quant-researcher AGENT.md files
30. Create `/run-research` skill
31. **Test:** Full multi-asset research question → specialized agents → math validation → peer review

### Phase 4 — PTJ Layer: Risk + Reports (Week 7-8)
32. Build `position_sizer.py` — Kelly criterion, volatility-adjusted sizing
33. Build `correlation_risk.py` — portfolio-level correlation, concentration limits
34. Build `drawdown_monitor.py` + `scenario_stress.py`
35. Build Jinja2 report templates (morning brief, research memo, forensic, monthly)
36. Build `generator.py` (WeasyPrint PDF export)
37. Build `research_pipeline.py` (full end-to-end orchestrator)
38. Wire Qdrant into memory-curator workflow
39. Update risk-manager AGENT.md with PTJ-layer tools
40. **Test:** Full pipeline → macro+micro → math → peer review → professional PDF with citations

### Phase 5 — Backtest Integration (Week 9-10)
41. Build `signal_bridge.py` — regime classification → SAMTC config overrides
42. Extend `VectorizedBacktester` to accept regime overlay parameter
43. Run comparative backtest: SAMTC with vs without regime filter
44. Build `signal_attribution.py` — which research signals drove P&L
45. Evaluate NautilusTrader integration path (document architecture, don't build yet)
46. **Test:** Regime-aware backtest shows improved risk-adjusted returns vs baseline

### Phase 6 — Dashboard + Portfolio Polish (Week 11-12)
47. Add research report viewer page to sigma-quant
48. Add macro regime dashboard widget (live regime + key levels)
49. Add multi-asset correlation heatmap component
50. Update sigma-linkedin config paths + generate portfolio post
51. Wire paper trading notification to Telegram (via OpenFang adapter)
52. Prepare 15-minute interview demo flow
53. **Test:** Full demo: `/morning-brief` → research → backtest → dashboard → PDF

---

## Part 9: Cost Analysis

### Monthly: $100-$105/month total
| Item | Cost |
|------|------|
| Claude Code Pro | $100 |
| FRED API | $0 (free with registration) |
| OpenBB SDK | $0 (free tier) |
| Ollama + models | $0 (local, ~9GB disk) |
| Qdrant | $0 (local binary, ~500MB) |
| sentence-transformers | $0 (local) |
| yfinance | $0 |
| Supabase | $0 (free tier) |
| Cloudflare Pages | $0 |
| SEC EDGAR | $0 (government data) |
| Tavily Search | $0 (1000 free/mo) or $5/mo upgrade |

### What This Replaces
Bloomberg Terminal ($24K/yr), OpenAI API ($50-200/mo), Pinecone ($70/mo), AWS ($50-200/mo)

---

## Part 10: Verification (End-to-End Tests)

1. **Data pipeline:** `python sigma-research/data/pipelines/fred_fetcher.py` → DXY parquet file exists
2. **Local LLM:** `curl localhost:11434/api/generate -d '{"model":"qwen2.5:7b","prompt":"classify: bullish or bearish"}` → response
3. **Vector memory:** Embed a research memo → query "SAMTC bear market" → retrieve relevant past research
4. **Morning brief:** Run `/morning-brief` → get PDF with regime, key levels, citations
5. **Full pipeline:** Ask "Should we increase position size?" → macro + micro + math + peer review → cited report
6. **Anti-hallucination:** Verify every numeric claim in report traces to a CitationRecord with source URL
7. **Backtest integration:** Run SAMTC with regime overlay → compare Sharpe/Calmar vs baseline
