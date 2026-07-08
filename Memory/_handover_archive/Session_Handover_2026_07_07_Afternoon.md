# Handover - July 7, 2026 Afternoon

## State
- **State-Engine measurement session (task 243)** - first empirical pass on storyline confluence, run on run_19 payload (mid-price, cost-free, EXPLORATORY, git-DIRTY, NOT a gate).
- Two new screens: [confluence_topdown_screen.py](../research/models/fob/alignment/confluence_topdown_screen.py) (top-down, grandparent dir x phase) + [anchor_and_bottomup_screen.py](../research/models/fob/alignment/anchor_and_bottomup_screen.py) (independent-anchor mirage test + bottom-up phase). Numbers artifact: research/outputs/fob_confluence_run19/confluence_directions.csv.
- **Direction-agreement-to-fixed-target = FALSIFIED** (strategy_log log_id 92): flat vs independent D1/W1 anchor (M5 dER=-0.030; artifact research/outputs/fob_confluence_run19/confluence_directions.csv).
- **UNRESOLVED (the live prize):** a strong intra-band counter/reversion signal - fade H1 on sub-H1 setups - that we cannot call edge-vs-artifact because run_19 has `realized_r` only (`mfe_r`/`mae_r` NULL -> blind to run-distance).
- Key limitation surfaced (Syafiq): `realized_r` = outcome-to-resolution, NOT how far price ran. Confluence's real payoff (bigger runs) is invisible in this emit.

## Next
1. **(task 246, P1)** FOB **excursion re-emit** - populate `mfe_r`/`mae_r` (ingest_fob phase-2b PART B / task 202) so confluence is testable on run-distance, not just hit-rate-to-target. The unblocker for everything below.
2. **(task 247, P1)** FOB **H1-band counter/reversion validation** - re-run the H1-controller screen on excursion (does "counter" actually RUN, or just resolve-to-target?), THEN MT5 trader (arbiter) on the fade-H1 setup. Depends on 246.
3. **(task 245, P2)** FOB **Location Detector** - continuous `room_R` (distance-to-wall). Still the untested lever; direction is dead, room is not.

## Blockers
- **246 gates 247 and any confluence verdict.** Cannot judge the intra-band signal on `realized_r` (blind to run-distance). Need the excursion re-emit first.

## Why
- **Ordering State-Engine measurement before build (Syafiq):** htf_state is already emitted (100% populated, per-TF `{dir,cf}`, own-PBO dir = independent by construction, [fob_types.mqh:276](../mt5/Include/fob_system/fob_types.mqh#L276)). So "record awareness" needed zero build - measure first on run_19, build the Selector only from what survives. Respects the [[fob_storyline_alignment_finding]] independence lesson.
- **Ownership settled (Syafiq):** cycle owned by the PARENT (PBO fires on setup_tf), TRADED by the child (VR/CF on setup_tf-1). Confirmed empirically - parent(setup_tf) dir == trade dir 100%. So parent-agreement is SOP-baked (low variance); confluence variance lives in the grandparent+ stack.
- **cf3 dropped (Syafiq, viability):** waiting for a 3rd CF starves trade count over 8yr - not worth it regardless of the survivorship question. Task 242 no longer needed.

## Ruled-Out
- **Direction-agreement as a hit-rate filter - FALSIFIED** (strategy_log log_id 92; artifact research/outputs/fob_confluence_run19/confluence_directions.csv). Top-down adjacent-grandparent looked huge (M5 counter dER=-0.847, t=-128) but is **VR-nesting coupling** - the parent PBO ~= the grandparent's VR/retrace leg, so "counter" mechanically = trading the pullback. Against an **independent** D1/W1 anchor it collapses to ~0.03R (M5 dER=-0.030 t=-4.95; M15 +0.006; M30 +0.009). Matches old guarded screens (results 20/21 ~ 0). Do not re-run direction-agreement-to-target as an edge filter.
- **Bottom-up direction-conditioning - do NOT try.** "Lower controls higher" makes a higher TF's direction a *definition* of its lower neighbor -> maximal tautology. Bottom-up is only valid as a LOCATION/phase lens, never a direction vote.
- **cf3 entry (task 242 survivorship) - dropped on viability**, not falsified. Too few trades over 8yr.

## Live-Threads
- **Intra-band counter/reversion (THE hot thread, task 247; artifact research/outputs/fob_confluence_run19/confluence_directions.csv):** H1-controller band (sub-H1 setups vs H1 own-dir) shows a massive counter split - M5 dER=-1.756 (t=-352), M15 dER=-1.655 (t=-112) - that survives at H1/M30/M15 but **dies at D1** (D1 anchor M5 dER=-0.030). This is Syafiq's "H1 controls the band below; D1 is too far, loses context." It is EITHER real intraband mean-reversion OR pullback-leg geometry inflating `realized_r`. **Un-callable until the excursion re-emit (246).** I retracted my earlier "99% mirage" - the D1-collapse is equally explained by "D1 too far to carry intraday context," not proof of artifact.
- **`realized_r` blind-spot:** it truncates at resolution; a move that ran the right way but missed target / reversed reads flat-negative. Every number this session inherits this. The excursion fields (`mfe_r`/`mae_r`) are the fix - confirm they populate on the re-emit before trusting any confluence read.
- **Bottom-up phase (weak proxy):** lower-TF cf-count as a location proxy was flat (H1 setup fresh/mid/late ~ -0.60 each; artifact research/outputs/fob_confluence_run19/confluence_directions.csv). Does NOT kill the room thesis - cf-count is a poor room proxy; true `room_R` (task 245) still untested.
