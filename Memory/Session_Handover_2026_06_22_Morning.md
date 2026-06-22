# Handover — June 22, 2026 Morning

## State (DESIGN session — Protocol 4.0 settled, nothing built yet)
- Full discuss-only session redesigning the research protocol. No code, no DB changes.
- BRC-001 IS ledger remains FROZEN = run 5 (strategy_log #54), untouched.
- Output = an agreed architecture for a clean rebuild next session.

**Decisions locked (Protocol 4.0 — "Lean Gates"):**
- **Gates 7 → 4.** Driven by Syafiq's 7yr-trader definition of a good strategy: (a) smooth equity curve, (b) acceptable drawdown, (c) holds under cost + walk-forward + Monte Carlo.
- **G1 Premise** — idea + simple rule + thesis. No code.
- **G2 Edge & Survival** — IS net-of-cost equity curve smooth + DD acceptable. The IS-NN tuning loop lives here (bad curve→tune signal/entry params; high DD→tune sizing/exits).
- **G3 Robustness** — survives cost + walk-forward + Monte Carlo (the anti-luck/anti-overfit test).
- **G4 Live** — MT5 tester EA → demo → live parity.
- **t-stat gate bar REMOVED as an auto-kill.** Inherited LdP/academic orthodoxy. Replaced by OOS/walk-forward persistence (direct luck-test) + QuantStats curve reads. Kill stays human + ≥2-falsified (rule 8b). t-stat may be *reported* beside the chart, never an automatic block.
- **Cost in IS from the first edge number** (net from G2). No separate cost gate. OOS also net.
- **MT5-native architecture** = standard for CFD/XAUUSD: EA emits the ledger in the Strategy Tester (faithful, causal, no look-ahead); Python = analysis layer only (PnL + stats on the emitted ledger). No Python→MQL5 port → old Gate-7 fidelity gap dissolves into G4 demo/live parity.
- **N_trials/trial_family DSR machinery → DROPPED**, replaced by per-idea **IS run numbering** (IS-01, IS-02…): add `is_run` label to result rows + tiny `is_runs` table (idea_id, label, what_changed, created_at). Query e.g. "BRC — which IS run gave best Sharpe/Sortino?".
- **QuantStats-lumi** (maintained fork, NOT original ranaroussi) = standard tearsheet/metrics layer. Feed it a daily equity series from the per-trade ledger. Descriptive only; keep a light own read for sample-size sanity. Pin version (Sharpe annualization must match our convention).
- **Venue = asset class:** CFD/FX/high-leverage→MT5 (wire now); equity/ETF→IBKR (design seam only, defer).
- **Tester-from-IDE workaround CONFIRMED (researched):** `terminal64.exe /config:tester.ini` with a `[Tester]` block (Expert/Symbol/Period/Model/FromDate/ToDate/Report/ShutdownTerminal) runs headless, writes xml report → parse via existing ingest_tester_report.py. MetaTrader5 Python pkg does NOT expose the tester. Gotcha: terminal must be CLOSED for /config to take. NOT yet smoke-tested on JM.

**Done earlier this session (committed):**
- docs/_archive/ created; 3 completed plans + 3 shipped/superseded specs moved there.
- docs/reference/README.md added — map of all protocol/gate files + py scripts.

## Next (the rebuild — execute in order, fresh context)
1. **Smoke-test the tester CLI** on the JM terminal (terminal must be closed): write a minimal
   tester.ini for brc_baysix, launch via Start-Process, confirm it runs headless + emits a report.
   This is the real "double-check" before baking it into the protocol.
2. **Write Protocol 4.0 spec** → docs/specs/2026-06-22-protocol-4.0-lean-gates.md (design-of-record)
   before touching code. Capture the 4 gates, the 3-criteria definition, the diagnostic loop.
3. **Phase 0 — capture before nuke:** backup research.db → research/db/_backup/; extract BRC seed
   (step1 BRC row + tester_zones run 5 + strategy_log #54 + open tasks 110/126/129/130).
4. **Phase 2 — code reshuffle:** archive dead model code (hmm/msm/orb) → models/_archive/; repackage
   research/code/ into gates/ lineage/ io/ infra/ subpackages; rewrite imports + hook path; run tests.
5. **Phase 3 — rebuild DB** on the lean 4.0 schema (drop trial_family + 3.3 columns; add is_runs;
   fold tester tables into db_init); re-import BRC seed. Archive old migrations.
6. **Phase 3b — wall the lean gates:** G2 evidence (logged net result required), mandatory
   idea_kind/output_type tagging at G1. (DS-3 pipeline-entry hook, DS-4/5 hygiene = follow-up tasks.)
7. **Phase 4 — docs:** rewrite research_protocol.md → 4.0; archive 3.2/3.3 specs; update CLAUDE.md
   gate rules + paths; update memory.

## Decisions still open (confirm next session before Phase 3)
- Keep empty step2_papers / log_agent tables, or drop? (Lean toward keep-empty for future pipeline.)
- Soften promising bar to a Sharpe/curve read at G2 — exact thresholds TBD with first real BRC run.

## Blockers
- None. Tester-CLI is researched but unverified on JM hardware (Next #1 clears it).
- Sequencing rule: Protocol 4.0 spec (Next #2) before any code — don't nuke/reshuffle on a verbal design.
