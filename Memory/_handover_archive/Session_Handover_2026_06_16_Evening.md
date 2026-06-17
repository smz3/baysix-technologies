# Handover — June 16, 2026 Evening

## State
- **Task 75 DONE** — STRUCT-001 breakout viz parity verified. Programmatic check over all 1443 D1 breakouts: 0 time-order + 0 close-vs-level violations (bullish close>broken high, bearish close<broken low, P4 always after swing). New matplotlib path added to [visual.py](research/models/struct/struct001/visual.py): `breakouts --mpl` (native GUI window, no browser) / `--png` (headless, agent-readable). kaleido installed.
- **Task 76 PARKED** (status=parked, P1) — legacy UTC-bucketed `XAUUSD_DAILY` retire. Does NOT block STRUCT (already on `aio.bars(tf,venue)`/M1 base). HARD TRIGGER: do before HMM-001 advances to OOS (HMM still on `daily_bars()`).
- **B2B → BRC rebrand COMPLETE.** Migration [029_rename_b2b_to_brc.py](research/migrations/029_rename_b2b_to_brc.py) ran: `B2B-001 → BRC-001` across 6 tables (24 refs, 0 leftover). STRUCT-001 untouched (stays the shared "Break" primitive). Rebrand drops the unfalsifiable "institutional/trapped-trader" narrative.
- **BRC package scaffolded** — [research/models/brc/brc001/](research/models/brc/brc001/): `__init__` + `zones.py`/`retest.py`/`continuation.py` stubs that IMPORT struct (rawbreakout/swingpoints/structures) via `_struct_on_path`, never fork. All stubs raise NotImplementedError; imports verified clean.
- **Task 106 LOCKED (spec).** Source of truth = [5PointB2BDetection.md](mt5/Include/Sigma_System/V5.0/Docs/5PointB2BDetection.md) (FINAL, overrides b2b-overview). BRC = 5-swing-point geometry confirmed by ONE breakout (P4), NOT two rawbreakouts. SELL order: P5(old low)→P1(high=L2)→P2(low=L1)→P3(lower high)→P4(closes below P5); BUY=mirror. L1=P2, L2=extreme(P1,P3) [MAX sell/MIN buy], invalidation=close beyond L2. Map: P1/P2/P3/P5=swings, P4=rawbreakout. Logged via log_human_decision (call 75).

## Next
1. **Task 107 (code zones.py)** — implement MINIMAL CORE 5-pointer in [zones.py](research/models/brc/brc001/zones.py) `detect_zones()`: P1-P5 + P4 confirm + L2-extreme. DEFER (later variants): V5.1.1 2-pass/freshest-P5, V5.1.2 no-interruption. Reference (do NOT fork): [b2b_engine.py](b2b/sigma_core/b2b/detectors/b2b_engine.py) + B2BDetector.mqh. D1 atom only.
2. **Task 109 (Gate 2)** — visualize BRC zones on D1, eyeball sane (new `brc/brc001/visual.py` importing struct's visual for close-line/breaks + zone rectangles).
3. **Task 108** — retest (L1 re-touch) + continuation label. NOTE: retest touch rule (close vs wick) deferred by Syafiq as premature — decide when starting 108.
4. Then **Task 110 (Gate 3)** edge test: H_base continuation vs H_alt-1 fade vs H_alt-2 single-vs-two-break, D1 atom, no russian-doll.

## Blockers
None. BRC-001 is at gate_1 passed; next legal gate = Gate 2 (sane output via tasks 107+109).
