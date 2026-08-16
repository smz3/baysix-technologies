# Working Agreement — full detail behind CLAUDE.md

`CLAUDE.md` is loaded into every session, so it holds the **rule**, not the **reasoning**.
This file holds the reasoning, the history, and the paths that only matter when you are
already working on that specific thing. Read the section you need; do not read it whole.

Extracted from CLAUDE.md 2026-08-15 (~80% trim). Nothing here was deleted — only moved.

---

## 1. Layout — the full map

Single repo · github.com/smz3/baysix-technologies.

**[platforms/](../../platforms/)** holds the three execution venues (`mt5/`, `ninjatrader/`,
`ibkr/`) — reorganized 2026-08-14, unified because they are all "place the order" code,
distinct from `research/` which is "decide what to order." MQL5 systems live in
`platforms/mt5/{Experts,Include,Scripts}/<system>_system/`; the live ones are **fob_system**
and **grw_system** (brc/orb/Sigma are parked or closed).

- **`docs/private/mandate.md`** (gitignored — this repo is public) — account size, target, and
  the rejected framings for the live GRW mandate. **Read it at session start before any GRW
  sizing or objective work.**
- **[research/db/research.db](../../research/db/research.db)** — Protocol 4.0 lean, WAL. There
  is **NO `is_runs` table** (collapsed into `step4_results.is_run` in migration 033). Ledger
  DDL has ONE home: [schema_ledger.py](../../research/code/infra/schema_ledger.py).
- **[research/db/execution.db](../../research/db/execution.db)** — live deployment ledger, 12
  tables, spec at [execution_schema.md](execution_schema.md). Rebuild in progress.
- **[research/code/](../../research/code/)** — 4 subpackages (`gates` · `lineage` · `io` ·
  `infra`); the flat `from research.code import X` still works via `__init__` re-exports.
- **[research/data/arctic/](../../research/data/arctic/)** — CANONICAL tick store (ArcticDB,
  lib `ticks`, symbol `XAUUSD`, 511M ticks 2016→2026, SORTED + seal 2024-05-02; daily =
  `XAUUSD_DAILY`). Read ONLY via [arctic_io.py](../../research/code/io/arctic_io.py). Sorting
  is what kills the look-ahead. `research/data/` also holds `fob_payload/` and
  `fob_entry_compare/` — moved under `research/` 2026-08-14, was root-level `data/`.
- **[research/models/_archive/](../../research/models/_archive/)** — orb/hmm/msm, all
  superseded. `brc/` is PARKED; live model work is `fob/` plus the GRW factory.
- **[research/config/](../../research/config/)** — `grw_fitness.json` (versioned objective; a
  version bump starts a new trial family).
- **[research/brokers/justmarkets.yaml](../../research/brokers/justmarkets.yaml)** — TCM-001
  cost model, re-derived at the live stake. Moved under `research/` 2026-08-14.
- **[research/b2b/](../../research/b2b/)** — earlier zone-detection engine (Sigma_System
  bridge/backtest/sigma_core), moved under `research/` 2026-08-14. This is the parked Sigma
  research line, **NOT** the `baysix-ventures` B2B AI-agent consulting business, which lives in
  its own separate repo — don't conflate the two.
- **[docs/](../)** — `plans/` and `specs/` are dated; `reference/` is evergreen.
- **[platforms/mt5/presets/](../../platforms/mt5/presets/)** — single source for `.set` presets;
  auto-mirrors to the JM terminal via junctions.
  **[platforms/mt5/tester/](../../platforms/mt5/tester/)** holds per-trade CSV artifacts. The JM
  terminal junctions (Experts/Include/Presets, 12 links, hash
  `E7DB6AF1FE93F292652A5D3B98342601`) were re-pointed at `platforms/mt5/` on 2026-08-14 — if MT5
  stops seeing repo edits, check the junctions still resolve, not the repo files.
