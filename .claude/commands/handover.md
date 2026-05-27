---
name: handover
description: 'Write a session handover to Memory/ before ending any session.'
---

# /handover — Session Handover Writer

## Step 1 — Get timestamp

```bash
date +"%Y_%m_%d"
```

Time-of-day label (24h): 05–11 → Morning · 12–16 → Afternoon · 17–20 → Evening · 21–04 → Night

Filename: `Memory/Session_Handover_<YYYY_MM_DD>_<TimeOfDay>.md`

## Step 2 — Write the file

```markdown
# Handover — <Month Day, Year> <TimeOfDay>

## State
[2–3 sentences. What exists, what works, what's broken. Current file paths if relevant.]

## Next
1. [Exact first action — include file path or command]
2. [Second action]
3. [Third action if any]

## Blockers
[None — or specific blocker and what's needed to unblock]
```

Keep it under 20 lines total. The next session reads this cold in 10 seconds.

## Step 3 — Confirm

```
Handover written: Memory/Session_Handover_<YYYY_MM_DD>_<TimeOfDay>.md
Next session picks up: [one sentence]
```
