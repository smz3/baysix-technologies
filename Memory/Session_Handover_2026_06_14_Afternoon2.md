# Handover — June 14, 2026 Afternoon2

## State
- **Task 76 multi-TF DONE + pushed.** Two layers built:
  - **`XAUUSD_M1` baked into Arctic** — 3,536,641 minute bars (mid-OHLCV), 2016-05-23→2026-05-18, PURE UTC, sorted, 0 dups. Build via `python research/code/arctic_io.py build-m1`. Store now: lib `ticks` → symbols `XAUUSD`(ticks) + `XAUUSD_M1` + `XAUUSD_DAILY`(legacy).
  - **On-read derive layer** `arctic_io.bars(tf, venue='JM_EET')` — resamples M1→{M5..MN1} on the broker wall clock (JM_EET=Europe/Bucharest, DST-aware), lru_cached. Verified: H4/D1 anchor to broker midnight, H1→H4 rollup diff = 0.0.
  - **struct generalized to any TF** — `swings(tf)`/`raw_breakouts(tf)`/`load(tf)` (default D1/JM_EET); `*_d1` aliases kept; `rawbreakout.py --tf` flag. b2b parity guard still 3/3 PASS.
- **Reconcile finding:** legacy UTC-bucketed `XAUUSD_DAILY` vs broker-aligned `bars('D1')` → **70.5% of days differ >$1 close** (median ~$3, max $185). Old daily was MT5-misaligned; struct now defaults to broker-aligned D1. (Diff measured live, not a logged result_id — infra reconciliation, no step4 metric.)
- **Profiling correction (important):** `detect_swings` is NOT the intraday bottleneck — its per-bar `break` early-exit makes it ~O(n) = 0.69s on 236k M15 bars. A swing-vectorize attempt was built, proven byte-identical, then **REVERTED** (~0× gain, dead complexity). The real cost is `detect_raw_breakouts` (1.91s at D1=3106 bars alone; scales ~bars×active-swings). detectors.py back to clean original.
- Memory written: [struct001_m1_base_timezone_design.md](../.claude/projects/c--Users-User-Desktop-baysix-technologies/memory/struct001_m1_base_timezone_design.md) (store M1 UTC, bucket at derive-time, DST-aware, Darwinex TBD).

## Next
1. **Task 77 (P2 infra):** vectorize `detect_raw_breakouts` — the real intraday bottleneck. SAFE: freeze loop as oracle, build vectorized alongside, parity-assert byte-identical breakouts across windows 3/5/7 on D1/H1/M15, swap only when green. Sequence AFTER scalping declares its TF.
2. **Reconcile/retire legacy `XAUUSD_DAILY`** — repoint or rebuild from `bars('D1','JM_EET')` so daily_bars() is broker-aligned too (currently still UTC-bucketed).
3. **Confirm Darwinex/FTMO server clocks** before deriving bars for those venues — only JM_EET verified.
4. Task 75 (open P1): struct breakout viz parity — dotted level lines connect to correct broken swing.

## Blockers
None. Scalping idea needs Gates 0–1 (declare breakout TF + rule) before task 77 is actioned. ⚠️ Scalping's real risk is COST not speed (see [[ib001_reversion_finding]], [[spread_winrate_drag]]).
