# Baysix Technologies

<!-- Quant co-founder. Validate edges, protect capital, compound from a conservative base. -->

---

## You're Talking To

Syafiq — 7yr Quant Trader → Quant Researcher (deployable).
Building an Autonomous Research Agent for systematic strategy discovery, trading XAUUSD live.
Objective is a **barrier** one — P(target before floor) on a single fixed stake, not log-growth.
The research process must survive out-of-sample; that is the constraint, not the mission.

Account size, target, and the rejected framings live in `docs/private/mandate.md` (gitignored —
this file is public). **Read it at session start before any GRW sizing or objective work.**


---

## Where Things Live (gotchas only — `ls` shows the rest)

Single repo · github.com/smz3/baysix-technologies. MQL5 systems live in `mt5/{Experts,Include,Scripts}/<system>_system/`; the live ones are **fob_system** and **grw_system** (brc/orb/Sigma are parked or closed).

- **[research/db/research.db](research/db/research.db)** — Protocol 4.0 lean, WAL. There is **NO `is_runs` table** (collapsed into `step4_results.is_run` in migration 033). Ledger DDL has ONE home: [schema_ledger.py](research/code/infra/schema_ledger.py).
- **[research/db/execution.db](research/db/execution.db)** — live deployment ledger, 12 tables, spec at [execution_schema.md](docs/reference/execution_schema.md). Rebuild in progress.
- **[research/code/](research/code/)** — 4 subpackages (`gates` · `lineage` · `io` · `infra`); the flat `from research.code import X` still works via `__init__` re-exports.
- **[data/arctic/](data/arctic/)** — CANONICAL tick store (ArcticDB, lib `ticks`, symbol `XAUUSD`, 511M ticks 2016→2026, SORTED + seal 2024-05-02; daily = `XAUUSD_DAILY`). Read ONLY via [arctic_io.py](research/code/io/arctic_io.py). Parquet RETIRED + deleted 2026-06-12 (task 51) — sorting is what kills the look-ahead.
- **[research/models/_archive/](research/models/_archive/)** — orb/hmm/msm, all superseded. `brc/` is PARKED; live model work is `fob/` plus the GRW factory.
- **[research/config/](research/config/)** — `grw_fitness.json` (versioned objective; a version bump starts a new trial family).
- **[brokers/justmarkets.yaml](brokers/justmarkets.yaml)** — TCM-001 cost model, re-derived at the live stake.
- **[docs/](docs/)** — `plans/` and `specs/` are dated; `reference/` is evergreen.
- **[mt5/presets/](mt5/presets/)** — single source for `.set` presets; auto-mirrors to the JM terminal via junctions. **[mt5/tester/](mt5/tester/)** holds per-trade CSV artifacts.

Decoupled repos (Desktop-level, own git remotes):
`~/Desktop/sigma-quant/` (Cloudflare Pages, deployed) · `~/Desktop/sigma-research/` (FastAPI + Qdrant/Groq) · `~/Desktop/sigma-linkedin/`

---

## Rules

**Safety & Git**
1. **Auto commit + push** at natural completion points — real message, push to master, no need to ask (standing authorization 2026-06-06). **`git add -A` is BANNED (HARD, set 2026-08-12):** several agent harnesses (Claude Code, grokbot, hermes) share ONE working copy on this PC, so `-A` stages another agent's half-finished edits into your commit and two bare `git commit`/`git push` calls race the shared index. Commit through **[agent_commit.py](.claude/hooks/git/agent_commit.py)** instead — it takes an exclusive lock, stages only the paths you name, and pathspec-limits the commit: `python .claude/hooks/git/agent_commit.py -m "msg" --agent claude-code <paths...>`. Enforced by the pre-commit hook (install via [install.sh](.claude/hooks/git/install.sh)), which blocks any commit made while another agent holds the lock. Guardrails: `.gitignore` is the safety net (secrets/.env, data/parquet/csv/pkl, logs, binaries all ignored — keep it airtight); pause and ask only if something sensitive/large looks like it'll slip through, or before any history rewrite / force-push.
2. **No destructive actions** (`rm -rf`, `reset --hard`, etc.) without telling Syafiq first.
3. **Never print API keys** — read from `.env` only.

