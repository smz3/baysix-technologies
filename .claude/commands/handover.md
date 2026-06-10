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
