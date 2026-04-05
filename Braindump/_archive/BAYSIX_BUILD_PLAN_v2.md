# Baysix Technologies — Master Build Plan & Agent Handover
**Version:** 2.0  
**Date:** 2026-04-03  
**Author:** Chief of Staff (Antigravity)  
**Status:** ACTIVE — supersedes PRD v4

---

## 0. Context for Resuming Agent

If you are reading this in a new session, this is the full context you need. Do NOT start building until you have read sections 0–4 in full.

**Who:** Syafiq M. Zin — solo founder, AI Quantitative Developer, Kuala Lumpur  
**What:** Baysix Technologies — an AI-native systematic trading system and portfolio showcase  
**Why:** Dual purpose — (1) live trading operation, (2) professional showcase for AI Quant Developer roles  
**Key files to also read:**
- `C:\Users\User\Desktop\sigma-brain\BAYSIX_CONTEXT_BRIEF.md` — full system context
- `C:\Users\User\Desktop\sigma-brain\Braindump\PRD_baysix_ai_hedge_fund_v4.md` — original PRD
- `C:\Users\User\Desktop\sigma-research\main.py` — existing LangGraph skeleton
- `C:\Users\User\Desktop\sigma-research\state\trading_state.py` — current state schema

---

## 1. Hardware & Infrastructure Constraints (CRITICAL — read before designing anything)

| Component | Spec | Implication |
|---|---|---|
| CPU | Intel i7-7700 @ 3.6GHz, 4 cores / 8 threads | No heavy parallel compute |
| RAM | 40GB | Good — supports large in-memory datasets |
| GPU | **NVIDIA RTX 3060 Ti — 8GB VRAM** | Gemma 4 9B Q4 quantized fits (~6-7GB) |
| OS | Windows 10 Home | Docker Desktop required (being installed) |
| Budget | $0 cloud spend (free tiers only) | Supabase free, Groq free, Gemini free |
| Storage | Standard SSD | Qdrant + RAGFlow will need ~20-50GB |

**GPU constraint:** Cannot run local LLM inference AND ML model training simultaneously. Plan cycles sequentially.

---

## 2. What Exists Today (Current State Per Project)

### sigma-quant (`C:\Users\User\Desktop\sigma-quant`)
- **Status:** Deployed and live at `syafiqmzin-sigma-quant.pages.dev`
- **Stack:** Next.js 15, TypeScript, Supabase, lightweight-charts, Recharts
- **What works:** Backtest dashboard, Research Hub (SAMTC paper + audit cards), auth, sidebar
- **What was stripped:** Intelligence page (being redesigned), Operations page (removed)
- **GitHub:** `github.com/smz3/SIGMA-Quant` (public)
- **Current task:** Intelligence page redesign pending — user wants premium terminal design, not the amateur-looking version that was built
- **Root redirect:** `/` currently redirects to `/backtest` temporarily

### sigma-research (`C:\Users\User\Desktop\sigma-research`)
- **Status:** Skeleton — runs but nodes are mostly stubs
- **Stack:** Python, LangGraph, Groq, Gemini, Ollama, Qdrant, Supabase, FRED, yfinance, CCXT
- **What works:** 5-node graph compiles and runs (Data Ingestion → Macro → Micro → Risk → CIO)
- **What's missing:** Real data in nodes, checkpointing, scheduler, equity researcher, RAGFlow
- **GitHub:** Not yet pushed (private, no remote set)

### sigma-brain (`C:\Users\User\Desktop\sigma-brain`)
- **Status:** HQ — agent configs, PRDs, memory files, skills
- **GitHub:** `github.com/smz3/sigma-brain` (private, just pushed 2026-04-03)

### sigma-core (`C:\Users\User\Desktop\sigma-brain\workspace\sigma_core`)
- **Status:** ✅ COMPLETE — compiled `.pyd` binary
- **What it is:** The B2B zone detection engine (Cython-compiled Python). Source never exposed.

### sigma-mt5 and sigma-crypto
- **Status:** Exist but not actively being developed in this phase

---

## 3. Architecture Decisions Made (2026-04-03 Session)

These decisions are FINAL. Do not re-debate them.

### 3.1 App Strategy — TWO Apps, Not One
- **sigma-quant** stays as the **public portfolio showcase** (backtest, research hub, SAMTC paper)
- **baysix-platform** is the **new private operational terminal** to be built
- Both share the same Supabase backend (same project)

