# Sigma-Brain — Reference Manual

> On-demand reference. Read sections as needed — do NOT load this entire file at session start.

---

## Research Philosophy (Hybrid — Three Legends)

1. **Ray Dalio layer (Macro Regime)** — Economic machine model (growth/inflation/liquidity) determines the regime. Top-level filter that gates everything below.
2. **Point72 layer (Sector/Instrument Selection)** — Within the regime, fundamental + quantitative analysis selects which asset classes and instruments have edge.
3. **Paul Tudor Jones layer (Risk Management)** — Obsessive risk management. Position sizing, stop placement, correlation risk, drawdown limits.

---

## Technology Stack

- **Orchestrator**: LangGraph `StateGraph` running in `sigma-research` (local machine → OCI ARM later)
- **LLM — Speed**: Groq `llama-3.3-70b-versatile` — structured JSON agent outputs
- **Data**: FRED API, yfinance, CCXT (crypto), NLP news scrapers — all free
- **IPC Bus**: Supabase (shared with sigma-quant) — `trading_context.json`, zone outcomes, agent logs
- **Sealed Core**: `sigma_core` `.pyd` binary — B2B engine, never exposed to LLM context
- **ML Models**: XGBoost (zone scorer), LSTM (regime classifier) — built on accumulated zone outcome data
- **Local LLMs**: Ollama (localhost:11434) — development and offline testing only (qwen2.5:7b, mistral:7b, others as configured)
- **Citations**: Every research claim must carry a CitationRecord (source, URL, date, confidence)

---

## Project Map

All sub-projects are accessible via `workspace/` junctions from sigma-brain root.

| Project | Workspace Path | Purpose |
|---------|---------------|---------|
| sigma-brain | `.` (this project) | HQ — orchestrator, agents, memory, PRD |
| sigma-research | `workspace/sigma-research/` | Python research infra (data pipelines, Qdrant, reports, local LLM) |
| sigma-crypto | `workspace/sigma-crypto/` | Python SAMTC engine (backtesting + live crypto) |
| sigma-mt5 | `workspace/sigma-mt5/` | MQL5 Expert Advisor (B2B zones, Forex) |
| sigma-quant | `workspace/sigma-quant/` | Intelligence Centre — public portfolio showcase. Live: syafiqmzin-sigma-quant.pages.dev |
| sigma-linkedin | `workspace/sigma-linkedin/` | AI LinkedIn content manager |
| sigma_core | `workspace/sigma_core/` | B2B math engine (compiled binary) |

Absolute paths (use if workspace/ junction unavailable):
- sigma-research: `C:\Users\User\Desktop\sigma-research`
- sigma-crypto: `C:\Users\User\Desktop\sigma-crypto`
- sigma-mt5: `C:\Users\User\Desktop\sigma-mt5`
- sigma-quant: `C:\Users\User\Desktop\sigma-quant`
- sigma-linkedin: `C:\Users\User\Desktop\sigma-linkedin`
- sigma_core: `C:\Users\User\Desktop\sigma-brain\workspace\sigma_core`

---

## Research Sub-Agents (spawned by quant-researcher, NOT by Chief of Staff directly)

| Agent | Role |
|-------|------|
| `macro-researcher` | Dalio layer — macro regime detection (DXY, yields, liquidity, cross-asset) |
| `micro-researcher` | Point72 layer — zone stats, instrument edge, entry precision |
| `equity-researcher` | Point72 layer — SEC filings, earnings, DCF, peer benchmarking |
| `fixed-income-researcher` | Point72 layer — duration risk, credit spreads, yield curve |
| `mathematician` | Statistical validation gatekeeper |
| `peer-reviewer` | Research quality gate — APPROVED required before CIO |
| `research-data-agent` | Shared data utility — fetches and caches market data for all researchers |

---

## Memory System

State files loaded by SessionStart hook (do NOT re-read manually):

- `Memory/strategy_state.md` — Current SAMTC version, active hypothesis, last backtest result
- `Memory/risk_parameters.md` — Current risk limits, kill switch conditions, max drawdown
- `Memory/research_queue.md` — Pending research tasks

On-demand reference files:
- `Memory/alpha_insights.md` — Discovered edges and pattern notes
- `Memory/agent_delegation_map.md` — Agent ownership map

After significant work, instruct the memory-curator to update these files.

---

## Infrastructure

| Component | Location | Purpose |
|-----------|----------|---------|
| Qdrant | `localhost:6333` (local binary) | Vector DB — semantic search over all research, citations, alpha insights |
| Ollama | `localhost:11434` (local) | Local LLMs — qwen2.5:7b (sentiment), mistral:7b (cross-check) |
| Supabase | API endpoint | IPC bus for sigma-research/sigma-quant inter-project comms (`trading_context.json`, zone outcomes, agent logs) |
| FRED API | `api.stlouisfed.org` | Macro data (T10Y2Y, Yield Curve Spread; FEDFUNDS, Interest Rates; CPI, Inflation) |
| Cloudflare Pages | `syafiqmzin-sigma-quant.pages.dev` | Production deploy for Intelligence Centre public portfolio showcase |
| Paperclip | `Management/paperclip/` (port 3100) | Task board — active_tickets/, completed_tickets/ |
| OpenFang | `Agents/openfang/` (port 4200) | Future: 24/7 background agents, Telegram alerts |
| Always-On Memory | `Memory/always-on-memory-agent/` | Reads trade logs every 30 min, writes to memory.db |
| Skills | `Skills/` | SOPs and single-task operations |
| Agents | `Agents/` | Contexts for isolated subagent operations |
| Audit | `Audit/` | Cost tracker, heartbeats, security alerts |
| Sandbox | `Sandbox/` | Agent-generated code review area |
| PRD | `Braindump/PRD_baysix_ai_hedge_fund_v4.md` | Full architecture blueprint — the source of truth |

---

## Worktree Protocol

All code changes by agents happen in isolated git worktrees — never on main branch.

**Workflow:**
1. quant-developer creates worktree: `git worktree add ../<project>-<task> -b baysix/agent/<task>-<date>`
2. Makes changes in isolation
3. Submits to code-reviewer → must receive APPROVED verdict
4. Returns diff + approval to Chief of Staff
5. Chief of Staff presents to user: `[REQUIRES APPROVAL]` to merge to main
6. Human confirms → merge happens

**Branch naming:** `baysix/agent/<task-slug>-<YYYYMMDD>`

**Allowed git ops for agents:** `git worktree add`, `git checkout -b`, `git diff`, `git status`, `git log`
**Denied git ops:** `git push`, `git merge`, `git reset --hard`