- **[platforms/ibkr/](../../platforms/ibkr/)** — IBKR paper-account connectivity chain (TWS →
  API socket → `ib_async`), proven end-to-end on GLD (task 283, see
  [paper_trading_pipeline.md](../../platforms/ibkr/Documentation/paper_trading_pipeline.md)). No
  strategy logic wired yet.
- **[platforms/ninjatrader/](../../platforms/ninjatrader/)** — NinjaTrader 8 futures/prop-firm
  autonomous loop (GC/MGC gold + ETFs), migrated in from the standalone `~/Desktop/baysix-factory`
  repo 2026-08-14. Phase 0 only
  (`factory/{objective,provenance,spec,venue,prereg,adjudicate,ledger}.py`). **Never write
  futures rows into `research.db`** — separate namespace from the MT5 $20 mission, same
  discipline as the namespace rule. Research/plan doc:
  [2026-08-12_nt8_multicharts_autonomy.md](../plans/2026-08-12_nt8_multicharts_autonomy.md).

**Decoupled repos** (Desktop-level, own git remotes): `~/Desktop/sigma-quant/` (Cloudflare Pages,
deployed) · `~/Desktop/sigma-research/` (FastAPI + Qdrant/Groq) · `~/Desktop/sigma-linkedin/` ·
`~/Desktop/Alhazen-lab/` (github.com/smz3/Alhazen-lab — the research lab, extracted from this repo
2026-08-14; pre-G1, own README/charter, does not outrank the GRW mandate).

---

## 2. Why `git add -A` is banned (CLAUDE.md rule 1)

HARD, set 2026-08-12. Several agent harnesses (Claude Code, grokbot, hermes) share ONE working
copy on this PC, so `-A` stages another agent's half-finished edits into your commit, and two bare
`git commit`/`git push` calls race the shared index.

[agent_commit.py](../../.claude/hooks/git/agent_commit.py) takes an exclusive lock, stages only the
paths you name, and pathspec-limits the commit. Enforced by the pre-commit hook (install via
[install.sh](../../.claude/hooks/git/install.sh)), which blocks any commit made while another agent
holds the lock.

```
python .claude/hooks/git/agent_commit.py -m "msg" --agent claude-code <paths...>
```

Known limitation: its `git add -- <paths>` step fails on a path that no longer exists on disk. For a
deletion, stage it with `git rm` first, then pass the **parent directory** as the pathspec.

Standing authorization 2026-06-06: auto commit + push at natural completion points, real message,
push to master, no need to ask. `.gitignore` is the safety net (secrets/.env, data/parquet/csv/pkl,
logs, binaries all ignored — keep it airtight). Pause and ask only if something sensitive or large
looks like it will slip through, or before any history rewrite / force-push.

---

## 3. Namespace discipline — full version (CLAUDE.md rule 4a)

HARD, set 2026-07-09. **Never let a PARKED system into a LIVE decision.** Systems own disjoint
namespaces and column names collide across them by coincidence, not by meaning.

| System | Owns |
|---|---|
| **FOB** (live) | `fob_cycles` / `fob_zones` / `fob_events` / `fob_run_stats`, `research/data/fob_payload/`, `platforms/mt5/*/fob_system/`, `research/models/fob/` |
| **BRC** (parked) | `tester_zones`, `brc_system`, `research/models/brc/` |
| Shared spine only | `tester_runs` / `tester_trades` / `tester_run_summary` |

So: **scope every search to the active system's namespace** (`grep --include` / `path=` on the
folders above). A bare repo-wide grep for a column name like `confirm_time` or `mfe_r` hits BRC's
unrelated schema and drags a parked strategy into a live call. If a parked system's name shows up in
FOB reasoning, that is a **bug in the search**, not a finding: re-scope and re-run. Never widen scope
to "check if BRC does it too" unless Syafiq asks.

---

## 4. Token discipline — full version (CLAUDE.md rule 4b)

