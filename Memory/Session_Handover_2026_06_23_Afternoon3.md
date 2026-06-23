# Handover — June 23, 2026 Afternoon3

## State
- **PIVOT: exit-first → ENTRY-first** (human_decision #82/#83/#84). The autopsy on real-tick IS-01 (result_id 3, −$0.649/trade) drove it.
- **#138 SHIPPED** — range_w now stashed at ARM (keyed on pending ticket == position_id) in [brc_trader.mq5](../mt5/Experts/brc_system/brc_trader.mq5). The 31% instant same-bar SL cohort previously logged realized_R=0; now all carry 1R. Compiles 0/0, committed `274fa15`. Re-run = tester run #11, net unchanged −$0.649/trade (bookkeeping-only ✓).
- **🔑 The fix corrected the baseline itself:** true sizing-neutral **E[R] = −0.224** (result_id 3 ledger), NOT the +0.10 the bug faked. BRC IS-01 is genuinely edgeless.
- **Diagnosis (result_id 3 ledger, run #11):** loss = the **never-green cohort** (mfe_r<0.25, **42%**, E[R] −0.965); the **went-green 58% are +0.315R** — a real edge. Filter the 42% → system flips positive.
- **WHERE-discovery (#142) = NEGATIVE.** The 42% is **diffuse**: never-green rate ~40% in EVERY bucket — session 40-49%, zone-age 38-44%, direction symmetric. range_w FALSIFIED (min-lot artifact: lots pinned 0.01 → wide stops just risk more $). TF constant (H1). **No entry-observable feature we emit separates the cohort.**
- **#140 RESOLVED: tester server = UTC** (exporter writes epoch-ms UTC; 2024 px cross-check vs arctic = offset 0). "No-Sunday week" was dukas data, not EET. zone-age neg was a local-TZ parse bug. Session(UTC)+zone-age now valid features.
- **IS versions run = 1** (IS-01 only; 10 tester runs + 2 results are all the same T1-first-retest-continuation logic). **Zero entry variants tested yet.**

## Decision (this session's discussion)
- Coarse FILTERS on IS-01 are exhausted — can't predict the bad 42% from what we record. Two structural gaps named by Syafiq: **(1) no zone-quality data** (we emit nothing on WHY a zone holds/fails) and **(2) no confirmation trigger** (blind passive limit, zero post-touch reaction).
- **IS question answered: open NEW IS labels (IS-02+) per entry rule; retire IS-01 as the null control.** A different entry mechanism ≠ IS-01. Zone-quality features = infrastructure feeding variants, not an IS.

## Next (entry program — all vs IS-01 control, real-tick model, from 2016.06.01)
1. **#132 depth sweep T1/T2/T3** (P1) — cheapest, free enum flip. Deeper entry mechanically thins the 42% (blow-through zones invalidate before reaching depth → never fill). New IS-02.
2. **Confirmation trigger** (P1, NEW) — add a post-touch reaction knob (close-back / rejection / momentum) vs blind limit. Attacks the 31% same-bar deaths. Honestly testable on real-tick (ORB fill-trap doesn't apply). New IS-03.
3. **Zone-quality feature emission** (P1, NEW) — emitter records zone width/ATR, P4 break impulse, prior-touch count, momentum-into-zone, HTF confluence. Answers Syafiq's "common denominator" → enables the real filter hunt the coarse one failed.

## Blockers
- None. OOS #126 stays blocked until a variant FREEZES with edge (IS-01 is the edgeless control, nothing to freeze yet).
