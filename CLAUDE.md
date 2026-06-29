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
│   │   ├── research.db       ← Protocol 4.0 lean: step1_ideas · step2_papers · step3_gates (G1-G4) · step4_results (+is_run) · is_runs · tester_runs/tester_trades/tester_zones · logs: log_agent · log_tasks · log_strategy
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
4b. **Token discipline** — the whole transcript (incl. every tool result) is re-read each turn, so keep it lean. Targeted reads (offset/limit, never whole files when a slice works); greps with `head_limit` + exclude-globs up front; counts over dumps. No pre-tool narration on routine work; fold "what I did" into one closing line — don't narrate mid-stream then re-summarize. Keep intent only before irreversible/non-obvious moves.

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
15. **Brevity (HARD RULE, overrides "be thorough")** — lead with the direct answer in the first 1–2 lines, then stop. Default ceiling ~150 words / ~8 lines for explanation-type replies; go longer ONLY when explicitly asked ("expand", "go deep", "full breakdown"). Depth of topic is NOT license for length. Banned unless asked: comparison tables, multi-point taxonomies, section headers, lead-ins ("Great question", "You're right that…"), restating the question. One example or one table only if it IS the answer. Smart Summary (rule 13) still applies where required, but the technical answer above it stays tight.

---

## MT5 / EA Workflow (XAUUSD live · Just Markets)

**Trust rule (HARD)** — the **MT5 strategy tester is the arbiter**; a Python/SQL query-layer number is NEVER a gate verdict. This is the ORB look-ahead lesson ([[orb_unsorted_tick_lookahead]]): a query layer manufactured a too-good edge the chronological tester later killed. Cheap query screens are allowed only if explicitly labelled exploratory, never reported as a result.

**Two EAs per system, separation of concerns:**
- **Emitter** (e.g. [brc_baysix.mq5](mt5/Experts/brc_system/brc_baysix.mq5)) = read-only chronological oracle: detects zones across TFs, writes a UTF-8 lifecycle CSV → ingested to `tester_zones`. NO orders. Keep pristine (needed pure for OOS re-emits).
- **Trader** (e.g. `brc_trader.mq5`) = the strategy: hosts swappable `brc_entry.mqh` / `brc_exit.mqh` / `brc_sizing.mqh` modules. Reuses the emitter's detection includes so zones are identical.

**Iteration model (no file-copy per version):** variants flip **enum modes + numeric inputs** and save a new **`.set` preset** — code is *changed* (extend an enum branch), **never replaced/duplicated**. One file per role; versions distinguished by git sha + `.set` + version stamp, NOT by copied `.mq5`. Duplicating EAs kills the tester sweep + git lineage.

**Version control / provenance:** `BRC_VERSION` `#define` in [brc_types.mqh](mt5/Include/brc_system/brc_types.mqh) + auto-generated `brc_version.mqh` (git sha/branch/dirty/build-time via `python research/code/infra/gen_brc_version.py`, run before every compile). The EA **prints its sha + dirty flag on init** — a DIRTY-tree number is not reproducible → exploratory only. Frozen tested inputs ship as versioned `.set`. Releases/`.ex5` artifacts + MQL5-Market protection layer deferred until sharing.

**Build (headless):** compile via MetaEditor64 CLI; `/inc` MUST point at `mt5/` (the MQL5 root containing `Include/`), NOT `mt5/Include` — else error 106 cascade. Compile log is UTF-16. ([[brc_compile_workflow]])

**Deploy:** reach the JM MT5 terminal (hash E7DB) via `mklink /J` junctions in Experts + Include (no elevation; `ln -s`/symlink fail on this host). MetaEditor → Refresh to see new files. ([[brc_terminal_junction_deploy]])

**Tester model:** BRC runs **"Open prices only"** — detection + invalidation are close-only so each bar's OHLC is final at close; real-ticks = >24h/8yr quadratic blow-up for no data gain ([[brc_emitter_open_prices_model]]). Fills are level-based (limit at zone level) to stay deterministic under this model. Tester needs UTC offset.

**Conventions:** new MQL5 files (`.mq5` + `.mqh`) = lowercase snake_case (`brc_system`); Sigma CamelCase is legacy, leave it ([[mql5_lowercase_filenames]]). ORB EAs live in their own `orb_system` namespace, magic-number per EA.

---

## FOB-001 — Canonical Knowledge (don't re-derive; deep refs at the bottom)

