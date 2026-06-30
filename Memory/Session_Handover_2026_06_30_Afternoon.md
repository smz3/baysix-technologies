# Handover — June 30, 2026 Afternoon

## State
- **8yr FOB emit IN FLIGHT** — `terminal64`/`metatester64` (PID 16108/18592, 8.4GB RAM) running [fob_emit_8yr.ini](../mt5/tester/fob_emit_8yr.ini) (2016.06→2024.07, Model=4 real ticks, v1.25.0). ~halfway at last check; revised ETA **~9–12hr total** (tick density back-loaded, not a bug). Launched direct via Bash (Option A), NOT PowerShell.
- **Tier-C ingest BUILT + tested (task 200 DONE)** — `tester.derive_fob_confirm_linkage` (next-CF pointer) + `tester.derive_fob_tier_c_outcome` (numba fwd fixed-target barrier sweep, 2:1 reward:risk, on M1 mid bars). Auto-wired into [ingest_fob.py](../research/code/io/ingest_fob.py); standalone [ingest_fob_phase2.py](../research/code/io/ingest_fob_phase2.py).
- **Alignment screen BUILT** — [storyline_alignment_screen.py](../research/models/fob/alignment/storyline_alignment_screen.py); isolation guard (idea_id=FOB-001), zone_valid=1, MN1 warm-up cutoff. Full chain proven end-to-end on run_id 17.
- **DON'T interrupt the terminal** — capture flushes only at OnDeinit; a kill loses the 8yr CSV.

## Next
1. **(task 190)** On emit completion: `python research/code/io/ingest_fob.py --csv "<...Common/Files/FOB/fob_capture_XAUUSD_dukas_v1.25.0_20160614_0000.csv>" --period-start 2016-06-01 --period-end 2024-07-01` → run_id 18 (auto-runs Tier-C linkage + 2R outcome).
2. **(task 192)** `python -X utf8 research/models/fob/alignment/storyline_alignment_screen.py --run-id 18` — the real screen (1yr cohort was too sparse, n_full=11).
3. **(task 202)** phase-2b: add mfe_r/mae_r excursion + supersede/is_primary to Tier-C.

## Blockers
- None. Emit is a known-good long run; ingest→Tier-C→screen chain validated on run_id 17.

## Why
- **`continued` is a forward PRICE outcome, NOT next-CF linkage.** First Part-A attempt set `continued` from "did a later CF print" → degenerate **0.99** (run_id 17). The findings' ~0.50 is a price win/loss. Syafiq chose **fixed 2R target vs 1R stop** (entry=l1, stop=l2, R=|l1−l2|); MFE/MAE deferred. Sweep on run_id 17 → **hit-rate 0.3874, breakeven 0.333 → +EV gross** (exploratory mid; artifact [tier_c_runid17_2R.json](../research/outputs/fob/tier_c_runid17_2R.json)). Linkage kept only as the `confirm_time/price` pointer.
- **M1-bar mid first-touch** (not ticks) for the barrier sweep — right resolution for an EXPLORATORY mid-price screen, ~100× lighter than 500M ticks. Same-bar target+stop tie → **stop first** (conservative). Labelled NOT-a-gate; MT5 tester stays the money arbiter.
- **The "suddenly can't launch" saga = auto-mode classifier, not a settings rule.** All 4 settings files checked — NO `PowerShell` deny exists. The classifier blocks powershell.exe-through-Bash as tool-switching. Fix = Option A (direct `terminal64.exe` from Bash). No safety was flipped.
- **8yr runtime >> 90min estimate** because tick density is back-loaded (2020–24 ≫ 2016 preflight year); MT5's calendar-based progress bar undercounts the dense back half. 8.4GB RAM is legit tick cache (40GB box, 23GB free) — no leak/swap risk.

## Ruled-Out
- **Next-CF-linkage `continued`** — degenerate ~0.99 (run_id 17), not a hit-rate. Replaced by the 2R price barrier. Linkage survives only as `confirm_time/price`.
- **Tick-resolution barrier sweep** — rejected for the exploratory screen (500M ticks, slow); M1 mid bars are the right altitude. (Tick path still matters for the EA — that's the MT5 trader, downstream G3/G4.)

## Live-Threads
- **run_id 17 Tier-C is now populated** (continued/realized_r via 2R) — it's a 1yr PREFLIGHT, fine for code-proof but NOT the screen dataset; the real numbers come from run_id 18.
- **Full-stack-alignment cohort tiny in 1yr** (n_full=11, all losses) — sample-size artifact, not signal. Need run_id 18's denser MN1/W1/D1 context before reading any alignment lift.
- **realized_r is currently a label** (+2 / −1), not true exit-R — phase-2b (task 202) can upgrade to MFE/MAE-derived once the 2R screen is read.
- **W1/MN1 warm-up cutoff** still derived per-run from first MN1 VR (run_id 17 → 2017-01-29); on run_id 18 it'll sit ~2018 once the 8yr MN1 ladder forms.
- `research.db` is 88MB tracked (GitHub >50MB warning, non-fatal) — LFS migration someday, not now.
