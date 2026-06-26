---
name: handover
description: 'Write a session handover to Memory/ before ending any session.'
---

# /handover — Session Handover Writer

## Step 1 — Get timestamp

Run this to get the date, slot, and next available filename:

```bash
python -c "
from datetime import datetime
from pathlib import Path
dt = datetime.now()
h = dt.hour
slot = 'Morning' if 5<=h<12 else 'Afternoon' if 12<=h<17 else 'Evening' if 17<=h<21 else 'Night'
date_str = dt.strftime('%Y_%m_%d')
base = f'Memory/Session_Handover_{date_str}_{slot}'
n = 1
while True:
    suffix = '' if n == 1 else str(n)
    path = Path(f'{base}{suffix}.md')
    if not path.exists():
        print(f'{base}{suffix}.md')
        break
    n += 1
"
```

Use the printed path as the filename. Never overwrite an existing file — the script handles numbering (Morning, Morning2, Morning3…) automatically.

## Step 2 — Write the file

The file has **two parts**, each with its own job:

- **HEAD** (`## State` / `## Next` / `## Blockers`) = the 10-second cold read — *what
  do I do now*. This mirrors `log_tasks`. **Keep the head under ~25 lines, bullets only.**
- **NARRATIVE** (`## Why` / `## Ruled-Out` / `## Live-Threads`) = the anti-rot context
  that lives NOWHERE ELSE — *why we're here, what's already dead, what's mid-flight*.
  Tight bullets, **no length cap**, but it is still read in full every session, so it
  earns its tokens by stopping re-litigation — never prose walls. Each narrative section
  is **mandatory**: write the bullets, or write `- None this session.` (the lint blocks
  a missing section, so you must consciously decide each one).

```markdown
# Handover — <Month Day, Year> <TimeOfDay>

## State
- [What exists / current config — file path if relevant]
- [What works]
- [What's broken or unresolved]

## Next
1. [Exact first action — include file path or command]
2. [Second action]
3. [Third action if any]

## Blockers
- [None — or specific blocker and what's needed to unblock]

## Why
- [Why the current State is shaped this way — decisions made + their rationale.
   Stops the next session re-arguing a settled call.]

## Ruled-Out
- [What we TRIED this session and rejected, so nobody retries it cold.
   For a strategy-defining kill (REJECTED/FALSIFIED), cite the strategy_log /
   result_id instead of re-prosing it — only light dead-ends live inline here.]
- [- None this session.  ← if nothing was ruled out]

## Live-Threads
- [Half-finished investigations / hunches mid-flight that are NOT clean enough
   to be a `## Next` task yet — the loose ends that rot if not named.]
- [- None this session.  ← if nothing is mid-flight]
```

**Why two parts:** the head is the actionable summary (also in `log_tasks`); the
narrative is the only home for *why / dead-ends / loose threads*. Squeezing both under
one tight cap is what made narrative rot — so the cap is on the HEAD only.

## Step 2.5 — Lint (BLOCKING)

The lint enforces three things, all blocking:
1. **Required sections present** — `State / Next / Blockers / Why / Ruled-Out /
   Live-Threads` must all exist (an explicit `- None this session.` satisfies the
   narrative ones). A missing section blocks — this is the teeth on the narrative
   contract (task 180); without it the narrative rules just rot like prose.
2. **State is bullet-point form** (no prose paragraphs).
3. **Every result-shaped number cites a backing artifact** — R-multiples, t-stats,
   win-rates, $/trade, Sharpe, z must cite a `step4_results` result_id (e.g.
   "result_id 121") or an on-disk artifact path (`ReportTester-*.xlsx`,
   `outputs/**/*.json|csv`) in the SAME `##` section. Kills the hand-typed-number
   bug (task 50).

```bash
python research/code/infra/handover_lint.py <the-handover-path-you-just-wrote>
```

If it prints **BLOCKED**, the handover is NOT done: add the missing citation
(re-run `pipeline.log_result()` for the number if no result_id exists yet, then
cite it), re-write, re-lint until it prints **OK**. Do not hand-wave past this —
the same gate runs again at `git commit` (`.git/hooks/pre-commit`).

## Step 2.6 — Sync log_tasks (BLOCKING)

Every handover MUST leave `log_tasks` reflecting reality before the file is written.
The SessionStart brief reads `log_tasks`, NOT this prose — an un-synced task rots
silently (the seam that cost 4 sessions: [[handover_nextsteps_must_be_tasks]]).

Do this via the code layer ONLY (`research/code/lineage/backlog.py` — never raw sqlite3):

1. **Resolve what you finished this session.** For each task you completed/dropped:
   ```bash
   python -c "from research.code.lineage.backlog import resolve_task; resolve_task(<task_id>, '<one-line resolution>', status='done')"   # or status='dropped'
   ```
2. **Open a task for every `## Next` line.** Each numbered action in your `## Next`
   block must map to an `open` task. If it doesn't exist yet, add it:
   ```bash
   python -c "from research.code.lineage.backlog import add_task; add_task('<title>', '<kind>', detail='<detail>', idea_id='<id>', priority='P1')"
   ```
3. **Re-prioritise anything stale** (`update_task(<task_id>, priority='P1')`).
4. **Verify the open backlog now matches your `## Next`:**
   ```bash
   python research/code/gates/idea_cli.py status
   ```
   If an open task has no home in `## Next` (or vice-versa), reconcile before continuing.

Do NOT write the handover until open `log_tasks` == your `## Next` / `## Blockers`.
This rule is mandatory for EVERY handover — new tasks and old.

## Step 3 — Confirm

```
Handover written: Memory/Session_Handover_<YYYY_MM_DD>_<TimeOfDay>.md
Next session picks up: [one sentence]
```
