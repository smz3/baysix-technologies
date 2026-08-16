---
name: handover
description: 'Write a session handover to memory/ before ending any session.'
---

# /handover — Session Handover Writer

**Order matters.** The backlog is reconciled BEFORE the file is written, not after.
`log_tasks` is what SessionStart actually reads — the prose mirrors it, never the
reverse. Doing it the other way round means writing a `## Next` block, then finding
out the backlog cap won't accept it, then rewriting the block. Sync first and the
`## Next` section is just a transcript of what you already filed.

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
base = f'memory/Session_Handover_{date_str}_{slot}'
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

## Step 2 — Sync log_tasks (BLOCKING, do this FIRST)

Every handover MUST leave `log_tasks` reflecting reality. The SessionStart brief reads
`log_tasks`, NOT this prose — an un-synced task rots silently (the seam that cost 4
sessions: [[handover_nextsteps_must_be_tasks]]).

Writes go through the code layer ONLY ([research/code/lineage/backlog.py](research/code/lineage/backlog.py) — never raw sqlite3, rule 10).

**2a. Pre-flight — how many slots do you actually have?**

The open backlog is capped at 6 (rule 15, `MAX_OPEN`). `add_task` raises
`BacklogFullError` at the cap, so find out BEFORE you plan the `## Next` block:

```bash
python -c "
from research.code.lineage.backlog import get_backlog, MAX_OPEN
rows=[r for r in get_backlog() if r['status'] in ('open','in_progress')]
print(f'OPEN {len(rows)}/{MAX_OPEN} — slots free: {MAX_OPEN-len(rows)}')
for r in rows: print(' ', r['task_id'], r['priority'], r['stream'], r['title'][:60])
"
```

**2b. Resolve what you finished — this is what frees slots.** For each task
completed or dropped this session:

```bash
python -c "from research.code.lineage.backlog import resolve_task; resolve_task(<task_id>, '<one-line resolution>', status='done')"   # or status='dropped'
```

**2c. Open a task for every `## Next` line you intend to write.**

```bash
python -c "from research.code.lineage.backlog import add_task; add_task('<title>', '<kind>', detail='<detail>', priority='P1', stream='<stream>')"
```

- `stream` is **REQUIRED** (rule 17) — one of `MT5` · `NinjaTrader` · `IBKR` · `Research` · `Ops`.
  Omitting it raises `ValueError`, it does not default.
- `kind` — one of `variant` · `sizing` · `filter` · `port` · `infra` · `data` · `cleanup`.
- `priority` — `P0` · `P1` · `P2`.
- `idea_id` is **optional** and means strictly "serves a live falsifiable idea". Most
  tooling/ops work has none — leave it off rather than inventing one.

**If you hit `BacklogFullError`:** the cap is Syafiq's deliberate call, not an obstacle
to route around. Do NOT raise `MAX_OPEN` and do NOT quietly drop the item. Resolve a
finished task to free the slot; if nothing is genuinely finished, stop and ask Syafiq
which open task to park. The overflow item goes in `## Live-Threads`, not `## Next`.

**2d. Re-prioritise anything stale:** `update_task(<task_id>, priority='P1')`.

**2e. Verify** the open backlog is now exactly what your `## Next` will say — re-run the
2a pre-flight. Do not proceed until open `log_tasks` == your intended `## Next` / `## Blockers`.

## Step 3 — Write the file

The file has **two parts**, each with its own job:

- **HEAD** (`## State` / `## Next` / `## Blockers`) = the 10-second cold read — *what
  do I do now*. This mirrors the tasks you just filed in Step 2. **Keep the head under
  ~25 lines, bullets only.**
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
   to be a `## Next` task yet — the loose ends that rot if not named.
   Anything that would not fit under the backlog cap lands HERE.]
- [- None this session.  ← if nothing is mid-flight]
```

**Why two parts:** the head is the actionable summary (also in `log_tasks`); the
narrative is the only home for *why / dead-ends / loose threads*. Squeezing both under
one tight cap is what made narrative rot — so the cap is on the HEAD only.

## Step 4 — Lint (BLOCKING)

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

## Step 5 — Confirm

```
Handover written: memory/Session_Handover_<YYYY_MM_DD>_<TimeOfDay>.md
Next session picks up: [one sentence]
```
