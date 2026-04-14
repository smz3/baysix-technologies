---
name: handover
description: 'Write a session handover to Memory/ and POST to the always-on memory agent if running. Run this before ending any session.'
---

# /handover — Session Handover Writer

You are writing a session handover document so the next Claude session starts with full context and zero re-explanation.

## Step 1 — Get Date/Time for Filename

Run this to get the timestamp:

```bash
date +"%Y_%m_%d"
```

Determine the time-of-day label based on current hour (24h):
- 05–11 → `Morning`
- 12–16 → `Afternoon`
- 17–20 → `Evening`
- 21–04 → `Night`

The filename will be: `Memory/Session_Handover_<YYYY_MM_DD>_<TimeOfDay>.md`

## Step 2 — Write the Handover File

Write `Memory/Session_Handover_<YYYY_MM_DD>_<TimeOfDay>.md` using this structure:

```markdown
# Session Handover — <Month Day, Year> (<TimeOfDay> — <1-line topic summary>)

## What Was Accomplished This Session

### 1. <Major thing done>
[Detail — what was built, decided, or changed. Include file paths, metrics, key outcomes.]

### 2. <Next major thing> (if any)
[Detail]

---

## What Is NOT Done / Still Open

- [Item] — [why it's open or blocked]

---

## Running Processes

| Task | Status | Notes |
|------|--------|-------|
| [process] | Running / Stopped | [notes] |

(Write "None" if nothing is running)

---

## Priority for Next Session

1. [Most important next action — be specific, include file paths]
2. [Second action]
3. [Third action]

---

## Key Decisions Made

- [Decision]: [rationale]

---

## Blockers

- [Blocker]: [what's needed to unblock]

(Write "None" if no blockers)
```

Be specific. Include file paths, metrics, command outputs, and line numbers where relevant. This document is the ONLY thing the next session reads — make it self-contained.

## Step 3 — POST to Always-On Memory Agent (if running)

After writing the file, try to POST the handover summary to the local memory agent:

```bash
curl -s -X POST http://localhost:8888/ingest \
  -H "Content-Type: application/json" \
  -d "{\"text\": \"<one-paragraph plain-text summary of the session>\", \"source\": \"session-handover\"}" \
  --connect-timeout 2 2>&1
```

- If the curl **succeeds** (returns JSON with `"status": "ingested"`): confirm "Memory agent updated ✓"
- If the curl **fails** (connection refused / timeout): confirm "Memory agent not running — markdown only ✓"

Do NOT error or retry. The markdown file is always the primary source of truth.

## Step 4 — Confirm

Report back:

```
## Handover Complete

**File written**: Memory/Session_Handover_<YYYY_MM_DD>_<TimeOfDay>.md
**Memory agent**: Updated ✓  /  Not running — markdown only ✓
**Next session starts with**: [2-sentence summary of what they'll pick up]
```
