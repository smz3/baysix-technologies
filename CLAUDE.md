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
│   │   ├── ideas_log.db      ← 62 ideas · generate_calls · build_order
│   │   ├── research_log.db   ← pipeline · pipeline_events (VALIDATE)
│   │   └── agent_log.db      ← agent_calls (gear · model · papers per QR run)
│   ├── code/                 ← shared DB layer (db_init · pipeline · ideas_log · agent_log)
│   ├── models/               ← one folder per foundational model
│   │   └── cusum/            ← CUSUM-001 changepoint detection (built · parked)
│   ├── migrations/           ← DB migration scripts (001–003 applied)
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

1. No git push without user approval.
2. No destructive actions (rm -rf, reset --hard) without telling the user first.
3. Never print API keys — read from `.env` only.
4. Brevity — lead with the answer, cut the padding.
5. File references use markdown links [filename](path), never backticks.
6. No loose single files or py scripts. everything needs a house/folder.
7. Don't assume, always ask if you're not sure. 
8. Don't make things complicated.
9. Only touch codes that you're supposed to touch.
10. After every quant-researcher agent call, immediately write to the correct DB before responding to Syafiq. No exceptions.
    - GENERATE gear → `research/db/ideas_log.db` (generate_calls table)
    - VALIDATE gear → `research/db/research_log.db` (pipeline_events table)
    - BOTH gears → `research/db/agent_log.db` (agent_calls table): log idea_id, idea_code, gear, model, task, papers JSON
    - Always tell Syafiq which model was used: "QR agent ran on Opus/Sonnet"
11. Before touching any file in `research/models/` or `research/code/`, read [research/RESEARCH_CODE_PROTOCOL.md](research/RESEARCH_CODE_PROTOCOL.md) first.
12. QR agent model selection — pass `model` explicitly on every Agent call:
    - Sonnet: GENERATE (exploring ideas), WebSearch + literature review, quick VALIDATE with simple stats
    - Opus: HMM/Kalman/heavy math derivations, multi-step validation chains, anything informing live capital decisions

---

## Startup

Read latest [memory/](memory/) handover. Brief Syafiq: "Here's where we left off" → wait for priority confirmation.
