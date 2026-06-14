# Handover — June 14, 2026 Afternoon

## State
- **STRUCT-001 is now fully decoupled from b2b** (commit pushed). The struct filing system stands alone — no more `sys.path → b2b` hack.
  - New [structures.py](../research/models/struct/struct001/structures.py) — struct owns the 5 types (SwingPointInfo/RawBreakoutInfo/DetectionConfig/SwingType/SignalDirection). B2B zone/flow types deliberately excluded.
  - New [detectors.py](../research/models/struct/struct001/detectors.py) — struct owns `detect_swings` (faithful close-based port).
  - swingpoints/rawbreakout/visual/audit all repointed to struct-owned imports.
  - [audit_detector_causality.py](../research/models/struct/struct001/audit_detector_causality.py) now **self-audits struct's own detectors** → 5/5 PASS (causal + parity at window=3).
  - Drift guard [test_struct_parity.py](../research/tests/test_struct_parity.py) → struct `detect_swings` == b2b, windows 3/5/7, **3 passed**. Fork can't silently diverge.
  - Behavior unchanged: 1528 swings / 1416 breakouts / 227 in-view, identical to pre-decouple.
- **Breakout viz reworked to MT5-faithful** ([visual.py](../research/models/struct/struct001/visual.py) `plot_breakouts`): dot+label on the broken swing (`Bob/Bos <swing>`), PLUS a lighter-shade dot+label on the breakout-bar close. Pairs each broken level with the close that broke it. Matches Visualizer.mqh DrawRawBreakout.
- struct still only detects **D1**. Multi-TF is the next build.

## Next (Phase 2 — multi-TF, design SETTLED this session)
1. **Build canonical `XAUUSD_M1` base from ticks (one-time, new window per rule 12)** — generalize [build_daily_symbol](../research/code/arctic_io.py#L144) to M1 mid-OHLC. This is the single expensive tick scan.
2. **Derive the other 8 TFs on-read from M1 (lazy + lru_cache)** — `bars(tf)` resamples M1→tf. Provably consistent rollup (open=first, high=max, low=min, close=last, vol=Σ all exact vs ticks→tf). One source of truth = no inter-TF drift.
3. **Broker-clock bucketing (UTC+3)** — every resample uses `origin`/`offset` so bar boundaries land where MT5's do (W1=broker week-open, MN1=calendar month). Get it right once in the cascade; all 9 inherit. Reconcile existing `XAUUSD_DAILY` vs M1→D1, keep M1-derived as canonical.
4. Generalize `swings(tf=...)` / `raw_breakouts(tf=...)` to accept a TF / list of TFs; `visual.py --tf H1`.
- Decision rejected: 9 independent ticks→TF resamples (risk of silent cross-TF boundary misalignment). Chosen: M1 base + cascade (option B1). Why it matters: cross-TF confirmation *timing* is the next signal.

## Blockers
None. Phase 2 build can start cold from step 1 above.
