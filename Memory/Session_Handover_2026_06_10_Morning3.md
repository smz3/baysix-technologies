# Handover — June 10, 2026 Evening2

## State
**ORB-002 fully validated (task 25 done, see Evening handover). Session wrapped after housekeeping discussion.**

One decision made this session:

**Option A chosen for orb/ folder restructure (task 27, P1):**
```
research/models/orb/
  orb001/     ← all London ORB-001 files
  orb002/     ← all NY ORB-002 files
  shared/     ← structures.py etc — only if genuinely imported by both
              (ORB-002 inlined trail logic, so shared/ may end up empty)
  orb003/     ← Task 26 noon ET anchor (new)
```
Rationale: maps 1:1 to DB idea_id, scales cleanly as the family grows. Option B (flat + naming convention) rejected — folder already strained at ~40 files.

## Open Backlog
| # | Pri | Title |
|---|-----|-------|
| 26 | P1 | ORB-002 transplant test @ mid-session ~12:00 ET anchor |
| 27 | P1 | Restructure research/models/orb/ into idea subfolders (Option A) |
| 4  | P2 | ORB-001 MQL5 port into Sigma EA (live XAUUSD) |

## Next Session — ordered
1. **Task 27 (P1) — do the restructure first.** Move ORB-001 files into `orb001/`, ORB-002 into `orb002/`, check if `shared/` is needed (likely not). Fix all import paths. Smoke-test: run `gate2_sanity.py` (London) and `gate2_sanity_ny.py` (NY) to confirm nothing broke.
2. **Task 26 (P1) — noon ET anchor scan.** After folder is clean, drop new files into `orb003/`. Cheap exploratory: reuse ORB-002 harness primitives, anchor=12:00 ET DST-aware, sweep N={5,15,30}, Gate 3 raw + Gate 5 net only (no full gate ladder unless it signals). NOT lit-backed — native hypothesis from our tape.
3. **Task 4 (P2)** — ORB-001 MQL5 port after the above.

## Notes
- Task 26 was bumped from P2 → P1 this session.
- Task 27 added this session (new task_id=27 in log_tasks).
- Folder restructure is a prerequisite for Task 26 (orb003/ slot needed).
