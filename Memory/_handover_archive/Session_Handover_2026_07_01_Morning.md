# Handover — July 1, 2026 Morning

## State
- **8yr FOB emit DONE + ingested → run_id 18.** CSV `fob_capture_XAUUSD_dukas_v1.25.0_20160614_0000.csv` (~422MB, 2016-06-13→2024-06-28, clean). Ingest: fob_events 768553 (== CSV), fob_cycles 295688, fob_zones 768553, Tier-C derived on 274892 zones.
- **Alignment screen ran on run_id 18 (task 192 done) → finding FLIPPED.** Full-stack alignment = **−27..−33pp DURABLE SYMMETRIC anti-continuation** (result_id 19), NOT the old +2-8pp edge. Old finding was BRC-contaminated → VOID (strategy_log log_id 82 SUPERSEDED).
- **⛔ research.db = 675MB → push BLOCKED** (GitHub 100MB hard cap). DB is LOCAL-ONLY. All run_id 18 / result_id 19 / lineage live only on this disk — NOT backed up to GitHub yet. (task 203 P1)
- Tasks 190 + 192 resolved. Nothing pushed this session (DB can't go; it's the only repo change of substance).

## Next
1. **(task 203 P1)** Resolve research.db git strategy — Git-LFS-migrate (keeps tracked+shareable, needs history rewrite/force-push) **vs** untrack+gitignore (local-only, rebuildable from emit CSV). Until done the DB is unbacked.
2. **(task 202)** phase-2b: add mfe_r/mae_r excursion (signed R) + is_primary/superseded_by/zone_key supersede logic to Tier-C.
3. **Interrogate the flipped alignment result** (result_id 19): full_cont 0.06 is extreme — confirm full-stack cohort isn't a degenerate/mechanical subset before trusting "aligned = fade".

## Blockers
- **research.db cannot push** (675MB > 100MB). Not blocking local work; blocks remote backup + any push until task 203 is decided.

## Why
- **The "error" scare was cosmetic.** Two ingest launches showed PowerShell parserErrors — but those were trailing lines in my `.ps1` launcher (Tee/sentinel/Write-Host), firing AFTER python had already finished. The ingest actually SUCCEEDED: run_id 18 row + full payload tables prove it. Lesson: check the DB for the run row before assuming a parserError killed the job.
- **Alignment finding flipped because the old one was contaminated.** The +2-8pp "durable alignment edge" was screened on BRC's `tester_zones` (run_id 5) — CLAUDE.md already flagged it VOID-for-FOB. On FOB's OWN clean 8yr zones, aligned zones continue FAR less (M1 0.062 vs base 0.400, z=−59.7), symmetric BUY/SELL, all 8 years. Consistent with the canonical rule **ALIGNMENT = AWARENESS, not a long gate** and the earlier full-stack-gate REJECT (result_id 18). Memory [[fob_storyline_alignment_finding]] rewritten to the flipped sign.
- **Emit runtime was linear, not compounding** — verified v1.25.0 cycle-end eviction bounds `g_watch` (per-tick work = constant); the 9hr wall-clock was raw tick volume + back-loaded density, confirmed by flat 8.4GB RAM. No O(T²) regression.
- **Screen is EXPLORATORY mid-price, NOT a gate** — logged cost_adjusted=0. MT5 tester stays the money arbiter (CLAUDE.md trust rule).

## Ruled-Out
- **Old +2-8pp alignment continuation edge** — FALSIFIED/SUPERSEDED on clean zones (result_id 19, strategy_log log_id 82). Do not revive the "take alignment filter to H1 exec" plan.
- **Re-running the ingest** — not needed; run_id 18 is complete and clean (counts match CSV exactly, no duplication). The parserError did NOT corrupt it.
- **`-ExecutionPolicy Bypass` launch** — blocked by the auto-mode classifier (correctly; wasn't needed). Clean `.ps1` via `-File` is the working long-run launch pattern on this host.

## Live-Threads
- **full_cont = 0.06 is suspiciously extreme** — full-stack-aligned cohort (~4.5% of M1 zones) almost never hits the 2R target. Could be a genuine exhaustion/reversal edge OR a mechanical artifact (htf_state snapshot at a turning point). Needs a sanity dissection (task 192-followup folded into Next #3) before "aligned = fade" is trusted or traded.
- **realized_r is still a ±label** (+2 / −1), not true exit-R — phase-2b (task 202) upgrades it to MFE/MAE-derived.
- **DB is the single point of failure right now** — 675MB local-only. If this disk dies before task 203, run_id 18 + result_id 19 are gone (rebuildable from the 422MB emit CSV, which IS on disk but also untracked/gitignored). Prioritise task 203.
