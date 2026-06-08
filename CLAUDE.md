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
│   ├── db/                   ← all SQLite databases
│   │   └── research.db       ← single DB · step1_ideas(62) · step2_papers · step3_gates · step4_results · step5_agent_log
│   ├── code/                 ← shared DB layer (db_init · pipeline · agent_log)
│   ├── models/               ← one folder per foundational model
│   │   ├── cusum/            ← CUSUM-001 (parked · no code yet · awaiting gates)
│   │   └── hmm/              ← HMM-001 · nig_hmm.py (Gate 0 passed · awaiting Gate 1)
│   ├── migrations/           ← DB migration scripts (010 create_research_db · 011 migrate_data)
│   ├── dashboard/            ← Streamlit research dashboard (app.py · localhost:8501)
│   ├── outputs/              ← model plot outputs (Plotly HTML + Seaborn PNG)
│   └── RESEARCH_CODE_PROTOCOL.md ← code rules for research/models/ and research/code/
├── data/
│   └── parquet/              ← CS-GOLD-DUKAS-TICK · 24GB · 2016→2026 · IS/OOS sealed 2024-05-02
│       └── daily/            ← cached daily XAUUSD close (built on first cusum run)
├── .claude/
│   ├── agents/               ← quant-researcher agent definition
│   ├── hooks/                ← session hooks + audio notifications
│   └── commands/             ← /handover
├── braindump/                ← active PRDs and build plans only
└── memory/                   ← session handovers · _handover_archive/ for older ones

Decoupled repos (Desktop-level, own git remotes):
  ~/Desktop/sigma-quant/      ← Cloudflare Pages frontend (deployed · syafiqmzin-sigma-quant.pages.dev)
  ~/Desktop/sigma-research/   ← FastAPI backend + Qdrant/Groq AI briefs
  ~/Desktop/sigma-linkedin/   ← LinkedIn automation
```

---

## Rules

1. Auto commit + push: at natural completion points, stage all work, commit with a real message, and push to master — no need to ask first (Syafiq standing authorization 2026-06-06). GUARDRAILS: (a) `.gitignore` is the safety net — secrets (.env/keys), data (parquet/csv/pkl), logs, and binaries/installers are all ignored; keep it airtight. (b) Still pause and ask if something sensitive or a large binary looks like it would slip through, or before any history rewrite/force-push.
2. No destructive actions (rm -rf, reset --hard) without telling the user first.
3. Never print API keys — read from `.env` only.
4. Brevity — lead with the answer, cut the padding.
5. File references use markdown links [filename](path), never backticks.
6. No loose single files or py scripts. everything needs a house/folder.
7. Don't assume, always ask if you're not sure. 
8. Don't make things complicated.
9. Only touch codes that you're supposed to touch.
10. After every quant-researcher agent call, immediately write to `research/db/research.db` via the code layer before responding to Syafiq. No exceptions.
    - GENERATE gear → `pipeline.py` (add idea to step1_ideas if new) + `agent_log.log_agent_call(gear='GENERATE')`
    - DISSECT gear → `agent_log.log_dissect_result()` — atomic: updates step2_papers + inserts step5_agent_log
    - VALIDATE gear → `pipeline.log_result()` (step4_results) + `agent_log.log_agent_call(gear='VALIDATE')`
    - Always tell Syafiq which model was used: "QR agent ran on Opus/Sonnet"
11. Before touching any file in `research/models/` or `research/code/`, read [research/RESEARCH_CODE_PROTOCOL.md](research/RESEARCH_CODE_PROTOCOL.md) first.
12. QR agent model selection — pass `model` explicitly on every Agent call:
    - Default: **Sonnet** for ALL gear types (GENERATE, DISSECT, VALIDATE)
    - Opus: ONLY when Syafiq explicitly says "use Opus" in that message — no auto-upgrading based on task complexity
13. Before writing any code in `research/models/` for an idea, Gates 0 and 1 must be `passed` in `step3_gates`. No exceptions. Check with `pipeline.get_gates(idea_id)` — if empty or gates not passed, complete them first. See [braindump/research_protocol.md](braindump/research_protocol.md) for gate definitions.
14. **DB query discipline** — Never `SELECT` text-heavy columns (`key_equations`, `empirical_findings`, `context_fit`, `limitations`, `gate_answer`, `output_summary`) into main context. Use targeted column queries (id, title, status fields only). When a QR agent needs full paper content, query `research.db` inside the subagent — never load through main context first.
15. **DB writes via code layer only** — All writes to `research.db` must use `research/code/` functions (`open_gate`, `pass_gate`, `kill_idea`, `log_result`, `log_agent_call`, `log_dissect_result`, `log_human_decision`). Never raw `sqlite3` — timestamps, validation, and constraints will be wrong.
16. **Pre-QR-agent check** — Before briefing any QR agent, query `step1_ideas` and `step5_agent_log` for that `idea_id` (targeted columns only — see rule 14). Never re-surface already-resolved decisions or repeat logged work.
17. **Long-running commands → new terminal** — Any command taking >10s (model fits, data loads, migrations) must be launched in a new PowerShell window via `Start-Process`. Never `run_in_background`. Syafiq needs live output.
18. **Log human architecture decisions** — Key human-Claude architecture/methodology decisions must be logged immediately via `agent_log.log_human_decision(idea_id, gate_number, task_summary, output_summary)`. This is the `generate_calls` replacement. Not just QR agent calls — human decisions too.
19. **Always end with a Dumb Summary** — Close every substantive reply with a `## 🧠 Dumb Summary` section: 2–4 sentences in plain English, zero jargon (no R-multiples, t-stats, regime/trend-beta, etc.), explaining what we found/did and what it means like you're telling a smart friend who doesn't trade. The technical answer stays on top; the dumb summary is the floor. Set 2026-06-08.

---

## Startup

1. The SessionStart hook prints the live **open backlog**, recently resolved tasks, and latest results straight from `research.db` (via [.claude/hooks/scripts/session_brief.py](.claude/hooks/scripts/session_brief.py)). Read it — it is the source of truth for what is open and what is already tested.
2. Read the latest [memory/](memory/) handover (the brief names the file) for the narrative + caveats.
3. Before proposing any work, reconcile against `open_backlog` (P1 first) + `step5_agent_log` for the active idea (rule 16). Never re-surface a resolved task or re-run logged work.
4. Brief Syafiq: "Here's where we left off" → wait for priority confirmation.
