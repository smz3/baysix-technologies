# Baysix Technologies

<!-- Quant co-founder. Validate edges, protect capital, build the pod shop from $50 up. -->

---

## You're Talking To

Syafiq — 7yr Quant Trader → Quant Researcher (deployable).
Building the Jane Street / RenTech of Malaysia from scratch. Starting capital: $50 XAUUSD live.
Goal: own Quant Pod Shop → Fund → Malaysian institutional name.


---

## Repo Layout

```
baysix-technologies/          ← single repo · github.com/smz3/baysix-technologies
├── mt5/                      ← Sigma V5.0 MQL5 EA (XAUUSD live · Just Markets)
│   ├── Experts/Sigma_System/ ← Sigma_V5.0.mq5 + compiled .ex5
│   ├── Include/Sigma_System/ ← all .mqh modules (B2B detection, trading, risk, UI)
│   └── Documentation/        ← EA architecture + SAMTC docs
├── b2b/
│   ├── code/                 ← B2B Python engine (zone detection, trade logic)
│   └── docs/                 ← B2B knowledge base (overview, zone lifecycle, russian doll, etc.)
├── brokers/                  ← venue specs: justmarkets.yaml (TCM-001 cost model) + .md per broker
├── research/
│   ├── db/                   ← all SQLite databases (2-DB design: workstation + VPS)
│   │   ├── research.db       ← pipeline: step1_ideas · step2_papers · step3_gates (Gates 0-7) · step4_results · tester_runs/tester_trades (Gate 7 FIDELITY) · logs: log_agent · log_tasks · log_strategy
│   │   └── execution.db      ← live deployment ledger (downstream twin · 12 tables · spec: docs/reference/execution_schema.md · rebuild in progress)
│   ├── code/                 ← shared DB layer (db_init · pipeline · agent_log)
│   ├── models/               ← one folder per foundational model
│   │   ├── cusum/            ← CUSUM-001 (parked · no code yet · awaiting gates)
│   │   └── hmm/              ← HMM-001 · nig_hmm.py (Gate 0 passed · awaiting Gate 1)
│   ├── migrations/           ← DB migration scripts (010 create_research_db · 011 migrate_data)
│   ├── dashboard/            ← Streamlit research dashboard (app.py · localhost:8501)
│   ├── outputs/              ← model plot outputs (Plotly HTML + Seaborn PNG)
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

**QR agent — paper specialist only**
5. The QR agent ONLY **finds** papers (Sonnet — cheap fan-out) and **dissects** them (Opus — high-value; only reads keepers the find-phase surfaced). Strategy/ideation and coding/backtests are done **inline by Claude**, never delegated. Pass `model` explicitly on every Agent call; tell Syafiq which ran ("find on Sonnet / dissect on Opus"). (Reversed the 2026-05-28 Sonnet-only-dissect call on 2026-06-09.)
6. **Pre-brief check** — before briefing the agent, query `step1_ideas` + `log_agent` for that `idea_id` (targeted columns — rule 9). Never re-surface resolved decisions or repeat logged work.

**Research DB**
7. Before touching anything in `research/models/` or `research/code/`, read [research/RESEARCH_CODE_PROTOCOL.md](research/RESEARCH_CODE_PROTOCOL.md) first.
8. Gates 0 and 1 must be `passed` in `step3_gates` before writing any model code for an idea — check `pipeline.get_gates(idea_id)`. Gate definitions: [docs/reference/research_protocol.md](docs/reference/research_protocol.md).
9. **Query discipline** — never `SELECT` text-heavy columns (`key_equations`, `empirical_findings`, `context_fit`, `limitations`, `gate_answer`, `output_summary`) into main context; use targeted column queries. QR agents query `research.db` inside the subagent, never through main context.
10. **Writes via code layer only** — all `research.db` writes use `research/code/` functions (`open_gate`, `pass_gate`, `kill_idea`, `log_result`, `log_agent_call`, `log_dissect_result`, `log_human_decision`, `log_change`). Never raw `sqlite3` (timestamps/validation/constraints break).
11. **Log immediately, before replying to Syafiq** — after every agent call or decision:
    - QR find → `log_agent_call(gear='GENERATE')`; dissect → `log_dissect_result()` (atomic: step2_papers + log_agent)
    - inline VALIDATE → `pipeline.log_result()`; human architecture/methodology decision → `log_human_decision()`
    - any strategy-defining change (ADOPTED / REJECTED / FALSIFIED / SUPERSEDED / VALIDATED / CREATED / PROPOSED) → `strategy_log.log_change()` with `component`/`from`/`to`/`verdict`/`rationale`/`result_id`. `log_strategy` is the lineage (birth→live config, read via `get_live_config(idea_id)`); `log_agent` is NOT a substitute.

**Execution**
12. **Long-running commands (>10s)** — model fits, data loads, migrations — launch in a new PowerShell window via `Start-Process`. Never `run_in_background`; Syafiq needs live output.

**Communication**
13. **Always end with a Smart Summary** — a `## 🧠 Smart Summary` of 2–4 plain-English bullets (point form, zero jargon — no R-multiples/t-stats/regime), explaining what we did/found like to a smart friend who doesn't trade. Technical answer on top; this is the floor.

---

## Startup

1. The SessionStart hook prints the live **open backlog**, recently resolved tasks, and latest results straight from `research.db` (via [.claude/hooks/scripts/session_brief.py](.claude/hooks/scripts/session_brief.py)). Read it — it is the source of truth for what is open and what is already tested.
2. Read the latest [memory/](memory/) handover (the brief names the file) for the narrative + caveats.
3. Before proposing any work, reconcile against `open_backlog` (P1 first) + `log_agent` for the active idea (rule 6), and check `strategy_log.get_live_config(idea_id)` for its current frozen config. Never re-surface a resolved task or re-run logged work.
4. Brief Syafiq: "Here's where we left off" → wait for priority confirmation.
