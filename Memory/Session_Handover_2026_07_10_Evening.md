# Handover — July 10, 2026 Evening

## State
- **EA is v1.41.0**, git `54b2b97`, clean tree, compiles 0 errors. [fob_baysix.mq5](../mt5/Experts/fob_system/fob_baysix.mq5).
- **Task 267 DONE — the trail was broken and is now fixed.** SL is floored at entry; `cand` normalized before the `tighter` compare (killed the 161k `Invalid stops` storm).
- **The trail fix is P&L-NEUTRAL.** result_id 55 = +$1.0349/tr vs result_id 39 = +$1.001/tr, **same 373 trades**. Bug real, not the lever.
- **Task 253 DONE — `InpExitOnCfInval` REJECTED** (strategy_log 116). CF1 paired Δ = +$0.0425/tr (result_id 58); CF3 paired Δ = **−$0.3272/tr** (result_id 60). Helps the loser, hurts the winner.
- **Task 254 DROPPED on evidence** (never run — OppPbo is strictly coarser than CfInval).
- **EXITS ARE SETTLED AT H4.** Stop distance falsified (paired k-sweep, result_id 27/30/31). Exit rule falsified (result_id 58/60).
- **CF1 tested for the first time ever: result_id 56 = −$0.5986/tr, t −2.93, n=1,226.** CF3−CF1 = +$1.63, Welch t +2.52 → the H4 CF3 hump is real.
- **H4-CF3 still NOT significant standalone**: +$1.0349/tr, t +1.68, n=373 (result_id 55); mean carried by ~3 trades.
- 6 results logged this session (**result_id 55–60**), 4 strategy_log entries (**113–116**).
- Frozen presets: [cf3 baseline](../mt5/presets/fob_system/fob_h4cf3_l1_k050_trail_a1r0_d1r5.set) · [cf1](../mt5/presets/fob_system/fob_h4cf1_l1_k050_trail_a1r0_d1r5.set) · [cf3 CFINVAL](../mt5/presets/fob_system/fob_h4cf3_l1_k050_trail_CFINVAL.set) · [cf1 CFINVAL](../mt5/presets/fob_system/fob_h4cf1_l1_k050_trail_CFINVAL.set). Baseline ledgers backed up to `research/outputs/fob_cfinval_ab/` (gitignored).

