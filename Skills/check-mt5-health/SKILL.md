---
name: 'check-mt5-health'
description: 'Sigma brain skill: check-mt5-health'
---

# Skill: check-mt5-health

Check the health and status of the sigma-mt5 Expert Advisor system.

## Usage
```
/check-mt5-health
```

## Steps

1. Read the current EA version and active development state:
   - `C:\Users\User\Desktop\sigma-mt5\Documentation\B2B_DETECTION_SYSTEM.md`
   - Check for any open bug documentation in `Documentation\B2B_CLUSTER_FIX_PLAN.md`

2. Check for any compiled EA binary:
   - Look for `.ex5` files in `C:\Users\User\Desktop\sigma-mt5\`
   - Note the version and last modified date

3. Review the system heartbeat (if available):
   - `C:\Users\User\Desktop\sigma-brain\Audit\system_heartbeats.log`

4. Scan the latest research archive for active development notes:
   - `C:\Users\User\Desktop\sigma-mt5\Include\Sigma_System\V5.0\Data\`

5. Return a health report:
   ```markdown
   ## MT5 EA Health Report

   **EA Version**: V[X.X]
   **Compiled Binary**: Found / Not Found — last modified [date]
   **Active Development**: Yes / No
   **Open Issues**: [list from bug docs, or "None"]
   **Last Research Entry**: [file name and date]
   **System Heartbeat**: [from log or "No heartbeat data"]
   **Status**: Healthy / Needs Attention / Unknown
   **Recommended Action**: [if any]
   ```

## Notes
- Read-only — never modify MQL5 source files as part of this health check
- If open issues exist in B2B_CLUSTER_FIX_PLAN.md, summarize the proposed solutions
- Alert the user if no compiled binary exists (EA cannot be running)
