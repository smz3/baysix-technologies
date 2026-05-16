# Session Handover — May 9, 2026 (Night — SAMTC V6.7 ported into sigma-lean)

## What Was Accomplished This Session

### 1. Workspace Consolidation — sigma_core orphan deleted

Audited all four workspace folders (sigma-research, sigma_core, sigma-crypto, sigma-lean) and found three copies of the same B2B detection logic:
- `workspace/sigma-crypto/core/` — original source (has git remote)
- `workspace/sigma_core/sigma_core/b2b/` — orphan Cython package (no git, no consumers)
- `workspace/sigma-lean/sigma_core/b2b/` — operational mirror (what LEAN actually uses)

**Actions taken:**
- Deleted `workspace/sigma_core/` entirely (no GitHub impact — no remote)
- Updated `workspace/sigma-lean/CLAUDE.md` to document the two-copy architecture
- Created `workspace/scripts/sync_core.sh` — one command to sync sigma-crypto/core → sigma-lean/sigma_core/b2b when B2B detection logic changes

### 2. Feasibility Analysis — Research + Crypto inside LEAN

Explored whether sigma-research and sigma-crypto can be consolidated into sigma-lean. Verdict:
- **sigma-research → leave alone** — separate GitHub remote (`smz3/sigma-research`), serves MT5 EA + sigma-quant frontend via Supabase, completely different domain (AI pipeline)
- **sigma-crypto → leave alone** — separate GitHub remote (`smz3/sigma-crypto`), stays as SAMTC source of truth
- **sigma-lean = the integration layer** — where both signal sources converge
- **Phase 1 (done this session):** port sigma-crypto's SAMTC logic into sigma-lean
- **Phase 2 (future):** add sigma-research rule-based macro regime as a pre-generated CSV overlay (VIX/CPI rules, not LLM — LLM signals can't be backtested deterministically)

### 3. SAMTC V6.7 Port into sigma-lean — COMPLETE (code written, not yet run)

Ported the full SAMTC orchestration layer from sigma-crypto into sigma-lean. All files written and import-verified. No backtest run yet.

**New files created:**
```
workspace/sigma-lean/sigma_core/b2b/strategy/
├── __init__.py
├── orchestrator.py          ← V6.7 Gate A / B / C, Storyline Latches
└── engines/
    ├── __init__.py
    ├── fracture_engine.py   ← Origin / Outpost / Magnet identification
    ├── state_manager.py     ← Per-TF FlowState, siege logic, successor promotion
    └── efficiency_governor.py ← Tier Gating, Structural Gasket, Structural Memory
```

**`workspace/sigma-lean/B2BZoneStrategy/main.py` — fully rewritten:**

| Before | After |
|--------|-------|
| H1 only | H1 primary + H4/D1/W1/MN1 via LEAN Consolidators |
| Enter on any L1 touch (T1) | `is_trade_allowed()` gate — T2/T3 only on H1 (T1 muted by tier gating) |
| No HTF narrative context | `update_flow_state()` called every H1 bar with all 5 TF zone lists |
| No SL feedback | SL hit → `report_trade_failure()` → Structural Memory |
| 500-bar warmup | 3000-bar warmup (~4 months for MN1 context to build) |

**`workspace/scripts/sync_core.sh`** — updated to also sync `strategy/` folder.

**Import verification:** Zero relative imports (`from ...`) in any strategy file. All use `from sigma_core.b2b.*` absolute paths.

**Known gap:** `main.py` date range is still `2024-01-01 → 2024-03-31` (placeholder). Must be updated before running cross-validation.

---

## What Is NOT Done / Still Open

- **Date range not updated** — `main.py` line 89-90 has `SetStartDate(2024, 1, 1)` / `SetEndDate(2024, 3, 31)`. Must change to IS period (`2020-01-01 → 2022-12-31`) before running cross-validation. OOS period (`2023-01-01 → 2025-12-31`) is a separate run.
- **No backtest run yet** — SAMTC port is code-complete but not validated in LEAN
- **Cross-validation not done** — IS + OOS Sharpe comparison vs custom engine's 1.16 still open
- **Monte Carlo not run** — `sigma-crypto/scripts/monte_carlo_validation.py` needs to be fed LEAN's trade log CSV output
- **VWAP, Mean Reversion, Trend Following, Orderflow strategies** — not started (Steps 2–5 of build order)
- **IBKR Paper Account** — Syafiq needs to register at interactivebrokers.com (free, instant)
- **FCPO data** — no confirmed source yet; Yahoo Finance `FCPO.KL` to be tested
- **sigma-research Phase 2 overlay** — rule-based macro regime CSV for LEAN (deferred after SAMTC validates)

---

## Running Processes

None

---

## Priority for Next Session

1. **Update date range in `main.py`** — change lines 89-90:
   - IS run: `SetStartDate(2020, 1, 1)` / `SetEndDate(2022, 12, 31)`
   - After IS run passes, separately set OOS: `SetStartDate(2023, 1, 1)` / `SetEndDate(2025, 12, 31)`

2. **Run `/check-lean-health`** — confirm Docker is up before anything else

3. **Run IS backtest** — `/run-backtest` with IS date range. Compare Sharpe vs custom engine baseline. Then run OOS.

4. **Run 3x Monte Carlo** — feed LEAN trade log CSV to `workspace/sigma-crypto/scripts/monte_carlo_validation.py`. All 3 must pass (Trade Shuffle, Parametric, Block Bootstrap).

5. **Decision point after validation** — if Sharpe < 1.0 in LEAN, debug gate logic. If Sharpe ≥ 1.16 (matching custom engine), SAMTC is validated. If Sharpe > 1.16, the H1 tier gating (blocking T1) is adding alpha.

---

## Key Decisions Made

- **sigma-lean is the integration layer**: sigma-research and sigma-crypto stay as separate repos with their own GitHub remotes. sigma-lean pulls from both as needed.
- **H1 T1 entries are blocked by design**: `EfficiencyGovernor.is_tier_allowed('H1', 'T1')` returns False — this is correct SAMTC V6.7 behavior. H1 requires T2 (50% touch) or T3 (L2 touch) to enter.
- **MN1 consolidated via `timedelta(days=30)`**: This is an approximation. If MN1 zone timing becomes critical, upgrade to LEAN's `CalendarType.Monthly` consolidator (flagged for future review).
- **sigma-research LLM signals cannot be backtested**: Only rule-based regime signals (VIX/CPI/yield spread thresholds) can be pre-generated for LEAN. LLM inference is non-deterministic.

---

## Blockers

- **LEAN backtest not yet run** — code is written but unvalidated. Run `/check-lean-health` first (Docker dependency).
- **IBKR Paper Account** — blocks live demo wiring (Step 8 of build order). Syafiq needs to register.
- **FCPO data source** — blocks Trend Following strategy on FCPO (Yahoo Finance `FCPO.KL` untested).
