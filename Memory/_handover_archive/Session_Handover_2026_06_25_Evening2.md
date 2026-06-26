# Handover — June 25, 2026 Evening2

## State (FOB-001 — T1 coin-flip GATE run on H1; continuation FALSIFIED, but measurement is ambiguous → next = decompose direction vs timing)

**One-line:** the breakout-confirmation (CF) DOES carry a strong directional signal (CF1 binomial z = −7.15, n=2210), but our symmetric ±1ATR market-on-CF test can't tell whether it's a real reversal or a pullback-then-continue we're getting stopped out of. So the open question is **execution, not "is there direction."**

## What happened this session (explicit narrative)
1. **T1 CF_ZONE, H1 setup (→CF on M30), 8yr real ticks → result_id 11:** WR **29.97%**, E[R] −0.419, −$746, z=−19.3. Looked like a brutal anti-edge.
2. **Diagnosed as a tight-stop SPREAD ARTIFACT, not a real anti-edge:** WR is monotonic in stop width (tight 0.14–0.62pt = 19% / mid = 30% / wide 1.23–21pt = 40.5%); median stop **0.86pt**, 58% of stops sub-1pt, **42% of SL hits in <2 min**. The CF-zone SL collapses to a sub-point bracket where the (hybrid-book) spread dominates → the binomial measured spread survival, not direction.
3. **Built the ATR variant (task 169 → DONE).** `fob_trader` v1.7.0→**v1.8.0**: added `InpRMode = CF_ZONE | ATR` (+ `InpAtrTf/InpAtrPeriod/InpAtrMult`). ATR mode = symmetric `InpAtrMult×ATR` bracket off CMP so risk-unit ≫ spread. CF_ZONE stays the pure default. Compiles 0 err (1 cosmetic Market-version warning). Pushed **sha 314914c**. Presets in [mt5/presets/fob_system/](mt5/presets/fob_system/): `…-T1-H1-CFZONE.set` and `…-T1b-H1-ATR.set` (only diff = `InpRMode` 0→1).
4. **ATR run, H1, 1.0×ATR(14) on M30, 1:1 → result_id 12:** stops FIXED (median **2.28pt**, only 4% sub-1pt). WR **42.88%**, z=−7.08, E[R] −0.136. Barriers clean (meanR|TP +1.05, meanR|SL −1.03). **Most of the CF_ZONE 30% was indeed spread; the clean read is ~43%.**
5. **cf_idx split (task 164 → DONE, from result_id 12):** **CF1 n=2210 WR 42.40% z=−7.15** (the entire signal); CF2 n=183 z=−0.81 (NS); CF3+ n=79 z=−0.56 (NS). The manual's "2nd CF is best" is **NOT supported** — the edge is CF1, and it points the *reversal* way.
6. **Reframe (strategy_log 73): continuation entry FALSIFIED** (1/2 falsified → reframe, not kill, rule 8b).
7. **Syafiq's key correction (the real insight):** the symmetric ±1ATR barrier **conflates direction + entry-timing + stop distance**. A −7 z does NOT prove "no continuation edge" — if price pulls back 1ATR (tags our stop) and *then* continues (totally normal on H1), the ledger logs a **loss** while the direction thesis was right. So "reversal" and "pullback-then-continue" are **indistinguishable in the current data.** Working hypothesis: **execution is wrong** (market-on-CF buys the breakout extension, the natural retest stops the tight bracket before the move develops — breakout-chaser bleed), not the direction.

## The plan (next session — tasks already in log_tasks)
1. **(task 170, P1) CF forward-excursion study — THE missing measurement.** For each CF1 on H1, track the next K bars in continuation dir: **MFE / MAE / terminal return.** If MFE is large but MAE tags 1ATR *first* → execution wrong (fade is a mirage). If terminal return is genuinely negative → real reversal (fade is real). Emitter can emit CF-anchored forward windows, OR a Python study on bars keyed to CF timestamps. **Do this BEFORE any more barrier backtests** — they keep returning a number that means three things at once.
2. **(task 171, P1) Retest entry: limit-on-pullback into the PBO zone** (vs market-on-CF). Tests Syafiq's mechanism: CF → pullback into PBO zone → continue (maybe a new same-dir PBO supersedes). Add `InpEntryMode = MARKET | LIMIT_PBO` (+ expiry). Folds the old E1–E4 sweep (task 165).
3. **(task 172, P2) Setup-TF sweep** — M30-M15, M15-M5, M5-M1, H4-H1, D1-H4 (`InpSetupTf` 1..7). Only H1→M30 done. Run AFTER measurement+entry are locked. Is the reversal-lean TF-universal or H1-specific?

## Artifacts / provenance
- EA: [fob_trader.mq5](mt5/Experts/fob_system/fob_trader.mq5) v1.8.0, magic 3001, sha **314914c**. Emitter [fob_baysix.mq5](mt5/Experts/fob_system/fob_baysix.mq5) still pristine. **Verified this session:** trader's 2-TF ingest produces byte-identical PBO/VR/CF events to the 9-TF emitter — `FobClassifyBreak` only ever touches `st[etf]` (PBO) and `st[etf+1]` (VR/CF), so setup S depends solely on breaks from {S-1, S}. Not a parity bug.
- Results: **result_id 11** (CF_ZONE, WR 29.97%), **result_id 12** (ATR, WR 42.88%). Strategy lineage: **log 72** (PROPOSED exit CF_ZONE→ATR), **log 73** (FALSIFIED entry continuation → PROPOSED fade CF1).
- Ledgers in `Common\Files\FOB\`: `…v170_H1_cf0…` (id 11), `…v180_H1_cfz…` (id 11 re-run, identical), `…v180_H1_atr_cf0…` (id 12).

## Blockers / notes
- None blocking. Tester chart's red/grey Ask/Bid bands annoy Syafiq — cosmetic only; fix is to save a clean `tester.tpl` (deferred, he can live with it).
- ATR run had tester visual-mode ON (slow, results unaffected) — turn off next run.
- Don't pick stop/RR on E[R] ([[er_denominator_illusion]]); rank by $/trade + survival. Bigger TP is the WRONG lever for a reversion/reversal signal (short moves).
