# Handover — June 26, 2026 Morning

## State (FOB classifier VR-picking bug fixed + handover-archive prune wired; no new research results)
- **FOB v1.9.0 (sha 2592f1c) — VR same-bar pick FIXED.** When one bar broke several opposite swings at once, the VR locked on the FIRST fed (oldest/furthest) swing instead of the NEWEST (nearest the turn — the red circle Syafiq drew). Now it locks on the newest swing among same-bar opposite breaks: replace-in-place on the already-emitted VR row (same dot, no duplicate event), gated to `bt == vr_time` so cross-bar opposite breaks still don't move the VR. Mirror of the PBO freshness gate + CF watermark.
  - [fob_sequence.mqh](mt5/Include/fob_system/fob_sequence.mqh) — same-bar VR-upgrade branch. [fob_types.mqh](mt5/Include/fob_system/fob_types.mqh) — `+vr_swing`, `+vr_ev_idx` on FobSetupState; FOB_VERSION 1.9.0. OnInit resets + `#property version` 1.9.0 in [fob_trader.mq5](mt5/Experts/fob_system/fob_trader.mq5) and [fob_baysix.mq5](mt5/Experts/fob_system/fob_baysix.mq5).
  - **Compiled clean** (0 err, 1 cosmetic Market-version warning) via PowerShell `Start-Process -Wait` — bash-direct metaeditor64 silently no-ops ([[brc_compile_workflow]]). `.ex5` regenerated 08:18.
  - ⚠️ **Side-effect:** the CF chain watermark is seeded from the VR swing, so CF1 timestamps shift wherever a same-bar tie existed. Any FOB visual/ledger from before 2592f1c is stale on those cycles.
- **Handover-archive prune wired (sha after).** [prune_handover_archive.py](.claude/hooks/scripts/prune_handover_archive.py) existed but was called by NOTHING → archive grew to 72. Now wired into SessionStart right after `archive_handovers.py` with `--days 2 --apply` ([settings.json](.claude/settings.json)). Ran it: 60 deleted (06-13→06-23), 12 kept (06-24+06-25).
- FOB-001 research state UNCHANGED from 06-25 Evening2: continuation entry FALSIFIED, CF1 carries the signal (reversal-lean), open question = execution vs direction.

## Next
1. **(task 173, P1) Visual-verify the v1.9.0 VR fix** — run `fob_baysix` visual on H1/D1 around the 23-25 Jun case; confirm VR sits on the newest swing + CF chain is sane. Pre-step to 170.
2. **(task 170, P1) CF forward-excursion study** (MFE/MAE/terminal-return per CF1) — decompose direction vs entry-timing. THE missing measurement; do before more barrier backtests.
3. **(task 171, P1) Retest entry** — limit-on-pullback into PBO zone (`InpEntryMode = MARKET | LIMIT_PBO`).

## Blockers
None. Headless compile requires the JM terminal CLOSED + PowerShell `Start-Process -Wait` (not bash-direct).