FOB = First Opposite Breakout, the active XAUUSD idea. **Read this section before any FOB work** — it is the source of truth so Syafiq doesn't re-explain. Authoritative deep docs are linked at the end; this is the load-every-session distilled form.

**What FOB IS (the model):** REACTION modeling on **CMP (Current Market Price)**, NOT prediction and NOT a win-rate-lifting classifier. Every PBO/VR/CF is a **tagged fact that already printed**; a trade is *a position within a confirmed nested storyline* (W1⊃D1⊃H4⊃H1⊃M30⊃M5…), not "a signal." Higher TF = **bias/context**, lower TF = **execution trigger**. ([[fob_cmp_storyline_model]])

**Core SOP — `CMP → BO → VR → CF`** (never enter the first BO):
- **PBO** = Primary BreakOut = the CMP breakout / setup anchor. Body must clear the level (wick ≠ count).
- **VR** = Valid Retracement = the **first opposite break, exactly one TF below**; happens **ONCE**; it tells you **which TF you're trading**. When two TFs break together, **whichever made the VR first** dictates the TF.
- **CF** = Confirmation = the continuation you actually enter on (in-zone = best; 2nd CF matters in sideways). **LR CF** = adjacent TF below (safer, premium price). **HRCF** = skip one TF (cheaper entry, higher risk; classifier currently PARKED).

**CYCLE (HARD):** a cycle = **PBO → VR → CF1 → CF2 → CF3…**, anchored by the PBO. **A NEW PBO starts a NEW cycle** — NOT "repeats when price breaks the VR." Maps to EA fields: `seq` = per-setup_tf PBO ordinal (= cycle id), `cf_idx` = CF order within the cycle.

**ALIGNMENT = AWARENESS, not a gate (HARD):** we do **NOT** trade only when all TFs agree. Record each higher TF's **live state** (esp. **W1 = Bias**, **D1 = Direction**) so we trade *aware* of context; the trade direction **depends on which TF setup we choose**. A TF's current direction = the direction of the **live cycle one TF below it** (lower TF controls higher). This is why the full-stack-alignment **trade gate was REJECTED** (result_id 18) — conceptually wrong, not just flat. *Example (gold, 2026-06-29): MN1 bull (live W1 CF5) but W1's dir = live D1 CF1 bear → Bias BEARISH; D1 bear w/ pending H4 CF → long-or-short depends on the setup TF.*

**VR Fresh vs Not-Fresh:** Fresh = price went straight to origin, **no close back into the VR zone** → layer in. Not-Fresh = price **closed back inside** the VR zone (wick ≠ count) = "VR structured" → ride the trend. The single most important behavioral flag on a zone.

**Data capture (schema LIVE, migration 035):** FOB owns its storyline payload — `fob_cycles` / `fob_events` (+ `htf_state` awareness JSON) / `fob_zones` (4-pointer + touches/RT/`vr_fresh`/lifecycle). FOB does **NOT** use `tester_zones` (that's BRC's 5-pointer table — the old P5 confusion). Shared spine: `tester_runs.run_role` (emitter|trader), `tester_run_summary`, `tester_trades`. Emit causally from the EA (path A); never Python-derive lifecycle (look-ahead). Round-1 = basics; CF↔VR distance + setup-type + regime/labels are deferred phase-2.

**Deep refs (open these for full detail, don't paste into context wholesale):** [FOB manual dissection](research/papers/fob/FOB_breakout_system.dissect.md) (the full Bonker manual) · [CMP storyline model](docs/specs/2026-06-27_fob_cmp_storyline_model.md) · [storyline-alignment findings](docs/specs/2026-06-27_fob_storyline_alignment_findings.md) (⚠️ numbers computed on BRC-contaminated `tester_zones` run_id 5 — VOID for FOB until re-screened on FOB own zones, task 192) · [data-capture + DB rebuild spec](docs/specs/2026-06-29_fob_data_capture_and_db_rebuild.md).

---

## Startup

1. The SessionStart hook prints the live **open backlog**, recently resolved tasks, and latest results straight from `research.db` (via [.claude/hooks/scripts/session_brief.py](.claude/hooks/scripts/session_brief.py)). Read it — it is the source of truth for what is open and what is already tested.
2. Read the latest [memory/](memory/) handover (the brief names the file) for the narrative + caveats.
3. Before proposing any work, reconcile against `open_backlog` (P1 first) + `log_agent` for the active idea (rule 6), and check `strategy_log.get_live_config(idea_id)` for its current frozen config. Never re-surface a resolved task or re-run logged work.
4. Brief Syafiq: "Here's where we left off" → wait for priority confirmation.
