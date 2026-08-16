# Baysix Technologies

Autonomous Research Agents for multiple trading platforms. From ideation - strategy building to testing

> Rules only below. The companion "why" doc was retired 2026-08-16 and has not been rebuilt yet —
> if a rule's reasoning is unclear, ask rather than guess.

## Rules

1. **`git add -A` is BANNED (HARD)** — agents share one working copy. Commit only via
   `python .claude/hooks/git/agent_commit.py -m "msg" --agent claude-code <paths...>`. Auto commit
   + push at completion points, no need to ask.
2. **No destructive actions** (`rm -rf`, `reset --hard`) without telling Syafiq first.
3. **Never print API keys** — `.env` only.
4. Only touch code you're meant to · no loose files · ask when unsure · don't overcomplicate.
5. **Namespace discipline (HARD)** — never let a PARKED system into a LIVE decision. Scope every
   search to the active system's folders and tables; a parked name surfacing in FOB reasoning is a
   bug in the search, not a finding.
6. **Token discipline** — targeted reads, greps with `head_limit`, counts over dumps, no mid-stream
   narration.
7. **Check current Anthropic docs** before improvising a Claude Code / API workflow.
9. **`idea_cli.py next <idea_id>`** gives the ONE next legal action — use it, don't recall the gate
   sequence. `prebrief` before briefing an agent. t-stat never auto-kills; a kill needs ≥2 falsified
   hypotheses.
10. **Writes via the code layer only** — never raw `sqlite3` on `research.db` (hook-enforced).
11. **Log immediately, before replying** — agent calls, results, decisions, and every
    strategy-defining change via `strategy_log.log_change()`.
12. **Never `SELECT` text-heavy columns** into main context.
13. **Papers: FIND (Sonnet) → fetch → Docling extract → DISSECT (Opus) on the `.md`.**
    Vision-reading a PDF is BANNED.
14. **Long-running commands (>10s)** → new PowerShell window via `Start-Process`, never
    `run_in_background`.


## Startup

1. Read the SessionStart brief — source of truth for what's open.
2. Read **every** handover from today in [memory/](memory/), oldest → newest; each tab writes one
   slice, the newest file is never the whole day.
3. Reconcile against the backlog + `get_live_config(idea_id)` before proposing work.
