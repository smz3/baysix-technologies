# Baysix Technologies

Syafiq — 7yr Quant Trader → Quant Researcher. Autonomous research + live systematic strategies on
MT5, NinjaTrader, IBKR. The process must survive out-of-sample; that is the constraint.

> Rules only below. Reasoning, history, full layout map:
> **[working_agreement.md](docs/reference/working_agreement.md)** — read a section when the *why*
> matters, never by default.

## Layout gotchas (`ls` shows the rest)

- **[platforms/](platforms/)** = place the order · **[research/](research/)** = decide what to
  order. Live MQL5: `fob_system`, `grw_system`.
- **`docs/private/mandate.md`** (gitignored) — read before ANY GRW sizing or objective work.
- **[research/data/arctic/](research/data/arctic/)** — canonical XAUUSD ticks, read ONLY via
  [arctic_io.py](research/code/io/arctic_io.py) (its sorting is what kills the look-ahead).
- **[research.db](research/db/research.db)** — Protocol 4.0 ledger, untracked/local, back it up.
- **[platforms/mt5/presets/](platforms/mt5/presets/)** mirrors to the JM terminal via junctions —
  MT5 not seeing your edits = check the junctions, not the repo. Futures rows never go in
  `research.db`; NinjaTrader owns its own.
- Parked: [models/_archive/](research/models/_archive/), [models/brc/](research/models/brc/),
  [research/b2b/](research/b2b/) (Sigma line, NOT the `baysix-ventures` repo).

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
8. Read [RESEARCH_CODE_PROTOCOL.md](research/RESEARCH_CODE_PROTOCOL.md) before touching
   `research/models/` or `research/code/`.
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
15. **`## 🧠 Smart Summary`** is the one permitted header: 2–4 plain bullets, zero jargon, last in
    the reply. Required on research findings + strategy decisions; skip on chores and when the reply
    is already plain. Name any DELETED file in it.
16. **Never caveat mid-price (HARD)** — "net" once on a G2/tester result, no spread/cost
    disclaimers during logic work.

## Startup

1. Read the SessionStart brief — source of truth for what's open.
2. Read **every** handover from today in [memory/](memory/), oldest → newest; each tab writes one
   slice, the newest file is never the whole day.
3. Reconcile against the backlog + `get_live_config(idea_id)` before proposing work.