### 3.2 Backend Architecture
```
Next.js (frontend)
    ↓  HTTP calls
FastAPI (Python API server — port 8000)
    ↓  LangServe routes
LangGraph Orchestrator
    ↓  reads/writes
Supabase (IPC bus + state + checkpoints + trade log)
    ↑  realtime subscriptions
Next.js (live updates to UI)
```

FastAPI is the **bridge** between TypeScript frontend and Python ML/agent backend. Not Next.js API routes.

### 3.3 LLM Routing Strategy (FINAL)

| Agent | Model | Reason |
|---|---|---|
| Data Agent | No LLM | Pure data fetching |
| Macro Researcher | **Gemma 4 9B Q4 (Ollama local)** | Structured JSON, private, free |
| Micro Researcher | **Gemma 4 9B Q4 (Ollama local)** | Zone probability estimation |
| Sentiment Agent | **Gemma 4 2B Q4 (Ollama local)** | Simple classification |
| P&L Attribution | **Gemma 4 9B Q4 (Ollama local)** | Structured report |
| Risk Manager | **Gemma 4 9B Q4 (Ollama local)** | Rule-based + narrative |
| Equity Researcher | **Gemini Flash (cloud)** | Long PDF context needed |
| Peer Reviewer | **Groq Llama 3.3 70B (cloud)** | Strong reasoning required |
| CIO Synthesizer | **Groq Llama 3.3 70B (cloud)** | Highest-stakes decision |

**Local-first principle:** ~80% of agent calls go to local Gemma 4. Cloud only for highest-stakes reasoning.

### 3.4 Knowledge Layer

```
Unstructured documents (PDFs, transcripts)  →  RAGFlow → Qdrant (dense vectors)
Structured/numerical data (prices, outcomes) →  Supabase SQL (direct queries)
Alpha insights / research memory             →  Qdrant (semantic search)
Agent state / checkpoints                    →  Supabase (PostgreSQL direct)
```

**Rule:** Never use RAG for numerical/structured data. Win rates, OHLCV, zone scores = SQL.

### 3.5 Research Cycle Scheduling — Three-Trigger Model

```
Trigger Type    When                            What Runs
────────────    ────────────────────────────    ─────────────────────────────
Scheduled       Market open (9am ET)            Full macro + micro cycle
                Every 4h during market hours    Watchlist refresh + regime check
                Market close                    P&L attribution cycle
                Sunday weekly                   XGBoost retraining job

Event-Driven    VIX > 25                        Risk-Off emergency protocol
                NFP / CPI / FOMC release        Macro event deep-dive
                Earnings surprise ≥ 5%          Equity researcher triggered
                New B2B zone detected           Zone Inspector + XGBoost scoring
                Kill switch breached            Risk Manager emergency cycle

On-Demand       User triggers via UI            Any agent, any scope
```

Sector awareness lives as a **state machine in Supabase:**
```json
{
  "sector_rotation": "tech_leading",
  "active_focus": ["QQQ", "NVDA", "MSFT"],
  "macro_regime": "Risk-On",
  "last_cycle_at": "2026-04-03T09:00:00Z"
}
```

### 3.6 LangGraph Checkpointing — MUST be Phase 0

```python
from langgraph.checkpoint.postgres import PostgresSaver

checkpointer = PostgresSaver.from_conn_string(
    os.environ["SUPABASE_DB_URL"]  # direct PostgreSQL, not REST API
)
app = graph.compile(checkpointer=checkpointer)
```

This cannot be retrofitted. Wire it before writing agent node logic.

### 3.7 Bull/Bear Debate Pattern — Upgrade to Current Graph

The current single Macro Researcher node becomes a three-node debate:
```
[Bull Agent] ─┐
               ├─→ [Arbiter/CIO]
[Bear Agent] ─┘
```
Bull Agent prompt: "Find the strongest case for Risk-On given this data."
Bear Agent prompt: "Find the strongest case for Risk-Off given this same data."
CIO reads both and adjudicates. Adds structural robustness against confirmation bias.

### 3.8 Model Collapse Safeguards (Non-Negotiable)

1. **Permutation test gate** — XGBoost must pass permutation test (p < 0.05) before deployment
2. **Time-decay weighting** — recent zone outcomes weighted 3x vs. 6+ month old data
3. **Hard sizing floor** — minimum multiplier 0.5x regardless of model output
4. **Manual kill switch** — one button freezes all AI execution

---

## 4. Docker Services Stack

Docker Desktop is being installed. The full local services stack:

