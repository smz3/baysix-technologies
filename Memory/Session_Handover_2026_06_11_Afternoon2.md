# Handover — June 11, 2026 Afternoon2

## State
**ORB-001 FAILED the fidelity check at $10k — port is NOT faithful.** $10k tester re-run (cap non-binding → 527 trades, DD 60.7%→3.0%) on XAUUSD_dukas real ticks: **net −$187.54, win 33.2%, PF 0.80, −$0.36/trade.** Entries match Python (527 vs research 522) — divergence is in the EXIT. Python `trail_1R_OOS_E_R`=+1.73, win **56.7%**, +$5.78/t vs tester **33.2%** / −$0.36. **Retracted my "look-ahead" claim** — read [trail_oos.py](../research/models/orb/orb001/trail_oos.py:120): trail is CAUSAL (running peak, gap-fill+slip stress already passed). So it's an **EA trailing-exit port bug**, not a research artifact (spread ruled out — Python slip sweep barely moves win rate). Report: [ReportTester-1100438548_10k.xlsx](../mt5/strategy_tester_xlsx/ReportTester-1100438548_10k.xlsx) (+ `_clean.xlsx` flattened, viewer-friendly).

**execution.db being redesigned + rebuilt from scratch (NOT executed yet — gated on Syafiq).** Current DB still OLD (12 tables, 43 obsolete D0-parity signals from [d0_parity.py](../research/models/orb/orb001/d0_parity.py); NOT tester contamination — tester is in tester_runs/tester_trades).

## Decisions locked this session
- **D0 SCRAPPED.** Gate ladder → **FIDELITY → FORWARD** (descriptive names · single FORWARD gate w/ demo→live sub-stages · statistical-equivalence pass: trade-overlap ≥95%, E[R]/win/$per-t in research 95% CI).
- **FIDELITY = MT5 Strategy Tester vs research on IDENTICAL Dukascopy data** (catches MQL5 port bugs). Hard rule: never broker history at fidelity.
- **3 DBs, final: research.db (agnostic) → tester.db (MT5-specific, exists ONLY because MQL5 is a language port; IBKR=Python→Python won't need it) → execution.db (ALL venues, venue=COLUMN, NOT per-venue; one portfolio/risk view).** execution starts **6 core tables**, grows to 10 (orders/fills/incidents/log_deploy added at FORWARD-live).
- Future refinements (multi-asset/prop): **`venue` should = protocol ('mt5'/'ibkr'), not broker**; broker→accounts field; add `instruments` specs table for futures (tick value/contract/expiry). accounts already has FTMO/prop rule columns.

## Next
1. **READ the EA MQL5 trailing-stop code** ([mt5/Experts/orb_system/baysix_orb_001.mq5](../mt5/Experts/orb_system/baysix_orb_001.mq5) + Include/orb_system/) — find why trail wins 33% not 57%. This is THE blocker for ORB-001 deploy. (task 43 fidelity diff depends on the fix.)
2. **Get Syafiq's go on the execution.db wipe+rebuild** (backup-first y/n? confirm 6-table lean vs 10). Then: read RESEARCH_CODE_PROTOCOL.md (rule 7) → migration `022` (drop old execution.db, build new FIDELITY/FORWARD + tester.db) → revise [execution.py](../research/code/execution.py) + new tester_db.py → smoke test guardrails.
3. **Fold the 2 doc refinements** (tester-is-MT5-port-specific rationale; venue=protocol + instruments table) into the already-edited [execution_protocol.md](../braindump/execution_protocol.md) + [execution_schema.md](../braindump/execution_schema.md). Docs already edited to FIDELITY/FORWARD + tester.db this session.

## Blockers
- ORB-001 deploy BLOCKED at fidelity until the EA trail bug is found + fixed.
- Rebuild NOT started — needs Syafiq's explicit go + backup/lean decisions. **No log_tasks row yet for the execution.db rebuild — create one** ([[handover_nextsteps_must_be_tasks]]).
