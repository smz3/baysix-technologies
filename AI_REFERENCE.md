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
- **Citations**: Every research claim must carry a CitationRecord (source, URL, date, confidence)

---

## Project Map

All sub-projects live as real directories inside `workspace/` — each is an independent git repo.

| Project | Workspace Path | Purpose |
|---------|---------------|---------|
| sigma-brain | `.` (this project) | HQ — orchestrator, agents, memory, plans |
| sigma-crypto | `workspace/sigma-crypto/` | Python SAMTC engine (backtesting + live crypto) |
| sigma-lean | `workspace/sigma-lean/` | LEAN CLI backtesting — sole backtest engine |
| sigma-quant | `workspace/sigma-quant/` | Intelligence Centre — public portfolio showcase. Live: syafiqmzin-sigma-quant.pages.dev |
| sigma-research | `workspace/sigma-research/` | FastAPI backend — Qdrant vector search, Groq AI briefs |
| sigma-mt5 | `workspace/sigma-mt5/` | MQL5 Expert Advisor (B2B zones, Forex) |
| sigma-linkedin | `workspace/sigma-linkedin/` | AI LinkedIn content manager (active) |
| kronos | `workspace/kronos/` | Time series forecasting — B2B zone survival prediction |

Absolute paths (use these when working on specific projects; their code is inside `workspace/`):
- sigma-crypto: `C:\Users\User\Desktop\sigma-brain\workspace\sigma-crypto`
- sigma-lean: `C:\Users\User\Desktop\sigma-brain\workspace\sigma-lean`
- sigma-quant: `C:\Users\User\Desktop\sigma-brain\workspace\sigma-quant`
- sigma-research: `C:\Users\User\Desktop\sigma-brain\workspace\sigma-research`
- sigma-mt5: `C:\Users\User\Desktop\sigma-brain\workspace\sigma-mt5`
- sigma-linkedin: `C:\Users\User\Desktop\sigma-brain\workspace\sigma-linkedin`
- kronos: `C:\Users\User\Desktop\sigma-brain\workspace\kronos`

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
| Qdrant Cloud | `sigma_market` collection (cloud) | Vector DB — 245 docs indexed, powers Vector Context panel |
| Groq API | cloud | Llama 3.3 70B for AI market briefs in sigma-quant |
| Supabase | API endpoint | IPC bus for sigma-research/sigma-quant inter-project comms |
| FRED API | `api.stlouisfed.org` | Macro data (T10Y2Y, Yield Curve Spread; FEDFUNDS; CPI) |
| Cloudflare Pages | `syafiqmzin-sigma-quant.pages.dev` | Production deploy for Intelligence Centre public portfolio showcase |
| Skills | `.claude/skills/` | SOPs and single-task operations (auto-discovered) |
| Agents | `.claude/agents/` | Specialized sub-agent definitions (auto-discovered) |
| Build plans | `Braindump/` | Active PRDs and build plans (3 files max — archive the rest) |

---

## Worktree Protocol

All code changes by agents happen in isolated git worktrees — never on main branch.

**Critical**: Each sub-project in `workspace/` is its own independent git repo. Worktrees must be created from **that sub-project's git root**, not from sigma-brain root. Example: to work on sigma-crypto, `cd workspace/sigma-crypto` first, then run `git worktree add`.

**Workflow:**
1. quant-developer `cd`s into the target sub-project root (e.g. `workspace/sigma-crypto/`)
2. Creates worktree: `git worktree add ../../<project>-<task> -b baysix/agent/<task>-<date>`
3. Makes changes in isolation
3. Submits to code-reviewer → must receive APPROVED verdict
4. Returns diff + approval to Chief of Staff
5. Chief of Staff presents to user: `[REQUIRES APPROVAL]` to merge to main
6. Human confirms → merge happens

**Branch naming:** `baysix/agent/<task-slug>-<YYYYMMDD>`

**Allowed git ops for agents:** `git worktree add`, `git checkout -b`, `git diff`, `git status`, `git log`
**Denied git ops:** `git push`, `git merge`, `git reset --hard`
