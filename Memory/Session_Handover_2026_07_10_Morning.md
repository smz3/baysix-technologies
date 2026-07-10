# Handover — July 10, 2026 Morning

## State
- **Task 265 DONE** — `InpInvertDir` shipped in [fob_baysix.mq5](../mt5/Experts/fob_system/fob_baysix.mq5) v1.40.0, git `46216a0`, `FOB_GIT_DIRTY=false`. Mirror geometry in all three entry funcs of [fob_entry.mqh](../mt5/Include/fob_system/fob_entry.mqh).
- **The CF direction flip is FALSIFIED at M30-M15 — BOTH directions lose.** strategy_log **112**.
  - normal **result_id 52** = −$0.5504/tr (n 6,688, t−7.74) · inverted **result_id 53** = −$0.4944/tr (n 6,473, t−7.25)
  - paired on the same CF events **result_id 54** = **+$0.0552/tr, t +0.46** → null. `is_run='IS-DIR-M30M15'`.
- **Task 266 DONE-as-moot** — both arms ran on ONE clean binary, so the A/B is valid; but the window was full-span (2016-06→2026-05), so the OOS block is consumed for M30-M15. No winner to validate, so it doesn't matter.
- **Live H4-CF3 config untouched** — `get_live_config('FOB-001')` still reads `cf3 k0.50 RR2.0` (log 111, result_id 25). Verified after the FALSIFIED write.
- **New defect, unfixed (task 267, P1):** `InpTrailActivateR=1.0` + `InpTrailDistR=1.5` puts the trailed stop **0.5R below entry** at activation. Nothing locks profit until peak > 1.5R.
- Two presets committed, verified to differ by exactly one value line: [A_baseline.set](../mt5/presets/fob_system/fob_m30m15_cfALL_trail_k050_A_baseline.set) / [B_inverted.set](../mt5/presets/fob_system/fob_m30m15_cfALL_trail_k050_B_inverted.set).
- Full write-up: [2026-07-10_fob_direction_ab_armA_exploratory.md](../docs/specs/2026-07-10_fob_direction_ab_armA_exploratory.md). Ledgers archived to `research/outputs/fob_ab_direction/` (gitignored).

## Next
1. **(task 268, P2 → treat as the lead)** Measure the **both-lose fraction on H4-CF3**, where the live edge is. At M30-M15 it is **40.7%** (see Why). If H4's is much smaller, the both-lose rate is the **TF-selection criterion**, not direction.
2. **(task 267, P1)** Decide trail semantics before reading ANY trail A/B — including tasks 255/263, whose "wide wins under trail" may be an artifact of which zones ever reach the trail distance at all.
3. **(task 263, P1)** Zone-width contradiction, 2×2 `range_w` × exit. **Now downstream of 267** — do not run it until the trail is settled.

## Blockers
- **Task 263 is now soft-blocked on 267** (it was unblocked). Reading a trail A/B while the trail's activation threshold is cosmetic risks a repeat of the storyline-alignment artifact.
- Tasks 260, 240, 245, 262 still blocked on **task 202** (no valid excursion measure). Unchanged.

