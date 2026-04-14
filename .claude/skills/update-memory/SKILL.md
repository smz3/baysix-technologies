---
name: 'update-memory'
description: 'Sigma brain skill: update-memory'
---

# Skill: update-memory

Trigger the memory-curator agent to synthesize recent work and update the Memory/ files.

## Usage
```
/update-memory [optional: what to capture]
```

## Steps

1. Collect context to synthesize:
   - What was done in this session (from conversation history)
   - Any agent outputs that contain new findings
   - Any backtest results or research conclusions

2. Spawn the memory-curator agent with:
   - A summary of what happened this session
   - Specific findings to be captured
   - Which memory files are likely affected

3. The memory-curator will update:
   - `Memory/strategy_state.md` — if strategy or backtest changed
   - `Memory/risk_parameters.md` — if risk limits were discussed or changed
   - `Memory/alpha_insights.md` — if a new edge or pattern was discovered
   - `Memory/research_queue.md` — if new tasks were identified
   - `Memory/performance_log.md` — if a backtest result was produced

4. Read back the updated files and confirm changes are accurate

5. Return a confirmation:
   ```markdown
   ## Memory Updated

   **Session Summary**: [1-2 sentence recap]
   **Files Updated**:
     - strategy_state.md: [what changed]
     - alpha_insights.md: [what was added]
     - research_queue.md: [new items]
   **Next Session Will Know**: [key facts now persisted]
   ```

## Notes
- Always run this at the end of a productive session
- If no significant work happened, skip (don't write empty updates)
- The goal is: the next session should need zero re-explanation of today's work
