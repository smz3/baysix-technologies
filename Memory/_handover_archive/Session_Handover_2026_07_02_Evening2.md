# Handover — July 2, 2026 Evening2

## State
- FOB visual refactor DONE: [fob_visual.mqh](mt5/Include/fob_system/fob_visual.mqh) 728→272 lines; out-of-line `CFobVisual` bodies moved to [fob_visual_prims.mqh](mt5/Include/fob_system/fob_visual_prims.mqh) (81) / [fob_visual_lifecycle.mqh](mt5/Include/fob_system/fob_visual_lifecycle.mqh) (106) / [fob_visual_draw.mqh](mt5/Include/fob_system/fob_visual_draw.mqh) (310), `#include`d after the class decl.
- Part-files carry NO include guard by design — pulled in only by fob_visual.mqh, never directly. EA + all consumers untouched. Headless compile = **0 errors** (1 benign MQL5-Market version-format warning). Pure code move, byte-identical logic (task 224 done).
- OPEN BUG (task 223, P1): live-chart **historical T-touch + RT dots are wrong on low TFs** (M5/M15/M30/H1), spot-on D1/W1/MN1. Not the refactor — a data-path issue.

## Next
1. **CONFIRM THE NATURE FIRST** (task 223): pick one wrong low-TF dot — is it a *constant directional shift* (≈ a fixed hour offset → timezone/UTC seam) or *random per-dot* (→ genuine dual-path drift)? A fixed few-hour offset is invisible on D1/W1/MN1 but dozens of bars on M5 — matches the symptom.
2. If offset → chase the server-time vs UTC seam between where touch time is stamped (`tk.time`) and where the dot is drawn (`iTime`); likely one-line fix, no redesign.
3. If drift → **kill Engine 2**: replace the live-only bar-wick backfill with a **deep causal warm-up over real historical TICKS** (`CopyTicksRange`) through the SAME `FobAcc*` accumulator on attach, so live == tester, tick-exact WHEN+WHERE. Alt: project pre-attach history from the EMIT CSV / `fob_zones` oracle.

## Blockers
- None — but do NOT redesign the load path until step 1 (offset-vs-drift) is confirmed; picking A/B/C blind would be guessing.

## Why
- **HARD REQUIREMENT (Syafiq):** the backfill MUST be truthful to *WHEN and WHERE* each zone was touched — these touch times are strategy-critical, and getting them wrong means the code can't be trusted yet.
- The distrust is real and structural: there are **TWO lifecycle engines on the display path** — (1) causal accumulator `FobAcc*` = the truth, runs in BOTH live and tester; (2) bar-wick backfill `FobBackfillLadderTimes` (task 217) = an approximation, **LIVE-CHART ONLY** (`if(live)`), bolted on to patch the pre-attach blind spot.
- Tester needs NO backfill because it replays every tick from test start → accumulator sees all history causally → **tester is already the single-engine, tick-exact gold standard.** The live chart is the one carrying the extra approximate patch.
- Physical constraint driving the whole decision: **bar OHLC cannot recover intrabar touch TIME** — a wick tells you the level was crossed *sometime in that bar*, not when. So bar-resolution backfill lands in the right day/week (D1/W1/MN1 look perfect) but the wrong minute-bar on low TFs. Tick-exact history REQUIRES replaying real ticks.
- Refactor split boundaries chosen to match existing conceptual seams (primitives / stamp-state / paint) so no method spans two files.

## Ruled-Out
- **Parent-row / cycle-end-eviction bug** (T dots read `ev[i]` PBO row vs RT dots read `ev[parIdx]` VR row): real asymmetry, but **MASKED on a live chart** because the backfill refills the frozen PBO row's empty slots from bars. It only surfaces in tester-visual (backfill off). NOT the cause of the live-chart symptom Syafiq is seeing. Do not chase it for the live bug.
- Bar-resolution *coarseness* as the explanation: rejected — coarseness would make HIGH TFs worse, not better; the symptom grades the opposite way, which points at a constant offset or a wrong-bar (drift), not coarseness.

## Live-Threads
- Constant-offset hypothesis is the leading unconfirmed lead — needs the one-look check in Next#1 before committing to any redesign.
- Load-path redesign (Option A deep tick warm-up / Option B project-from-EMIT-oracle) is a design decision that should get its own spec once the nature is confirmed; the "kill Engine 2, one accumulator everywhere" direction is agreed in principle but not yet scoped.