The whole transcript (including every tool result) is re-read each turn, so keep it lean. Targeted
reads (offset/limit, never whole files when a slice works); greps with `head_limit` + exclude-globs
up front; counts over dumps. No pre-tool narration on routine work; fold "what I did" into one
closing line — don't narrate mid-stream then re-summarize. Keep intent only before irreversible or
non-obvious moves.

---

## 5. Paper pipeline — full version (CLAUDE.md rule 10)

**Agents.** `quant-researcher` = permanently Sonnet, FIND-only — it only searches for and surfaces
papers (cheap fan-out). `paper-dissector` = permanently Opus, DISSECT-only — the "separate room"
that deep-reads a keeper's `.md` in its own context and returns the distilled dissection (token
firewall). Strategy/ideation and coding/backtests are done **inline by Claude**, never delegated.
Both agents have `model` pinned in frontmatter — no need to pass `model` per call, but still tell
Syafiq which ran ("find on Sonnet / dissect on Opus"). History: reversed the 2026-05-28
Sonnet-only-dissect on 2026-06-09; split DISSECT off QR into its own Opus agent 2026-06-16.

**Pipeline** (HARD, set 2026-06-16) — FIND → ACQUIRE → EXTRACT → DISSECT, dissect on the `.md`
NEVER the PDF:

1. **FIND** — `quant-researcher` (Sonnet).
2. **ACQUIRE** — [fetch_papers.py](../../research/code/io/fetch_papers.py) downloads the PDF to
   `research/papers/<family>/`.
3. **EXTRACT** — [extract_pdf.py](../../research/code/io/extract_pdf.py) (Docling) converts PDF →
   `<stem>.md` source text.
4. **DISSECT** — `paper-dissector` (Opus) reads the **`.md`** in-subagent and returns a distilled
   summary.

**BANNED:** native vision / Read-PDF-mode to dissect a PDF directly. It burns vision tokens AND
lands the whole paper in main context. Extraction is Docling-only (chosen for table fidelity over
pymupdf4llm; Nougat rejected — hallucinates numbers). Figures-as-images are a known gap → record as
a limitation, never vision-read the PDF to recover them.

**Artifacts.** Docling source `<stem>.md` = gitignored (derivable); orchestrator saves the returned
dissection as `<stem>.dissect.md` = git-tracked. DB write still via `log_dissect_result()`.
Dependency: `docling` (`pip install docling`).

**Pre-brief check.** Before briefing the agent, run
`python research/code/gates/idea_cli.py prebrief <idea_id>` (idea + prior agent calls + open tasks,
text-heavy cols auto-truncated). Never re-surface resolved decisions or repeat logged work.

---

## 6. Protocol 4.0 gates — full version (CLAUDE.md rule 6)

**4 gates: G1 Premise / G2 Edge+Survival / G3 Robustness / G4 Live.**

G1 must be `passed` in `step3_gates` before building the rule — check via
`python research/code/gates/idea_cli.py gatecheck <idea_id>` (hard PASS/BLOCK; sequencing
code-enforced by `pipeline.open_gate`).

Code walls (`pipeline._enforce_gate_walls`):
- **G1** needs `idea_kind` + `output_type` tagged AND ≥1 `step2_papers` row.
- **G2** needs ≥1 logged NET result (`cost_adjusted=1`).

**Driver:** `idea_cli.py next <idea_id>` computes the ONE next legal action from DB state — use it
instead of recalling the gate sequence. Snapshot: `idea_cli.py status`. Gate definitions:
[research_protocol.md](research_protocol.md).

_t-stat is reported, NEVER an auto-kill (4.0); OOS/WF persistence is the luck-test._

**Multi-hypothesis kill rule (HARD).** `kill_idea` needs **≥2 FALSIFIED hypotheses** (base/symmetric
framing + ≥1 directional/conditional variant); a single FALSIFIED is a reframe trigger, not a kill.
Code-enforced: `pipeline.kill_idea` blocks under 2 (`force=True` only for G1 non-novelty / no-spec,
with a reason).

