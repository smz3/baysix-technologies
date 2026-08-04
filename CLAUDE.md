# Baysix Technologies

<!-- Quant co-founder. Validate edges, protect capital, compound from a conservative base. -->

---

## You're Talking To

Syafiq — 7yr Quant Trader → Quant Researcher (deployable).
Building an Autonomous Research Agent for systematic strategy discovery, trading XAUUSD live.
Goal: a research process that survives out-of-sample, scaled up over time.


---

## Repo Layout

```
baysix-technologies/          ← single repo · github.com/smz3/baysix-technologies
├── mt5/                      ← MQL5 EAs (XAUUSD live · Just Markets)
│   ├── Experts/              ← Sigma_System/ (Sigma_V5.0 B2B EA + .ex5) · orb_system/ (baysix_orb_NNN EAs)
│   ├── Include/              ← Sigma_System/ (.mqh: B2B detect, trade, risk, UI) · orb_system/ (ORB modules)
│   ├── Scripts/orb_system/   ← ORB helper scripts
│   ├── Documentation/        ← Sigma EA architecture + SAMTC · orb_system/ (per-EA docs)
│   └── strategy_tester_xlsx/ ← MT5 Strategy Tester report exports
├── b2b/
│   ├── code/                 ← B2B Python engine (zone detection, trade logic)
│   └── docs/                 ← B2B knowledge base (overview, zone lifecycle, russian doll, etc.)
├── brokers/                  ← venue specs: justmarkets.yaml (TCM-001 cost model) + .md per broker
├── research/
│   ├── db/                   ← all SQLite databases (2-DB design: workstation + VPS)
│   │   ├── research.db       ← Protocol 4.0 lean (WAL): step1_ideas · step2_papers · step3_gates (G1-G4) · step4_results (+is_run/what_changed — there is NO is_runs table, collapsed in migration 033) · spine: tester_runs/tester_trades/tester_zones/tester_run_summary · fob_* payload · grw_batches/grw_passes (GRW-001 factory) · logs: log_agent · log_tasks · log_strategy. Ledger DDL has ONE home: research/code/infra/schema_ledger.py
│   │   └── execution.db      ← live deployment ledger (downstream twin · 12 tables · spec: docs/reference/execution_schema.md · rebuild in progress)
│   ├── code/                 ← shared DB layer, 4 subpackages (flat `from research.code import X` preserved via __init__ re-exports): gates/ (pipeline·protocol·idea_cli) · lineage/ (strategy_log·agent_log·backlog) · io/ (arctic_io·tester·ingest_*·fetch/extract/backfill) · infra/ (db_init·run_and_log·run_tracked·handover_lint·execution)
│   ├── models/               ← one folder per idea/model (brc/ = active BRC-001 · struct/ = STRUCT-001 primitive · cusum/ · _archive/ = orb/hmm/msm, superseded)
│   ├── migrations/           ← DB migration scripts (010 create_research_db · 011 migrate_data)
│   ├── dashboard/            ← Streamlit research dashboard (app.py · localhost:8501)
│   ├── outputs/              ← model plot outputs (Plotly HTML + Seaborn PNG · gitignored)
│   ├── papers/               ← QR-agent paper dissection notes
│   ├── tests/                ← pytest suites (test_backlog.py · …)
│   └── RESEARCH_CODE_PROTOCOL.md ← code rules for research/models/ and research/code/
├── data/
│   └── arctic/               ← CANONICAL tick store: ArcticDB (lib 'ticks', symbol 'XAUUSD',
│                                 511M ticks 2016→2026, SORTED + seal 2024-05-02). Daily =
│                                 symbol 'XAUUSD_DAILY'. Read ONLY via research/code/arctic_io.py
│                                 (tick_months/read_tick_month/is_ticks/oos_ticks/daily_bars).
│                                 Parquet RETIRED+deleted 2026-06-12 (task 51) — sort kills look-ahead.
├── .claude/
│   ├── agents/               ← quant-researcher agent definition
│   ├── hooks/                ← session hooks + audio notifications
│   └── commands/             ← /handover
├── docs/                     ← plans/ (dated build plans) · specs/ (dated design docs) · reference/ (evergreen schemas + protocols)
└── memory/                   ← session handovers · _handover_archive/ for older ones

Decoupled repos (Desktop-level, own git remotes):
  ~/Desktop/sigma-quant/      ← Cloudflare Pages frontend (deployed · syafiqmzin-sigma-quant.pages.dev)
  ~/Desktop/sigma-research/   ← FastAPI backend + Qdrant/Groq AI briefs
  ~/Desktop/sigma-linkedin/   ← LinkedIn automation
```

---

## Rules

**Safety & Git**
1. **Auto commit + push** at natural completion points — stage all (`git add -A`), real message, push to master, no need to ask (standing authorization 2026-06-06). Guardrails: `.gitignore` is the safety net (secrets/.env, data/parquet/csv/pkl, logs, binaries all ignored — keep it airtight); pause and ask only if something sensitive/large looks like it'll slip through, or before any history rewrite / force-push.
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
13. **Smart Summary on research/decisions** — end research findings and strategy decisions with a `## 🧠 Smart Summary` of 2–4 plain-English bullets (point form, zero jargon — no R-multiples/t-stats/regime), explaining what we did/found like to a smart friend who doesn't trade. Technical answer on top. Skip it on pure infra/cleanup/config/chore replies unless asked.
14. **Bullet-point format (HARD RULE)** — ALL explanation, regardless of topic, MUST be in bullet-point form. No prose paragraphs. This applies to the technical answer too, not just the Smart Summary. Flagged repeatedly by Syafiq — make it permanent.
15. **Brevity (HARD RULE)** — see global directives. Project-specific: Smart Summary (rule 13) still applies where required, but the technical answer above it stays tight.
16. **Never caveat mid-price (HARD).** A number is cost-free unless it is a G2/tester result, where you say "net" once. No disclaimers about spread/cost during logic work — ever.

---

## Startup

1. The SessionStart hook prints the live **open backlog**, recently resolved tasks, and latest results straight from `research.db` (via [.claude/hooks/scripts/session_brief.py](.claude/hooks/scripts/session_brief.py)). Read it — it is the source of truth for what is open and what is already tested.
2. Read the latest [memory/](memory/) handover (the brief names the file) for the narrative + caveats.
3. Before proposing any work, reconcile against `open_backlog` (P1 first) + `log_agent` for the active idea (rule 6), and check `strategy_log.get_live_config(idea_id)` for its current frozen config. Never re-surface a resolved task or re-run logged work.
4. Brief Syafiq: "Here's where we left off" → wait for priority confirmation.
