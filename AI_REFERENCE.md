# Sigma-Brain — Reference & Directives

> **Non-Claude AI agents:** read this entire file at session start.  
> **Claude Code:** behavioral sections (Identity through Session Protocol) are always active. Project/infra sections are on-demand.

---

## Identity & QR Standard

**Who you're working for:** Syafiq M. Zin — 7yr Quant Trader, building toward **Quant Researcher (deployable)**. NOT an AI Quant Dev.  
**Target firms:** Balyasny Asset Management + Millennium Management (Tier C multi-manager pod shops, direct approach). NOT Quantedge, Dymon, or GIC.  
**Career goal chain:** QR Job → Experience → Launch own fund → Family Office → Private Family Office.

**QR framing — strategy-dependent metric language (do NOT default to IC):**
- **Match the primary metric to the idea type** (Tier 2): IC/ICIR/IC-decay *only* for cross-sectional return-prediction; hit rate / predictive accuracy for timing; MAE-MFE / trend consistency for momentum-breakout; half-life / z-score stability for mean reversion; order-flow imbalance / fill rate for microstructure. Forcing IC onto a single-asset timing edge (XAUUSD B2B) is a category error.
- **Speak validity + survival regardless of idea type:** honest `N_trials`, net Sharpe, Calmar, ruin probability, OOS/IS stability, DSR/PSR. Universal; the edge metric is not.
- "Signal capacity estimated at $50M before market impact exceeds alpha" — not "it's scalable"
- "Gate PASSED / FAILED" — not "looks good / doesn't work"

**Research standard:** (canonical methodology = [BAYSIX_FRAMEWORK.md](BAYSIX_FRAMEWORK.md))
- research-engine is the hypothesis-testing factory — measurement-first, falsification-first, idea-appropriate primary metric on every signal
- lean-engine (`research-engine/core/engines/lean-engine`) is the execution survival gate — "can I capture the alpha?" (run after research validates a signal)
- b2b-mt5 (`trading-engine/mt5-path/`) is the production layer — MQL5 EA for Just Markets and Darwinex Zero
- B2B knowledge base: `vault/wiki/strategy/b2b-overview.md`

---

## Three-Venue Deployment Model (Locked 2026-05-20 — DO NOT COLLAPSE)

| Venue | Broker | Instruments | Purpose |
|-------|--------|-------------|---------|
| **Just Markets** | MT5 | XAUUSD (high leverage, no holds barred) | Personal live trading — monetize proven B2B edge now |
| **Darwinex Zero** | MT5 | Futures (real CME/Eurex exchange) + ETFs (IBKR-routed, real exchange) | Allocatable track record → external capital. NOT CFD. |
| **IBKR Paper** | IBKR API | Cross-sectional equities | Demonstrate pod-shop-grade alpha to BAM/Millennium |

The Research Engine (research-engine) measures edge. Surviving edges are routed to the appropriate venue adapter in trading-engine.

---

## Delegation Protocol

**Rule #1: Delegate before you do.** If a task belongs to a specialist, spawn that agent.

### Agent Roster

| Task Class | Agent | Notes |
|-----------|-------|-------|
| Strategy research, hypothesis testing | `quant-researcher` | Orchestrates full research pipeline |
| Code changes, backtests, builds | `quant-developer` | Must use worktree + code-reviewer gate |
| Signal monitoring, trade review | `quant-trader` | Read-only observer |
| Risk, drawdown, kill switch | `risk-manager` | Blocks unsafe actions |
| Memory synthesis, insight capture | `memory-curator` | Writes to Memory/ files |
| Strategic priority, allocation | `cio` | Final strategic call |

### Quality Gates

| Agent | Gate |
|-------|------|
| `code-reviewer` | ALL code must be APPROVED before execution |
| `peer-reviewer` | ALL research must be APPROVED before reaching CIO |

**How to spawn:** `Agent(subagent_type="<name>")`. Pass full context (user request + file paths + prior findings). Synthesize findings for the user.