```yaml
# docker-compose.yml (to be created in sigma-research root)
services:
  ragflow:        # Document ingestion — port 9380
  qdrant:         # Vector search — port 6333
  ollama:         # Local LLM inference — port 11434
  redis:          # Celery broker for event scheduler — port 6379
  fastapi:        # Python API server — port 8000
```

Supabase stays cloud-hosted (already deployed, free tier).

---

## 5. Build Phases (REVISED — Final Order)

### Phase 0 — Foundation (DO FIRST — everything else depends on this)
- [ ] Verify Docker Desktop installed and running
- [ ] `docker-compose.yml` for Qdrant + Redis + Ollama
- [ ] Pull Gemma 4 9B Q4 via Ollama: `ollama pull gemma3:9b` (or `gemma4:9b` if available)
- [ ] LangGraph `PostgresSaver` checkpointer wired to Supabase direct DB connection
- [ ] FastAPI skeleton (`main.py`, `/health`, `/trigger` stub)
- [ ] Supabase schema: `agent_status`, `research_cycles`, `sector_state`, `agent_logs` tables
- [ ] `.env` updated with `SUPABASE_DB_URL` (direct PostgreSQL connection string, not REST)
- [ ] Bull/Bear Agent nodes added to LangGraph graph topology

### Phase 1 — sigma_core ✅ DONE

### Phase 2 — Data Layer
- [ ] Data Agent: FRED, yfinance, CCXT pulls → structured Supabase tables
- [ ] Event Scheduler: APScheduler or Celery + Redis watching VIX, FOMC calendar, earnings dates
- [ ] Sector State updater: XLK/XLE/XLF relative strength → `sector_state` Supabase table

### Phase 3 — Research Agents (Macro + Sentiment)
- [ ] Macro Researcher node: Replace Groq call with local Gemma 4 9B via Ollama
- [ ] Bull Agent + Bear Agent nodes
- [ ] Sentiment Agent: news scraper + Gemma 4 2B classifier
- [ ] RAGFlow: Docker container running, document ingestion pipeline wired

### Phase 4 — Zone Inspector + Feedback Loop (CRITICAL)
- [ ] Zone Inspector: calls `sigma_core.b2b` binary, extracts active zones
- [ ] Zone outcome tracker: auto-writes feature vector + outcome to Supabase at trade close
- [ ] Feature vector schema: `(zone_id, tf, direction, zone_age, touch_count, atr, session, macro_regime, sentiment_score, outcome, r_multiple)`
- [ ] This is the data the XGBoost model trains on — it must be bulletproof

### Phase 5 — Equity Researcher Agent
- [ ] SEC EDGAR API integration (edgartools library)
- [ ] Earnings transcript ingestion pipeline → RAGFlow
- [ ] 10-K / 10-Q PDF ingestion → RAGFlow table-aware parsing
- [ ] Equity researcher queries RAGFlow + runs simple DCF on parsed statements
- [ ] Output: `equity_context.json` per ticker → Supabase

### Phase 6 — P&L Attribution + Statistical Researcher
- [ ] P&L Attribution Agent: daily report, maps outcomes → regime → zone score → sizing
- [ ] Every trade gets a `logic_trace.md` entry (explainability / audit trail)
- [ ] Statistical Researcher: regime-conditioned hit-rate tables per instrument

### Phase 7 — XGBoost Zone Scorer v1
- [ ] Requires Phase 4 data (minimum 500 zone outcome records)
- [ ] Feature engineering from zone outcome table
- [ ] XGBoost training pipeline + permutation test gate
- [ ] Model artifacts stored in Supabase Storage
- [ ] Score injected into trading_context.json

### Phase 8 — Execution Bridge
- [ ] Supabase `trading_context.json` → MT5 EA polling
- [ ] sigma-crypto Binance integration
- [ ] Dead Man's Switch: context > 24h old → auto-drop to 0.5x sizing

### Phase 9 — Gemma 4 Fine-Tuning (LoRA)
- [ ] Requires Phase 4 data accumulated (500+ zone outcome records with reasoning)
- [ ] LoRA fine-tuning dataset: zone context → quality reasoning → outcome
- [ ] Training via Unsloth (memory-efficient, works on 8GB VRAM)
- [ ] Fine-tuned model replaces base Gemma 4 9B in Macro + Micro agents

### Phase 10 — LSTM Regime Classifier
- [ ] Multi-timeframe macro time-series features
- [ ] LSTM training pipeline
- [ ] Regime label becomes an additional feature in XGBoost zone scorer

