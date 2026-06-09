# Handover — June 9, 2026 Evening

## State
**London fully sealed** — closed the last 2 ORB-001 variants, both FALSIFIED, live config UNCHANGED (09:00/N5 · trail_1R · Mode-A 5% cap · immediate breakout). **Task 19 re-entry/2nd-breakout FALSIFIED**: 2nd breakout after a losing 1st trade has negative edge (IS $/t -0.21, t-13.9) + worsens $50 survival (p90 DD 10.9→18.8%); the tempting after-WIN arm ($/t +2.84) was an **idealised-fill artifact** (100% phantom fills, price mean $2.37 past the OR level — task-12 trap, caught via sameDir=100% + gap diag). **Task 20 fade FALSIFIED peek**: fading a failed breakout loses across all windows (IS $/t ~-0.17, t-10.4), honest fills — NOT spun out as ORB-003. New harnesses [reentry.py](../research/models/orb/reentry.py), [fade.py](../research/models/orb/fade.py). DB: results 76-79, strategy_log #15/#16, tasks 19/20/24 done. **Infra: fixed run-completion notify** — old waiter polled output mtime "within 5s" (a once-written file never satisfies it → hung, never notified). New [run_tracked.py](../research/code/run_tracked.py): launches in -NoExit window + drops a DONE sentinel (exit code, in finally); wait existence-only. Dogfooded on the fade run — works. **Task 24 done**: [archive_handovers.py](../.claude/hooks/scripts/archive_handovers.py) auto-sweeps older handovers to _handover_archive on SessionStart (keeps today's).

## Next
1. **Task 3 (P1, variant)** — ORB-002 NY-session ORB (Syafiq's fork: London→**NY**→compare→MT5). NY needs real DST (America/New_York 09:30 → 13:30/14:30 UTC) — NOT a fixed UTC anchor like London. Spec before building.
2. OR **Task 4 (P2, port)** — ORB-001 MQL5 port into live Sigma EA (trail_1R + 09:00 anchor).
3. Infra (both quick, non-urgent, no live impact): **task 23** — gate_pipeline view shows false-blocked HMM-001 G2/G4 (stale attempts; dedupe to MAX(attempt) per idea,gate in db_init.py + migration). **task 7** — fold utf-8 stdout tee into run_tracked.py (harnesses already emit utf-8 JSON/CSV; only the tee log is missing).

## Blockers
None. All committed + pushed to master. Launcher pattern: `python research/code/run_tracked.py <name> -- python -X utf8 <script.py>`, then `until [ -f research/outputs/_runs/<name>.done ]; do sleep 10; done` (run_in_background). Pass a script PATH not inline `-c`.