---

## Risk Rules (Non-Negotiable)

1. **Never authorize live trades without explicit human confirmation**
2. **Never push to git remotes without user approval**
3. **Never expose API keys** — read from .env, never print them
4. **Never delete files** without telling the user first
5. **Always report drawdown breaches** to the risk-manager before proceeding
6. **Two-key rule**: Any live execution action requires both your assessment AND user confirmation
7. **Code gate**: No code runs without code-reviewer APPROVED verdict
8. **Research gate**: No research reaches CIO without peer-reviewer APPROVED verdict

---

## Session Protocol

### Startup
1. Read the latest `Memory/Session_Handover_*.md` (sort by date, take newest) — current state and next actions
2. Brief Syafiq: "Here's where we left off: [summary]" and wait for him to confirm priority

Notes:
- strategy_state, risk_parameters, research_queue are injected by the SessionStart hook — do NOT re-read them
- Never read files in `_archive/` directories unless explicitly asked

### Shutdown ("Sleep" command)
1. Halt execution and prioritize context preservation
2. Write `Memory/Session_Handover_[Date]_[Time].md` with:
   - **Accomplished:** what was completed
   - **WIP / Blockers:** what is broken or pending
   - **Next Action:** explicit first step for the next agent
3. Report: "Handover file created. Standing by."

### Output Standards
- Attribute which agent produced which finding
- Structure outputs: **Finding → Recommendation → Action Required**
- Flag anything requiring human approval with: `[REQUIRES APPROVAL]`

---

## Project Map

All sub-projects live inside `workspace/` — each is an independent git repo.

| Project | Path | Purpose |
|---------|------|---------|
| sigma-brain | `.` | HQ — orchestrator, agents, memory, vault |
| **baysix-engine** | `workspace/baysix-engine/` | Unified research + trading monorepo (ONE git repo). GitHub: smz3/baysix-engine |
| **research-engine** | `workspace/baysix-engine/research-engine/` | Alpha Research Engine — Python hypothesis factory (was sigma-are / alpha-engine). 5-step funnel |
| **b2b-mt5** | `workspace/baysix-engine/trading-engine/mt5-path/b2b-mt5/` | MQL5 Expert Advisor (B2B zones, XAUUSD live; was sigma-mt5). Junction-linked to MT5 |
| sigma-quant | `workspace/sigma-quant/` | Intelligence Centre frontend. Deployed: syafiqmzin-sigma-quant.pages.dev |
| sigma-research | `workspace/sigma-research/` | FastAPI backend — Qdrant vector search, Groq AI briefs |
| sigma-linkedin | `workspace/sigma-linkedin/` | LinkedIn automation (active) |

### baysix-engine Internal Structure (monorepo — restructured 2026-05-24; alpha-engine umbrella dissolved)
```
baysix-engine/
├── research-engine/               ← measures edge (was sigma-are/alpha-engine). 5-step funnel
│   ├── step1_ideation/            ← layers: deployment-profile · hypothesis-metric-lock (ideas/) · data-structure-gate
│   ├── step2_signal/              ← layers: signal-build · sizing
│   ├── step3_in-sample/           ← layers: gross-baseline · cost-haircut · event-based
│   ├── step4_validation/          ← layers: oos-walkforward-cpcv · full-cost · monte-carlo · snooping-audit
│   ├── step5_forward-fit/         ← layers: paper-forward · portfolio-fit-gate
│   ├── core/                      ← lib/ (corelib·dataset·db·idea_bank·tools) + engines/ (cost-venue·ic·factor-model·lean — tools steps CALL)
│   ├── data/  strategies/  research-note/  research-ledger/  notebooks/
├── trading-engine/                ← deploys surviving edge (was execution-engine; sibling of research-engine)
│   ├── portfolio-risk/  monitoring/
│   ├── mt5-path/{b2b-mt5, darwinex-zero, high-leverage-broker, retail-prop-firm}
│   └── api-path/{ibkr, moomoo-webull}
├── market-state-engine/           ← measurement layer (cross-asset·dealer-gamma·positioning·volatility·order-flow). SHARED by both engines
├── context-engine/                ← regime classification. SHARED (same code research validates + trading reads — no train/serve skew)
└── architecture-decisions/        ← ADRs; governs both engines
```

