# Instruction-Surface Audit — 2026-08-04

Everything the agent reads as authority, audited against the disk and the DB.
Each item is `MEASURED` (a command run this session), `CITED` (read from the file, with
line), or `FIXED` (changed this session — the diff is in the same commit as this file).

**Surface audited** (`MEASURED`):

| Layer | Path | Size | In git? |
|---|---|---|---|
| Global directives | `C:\Users\User\.claude\CLAUDE.md` | 7 lines | **no** |
| Project directives | [CLAUDE.md](../../../CLAUDE.md) | 117 lines | yes |
| Memory store | `~\.claude\projects\c--Users-User-Desktop-baysix-technologies\memory\` | **111 files** + index | **no** |
| Subagents | [.claude/agents/](../../../.claude/agents/) | 2 files (413 lines) | yes |
| Slash command | [.claude/commands/handover.md](../../../.claude/commands/handover.md) | 138 lines | yes |
| Hooks | [.claude/hooks/scripts/](../../../.claude/hooks/scripts/) | 9 scripts | yes |
| Settings | [.claude/settings.json](../../../.claude/settings.json) · `settings.local.json` · `~\.claude\settings.json` | — | 2 of 3 |

**There is no `AGENTS.md` in this repo** (`MEASURED`). If you ever open this repo in a tool
that reads `AGENTS.md` (Cursor, Codex, Copilot Workspace), it gets **no instructions at
all** — `CLAUDE.md` is the only entry point that exists. See F3.

A verbatim copy of the global file is at
[global_CLAUDE.mirror.md](global_CLAUDE.mirror.md) — it is a **mirror**, labelled as one.

---

## A — Contradictions (a live decision could have gone wrong)

### A1 — The memory store told every session to build a scalper `[FIXED]`

- **File:** `memory/grw_20usd_scalp_mandate.md` (outside git)
- **Was:** *"HARD — GRW mission is grow $20 via scalping, hundreds of trades/day."*
- **Now contradicted by:** [grw_fitness.json](../../../research/config/grw_fitness.json)
  v2.0.0 — a barrier method resolving in ~21 trades (task 307, executed this session).
- **Why this is the worst one on the list:** memories are injected as background context at
  the start of **every** session and read as canonical. A fresh agent would have read
  "hundreds of trades a day, HARD" and the new objective in the same context window, with
  no way to tell which one was current.
- **Fixed:** rewritten to the barrier mandate, with the scalp framing marked SUPERSEDED
  rather than deleted, and the index row updated.

### A2 — Same file family: "Ranking metric is log-growth" `[FIXED]`

- **File:** `memory/grw001_autonomous_loop.md`
- **Fixed:** objective paragraph replaced with the v2.0.0 barrier statement; the parts that
  survive the change (drawdown/Sharpe reported-never-constrained, MQL5-native, no separate
  DB) left intact.

### A3 — A memory recommended an unreachable account `[FIXED]`

- **Was:** *"JM RAW is cheaper at 0.01 lot ($0.17 round-trip vs Pro's $0.20) — an
  unexploited lever."*
- **Contradicted by** [justmarkets.yaml:71](../../../brokers/justmarkets.yaml#L71):
  Raw `min_deposit_usd: 200` — **10x the entire stake**.
- The file contained both halves of the contradiction and still read as an action item.
- **Fixed:** struck through in place, with the reason.

### A4 — Code still defaulting to the parked objective `[FIXED]`

| File | Was | Now |
|---|---|---|
| [grw.py:389](../../../research/code/gates/grw.py#L389) | `promote(metric_key="oos_log_growth")` | `"oos_barrier_hit"` |
| [schema_ledger.py:307](../../../research/code/infra/schema_ledger.py#L307) | `is_fitness … (log-growth)` | barrier outcome, with the censored sentinel spelled out |
| [grw_types.mqh:262](../../../mt5/Include/grw_system/grw_types.mqh#L262) | *"the objective stays pure log-growth"* | barrier hit-rate (v2.0.0) |
| [grw_autonomous_workflow.md:354](../../../docs/reference/grw_autonomous_workflow.md#L354) | ✅ log-growth fitness | SUPERSEDED note added; history left standing |

### A5 — The project goal line still predates the deployment mandate `[OPEN — your call]`

- **File:** [CLAUDE.md:11](../../../CLAUDE.md#L11) — *"Goal: a research process that survives
  out-of-sample, scaled up over time."*
- Says nothing about the one-shot $20. Both are true and they are different objects (a
  research process vs a deployment), which is exactly why the file should state the
  relationship rather than one of them. Flagged in the prior corrections doc as B4 and
  **left for you to word** — it is your mission statement, not mine to draft.

---

## B — The repo map in CLAUDE.md has drifted (`MEASURED` against disk)

This is the file every session loads first, so a wrong map is a wrong first move.

| # | [CLAUDE.md](../../../CLAUDE.md) says | Disk says |
|---|---|---|
| B1 | `:21-22` Experts/Include = `Sigma_System/` + `orb_system/` | **5 each**: `Sigma_System brc_system fob_system grw_system orb_system`. The two LIVE systems (fob, grw) are absent; the only one named is ORB, a **closed** family |
| B2 | `:30-41` research/ lists 9 subfolders | `research/config/` missing — and that is where [grw_fitness.json](../../../research/config/grw_fitness.json), the objective of record, lives |
| B3 | `:20-28` mt5/ lists 4 subfolders | `mt5/presets/` and `mt5/tester/` missing (presets junction-deploy and the tester artifact CSVs) |
| B4 | `:19-56` top level | `ibkr/` (8 tracked files), `telegram_bridge/` (2), `tmp/` (0) are not in the map |
| B5 | `:52` docs/ = plans, specs, reference | also `_archive/`, `job-hunt/` |
| B6 | `:42-47` data/ = arctic only; *"Parquet RETIRED+deleted 2026-06-12"* | `data/parquet/` **still exists**, 3.5 MB, 4+ files (D1/H1 IS/OOS), untracked. Also `data/fob_payload/`, `data/fob_entry_compare/` unlisted. The tick-store rule is unaffected — the word "deleted" is just false |
| B7 | `:49` `.claude/agents/` = *"quant-researcher agent definition"* | **two** agents; `paper-dissector` has existed since 2026-06-16 and rule 5 of the same file describes it |
| B8 | — | `data/grw_runs/` does **not exist**, though [schema_ledger.py](../../../research/code/infra/schema_ledger.py) points `prereg_path` there. It will bite on the first pre-registration (task 293) |

None of these are wrong *rules*. They are a wrong *picture*, and the failure mode is an
agent grepping the wrong tree or believing a live system is not there.

---

## C — Enforcement claims: all four verified TRUE

Stated rules that are actually executable, checked rather than assumed:

- **`protocol_guard` blocks raw sqlite3 writes** (`MEASURED`, the hard way): it blocked a
  probe command *of mine* mid-audit. Rule 10 is real.
- **`claim_lint`** is wired at both `PreToolUse(Write|Edit)` and `Stop`
  ([settings.json:124-132, 240-248](../../../.claude/settings.json)) — matching task 291.
- **SessionStart chain** (`archive_handovers` → `prune_handover_archive` → `session_brief`)
  fired this session; its output is the brief at the top of this conversation.
- **`handover_lint`** runs clean when invoked directly (`MEASURED`, on this session's
  handover), and both the hook and its installer are tracked at
  [.claude/hooks/git/](../../../.claude/hooks/git/).
  - **BUT THE COMMIT GATE IS A NO-OP** (`MEASURED`, and it corrects what an earlier pass of
    this same document claimed). The hook lints *staged* `memory/*.md` — and
    [.gitignore:38-40](../../../.gitignore#L38) ignores `memory/` entirely
    ("kept private, untracked 2026-07-25"). `git ls-files memory/` returns **0**; `git add
    memory/` is refused. **No handover can ever be staged, so the hook exits 0 without
    linting anything, every time.**
  - The lint is real when run by hand (this session's `/handover` ran it and passed). The
    *enforcement* is not. Pick one: un-ignore `memory/`, or move the gate to the
    `/handover` command where it can actually fire, or stop citing pre-commit as teeth
    ([[handover_lint_gate]] and this file both did).

---

## D — Two bugs inside the newest guard `[BOTH FIXED]`

`claim_lint.py` shipped yesterday (task 291) and both bugs were found by it blocking
legitimate writes during this audit — including, on the second one, the write of this very
document.

### D1 — It linted files outside the repo

- It checked **every** `.md/.json/.yaml` Write/Edit, including the memory store. Memory
  files link each other by bare filename, relative to the memory folder, so every link
  read as `DEAD_PATH` and the write was **blocked** (`MEASURED` — it refused the
  `MEMORY.md` edit in this session).
- **Fixed** at [claim_lint.py:271](../../../.claude/hooks/scripts/claim_lint.py#L271):
  skip paths outside the repo. `DEAD_PATH` is only decidable for paths that are supposed to
  resolve under the repo.

### D2 — It resolved links against the repo root only

- Markdown links are relative to **their own file**. The linter tried repo-root and
  absolute candidates only, so a doc in a subfolder linking a **sibling** was reported dead
  — while `../../../CLAUDE.md` passed by *accident*, because stripping the `../` segments
  happened to collapse it onto the repo root.
- **Fixed** at [claim_lint.py:124](../../../.claude/hooks/scripts/claim_lint.py#L124):
  `lint()` takes the target file's own directory and resolves against it too.
- Verified both directions: a sibling link and a `../../../` link now pass; a genuinely
  nonexistent path still blocks.

---

## E — Memory store hygiene

- **Index integrity is perfect** (`MEASURED`): 111 files on disk, 111 rows in `MEMORY.md`,
  **zero** orphans and **zero** phantom rows.
- **8 dangling `[[links]]`** (`MEASURED`). Four are slug-format typos — hyphens where the
  file uses underscores: `feedback-brevity-delivery`, `feedback-discuss-before-build`,
  `lean-cli-runnability-status`, `per-period-sharpe-units-rule`. Four point at memories
  that do not exist: `brc_emitter_open_prices_model`, `build_docx_reusable_generator`,
  `job_hunt_tracker_db`, `job_hunt_workspace_split`.
- **Tombstones still loaded every session:** `active_work_state.md` (⚠️ STALE, ORB era),
  `project_ib001_hypothesis.md` (⚠️ SUPERSEDED), `orb001/002/003` (⚠️ FALSIFIED /
  ABANDONED-UNPROVEN). The warnings work — they cost tokens forever to keep working.
  `active_work_state` in particular is superseded by the handover + brief and can go.
- **The structural one, and it is bigger than the memory store.** 111 memory files **plus
  every handover in `memory/`** (`MEASURED`: 0 tracked, the directory is gitignored) are
  read as canonical every session and are **outside git, outside enforcement, outside
  review**. There is no history, no diff, no blame — for either. A1, A2 and A3 are three separate wrong instructions that survived there with
  nothing able to catch them. This was already filed as B8 in the prior corrections doc,
  about a single file; it is 111 files.
  - Options, cheapest first: (1) accept it and audit on a cadence; (2) mirror the store into
    the repo read-only so git can at least see drift; (3) move project-scoped memories into
    `docs/reference/` and keep only user/feedback ones outside. **Your call — (2) is what I
    would do.**

---

## F — Global vs project, and the missing entry point

- **F1 — Format rules collide, and the resolution is unwritten.** The global file bans
  section headers, comparison tables and multi-point taxonomies
  ([mirror](global_CLAUDE.mirror.md), line 5); project rule 13 mandates a `## 🧠 Smart
  Summary` section and every handover is headers-and-taxonomies end to end. In practice the
  split is **replies vs artifacts** and it has never caused a problem — but it is not
  written anywhere, so it is one re-read away from being applied to the wrong one. One
  clause in the global file fixes it permanently.
- **F2 — Project rule 15 is a pure pointer** to the global brevity rule. Harmless, but it
  means the brevity ceiling has two homes and one of them is invisible to git.
- **F3 — No `AGENTS.md`.** Nothing outside Claude Code can read your rules. If you want the
  repo to be legible to other agent tooling, the cheap version is a 3-line `AGENTS.md`
  pointing at `CLAUDE.md`; the expensive version is maintaining two files, which is how they
  diverge. Recommend the pointer, or nothing at all.

---

## G — Settings

- **G1 — Dead MCP config:** [settings.json:30-34](../../../.claude/settings.json) enables
  `context7`, `supabase`, `playwright`; `settings.local.json` disables the first two. Net
  effect is playwright only. Harmless, but it reads as three servers.
- **G2 — Redundant permissions:** `Bash(*)` is allowed, and so are four narrower `Bash(...)`
  entries that are strict subsets of it.
- **G3 — Possible guard hole, UNVERIFIED:** the project `ask` list gates
  `Bash(git reset --hard*)`, while `settings.local.json` **allows** the broader
  `Bash(git reset *)`. Whether local-allow overrides project-ask is precedence behaviour I
  have not tested — flagging, not asserting. It touches CLAUDE.md rule 2, so it is worth
  one deliberate test.
- **G4 — Global settings** (`~\.claude\settings.json`): `model: opus`, `effortLevel: xhigh`,
  `defaultMode: auto`. Consistent with how the sessions actually run.

---

## H — Backlog noise (unchanged, and now measurable)

`MEASURED`: **62 open tasks**, of which ~48 are FOB P1s, while FOB sits at `gate_1`. The
SessionStart brief prints all of them as live priority every session, which is why a fresh
agent cannot tell from the brief what is actually active. Bulk-park the FOB P1s or accept
that the brief's P1 section is decoration. (Same finding as the prior corrections doc,
section E — repeated here because nothing has changed and it is now the single biggest
signal-to-noise cost at session start.)

---

## Order I would fix the rest in

| Step | Item | Why |
|---|---|---|
| 1 | **A5** goal line | One sentence, and it is the first thing every session reads |
| 2 | **B1-B8** repo map | Mechanical; stops agents grepping dead trees and missing live ones |
| 3 | **E** memory store into git (option 2) | The place all three wrong instructions hid |
| 4 | **C** pre-commit fragility | Either commit a `.pre-commit-config.yaml` or stop citing the hook as enforcement |
| 5 | **G3** permission precedence test | One test; it touches a destructive-command guard |
| 6 | **E** dangling links + tombstones | Token hygiene |
| 7 | **F1/F3** | Cheap clarity, no urgency |

---

## Changelog

| Date | Entry |
|---|---|
| 2026-08-04 | Created alongside tasks 307/308. A1-A4 and D1/D2 fixed in the same commit; everything else left open on purpose. |
