# Handover — June 24, 2026 Morning

## State
- **IS-03 simplified 9→3 rules, BUILT, then bug-fixed.** Binary `git cb04750`, clean, v1.2.1, compile 0err/0warn.
- **Design simplified (strategy_log #62):** 3 rules — A=gate (retested H1 + fresh same-dir M15, `M15.p4>H1.t1`, spatial-agnostic), B=entry (reused IS-01 plan on M15 zone: limit M15.l1, stop M15.l2+0.20w), C=lifecycle (first complete pair, one-at-a-time, NO supersede; one trade per H1). Spec: [docs/specs/2026-06-23_brc_is03_m15_confirmation.md](../docs/specs/2026-06-23_brc_is03_m15_confirmation.md).
- **Built (strategy_log #63, task 146 done):** `BRC_MODE_M15_CONFIRM` enum in [brc_entry.mqh](../mt5/Include/brc_system/brc_entry.mqh); dual detection (g_s=H1 + g_m15=M15) via param'd `IngestBarInto` + `TryArmConfirm` bind in [brc_trader.mq5](../mt5/Experts/brc_system/brc_trader.mq5). Ledger +`parent_h1_key` col + mode in filename. **Real-tick model, H1 chart** (M15 needs sub-TF materialization).
- **First run VOID (strategy_log #64):** froze at 2018-01 — only **n=31**, E[R] −0.163, never-green 48.4%, $/trade −0.495 (artifact `Common/Files/BRC/brc_trades_XAUUSD_dukas_v120_M15CONF_L1_CONTINUATION_k020_20240628_2359.csv`). Cause: GTC M15 limit + ever-alive parent H1 starved the single slot (TS_PENDING forever). **NOT logged as a result.**
- **Fixed (v1.2.1, cb04750):** M15 limit now expires `InpRetestExpiryHrs` after M15.p4 + stale-M15 skip; parent-H1 still governs cancel.

## Next
1. **RE-RUN IS-03 (task 148, P1):** full 8.5yr (2016.06.01–2024.06.30), real-tick, H1 chart, `InpEntryMode=M15_CONFIRM`. Confirm trade count spans the whole range (no 2018 freeze).
2. **Ingest + score vs IS-01 control (result_id 3, −0.649/trade):** report **R-tail dist + n + never-green % FIRST**, $/trade last. THEN `pipeline.log_result()`.
3. **TPO/zone-quality (tasks 147/144)** in parallel — own time-based TPO from tick store (zone screen #2).

## Blockers
- None. OOS #126 stays blocked (no IS variant frozen with edge yet).
