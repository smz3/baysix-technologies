# FOB Tick Warm-up — Kill the Dual Display Engine (single-engine touch ladder)

**Date:** 2026-07-02 · **System:** fob_system · **Task:** 223 (P1) · **Status:** SPEC (pre-build)

## Problem

On a LIVE chart the FOB display runs **two lifecycle engines**, and only one is correct:

- **`FobAcc*` causal accumulator** — the truth. Advances the touch ladder tick-by-tick. Runs in **both** live and tester. Tester feeds it every historical tick from test-start → tester is already single-engine and tick-exact.
- **`FobBackfillLadderTimes` + `FobBackfillRtTimes`** — wick-approximation touch-fill, **live-chart only** (`if(live)`, [fob_baysix.mq5:361](../../mt5/Experts/fob_system/fob_baysix.mq5)). Guesses touch *times* from bar wicks for zones born before attach.

A wick says "price crossed this level **sometime** in this bar," never **when**. So the guess lands in the right day/week (D1/W1/MN1 look perfect) but the **wrong minute-bar on low TFs** (M5/M15/M30/H1) — the funky T-touches Syafiq is seeing. This is a physical ceiling of bar data, not a tunable bug.

**Hard requirement (Syafiq):** the backfill must be truthful to *WHEN + WHERE* each zone was touched — these times are strategy-critical.

## Root cause (confirmed in code)

First `OnTick` after attach:
1. `FobIngestTf` → `CopyRates(period, 1, 64, r)` per TF → builds breaks → classify → seeds `g_events`/`g_acc`, populates `g_watch`. **Structure = correct** (bar-close-defined).
2. **Close path** ([fob_baysix.mq5:298-322](../../mt5/Experts/fob_system/fob_baysix.mq5)) sweeps all 64 closed bars → `FobAccOnClose` sets invalidation / vr_fresh / bars_alive. **Correct.**
3. **Tick path** ([fob_baysix.mq5:324-339](../../mt5/Experts/fob_system/fob_baysix.mq5)) feeds `FobAccOnTick` **only the single current live tick**. Pre-attach ticks never seen → **touch ladder t1/t2/t3 (+ RT rt1/rt2/rt3) empty for every historical zone.**
4. Wick backfill fills those empty slots — the broken approximation.

## Design — one engine everywhere

Keep the structure pass (1) — it's already right, it's what paints "current zones" on attach. **Replace the wick backfill with a real tick replay through the SAME `FobAcc*`**, so the live touch ladder is built the identical way the tester builds it.

The subtlety: the touch ladder and invalidation must be **interleaved in tester order** (ticks of bar N processed *before* bar N's close — see [fob_lifecycle.mqh:181](../../mt5/Include/fob_system/fob_lifecycle.mqh)). Because `FobAccOnTick` routes T-ladder vs RT-ladder off `a.invalidated`, a post-hoc tick replay (after the close pass has already set `a.invalidated`) would misroute every tick into the RT branch. So the warm-up must **re-seed and replay closes + ticks together**, not bolt ticks on after.

### Warm-up routine (LIVE only, first tick, once)

`FobWarmupReplay()` — runs after the structure pass builds `g_events`/`g_acc`/`g_watch`, **in place of** the plain 64-bar close pass, when `live`:

1. `warm_start = TimeCurrent() - InpTickWarmDays*86400` (0 ⇒ unbounded, back to oldest structure bar).
2. `CopyTicksRange(_Symbol, ticks, COPY_TICKS_ALL, warm_start_ms, now_ms)` — one pull.
3. Re-seed every event's accumulator to pristine (`FobAccInit`) so the replay is causal (structure/classification untouched — only ladder + acc state reset).
4. Merge into one chronological stream: the window's **ticks** + the window's **per-TF closed bars** (already in `g_tf[t]` buffers) as close-events. Walk it; tester ordering (bar-N ticks before bar-N close):
   - tick → for each watched zone: `FobAccOnTick`
   - bar-close(TF t) → for each watched zone of TF t: `FobAccOnClose` (drop dead CF/PBO from `g_watch`, VR opens RT)
5. Bars **older than `warm_start`** but inside the 64-bar structure buffer: close-only fallback (no ticks exist) — establishes invalidation/vr_fresh but leaves the ladder at window edge. Affects only pre-window (old, high-TF) zones.

### Delete
- `FobBackfillLadderTimes`, `FobBackfillRtTimes` ([fob_lifecycle.mqh:331,372](../../mt5/Include/fob_system/fob_lifecycle.mqh))
- `CFobVisual::BackfillChartLadder`, `BackfillChartRt` + call sites ([fob_baysix.mq5:361-369](../../mt5/Experts/fob_system/fob_baysix.mq5), [fob_visual_lifecycle.mqh](../../mt5/Include/fob_system/fob_visual_lifecycle.mqh))

## Window bound — `InpTickWarmDays` (default **30**)

64 bars is a very different real span per TF, so replaying the full structure window on EMIT-live (MN1×64 ≈ 5 yr of ticks) is unusable — and `OnInit` re-fires on every period-switch/recompile, so warm-up runs **often** and must stay cheap.

**Default 30 days fully covers the reported bug:** M5×64≈5h, M15×64≈16h, M30×64≈32h, H1×64≈64h, H4×64≈11d — all ≪ 30d ⇒ tick-exact. Only D1 (×64≈64d) and W1/MN1 truncate at the window edge; those are the "higher TF" zones that already look correct on bars, and are **not** the bug. Knob raises it; `0` = unbounded (truest, slow attach on EMIT).

| Mode | Ingested TFs | Warm-up cost |
|------|--------------|--------------|
| TRADE / STUDY | setup pair (low TFs) | trivial (hours of ticks) |
| EMIT-live | 9 TFs incl W1/MN1 | bounded to `InpTickWarmDays`; low TFs exact, D1+ truncated |

## Tester parity (HARD)

Warm-up is `if(live)`-gated. The tester path (`!MQLInfoInteger(MQL_TESTER)`) is **untouched** — it already replays every tick causally. OOS re-emit CSVs stay **byte-identical**. This is the same live-only contract the deleted wick backfill had.

## Files touched
- [fob_baysix.mq5](../../mt5/Experts/fob_system/fob_baysix.mq5) — first-tick path: call `FobWarmupReplay` (live) vs plain close pass; drop backfill calls; add `InpTickWarmDays`.
- [fob_lifecycle.mqh](../../mt5/Include/fob_system/fob_lifecycle.mqh) — add `FobWarmupReplay`; delete `FobBackfillLadderTimes`/`FobBackfillRtTimes`.
- [fob_visual_lifecycle.mqh](../../mt5/Include/fob_system/fob_visual_lifecycle.mqh) — delete `BackfillChartLadder`/`BackfillChartRt`.
- `fob_types.mqh` — bump `FOB_VERSION` (behaviour change), regen `fob_version.mqh`.

## Open decision (confirm before build)
- **`InpTickWarmDays` default** — proposed **30** (fixes M5–H4 fully, cheap attach). Alternatives: **70** (adds D1), **0** (unbounded, slow EMIT attach).