### Absolute Paths
- research-engine: `C:\Users\User\Desktop\sigma-brain\workspace\baysix-engine\research-engine`
- lean-engine: `C:\Users\User\Desktop\sigma-brain\workspace\baysix-engine\research-engine\core\engines\lean-engine`
- b2b-mt5: `C:\Users\User\Desktop\sigma-brain\workspace\baysix-engine\trading-engine\mt5-path\b2b-mt5`
- sigma-quant: `C:\Users\User\Desktop\sigma-brain\workspace\sigma-quant`
- sigma-research: `C:\Users\User\Desktop\sigma-brain\workspace\sigma-research`
- vault (B2B knowledge): `C:\Users\User\Desktop\sigma-brain\vault`

---

## Technology Stack

| Component | Role |
|-----------|------|
| research-engine | Python ARE — hypothesis factory, idea-appropriate primary-metric measurement |
| lean-engine | LEAN CLI — event-driven execution survival validation (`research-engine/core/engines/lean-engine`) |
| b2b-mt5 | MQL5 EA — B2B zones, Just Markets + Darwinex Zero production |
| sigma-quant | React/Next.js — Intelligence Centre, Cloudflare Pages |
| sigma-research | FastAPI — Qdrant vector search, Groq AI market briefs |
| yfinance / FRED API | Market + macro data (free tier) |
| Groq `llama-3.3-70b-versatile` | AI brief generation in sigma-quant |
| Qdrant Cloud | Vector DB — `sigma_market` collection, 245 docs |

---

## Infrastructure

| Component | Location | Purpose |
|-----------|----------|---------|
| Qdrant Cloud | `sigma_market` collection | Vector DB — powers Vector Context panel in sigma-quant |
| Groq API | cloud | Llama 3.3 70B for AI market briefs |
| FRED API | `api.stlouisfed.org` | Macro data (T10Y2Y, FEDFUNDS, CPI) |
| Cloudflare Pages | `syafiqmzin-sigma-quant.pages.dev` | Production deploy for Intelligence Centre |
| `.claude/agents/` | local | Specialized sub-agent definitions (auto-discovered) |
| `.claude/skills/` | local | SOPs and single-task operations (auto-discovered) |
| `vault/wiki/` | local | B2B knowledge base, strategy docs |
| `Braindump/` | local | Active PRDs and build plans (3 files max) |
| `Memory/` | local | Session handovers — read newest at startup |

---

## Worktree Protocol

All agent code changes happen in isolated git worktrees — never on main branch.

**Critical:** Each `workspace/` sub-project is its own independent git repo. Always create worktrees from the **sub-project's git root**, not sigma-brain root. NOTE: `baysix-engine/` is now ONE monorepo — research-engine, trading-engine, market-state-engine, context-engine, and lean-engine are all tracked by baysix-engine's single git root (`workspace/baysix-engine/`), not separate repos.

**Workflow:**
1. `cd` into the target sub-project root (e.g. `workspace/baysix-engine/` for any engine work)
2. Create worktree: `git worktree add ../../../<project>-<task> -b baysix/agent/<task>-<date>`
3. Make changes in isolation
4. Submit to code-reviewer → must receive APPROVED verdict
5. Return diff + approval to Chief of Staff
6. Chief of Staff presents `[REQUIRES APPROVAL]` to user
7. Human confirms → merge happens

**Branch naming:** `baysix/agent/<task-slug>-<YYYYMMDD>`

**Allowed:** `git worktree add`, `git checkout -b`, `git diff`, `git status`, `git log`  
**Denied:** `git push`, `git merge`, `git reset --hard`
