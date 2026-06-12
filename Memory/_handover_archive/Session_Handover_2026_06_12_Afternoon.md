# Handover — June 12, 2026 Afternoon

## TL;DR (read this, not the chain)
ORB-001 Gate-7 is **NOT a data bug and NOT a spread bug** (both fixed this session). The **live blocker is a fill-model fidelity gap**: the EA trades on **bid/ask with no tolerance**; Python validated on **mid + ½-spread tolerance**. ORB-001's `range_w` (~$0.4–1.0) is so small that this ~$0.10 (1-pip) gap **flips trade direction on 8/22 days and whipsaws winners out**. Same month/config/spread: **Python +67.4R / 56.5% win vs EA −$11 / 13.6% win.** The edge lives at sub-spread resolution.

## What got fixed this session (real, verified)
1. **Margin bug (no trades fired).** [import_custom_ticks.mq5](mt5/Scripts/orb_system/import_custom_ticks.mq5) forced CFD calc + XAU margin → margin uncomputable in USD (blank usd/lot) → every order silently rejected. Fix: stop overriding calc mode (inherit working `XAUUSD_dukas`), override only digits/tick-size/point/tick-value. Recompiled headless (JM metaeditor64, 0/0). ✅
2. **Spread mismatch (9% win).** Parquet carries Dukascopy's **native ~$0.50 (5-pip)** spread at the 09:00 open (measured: median 0.500/mean 0.509; overall median 0.387) vs Python/JM **2-pip ($0.20)**. Fix (Syafiq chose): synthesize 2-pip in [export_ticks_mt5.py](research/code/export_ticks_mt5.py) — `bid/ask = parquet_mid ± HALF_SPREAD(0.10)`. May-2024 re-exported (5.0M ticks, spread=0.20 verified, self-test PASS). Logged: `log_human_decision` call_id=39. ✅

## The actual root cause (the new finding)
After data+spread fixed, EA still 13.6% win / net −$10.98 (report `ReportTester-1100438548_3.xlsx`, 22 trades). Decisive comparison run (Python `_simulate_day`, 09:00/N=5/trail_1R/2-pip, May-2024):

| | Trades | Win% | Sum R | Net |
|---|---|---|---|---|
| Python | 23 | 56.5% (13W) | **+67.4R** | strong + |
| EA tester | 22 | 13.6% (3W) | — | −$11 |

**Two symptoms, one cause:**
- **Direction flips 8/22 days** (05-06, 08, 13, 21, 23, 24, 28, 30) — and they're the **big-trend days** (Python 05-06 +11.96R, 05-13 +14.28R, 05-21 +10.79R). EA bets the wrong way on exactly the days the edge lives.
- **Trail too tight even on direction-correct days.** 05-22 both short: EA **−$0.68**, Python **+12.63R** — EA's stop fired ~0.10 earlier on the whipsaw.

**Mechanism:** EA ([baysix_orb_001.mq5](mt5/Experts/orb_system/baysix_orb_001.mq5)) — OR from bid-bar hi/lo (L209-211), entry `bid>=or_high` (L274), stop=opposite boundary, trail `peak_bid−range_w` (L336), all bid/ask, **no tolerance**. Python ([anchor_oos.py:76-99](research/models/orb/orb001/anchor_oos.py#L76-L99)) — OR from tick mids, trigger `or_hi−half`, exit `peak−rw+half`, all **mid + ½-spread**. The ~$0.10 convention gap is the whole divergence.

## DECISION FORK (decide fresh — do not auto-build)
- **A) Re-validate Python with realistic bid/ask fills** (re-implement EA conventions in Python on the ticks). If edge dies → ORB-001 was a fill-model artifact. **Cheap + honest + decisive. Lean: do this first.**
- **B) Port EA to Python's mid+tolerance model** → Gate 7 passes, but live may underperform what the idealized backtest promised.

## Next steps (also in log_tasks)
1. Run fork **A**: Python EA-emulation (bid/ask fills, no tolerance, trail from fill) on May-2024 → if it reproduces ~13%/negative, root cause is 100% confirmed AND edge fragility is proven.
2. Based on A's result, either fix the EA (B) or re-open ORB-001's validation (the +67R may be idealized).
3. Then re-run tester + real Gate-7 diff. Only after pass → full-OOS export (`export_ticks_mt5.py 2024-05 2026-05`, ~3.8GB, own window).

## Handoff-failure lesson (why this took a whole session to re-find)
The prior handover declared root cause = DATA and carried **"trail port bug → FALSIFIED (emulations agree 95.6%)"** as settled. That falsification was done **on the mismatched data** — a poisoned conclusion, void once data was fixed. It was inherited, not re-opened, so this session re-walked the whole chain. **Rule: a falsification made under a condition later proven wrong must be RE-OPENED, not inherited.** See memory [[reopen_falsified_on_new_data]].

## State of files
- Export + import scripts patched & committed-pending. EA source **unchanged** (no fix applied — diagnosis only).
- Custom symbol `XAUUSD_pq` currently holds May-2024 @ 2-pip synthetic spread.
- Reports in [mt5/strategy_tester_xlsx/](mt5/strategy_tester_xlsx/): `_3` = latest (2-pip, the 13.6% run).
