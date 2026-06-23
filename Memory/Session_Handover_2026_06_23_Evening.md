# Handover — June 23, 2026 Evening

## State
- **Entry-program continues; this session ran the DEPTH sweep (task 132) + adopted a buffered stop.** Binary now `git 67cda55` clean (`brc_trader.ex5`, built 17:40). All runs real-tick, 2016.06.01→2024.06.30, Deposit 10k, Visual OFF, JM `XAUUSD_dukas`.
- **T2/MID = FALSIFIED** (result_id 4, run #12, strategy_log #58). Deeper entry made the population WORSE on stop-neutral cohort metrics: never-green 42.1%→52.5%, went-green share 57.9%→47.5% with edge +0.315→+0.140R; E[R] −0.224→−0.519. The −$0.490/trade "improvement" was [[er_denominator_illusion]] (tighter stop risks fewer $). Deeper fills buy INTO the momentum punching to L2.
- **🔑 Buffered stop ADOPTED but EDGE-NEUTRAL** (result_id 5, run #13, strategy_log #59). New input `InpSlBufferK` (default 0.20): `SL = L2 ± k·|L1−L2|`, pushed beyond invalidation. vs SL@L2 control (result_id 3): E[R] −0.224→−0.213 (FLAT), net/trade −0.649→−0.672 (worse, fixed-lot artifact), but win 25.0→27.8%, SL-exits 65.9→60.8%, ≤60m deaths 38.9→33.4%. Improves survival/shape, NOT edge. Kept for structural reasons (cleaner cohort signal + makes T3/L2 non-degenerate; `k=0` reproduces legacy).
- **Confirmed via the cohort work: the never-green ~42% is an ENTRY-QUALITY problem, not stop/depth.** Neither deeper entry nor a wider stop rescues it — confirms the pivot to confirmation/zone-quality.
- **Latent footgun:** trader ledger CSV filename keys on symbol+version+last-bar, NOT the variant → every run OVERWRITES the prior (T2 silently overwrote T1 earlier). Safe only because each run is ingested to `tester_trades` immediately. MUST fix before any optimization/k sweep.

## Next
1. **Run T3/L2 buffered** (task 132): `InpEntryTouch=BRC_ENTRY_L2`, `InpSlBufferK=0.20`. Now non-degenerate (r_unit=k·width). Completes the all-T-touches dataset. Ingest → compare T1/T2/T3 under the buffered stop.
2. **Fix ledger filename to encode entry-touch + slbuf_k** (infra, BLOCKS sweeps): edit `WriteTradeLedger` in [brc_trader.mq5](../mt5/Experts/brc_system/brc_trader.mq5) so runs/optimization passes don't overwrite. Then a k-sweep `InpSlBufferK ∈ {0.10,0.20,0.35,0.50}` is one launch.
3. **#143 confirmation trigger** (P1, the real edge lever) — post-touch reaction knob (close-back/rejection/momentum) vs blind limit in `brc_entry.mqh`. Attacks the never-green entry-quality cohort that depth+stop could not.

## Blockers
- None. OOS #126 stays blocked (no variant has frozen with edge — IS-01 is the edgeless control; buffer is edge-neutral).
