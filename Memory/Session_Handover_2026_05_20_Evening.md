# Session Handover — May 20, 2026 (Evening — repo scorched-earth reset + architecture lock)

## What Was Accomplished This Session

### 1. Scorched-Earth Repo Reset
Deleted all legacy and competing architecture documents to stop session drift:
- Deleted `workspace/baysix-engine/Research/` entirely (ADRs 001-006, ENGINE_BLUEPRINT.md, RESEARCH_FRAMEWORK.md, engine-architecture/, engine-diagram/, _superseded/)
- Deleted sigma-lean contents (crypto-era B2BZoneStrategy/, duplicate sigma_core/) — kept lean.json + parquet_to_lean.py, renamed folder to `lean-engine`, moved inside sigma-are
- Deleted `GEMINI.md`, `AI_INSTRUCTIONS.md`, `DEPLOYMENT_HANDOVER.md`
- Deleted stale resume/, `_archive/BAYSIX_CONTEXT_BRIEF.md`
- Deleted sigma-are's crypto/SAMTC era: `_archive/`, `core/`, `scripts/tools/`, `reports/`, `tests/`

### 2. Architecture Locked (2026-05-20)
Three-venue model defined and locked in CLAUDE.md — do NOT redesign:
| Venue | Broker | Instruments | Purpose |
|-------|--------|-------------|---------|
| Just Markets | MT5 | XAUUSD (high leverage) | Personal live trading |
| Darwinex Zero | MT5 | Futures (CME/Eurex real exchange) + ETFs (IBKR-routed) | Allocatable track record |
| IBKR Paper | IBKR API | Cross-sectional equities | BAM/Millennium demonstration |

sigma-are = Alpha Research Engine (hypothesis-testing factory). lean-engine = execution survival gate. sigma-mt5 = production.

### 3. sigma-are Restructured
New clean layout committed to `smz3/sigma-are` (commit `b4a122e`):
```
sigma-are/
├── research-engine/        ← renamed from research/ to differentiate from sigma-research
│   ├── data/quant-data-manager/
│   ├── notebooks/          ← 3 notebooks: 00_data_audit, 02_ic_measurement_v2, 03_cost_adjusted
│   └── strategies/b2b-gold/
│       ├── b2b-pyscripts/  ← B2B Python detectors (b2b_engine, swing_points, zone_manager, etc.)
│       └── b2b-markdowns/  ← B2B strategy docs (B2B_STRATEGY_MASTER, hypothesis, decisions, etc.)
├── lean-engine/            ← LEAN CLI gate (lean.json + scripts/parquet_to_lean.py)
└── brokers/                ← venue stubs (darwinex-zero, ibkr, high-leverage, moomoo-webull, retail-prop-firm)
```
Data files (.parquet, .csv) excluded via .gitignore — stay local only.

### 4. Governance Docs Consolidated and Rewritten
- `CLAUDE.md` — fully rewritten: three-venue model, architecture lock, updated workspace layout, writing style rules (simple words, clickable markdown links)
- `AI_REFERENCE.md` — merged AI_INSTRUCTIONS.md into it; now single source for directives + reference
- `AI_INSTRUCTIONS.md` — deleted (consolidated into AI_REFERENCE.md)
- `GEMINI.md` — deleted (user confirmed not relevant)
- `.mcp.json` — removed playwright, kept context7 + supabase
- `.gitignore` — removed stale Research/brokers/lean-engine negations; workspace section simplified

### 5. Global Claude Config Created
`C:\Users\User\.claude\CLAUDE.md` created with two global rules:
- Simple words, straight forward delivery
- Always use markdown link syntax for file references (clickable in VS Code)

### 6. Both Repos Pushed
- sigma-brain: `smz3/sigma-brain` commit `235d541` — 92 files, 9399 deletions
- sigma-are: `smz3/sigma-are` commit `b4a122e` — 166 files, 54914 deletions

---

## What Is NOT Done / Still Open

- `research-engine/` framework is empty — no data pipeline, no IC measurement runner, no signal registry. Just notebooks and moved Python files. Needs to be rebuilt from scratch with correct structure.
- `research-engine/data/quant-data-manager/` — exists but not wired up. XAUUSD H1 parquet is local only (gitignored).
- lean-engine has `lean.json` and `parquet_to_lean.py` but no active LEAN strategy configured for the new structure.
- sigma-mt5 untouched this session — no changes made.

---

## Running Processes

None

---

## Priority for Next Session

1. **Rebuild research-engine framework** — design the foundational structure: data pipeline (fetch → validate → store), signal measurement runner (IC/ICIR/decay), and signal registry. Start from first principles. Key path: `workspace/baysix-engine/sigma-are/research-engine/`
2. Define what "one completed signal" looks like end-to-end through the ARE pipeline — from raw data to IC measurement output
3. Decide on quant-data-manager role: is it a standalone module or integrated into research-engine?

---

## Key Decisions Made

- **lean-engine lives inside sigma-are** (not at baysix-engine level) — user preference
- **research-engine** (not research/) — renamed by user to differentiate from sigma-research FastAPI backend
- **AI_REFERENCE.md is the single source** for all agent directives + reference — AI_INSTRUCTIONS.md deleted
- **Architecture is locked** — the only thing that can change it is a validated measurement from sigma-are
- **Darwinex Zero uses real exchange instruments** — futures via CME/Eurex, ETFs via IBKR routing. NOT CFD.

---

## Blockers

None
