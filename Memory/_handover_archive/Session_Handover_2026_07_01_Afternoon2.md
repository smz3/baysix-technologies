# Handover — July 1, 2026 Afternoon2

## State
- **Shipped: parent-PBO context overlay** (commit 394edb7) — [fob_visual.mqh](mt5/Include/fob_system/fob_visual.mqh) `DrawParentPbo`. On any chart, draws the ACTIVE parent-TF (E+1) PBO zone **dimmed + dotted** (e.g. D1's PBO on H4) for storyline context. Toggle `InpShowParentPBO` (default on). Read-only projection, cannot perturb detection. Compiles clean (v1.25.0, 0 err). Syafiq confirmed working on chart.
- **Backlog re-prioritised for CF-first:** 207 (vr_fresh)→P2; **208 split** → VR-placement/clean-messy only, →P2; **209 NEW P1** = CF break-state A/B/C entry logic (carved out of 208).
- **Open bug found (task 210 P1), NOT yet fixed:** messy VRs render as **nothing** on M1. A VR/CF whose 4-pointer band is invalid (`zone_valid=0`) is dropped at [fob_visual.mqh:482](mt5/Include/fob_system/fob_visual.mqh#L482) (`if(!ev[i].zone.valid) return;`).
- **Syafiq's decision: he wants the FULL BOX always drawn** (not just a bare level). Direction locked = method 2 below. Two questions still unanswered → blocking the build.

## Next
1. **(task 210 P1)** Get Syafiq's 2 answers: **(a) real box (feeds trader SL/1R) vs visual-only**, and **(b) confirm method 2** (measure far-edge from raw pullback extreme). Then build: when the clean 4-pointer fails, set L2 = deepest pullback price between origin and break bar (past-only, no look-ahead); fold in "loosen freshness/gap-val from reject→flag". Box then always draws.
2. **(task 209 P1)** CF break-state A/B/C entry screen — DERIVE off run_id 18, cont-lift + net $/oz per bucket. The pressing lever after the box fix.
3. **/handover-adjacent:** if box logic changes zone-building (fob_breakouts), re-emit is NOT auto — the trader reads the same zone, so re-test both EAs.

## Blockers
- **task 210 build is gated on Syafiq's 2 answers** (real-vs-visual box; method-2 confirm). Nothing else blocked.

## Why
- **Parent-PBO overlay = Syafiq's explicit ask** ("see where D1's PBO sits while trading H4") — pure storyline context, so built read-only off the existing event log (zones are absolute-price → render on any TF). Parent-only + active-cycle-only chosen (his pick) over full ancestor stack to avoid clutter.
- **CF-first re-prioritisation:** Syafiq called CF entry logic the pressing matter; VR *placement* is a selection filter (upstream but not the edge), CF *break-state* (A/B/C: trap/best-entry/reversal) is the real lever that likely un-pools the dead baseline (result_id 22). CF *placement* is a minor entry-mechanic (ranked lowest), so 209 targets break-STATE, not placement.
- **The messy-VR bug is real, proven not theorised:** cycle 160 (run_id 18) = PBO(M5,valid) → VR(M1,**invalid**) → CF1(M1,invalid) → CF2/CF3(valid). VR **detection** needs only the ONE broken swing (bar-close, certain); the **box** needs P1+P3 opposite pivots + freshness + gap-val — on a straight-rip/choppy M1 pullback P3 never forms as a confirmed swing → no box. M1 is worst (5997 invalid VRs ~4%, vs M15 86, H1 8, D1 0) because it's noisiest → that's why only M1 looks broken. It's frequency, not an M1-only code path.

## Ruled-Out
- **Same-bar VR freshness upgrade** ([fob_sequence.mqh:117-134](mt5/Include/fob_system/fob_sequence.mqh#L117-L134)) — Syafiq questioned it, then set aside: "it's fine, already baked." It's a correctness tie-breaker (newest broken swing wins within one bar), unrelated to fresh-vs-not-fresh. NOT to be removed. Distinct from `vr_fresh` (task 207).
- **Bare-level-only fix for messy VR — REJECTED by Syafiq.** He does not want just a line; he wants the full box. So the fix must synthesize the far edge, not skip it.
- **Full HTF ancestor stack on the overlay — deferred.** Parent-only chosen; extensible later if wanted.

## Live-Threads
- **Box far-edge = trader stop/1R ref.** Whatever L2 method we pick for messy zones **changes the trades** on those setups (SL sizing). This is the crux of task 210 question (a) — don't build until Syafiq rules real-vs-visual.
- **"Messy VR" == clean/messy flag (Img 3.7).** An invalid-band VR is literally the messy case — so how we render/flag it feeds the demoted clean/messy co-rider in task 208. Worth tagging the fallback zones `messy=1` for the later screen.
- **research.db is LOCAL-ONLY** (675MB > GitHub cap, task 203) — run_id 18 / result_id 19-22 / cycle 160 proof all live only on this disk. Rebuildable from emit CSV (backed up to G:\My Drive\baysix_backups).
- **mfe_r/mae_r NULL on run_id 18** (task 202) — still blocks payoff-magnitude buckets in 209.