### Phase 11 — sigma-quant Intelligence Page Redesign
- [ ] User confirmed: wants premium terminal redesign, not the amateur version
- [ ] Design discussion required before implementation — DO NOT build without user design approval
- [ ] Must feel like Bloomberg / institutional terminal

### Phase 12 — baysix-platform New App
- [ ] New Next.js app (separate from sigma-quant)
- [ ] Stack: Next.js 15, shadcn/ui, TanStack Query, TanStack Table, ECharts, Supabase Realtime
- [ ] 5 core views: Terminal, Research, Operations, P&L, Knowledge Base
- [ ] Connects to FastAPI backend via REST + WebSocket
- [ ] Agent trigger panel (fire cycles, see what's running, stop cycles)

### Phase 13 — OCI ARM Migration
- [ ] Migrate FastAPI + LangGraph orchestrator to Oracle Cloud ARM (free tier)
- [ ] Supabase IPC bus means MT5 + sigma-quant work regardless of where orchestrator runs

---

## 6. Key Design Principles (Do Not Violate)

1. **The AI does not discover strategies. It learns to deploy one strategy better.** — B2B zones are the edge. AI learns when/where the edge works.
2. **No LLM execution rule.** — LLMs generate context and signals. They never call broker APIs.
3. **Two kill switches always.** — EA hard limits (local) + AI `kill_switch` flag (Supabase).
4. **Sealed core rule.** — `sigma_core` source never enters any LLM context window.
5. **ML gate rule.** — No model version deploys without permutation test p < 0.05.
6. **Code gate rule.** — No code runs without code-reviewer APPROVED verdict.
7. **Research gate rule.** — No research reaches CIO without peer-reviewer APPROVED verdict.
8. **Local-first LLM.** — Route to Gemma 4 local before cloud. Cloud only for highest-stakes reasoning.
9. **RAG for text, SQL for numbers.** — Never use vector search for structured/numerical data.
10. **Checkpointing is not optional.** — PostgresSaver from Phase 0, not retrofitted later.

---

## 7. Immediate Next Actions (When Resuming)

**Step 1:** Confirm Docker Desktop is installed and running
```powershell
docker --version
docker compose version
```

**Step 2:** Check if Ollama is already installed
```powershell
ollama --version
ollama list  # see what models are already pulled
```

**Step 3:** Pull Gemma 4 (or best available) locally
```powershell
ollama pull gemma3:9b       # if gemma4 not yet available
# or
ollama pull gemma4:9b       # if released
```

**Step 4:** Get Supabase direct DB connection string
- Go to Supabase dashboard → Settings → Database → Connection String → URI (not pooler)
- Add to `sigma-research/.env` as `SUPABASE_DB_URL=postgresql://...`

**Step 5:** Start building Phase 0 — docker-compose.yml + FastAPI skeleton + PostgresSaver checkpointer

---

## 8. What NOT to Do When Resuming

- ❌ Do NOT rebuild the sigma-quant Intelligence page without user design approval first
- ❌ Do NOT add more agent nodes before Phase 0 checkpointing is wired
- ❌ Do NOT use RAG for numerical/structured quant data
- ❌ Do NOT start the XGBoost model before Phase 4 feedback loop is collecting data
- ❌ Do NOT run Gemma 4 and ML training simultaneously (8GB VRAM cannot support both)
- ❌ Do NOT push to GitHub without checking `.env` files are excluded

---

## 9. Open Design Decisions (Still Need User Input)

| Decision | Options | Status |
|---|---|---|
| baysix-platform scope | Operational only / Portfolio+Operational hybrid | ⏳ Pending user decision |
| sigma-quant Intelligence page design | Premium terminal — design needed | ⏳ Pending design brainstorm |
| Gemma 4 specific version tag | gemma4:9b / gemma3:9b / other | ⏳ Depends on what Ollama has |

---

## 10. Repository Map

| Repo | Path | GitHub | Access |
|---|---|---|---|
| sigma-brain | `C:\Users\User\Desktop\sigma-brain` | github.com/smz3/sigma-brain | Private |
| sigma-quant | `C:\Users\User\Desktop\sigma-quant` | github.com/smz3/SIGMA-Quant | Public |
| sigma-research | `C:\Users\User\Desktop\sigma-research` | Not pushed yet | — |
| sigma-crypto | `C:\Users\User\Desktop\sigma-crypto` | Not pushed | — |

---

*This document is the source of truth for the next build phase. Keep it updated as decisions are made and phases complete.*