## Next
1. **(task 270, P1)** Entry-mechanic A/B at H4-CF3: `InpEntryMode` CF_MARKET vs CF_L1_LIMIT, one line off the cf3 preset. **The first entry-timing test.** Arms are NOT paired (n differs — the limit doesn't always fill); compare $/trade **and** the instant-death fraction (defined in Live-Threads).
2. **(task 269, P1)** Reframed to entry timing only. Is L1 a bad price, a bad *moment*, or is the CF zone simply not support/resistance?
3. **(task 271, P2)** Multiplicity audit on the H4 cell before adding any further selector.

## Blockers
- **Tasks 202, 260, 240, 245, 262 unchanged** — still no valid excursion measure (task 202 unblocks them).
- Task 269's deeper measure (MFE-before-SL on the 54% cohort) needs task 202. Task 270 does not — run it first.
- Headless tester still requires `terminal64.exe` closed ([[brc_headless_tester_fires]]).

## Why
- **Syafiq opened the session near quitting.** The trail defect gave a concrete thing to fix; fixing it produced three falsifications in one sitting. That is the session's real output, not a P&L number.
- **The trail bug was real.** At `activate=1.0 / dist=1.5`, the candidate SL at activation is `(entry + 1.0R) − 1.5R = entry − 0.5R` — tighter than the original `−1.0R` stop, so it passed the ratchet and *was placed*, on the losing side. Nothing locked until peak > 1.5R.
- **But the fix cancelled itself out** (result_id 55 vs 39, same 373 trades). It converted 53 trades from ~−0.5R to breakeven — *and* the tighter breakeven stop killed ~7 recoveries (WR 34.0 → 32.2). I **pre-registered a prediction that the median would lift hard. It did not.** `medR` went −0.95 → −0.954. On the record.
- **Why the median didn't move, and this reframed everything:** the median trade never reaches +1R at all, so the trail never arms. `medR −0.954` is a *full* stop-out.
- **`InpCfIdxFilter=0` means ALL CFs, not CF1.** Syafiq asked to "run CF=0"; it was already run (result_id 41, −$0.516). **CF1 alone had never been tested at H4** — every logged H4 key was cf0/cf2/cf3. "CF1 has no edge" was an assumption, not a measurement.
- **CF1 was run and is a decisive loser** (result_id 56, t −2.93, n=1,226). That is *good news*: a strong negative next to a positive cell is what makes CF3 meaningful. CF3 beats CF1 on **win rate** (32.2 vs 27.6), **not** on the tail (R>2: 10.2% vs 8.4%).
- **CfInval was rejected by a rule set BEFORE the data.** Required: help both arms. It helped CF1 (+0.0425, t+0.73) and hurt CF3 (−0.3272, t−1.03). Neither significant. The n=373 arm never got a chance to flatter us.
- **The asymmetry is the lesson.** On CF3 it improved 36 trades by ~+0.12R and destroyed **6 at −2.92R each**. FOB H4 is **tail-carried**: 38 trades with R>2 sum to +164R against a total of +35R (result_id 55 notes); drop the top 3 and meanR collapses +0.094 → +0.016. **On a tail-carried distribution, any early-exit rule destroys more right tail than it saves left tail.** CF1 has a thin tail → benefits. CF3 *is* the tail → bleeds.
- **Independently corroborated:** result_id 40 (fixed TP rr200, +0.814) < result_id 55 (uncapped trail, +1.035). Capping the tail costs money. Two experiments, same law.
- **The structural finding that closed exits:** CfInval fired on only 9.8% (CF1) / 11.3% (CF3) of trades and rescued **15–17%** of the `R ≤ −0.9` cohort. **83–85% of losers traverse L2 *and* the SL inside a single H1 bar** — an intrabar impulse with no intermediate state for *any* exit rule to react to.
- **Stop distance was already falsified in the DB, unnoticed:** the k-sweep (result_id 27/30/31, n=373 each, so `k` moves only the stop → paired) gives k=0.25/0.50/1.00 → +$0.19/+$0.34/+$0.31. Quadrupling the buffer barely moves $/trade.
- **Geometry note (why the stop is not "tight"):** entry = L1 (zone near edge, limit fill), SL = `L2 ∓ k·band`, so **R = band × (1+k) = 1.5 × band**. To lose 1R, price must traverse the whole CF zone *and 50% more*.
- **Both structural exits were OFF in every result ever discussed.** Proven, not assumed: `exit_reason` derives from `DEAL_REASON`, and an EA close lands as `EXPERT`. All 373 CF3 and all 1,226 CF1 baseline exits read `SL`. Zero expert closes.
- **`InpCfIdxFilter` re-run needed a filename guard.** The ledger name encodes `emtok`/`dirtok`/`k`/`rr`/`cf` but **NOT** `InpExitOnCfInval` — the ON run overwrites its baseline in place (the task-265 arm-B bug). Baselines were copied out first. **Any future toggle A/B must check the filename encodes it.**

## Ruled-Out
- **`InpExitOnCfInval` — REJECTED, strategy_log 116, result_id 58 (CF1) + 60 (CF3).** Mechanism is real (fires on ~10% of trades; 112/121 and 36/42 changed trades improved) but economically null on CF1 and net-negative on CF3. Do not re-run.
- **`InpExitOnOppPbo` (task 254) — DROPPED on evidence, never run.** Strictly coarser than CfInval: fires later, on a whole new opposite cycle. It can only help less and truncates the same right tail.
- **The exit as the lever at H4 — FALSIFIED on two independent axes.** Stop *distance* (paired k-sweep, result_id 27/30/31) and exit *rule* (result_id 58/60). Do not propose a third exit variant without first defeating the intrabar-impulse finding.
- **The trail defect as the explanation for `wideRange`/trail results — WRONG, and it was my claim last session.** result_id 55 shows the fix is P&L-neutral. The contamination warning on result_id 39/41/42/47/48/49/50/51 is **mild, not fatal** → tasks 255/263/268 are **unblocked**, not soft-blocked.
- **"Run CF=0" — not a thing.** `InpCfIdxFilter=0` = ALL CFs, stacked concurrent positions, population screen only (result_id 41, −$0.516/tr). Already in last session's Ruled-Out; Syafiq re-asked, so it is restated here.
- **`cf_idx` as a universal conditioner — dead.** The M30-M15 cfALL ledger (n=8,284, real ticks) is flat and uniformly negative: cf1 −0.65, cf2 −0.51, cf3 −0.58, cf4 −0.43 $/tr, with never-reach-1R at 57–59% at **every** index (`research/outputs/fob_cfinval_ab/`, derived from the v1400 M30 ledger). The CF3 hump is **H4-specific**.
- **My pre-registered prediction that fixing the trail would lift `medR` hard — WRONG.** Stated before the run, falsified by result_id 55. Left on the record deliberately.

## Live-Threads
- **The 54% instant-death cohort is now THE thread.** 52.5% at H4-CF3 (result_id 55), 54.5% at H4-CF1 (result_id 56), 57–59% at every cf_idx on M30-M15. **Invariant to CF index and to timeframe.** 83–85% of it is intrabar impulse. Nothing we have tried moves it. Task 270 is the first probe that can.
- **The uncomfortable question behind task 270:** if switching to CF_MARKET does *not* move the never-reach-1R fraction, then the CF zone is **not a real support/resistance level**, and FOB needs a premise re-think rather than another parameter. That outcome is on the table and should be named out loud before the run, not after.
- **H4-CF3's whole case rests on ~3 trades.** +$1.0349/tr at t +1.68 over 8 years (result_id 55); drop the top 3 and meanR is +0.016. Its OOS win is n=43 (result_id 50). It survived a genuine contrast against CF1 (Welch t +2.52) — but **4 H4 cells have now been tested**, and the multiplicity has never been counted. Task 271.
- **The H4 ladder is non-monotone**: cf1 −0.599 (result_id 56), cf2 −1.064 (result_id 33), cf3 +1.035 (result_id 55). A spike at one cell is weaker evidence than a gradient. Nobody has explained *why* the third confirmation specifically.
- **A ledger-filename audit is overdue.** `InpExitOnCfInval` is not in the name and silently overwrote its baseline; `InpExitOnOppPbo`, `InpTrailStop`, `InpTrailActivateR/DistR`, `InpSessionFilter` and `InpDirFilterTf` are **also absent**. Every one is an in-place-overwrite trap for the next A/B. Not yet a task.
- **M30-M15's OOS block is spent** (carried, unchanged). Both direction arms ran full-span.
- **Doc landmines, still not fixed** (carried, unchanged): [storyline-alignment findings](../docs/specs/2026-06-27_fob_storyline_alignment_findings.md) §2 is void with no banner; [v0.2 entry-logic spec §6](../docs/specs/2026-07-02_fob_sequence_storyline_entry_logic_v0.2.md) points at retired `fob_trader.mq5`.
- **$50 rapid-scalp mandate still unscoped** (carried). Live H4-CF3 is a swing setup. The M30 reversal "cheat code" (imgs 6.5/6.6) remains the one cheap falsifiable scalp claim, unclaimed.