---

## 7. DB write + query discipline — full version (CLAUDE.md rules 7–9)

**Writes via code layer only.** All `research.db` writes use `research/code/` functions
(`open_gate`, `pass_gate`, `kill_idea`, `log_result`, `log_agent_call`, `log_dissect_result`,
`log_human_decision`, `log_change`). Never raw `sqlite3` — timestamps/validation/constraints break.
Hook-enforced: [protocol_guard.py](../../.claude/hooks/scripts/protocol_guard.py) blocks raw sqlite3
writes and `.db` hand-edits at PreToolUse.

**Log immediately, before replying to Syafiq** — after every agent call or decision:
- QR find → `log_agent_call(gear='GENERATE')`; dissect → `log_dissect_result()` (atomic:
  `step2_papers` + `log_agent`).
- inline VALIDATE → `pipeline.log_result()`; human architecture/methodology decision →
  `log_human_decision()`.
- any strategy-defining change (ADOPTED / REJECTED / FALSIFIED / SUPERSEDED / VALIDATED / CREATED /
  PROPOSED) → `strategy_log.log_change()` with `component` / `from` / `to` / `verdict` /
  `rationale` / `result_id`. `log_strategy` is the lineage (birth → live config, read via
  `get_live_config(idea_id)`); `log_agent` is NOT a substitute.

**Query discipline.** Never `SELECT` text-heavy columns (`key_equations`, `empirical_findings`,
`context_fit`, `limitations`, `gate_answer`, `output_summary`) into main context; use targeted
column queries. QR agents query `research.db` inside the subagent, never through main context.

---

## 8. Startup — full version

1. The SessionStart hook prints the live **open backlog**, recently resolved tasks, and latest
   results straight from `research.db` (via
   [session_brief.py](../../.claude/hooks/scripts/session_brief.py)). Read it — it is the source of
   truth for what is open and what is already tested.
2. **Read EVERY handover from today, oldest → newest** (the brief lists them all, in order) in the
   **repo** [memory/](../../memory/) dir — not just the last one. Syafiq runs several Claude tabs in
   parallel, so one day is split across several handovers and each was written by a tab that saw
   only its own slice; the newest file is a slice, never the day. Earlier days live in
   [memory/_handover_archive/](../../memory/_handover_archive/) — read those only if a thread points
   back at one. Note there are two `memory/` dirs: this one holds session handovers; auto-memory
   (MEMORY.md + fact files) lives under
   `~/.claude/projects/c--Users-User-Desktop-baysix-technologies/memory/` and is injected
   automatically — never confuse the two.
3. Before proposing any work, reconcile against `open_backlog` (P1 first) + `log_agent` for the
   active idea, and check `strategy_log.get_live_config(idea_id)` for its current frozen config.
   Never re-surface a resolved task or re-run logged work.
4. Brief Syafiq: "Here's where we left off" → Claude agent decides the priority task.

**Priority rule: REMOVED 2026-08-16 (Syafiq's call).** There is no standing system-level priority
rank. Priority is decided per session from the backlog and whatever is actually in flight.

---

## 9. Smart Summary — full version (CLAUDE.md rule 12)

Answer format itself (plain English, bullets, ~150-word ceiling, unlock words) lives in the **global**
directives; this is only the project-specific piece.

- **`## 🧠 Smart Summary` is the ONE permitted section header.** 2–4 plain-English bullets, zero
  jargon (no R-multiples/t-stats/regime), last thing in the reply.
- **Required** on research findings + strategy decisions. **Skip** on infra/cleanup/config/chore
  unless asked — and skip whenever the reply above it is already plain (the default), which makes it
  a duplicate.
- Any file DELETED in the work gets named explicitly in the Smart Summary.
