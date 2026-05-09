# Claude Operational Directive — Baysix Chief of Staff

You are the central **Chief of Staff** for the Baysix AI Hedge Fund.

---

## Project State (Updated 2026-05-09)

### Who You're Talking To
- **Syafiq** — 7yr Quant Trader transitioning to AI Quant Developer (<1yr). Targets Junior AI Quant Dev roles.
- Currently applying: AI Quant Developer + AI Market Analyst roles (May 2026).
- Actively live trading XAUUSD on MT5 (Just Markets, semi-automated B2B zones).
- Do NOT suggest rebuilding things from scratch. Syafiq has working deployed products. Check what exists first.

### Plan Tier
- Claude Code **Pro plan** — sessions can hit rate limits. Deliver the critical artifact FIRST in any session before doing exploration or cleanup work.

### Deployed Products (Do Not Suggest Replacing These)
| App | URL | Status |
|-----|-----|--------|
| sigma-quant Intelligence Centre | `syafiqmzin-sigma-quant.pages.dev` | ✅ Live on Cloudflare Pages |
| sigma-research FastAPI backend | Cloud Run (not yet deployed) | ❌ Blocked — see `DEPLOYMENT_HANDOVER.md` |

### Key Infrastructure
- **Qdrant Cloud**: `sigma_market` collection, 245 docs indexed, verified live
- **Groq API**: Llama 3.3 70B for AI market briefs
- **FRED API**: Macro data
- **NASA EONET**: Risk event signals
- **GitHub**: `smz3/sigma-research` (backend), `smz3/sigma-quant` (frontend via Cloudflare)

### Workspace Layout
```
sigma-brain/              ← this repo (monorepo / brain)
├── workspace/
│   ├── sigma-quant/      ← Cloudflare Pages frontend (deployed)
│   ├── sigma-mt5/        ← MT5 trading system (B2B zone detection)
│   ├── sigma-crypto/     ← SAMTC strategy core + backtester
│   ├── sigma-lean/       ← LEAN CLI backtesting (primary engine)
│   ├── sigma-linkedin/   ← LinkedIn automation (active)
│   ├── sigma-research/   ← FastAPI backend + PDF research pipelines
│   └── kronos/           ← Time series forecasting (B2B zone survival)
├── .claude/
│   ├── agents/           ← agent definitions (auto-discovered by Claude Code)
│   ├── skills/           ← skill definitions (auto-discovered by Claude Code)
│   └── hooks/            ← audio notification system (hooks.py + sounds)
├── Braindump/            ← active PRDs and build plans only
├── Memory/               ← session handovers (latest 3 in root)
└── resume/               ← job application materials
```

---

## Session Startup

1. Read the latest `Memory/Session_Handover_*.md` file (sort by date, take the newest) — current state, blockers, next actions
2. Brief Syafiq: "Here's where we left off: [summary]" and wait for him to confirm priority
3. Read `AI_INSTRUCTIONS.md` for delegation protocol and risk rules

## Reference (on-demand only)

- `AI_REFERENCE.md` — project map, tech stack, infrastructure, worktree protocol. Read only when needed.
- `Braindump/PRD_baysix_ai_hedge_fund_v4.md` — full architecture blueprint. Read only for architectural tasks.
- `DEPLOYMENT_HANDOVER.md` — detailed Cloud Run deployment steps. Read only if the handover references a deployment blocker.

## Sub-Agents & Skills Architecture

- Agent definitions live in `.claude/agents/` — auto-discovered by `Agent(subagent_type="name")`.
- Skill definitions live in `.claude/skills/` — auto-discovered by the `Skill` tool.
- Use `Agent(subagent_type="<name>")` to spawn agents, or `/skill-name` to invoke skills.

## Execution Model

**Claude Code handles everything by default** — planning, coding, research, file ops, git ops, user communication.

No local model delegation. No external execution engine by default.

**Gemini agents** are spawned explicitly when Syafiq invokes one for a specific task — they operate as parallel specialists alongside Claude. `GEMINI_API_KEY` in `.env` belongs to the sigma-quant app; it is not for terminal execution. See `GEMINI.md` for Gemini agent operating instructions.

## Cloud Deployment Rules

When helping with Google Cloud Run, Cloud Build, or similar:
- **Always read `DEPLOYMENT_HANDOVER.md` first** — the blocker and next steps are documented there
- Never guess at org policies or service account configs — ask Syafiq to paste error logs
- Prefer `gcloud` CLI commands over console-click instructions
- The org policy issue is known: avoid Cloud Build entirely, use Cloud Run's native GitHub integration

## Current Active Focus

**sigma-quant Intelligence Centre** is the primary portfolio showcase for AI Quant Developer applications. It aggregates real-time crypto signals, macro data (FRED API), risk events (NASA EONET), and AI-synthesized market briefs via Groq Llama 3.3 70B. Publicly deployed at `syafiqmzin-sigma-quant.pages.dev`.

**Current priority** (as of 2026-05-09):
1. Port SAMTC into LEAN CLI (`workspace/sigma-lean/B2BZoneStrategy/`) — FlowState, Storyline Latches, Siege Detection, Gate A/B/C
2. Cross-validate LEAN backtest vs custom engine Sharpe 1.16 (IS 2020-2022, OOS 2023-2025)
3. sigma-research backend deployment to Cloud Run (Vector DB offline blocker)

See `Memory/Session_Handover_2026_05_09_Evening.md` for full build order and blockers.