**Working style**
4. Only touch code you're meant to · no loose files (everything lives in a folder) · ask when unsure, don't assume · don't overcomplicate. (Brevity + markdown file-links live in the global directives.)
4a. **Namespace discipline — never let a PARKED system into a LIVE decision (HARD, set 2026-07-09).** Systems own disjoint namespaces and column names collide across them by coincidence, not by meaning. **FOB** = `fob_*` tables (`fob_cycles`/`fob_zones`/`fob_events`/`fob_run_stats`), `data/fob_payload/`, `mt5/*/fob_system/`, `research/models/fob/`. **BRC (parked)** = `tester_zones`, `brc_system`, `research/models/brc/`. Shared spine only: `tester_runs` / `tester_trades` / `tester_run_summary`. So: **scope every search to the active system's namespace** (`grep --include` / `path=` on the folders above) — a bare repo-wide grep for a column name like `confirm_time` or `mfe_r` hits BRC's unrelated schema and drags a parked strategy into a live call. If a parked system's name shows up in FOB reasoning, that is a **bug in the search**, not a finding: re-scope and re-run. Never widen scope to "check if BRC does it too" unless Syafiq asks.
4b. **Token discipline** — the whole transcript (incl. every tool result) is re-read each turn, so keep it lean. Targeted reads (offset/limit, never whole files when a slice works); greps with `head_limit` + exclude-globs up front; counts over dumps. No pre-tool narration on routine work; fold "what I did" into one closing line — don't narrate mid-stream then re-summarize. Keep intent only before irreversible/non-obvious moves.
4c. **Check Anthropic docs when applicable** — for Claude Code features/config (hooks, subagents, slash commands, settings, SDK) or Claude API usage, check current Anthropic docs (via the `claude-code-guide` agent or `WebFetch`/`WebSearch` on docs.claude.com / docs.anthropic.com) before improvising a workflow, so setup follows current best practice instead of stale assumptions.

**Paper agents — FIND vs DISSECT are now two separate agents (updated 2026-06-16)**
5. **`quant-researcher` = permanently Sonnet, FIND-only.** It ONLY searches for + surfaces papers (cheap fan-out). **`paper-dissector` = permanently Opus, DISSECT-only** — the "separate room" that deep-reads a keeper's `.md` in its own context and returns the distilled dissection (token firewall). Strategy/ideation and coding/backtests are done **inline by Claude**, never delegated. Both agents have `model` pinned in their frontmatter — no need to pass `model` per call, but still tell Syafiq which ran ("find on Sonnet / dissect on Opus"). (Reversed 2026-05-28 Sonnet-only-dissect on 2026-06-09; split DISSECT off QR into its own Opus agent 2026-06-16.)
5b. **Paper pipeline (HARD, set 2026-06-16) — FIND → ACQUIRE → EXTRACT → DISSECT, dissect on the `.md` NEVER the PDF:**
    - **FIND** (`quant-researcher`, Sonnet) → **ACQUIRE** [fetch_papers.py](research/code/io/fetch_papers.py) downloads PDF to `research/papers/<family>/` → **EXTRACT** [extract_pdf.py](research/code/io/extract_pdf.py) (Docling) converts PDF → `<stem>.md` source text → **DISSECT** (`paper-dissector`, Opus) reads the **`.md`** in-subagent and returns a distilled summary.
    - **BANNED:** native vision / Read-PDF-mode to dissect a PDF directly. It burns vision tokens AND lands the whole paper in main context. Extraction is Docling-only (chosen for table fidelity over pymupdf4llm; Nougat rejected — hallucinates numbers). Figures-as-images are a known gap → record as a limitation, never vision-read the PDF to recover them.
    - **Artifacts:** Docling source `<stem>.md` = gitignored (derivable); orchestrator saves the returned dissection as `<stem>.dissect.md` = git-tracked. DB write still via `log_dissect_result()` (rule 10). Dep: `docling` (`pip install docling`).
6. **Pre-brief check** — before briefing the agent, run `python research/code/gates/idea_cli.py prebrief <idea_id>` (idea + prior agent calls + open tasks, text-heavy cols auto-truncated). Never re-surface resolved decisions or repeat logged work.

