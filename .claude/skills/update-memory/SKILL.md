---
name: update-memory
description: >
  Synthesize this session's work into the structured Memory/ state files (strategy_state,
  risk_parameters, research_queue, alpha_insights) so the next session starts smart. Run at the
  end of a productive session, or after a backtest/research result lands. Distinct from /handover
  (which writes the narrative session log) — this updates the durable state the SessionStart hook
  reads. Skip if nothing significant changed.
---

# Skill: update-memory

Update the structured `Memory/` state files directly (no agent spawn — this skill does the work).
These are the files the SessionStart hook surfaces at startup.

## Usage
```
/update-memory [optional: what to capture]
```

## Procedure
1. **Collect** what changed this session: decisions, backtest/research results, new edges, new tasks, risk-limit changes.
2. **Classify** each item → which file it belongs in (below).
3. **Check** for contradiction with an existing entry; mark superseded ones `[SUPERSEDED: date]` rather than silently overwriting.
4. **Write** concisely, date-stamped. Edit/append — never delete a memory file.
5. **Read back** and confirm.

## Target files (in `Memory/`)
- `strategy_state.md` — active strategy version + hypothesis under test; latest backtest (test ID, period, Sharpe/Calmar/DD, status). *(Backtest results go here — there is no separate performance_log.)*
- `risk_parameters.md` — Deployment Profile(s) + limits, if discussed or changed.
- `research_queue.md` — new tasks/ideas identified, with priority.
- `alpha_insights.md` — a new edge or pattern, with the evidence and status (Hypothesis / Validated / Invalidated).

## Output
```markdown
## Memory Updated
**Session summary**: [1–2 sentences]
**Files updated**: [file: what changed]
**Conflicts resolved**: [contradictions found + how]
**Next session will know**: [key facts now persisted]
```

## Notes
- Run at the end of a productive session. If nothing significant happened, skip — don't write empty updates.
- For the global cross-project auto-memory (`MEMORY.md` + `memory/`), that's managed separately per the user-memory protocol — this skill is only the project `Memory/` state files.
