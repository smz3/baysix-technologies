# Handover — July 3, 2026 Afternoon2

## State
- **FOB v1.33.0 SHIPPED + pushed** — new `InpEntryMode` toggle `{CF_MARKET, CF_L1_LIMIT}` on the TRADE path. Compiles 0 errors (only benign MQL5-Market version-format warning). `.ex5` built 15:44, junction-deployed to JM terminal.
- **CF_L1_LIMIT** = pending BUY/SELL LIMIT at the CF zone **L1 (T1/near edge)** instead of market-on-confirm. Fills only on a pullback to L1; SL unchanged (l2±k·band); TP off L1; risk = band·(1+k). Runaway winner (no pullback) cancelled on a **new setup-TF PBO (parent cycle end)**. Files: [fob_entry.mqh](../mt5/Include/fob_system/fob_entry.mqh) (FobPlaceLimit), [fob_ledger.mqh](../mt5/Include/fob_system/fob_ledger.mqh) (FobPendingBook/StashPending/CtxForPending/CancelPendingsForNewPbo + ledger DEAL_ORDER resolution), [fob_baysix.mq5](../mt5/Experts/fob_system/fob_baysix.mq5) (enum+input, g_pend, ActOnNewEvents branch).
- **CF_MARKET = untouched baseline** (default). The new mode is **opt-in**.
- **Syafiq's last run fired on CF-confirm** — near-certain cause: `InpEntryMode` left at default `CF_MARKET` (must flip to `CF_L1_LIMIT`); secondary suspect = stale `.ex5` in terminal (verify init log says `v1.33.0`). NOT re-verified yet.
- **8yr run (task 220) PARKED** by Syafiq — do this entry test first. Fresh 8yr CSV still does NOT exist (only 1yr v1.32.0 preflight probe).

## Next
1. **(task 233, P1)** Run the CF_L1_LIMIT 1yr A/B: TRADE mode, `InpTfPair=H4→H1`, real ticks Model=4, 2022 window. Run A `InpEntryMode=CF_MARKET`, Run B `CF_L1_LIMIT`. FIRST confirm init log prints `v1.33.0` + set the toggle (default is CF_MARKET — the reason last run fired market). A/B the two `fob_trades_*.csv` (Common\Files\FOB): expect fewer trades on L1_LIMIT, tighter R on fills; verify entries print ≈L1 + `realized_r` populated.
2. **(task 220, P1 — parked)** After entry test: full 8yr EMIT mine via [fob_emit_8yr.ini](../mt5/tester/fob_emit_8yr.ini) (already staged, correct: Model=4, Visualize=false, 2016.06→2024.07) → [ingest_fob.py](../research/code/io/ingest_fob.py).
3. **(task 222, P1)** VR contamination audit after 220's clean re-emit.

## Blockers
- None.

## Why
- **Entry moved market→L1 limit** because CF-confirm market chases price at the worst point; L1 (the near edge / first-touch) is the premium pullback entry the manual intends → tighter R, better fills, at the cost of missed runaway winners. Toggle (not replace) per the no-file-copy iteration rule so CF_MARKET stays A/B-runnable.
- **Cancel = new setup-TF PBO, NOT zone invalidation** (confirmed with Syafiq): a bull limit at L1 fills on the way DOWN, so by the time the zone invalidates (close below L2) the limit already filled + got stopped — cancel-on-invalidation almost never fires for an *unfilled* pending. The only orphan case is the runaway winner (price never returns to L1), which ONLY a new parent PBO cancels. Zone invalidation is covered by the SL on a filled order.
- **Pending LIMIT over on-tick market order** (Syafiq's call): deterministic level-fill in the real-tick tester (matches [[brc_trader_realtick_model]]), broker/tester owns the fill = less EA state. On-tick market would hand-roll touch-detection + dedupe + the same cancel logic + eat spread — more code, worse fill realism.
- **Ledger keys limit fills by DEAL_ORDER→pending-book** (market still by position id) — a pending carries its cycle context before it fills; the IN-deal's DEAL_ORDER recovers it. Avoids live fill-polling entirely.

## Ruled-Out
- **Splitting the 8yr mine into parallel sub-windows for speed** — rejected: W1/MN1 swing lookback spans years, so window boundaries produce different zones than the single causal stream → changes detection nuance. A causal oracle must be one contiguous pass.
- **Dropping tester to a lower tick model for speed** — banned: FOB is tick-resolution, real-ticks Model=4 is the fidelity floor (Syafiq's own constraint). Tester is already near-optimal (visual/warm-up/debug all tester-gated off; §4 tick loop decimated + eviction-bounded). No free speed lever remains.
- **Adding RT retest repeat-COUNT before mining** — deferred (Syafiq): CSV logs rt1/rt2/rt3_time (arrival at L2/mid/L1 on the return) but NOT how many times a level was re-poked (dropped v1.29.0). The RT *directional-edge* study (181/182) is fully answerable without the count; only the "5×-vs-1× retest" question isn't. Not worth a re-mine.

## Live-Threads
- **Nested cycle engine does NOT exist** — we have a per-TF cycle state machine (each TF's own PBO→VR→CF: dir/seq/cf_count in FobSetupState) + htf_state snapshot, but NO hierarchical engine: no parent-child nesting (W1⊃D1⊃H4 edges), no bottom-up direction derivation (X-dir = live cycle on X-1), no top-down bias chain. Deliberately deferred to a Python analysis layer that was never written ([fob_types.mqh:273](../mt5/Include/fob_system/fob_types.mqh#L273) says so). **Assessed sufficient to build post-8yr-mine without re-mining** — htf_state changes only on PBO/CF events (both co-emit a fresh 9-TF snapshot → complete gap-free state series); bottom-up is a pure remap; nesting reconstructable from cycle time-overlap. Build it AFTER 220.
- **LIVE-visual cycle dots for limit fills deferred** — CollectLiveCycles keys off g_book (bypassed for pendings), so limit-filled positions won't draw live-cycle dots. Tester + ledger fully correct; live-chart cosmetic only. Fix later if it matters.
- **`active` never flips flat mid-run** — a TF's htf_state direction is leg-continuous (last PBO dir until an opposite PBO), never goes "" on invalidation. Fine for direction; if the nesting engine needs an inline "parent zone alive?" flag, join to the zone table's invalidation_time.
