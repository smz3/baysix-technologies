# Handover — June 22, 2026 Afternoon

## State (Protocol 4.0 rebuild — design + Phases 0/2-partial done; DB rebuild NOT started)
- **Spec written + canonical:** [docs/specs/2026-06-22-protocol-4.0-lean-gates.md](docs/specs/2026-06-22-protocol-4.0-lean-gates.md) — 4 gates (G1 Premise/G2 Edge+Survival/G3 Robustness/G4 Live), 3-criteria def, MT5-native, metrics stack, IS-run numbering, what's dropped vs 3.2/3.3.
- **Metrics stack SETTLED:** MT5 tester report = decides · empyrical = our-convention per-trade Sharpe (T=trades, no √252) · QuantStats-lumi = decorates only · MC+WF = bespoke on the trade list. Unit = a trade, never a calendar day (we're event-driven).
- **Tester CLI VERIFIED:** `terminal64.exe /config:`[mt5/tester/brc_smoke.ini](mt5/tester/brc_smoke.ini) ran brc_baysix headless, emitted report + CSV, self-closed. Terminal must be CLOSED first. JM `XAUUSD.s` history only reaches 2025-01-02 → full-IS emits use custom Dukascopy symbol (`XAUUSD_dukas`/`XAUUSD_pq`).
- **Phase 0 done:** 102MB backup → research/db/_backup/ (gitignored). BRC seed (60 metadata rows incl. strategy_log #54 frozen config) → [research/db/_seed/brc_seed.sql](research/db/_seed/brc_seed.sql). tester_zones run 5 (100,034 rows) re-imports from backup via ATTACH in Phase 3.
- **Phase 2 PARTIAL:** hmm + msm archived → research/models/_archive/ (zero importers, zero test regressions: same 68 pass / 9 pre-existing 3.2-3.3-machinery fails before+after).
- **Decision locked:** step2_papers MANDATORY — every idea links a paper at G1 ([[g1_requires_linked_paper]]).
- BRC-001 IS ledger still FROZEN = run 5. Nothing in research.db changed this session.

## Next (Phase 3 — the destructive rebuild; do in order, fresh context)
1. **Archive orb cluster FIRST** — orb has live coupling (orb ↔ export_ticks_mt5 ↔ fills, + pre-broken test_equity_sim). De-couple deliberately (relocate `orb_core._tick_files`; assess if export_ticks_mt5/fills are also ORB-era dead), then orb → models/_archive/.
2. **Repackage research/code/ survivors ONLY** into gates/lineage/io/infra — do this AFTER step 1 so we don't rewrite imports in ~45 dead files (measured: 85 imports across 67 files, ~45 in dead orb/hmm/migrations). Delete 3.3-machinery code (trial_family/gate2_sanity/gate5_report) here — they own the 9 failing tests.
3. **Rebuild DB** on lean 4.0 schema: drop trial_family + 3.3 columns; add `is_runs` (idea_id,label,what_changed,created_at) + `is_run` on result rows; fold tester tables into db_init; KEEP step2_papers + log_agent (mandatory). Re-import BRC seed + ATTACH run-5 zones.
4. **Wall gates:** G2 needs a logged net result; G1 needs idea_kind/output_type + ≥1 step2_papers row.
5. **Docs:** rewrite research_protocol.md → 4.0; archive 3.2/3.3 specs; update CLAUDE.md gate rules + paths.

## Decisions still open
- Exact G2 "promising" bar (Sharpe/curve read) — TBD with first real BRC run (not a schema blocker).

## Blockers
- None. Sequencing rule: archive-dead BEFORE repackage BEFORE DB-rebuild — don't reorder (avoids churning corpses / half-moved tree).