## Why
- **Syafiq's question was "swap CF buy = sell, can we test it?" The answer was yes, and it was worth testing.** Arm A (continuation, M30-M15, ALL CFs, trail-only, k=0.50) is a decisive loser — **result_id 52**, t−7.74 — which is exactly the precondition a fade needs.
- **A naive `dir` flip would not have compiled into a valid order.** `sl = l2 ∓ buffer` where `l2` is the far edge *in the CF's own direction*; flipping `is_long` alone puts the stop on the wrong side of entry → broker reject. `InpInvertDir` instead measures `risk` off the structural stop then places the stop `|risk|` away **on the side actually traded**. At `invert=false` this is an algebraic identity, so the baseline stays byte-identical — **and it did**: clean arm A reproduced the earlier DIRTY v1.39.0 run to 4dp (−0.6188, n=8,284).
- **Why the flip fails, and this is the finding.** Paired on the same 8,049 CF events (**result_id 54**): A wins 29.8%, B wins 29.0%, **both lose 40.7%**, both win **0.0%**. `corr(R_A, R_B) = −0.360`, **not −1** ⇒ the flip is *not* a mirror. The both-lose bucket is **spread + trail whipsaw**: price runs against A and stops it, reverses, stops B. Money the structure never paid to either side cannot be recovered by changing sides. **Arm A's loss is not invertible signal.**
- **I pre-registered a prediction and it was wrong, on the record.** I predicted +$0.2 to +$0.5/tr, arguing path-dependence "favours the flip." It cuts the other way. The prediction is in the spec above the verdict — leave it there.
- **Two safeguards earned their keep.** The ledger filename gained a `nrm|inv` token (arm B would otherwise have overwritten arm A **in place**), and the init line now prints `DIR=NORMAL|INVERTED`. Syafiq's first "inverted" run was actually arm A again — the token and the stamp caught it in seconds instead of producing a fake null.
- **The v1.39.0 run was quarantined, not logged.** Its `.ex5` stamped `git a025224-DIRTY`. human_decision **call_id 97** records the call: re-run on a clean binary rather than log an irreproducible number into the lineage.

## Ruled-Out
- **CF direction inversion (mirror fade) at M30-M15 — FALSIFIED, strategy_log 112, result_id 54.** Do not retry the flip anywhere until task 268 finds a TF with a small both-lose bucket. Scope is M30-M15 / ALL-CFs / trail-only; it says nothing about H4-CF3.
- **The naive `-1×` intuition ("invert a loser to get a winner") — dead on two counts.** Spread is paid on both sides and does not invert; and with a path-dependent exit the barriers are not reflections, so gross P&L does not flip sign. Both were argued *before* the run and both held.
- **The v1.39.0 full-span arm-A run as a logged result — rejected (call_id 97).** DIRTY binary. Superseded by result_id 52; its numbers happen to match exactly, which is a validation of the identity, not a reason to trust DIRTY runs.
- **`InpCfIdxFilter=0` as a deployable config — never was.** It means ALL CFs (not CF1), stacked concurrent positions. Population screen only.

## Live-Threads
- **The 40.7% both-lose bucket is the loudest thread in the repo right now** (task 268). It reframes TF selection: the question is not "which TF has directional edge" but "which TF has a small fraction of events where both sides get stopped." H4-CF3 works — is its both-lose fraction low? That is one cheap query on an existing ledger, and it may explain the whole TF ladder.
- **The trail defect (task 267) contaminates more than this A/B.** It affected both arms identically here, so the direction verdict stands. But every prior trail result — the `wideRange` +2.73 (result_id 48 family), tasks 255/263 — was read through a trail that cannot lock profit below 1.5R. "Wide wins under trail" may simply mean "only wide zones ever reach 1.5R."
- **161,133 failed `Invalid stops` trail-modify calls** in one run (185 MB tester log). The EA re-issues a modify every tick even when the SL hasn't moved. Log noise, not a correctness bug, but it should be gated on a changed SL — folded into task 267.
- **M30-M15's OOS block is spent.** Both arms ran full-span. Nothing is lost (no winner), but if we ever revive this TF pair, there is no clean held-out window left for it.
- **Doc landmines, still not fixed** (carried, unchanged): [2026-06-27_fob_storyline_alignment_findings.md](../docs/specs/2026-06-27_fob_storyline_alignment_findings.md) §2 is void with no banner; [v0.2 entry-logic spec §6](../docs/specs/2026-07-02_fob_sequence_storyline_entry_logic_v0.2.md) points at retired `fob_trader.mq5`.
- **$50 rapid-scalp mandate still unscoped** (carried). Live H4-CF3 is a swing setup. The M30 reversal "cheat code" (imgs 6.5/6.6) remains the one cheap falsifiable scalp claim, unclaimed.