**Research DB**
7. Before touching anything in `research/models/` or `research/code/`, read [research/RESEARCH_CODE_PROTOCOL.md](research/RESEARCH_CODE_PROTOCOL.md) first.
8. **Protocol 4.0 — 4 gates (G1 Premise / G2 Edge+Survival / G3 Robustness / G4 Live).** G1 must be `passed` in `step3_gates` before building the rule — check via `python research/code/gates/idea_cli.py gatecheck <idea_id>` (hard PASS/BLOCK; sequencing code-enforced by `pipeline.open_gate`). Code walls (`pipeline._enforce_gate_walls`): **G1** needs `idea_kind`+`output_type` tagged AND ≥1 `step2_papers` row; **G2** needs ≥1 logged NET result (`cost_adjusted=1`). **Driver: `idea_cli.py next <idea_id>`** computes the ONE next legal action from DB state — use it instead of recalling the gate sequence. Snapshot: `idea_cli.py status`. Gate defs: [docs/reference/research_protocol.md](docs/reference/research_protocol.md). _t-stat is reported, NEVER an auto-kill (4.0); OOS/WF persistence is the luck-test._
8b. **Multi-hypothesis kill rule (HARD)** — `kill_idea` needs **≥2 FALSIFIED hypotheses** (base/symmetric framing + ≥1 directional/conditional variant); a single FALSIFIED is a reframe trigger, not a kill. Code-enforced: `pipeline.kill_idea` blocks under 2 (`force=True` only for G1 non-novelty/no-spec, with reason).
9. **Query discipline** — never `SELECT` text-heavy columns (`key_equations`, `empirical_findings`, `context_fit`, `limitations`, `gate_answer`, `output_summary`) into main context; use targeted column queries. QR agents query `research.db` inside the subagent, never through main context.
10. **Writes via code layer only** — all `research.db` writes use `research/code/` functions (`open_gate`, `pass_gate`, `kill_idea`, `log_result`, `log_agent_call`, `log_dissect_result`, `log_human_decision`, `log_change`). Never raw `sqlite3` (timestamps/validation/constraints break). Hook-enforced: [.claude/hooks/scripts/protocol_guard.py](.claude/hooks/scripts/protocol_guard.py) blocks raw sqlite3 writes + `.db` hand-edits at PreToolUse.
11. **Log immediately, before replying to Syafiq** — after every agent call or decision:
    - QR find → `log_agent_call(gear='GENERATE')`; dissect → `log_dissect_result()` (atomic: step2_papers + log_agent)
    - inline VALIDATE → `pipeline.log_result()`; human architecture/methodology decision → `log_human_decision()`
    - any strategy-defining change (ADOPTED / REJECTED / FALSIFIED / SUPERSEDED / VALIDATED / CREATED / PROPOSED) → `strategy_log.log_change()` with `component`/`from`/`to`/`verdict`/`rationale`/`result_id`. `log_strategy` is the lineage (birth→live config, read via `get_live_config(idea_id)`); `log_agent` is NOT a substitute.

**Execution**
12. **Long-running commands (>10s)** — model fits, data loads, migrations — launch in a new PowerShell window via `Start-Process`. Never `run_in_background`; Syafiq needs live output.

**Communication**
13. **Smart Summary — the project-only piece.** Answer format itself (plain English, bullets, ~150-word ceiling, unlock words) lives in the global directives; do not restate it here.
    - **`## 🧠 Smart Summary` is the ONE permitted section header.** 2–4 plain-English bullets, zero jargon (no R-multiples/t-stats/regime), last thing in the reply.
    - **Required** on research findings + strategy decisions. **Skip** on infra/cleanup/config/chore unless asked — and skip whenever the reply above it is already plain (the default), which makes it a duplicate.
    - Any file DELETED in the work gets named explicitly in the Smart Summary.
14. **Never caveat mid-price (HARD).** A number is cost-free unless it is a G2/tester result, where you say "net" once. No disclaimers about spread/cost during logic work — ever.

---

## Startup

1. The SessionStart hook prints the live **open backlog**, recently resolved tasks, and latest results straight from `research.db` (via [.claude/hooks/scripts/session_brief.py](.claude/hooks/scripts/session_brief.py)). Read it — it is the source of truth for what is open and what is already tested.
2. **Read EVERY handover from today, oldest → newest** (the brief lists them all, in order) in the **repo** [memory/](memory/) dir — not just the last one. Syafiq runs several Claude tabs in parallel, so one day is split across several handovers and each was written by a tab that saw only its own slice; the newest file is a slice, never the day. Earlier days live in [memory/_handover_archive/](memory/_handover_archive/) — read those only if a thread points back at one. Note there are two `memory/` dirs: this one holds session handovers; auto-memory (MEMORY.md + fact files) lives under `~/.claude/projects/c--Users-User-Desktop-baysix-technologies/memory/` and is injected automatically — never confuse the two.
3. Before proposing any work, reconcile against `open_backlog` (P1 first) + `log_agent` for the active idea (rule 6), and check `strategy_log.get_live_config(idea_id)` for its current frozen config. Never re-surface a resolved task or re-run logged work.
4. Brief Syafiq: "Here's where we left off" → Claude agent decides the priority task.

**Priority rule (set 2026-08-11): GRW outranks FOB.** The barrier run is the mission, so an open GRW task beats an open FOB task of the same P-level — always. FOB keeps running as research (it is 38 tasks deep and feeds GRW its strategy), but it never preempts a live GRW task. Backlog volume is NOT a priority signal; the mandate is.
