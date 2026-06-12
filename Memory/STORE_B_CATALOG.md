# Store B — Auto-Memory Catalog (snapshot 2026-06-12)

These are the **58 persistent notes** Claude carries between sessions — my private fact-store, living at
`C:\Users\User\.claude\projects\c--Users-User-Desktop-baysix-technologies\memory\` (NOT in this repo's git;
this catalog is just a human-readable snapshot and may drift from the live `MEMORY.md` index over time).

Four types: **user** (who you are) · **feedback** (how I should work) · **project** (ongoing work/state) · **reference** (pointers).

---

## 👤 USER — who you are (4)

| Note | What it holds |
|------|---------------|
| user_career_goals | Building Baysix as founder/PM, no external job target. Goal: $50 → Pod Shop → Fund → Malaysian institutional name. |
| user_career_transition | 7yr Quant Trader → Quant Researcher (deployable). NOT "AI Quant Dev". |
| user_sme_focus | Your two specialist pillars: Implied Volatility (IV rank, VRP, option chain) + Hidden Markov Models (regime detection). |
| user_live_trading | You actively live-trade XAUUSD on MT5 (Just Markets, semi-automated B2B zones). |

---

## 📌 REFERENCE — external pointers (2)

| Note | What it holds |
|------|---------------|
| strategy_log_reference | What the `log_strategy` table is (strategy birth→live-config lineage) and how to read it (`get_live_config(idea_id)`). |
| reference_mt5_bridge | MT5↔Python bridge facts: MetaTrader5 pkg, symbol `XAUUSD.s`, ~65k bar cap, EA exports QUANT_ZONES CSVs (UTF-16, 40-col). |

---

## 🛠️ FEEDBACK — how I should work (26)

### Communication & style
| Note | Rule it encodes |
|------|-----------------|
| feedback_brevity_delivery | Keep replies short, lead with the answer, no padding. |
| feedback_smart_summary | Always end substantive replies with a plain-English Smart Summary in point form. |
| feedback_quant_explanation_style | Explain quant concepts as a layered hierarchy (Foundation → Model → Applications), not prose. |
| feedback_doc_abbreviations | Spell out every abbreviation + give each metric a what/why/mental-model (for you + recruiters). |
| feedback_discuss_before_build | "Discuss/dissect/dig into" = TALK ONLY — no files/code until an explicit build order. |
| feedback_ideation_generate | In ideation, generate ranked ideas + commit to a pick — don't bounce decisions back as questions. |
| feedback_multi_asset_framing | Don't anchor examples to XAUUSD — assume multi-asset always. |

### Workflow & process
| Note | Rule it encodes |
|------|-----------------|
| feedback_handover_naming | Handover naming: if timeslot taken, append a number (Evening2). Never overwrite. |
| handover_nextsteps_must_be_tasks | Every deferred "Next step" in a handover MUST also be a `log_tasks` row (the brief reads tasks, not prose). |
| handover_lint_gate | Handover result-numbers MUST cite a result_id/artifact — enforced by `handover_lint.py` + git pre-commit. |
| feedback_adr_governance | Major component decisions need an ADR with alternatives + trigger conditions (prevents agent drift). |
| feedback_log_architecture_discussions | Log key human architecture/methodology decisions to the DB immediately, not just agent calls. |
| git_workflow_whole_tree_push | Auto commit+push (standing authz 2026-06-06); `git add -A` whole tree; reset/merge stay gated. |
| feedback_long_run_terminal | Long-running commands → open a new PowerShell window (Start-Process) so you see live output. |
| long_run_completion_sentinel | To detect a new-window run finished, wait on a DONE-sentinel's existence (`run_tracked.py`), never on output mtime. |
| feedback_progress_bars | All research loops must use tqdm + per-iteration print. No silent loops. |

### Research-DB discipline
| Note | Rule it encodes |
|------|-----------------|
| feedback_db_layer_usage | All `research.db` writes go through `research/code/` functions — never raw sqlite3 (breaks timestamps). |
| feedback_db_query_discipline | Never SELECT text-heavy columns into main context (a 31.5KB dump once killed a session). |
| feedback_qr_agent_pre_brief | Pre-read ideas + agent-call log from the DB before briefing the QR agent. |
| feedback_hmm001_dissect_model | QR agent = paper-only: Sonnet FINDS papers, Opus DISSECTS them. |
| feedback_verify_against_live_ea | For B2B, verify Python against the live MT5 EA (ground truth), not Plotly reconstructions. |

### Quant methodology (hard-won)
| Note | Rule it encodes |
|------|-----------------|
| per_period_sharpe_units_rule | Sharpe→t-stat MUST use per-period Sharpe + T=obs count, never annualised. (Recurred 3×.) |
| er_denominator_illusion | Never pick a stop on E[R] — tighter stops inflate E[R] while making fewer dollars. Rank by $/trade + survival. |
| spread_winrate_drag | Spread on B-book/swap-free = win-rate drag (barriers shift half-spread), NOT a payoff deduction. |
| reopen_falsified_on_new_data | A falsification made under a later-disproven condition is VOID — re-open it, don't inherit it. |
| orb_unsorted_tick_lookahead | ROOT CAUSE of the ORB saga: unsorted parquet ticks → "first breakout" = look-ahead. Always sort+assert monotonic. |

---

## 📂 PROJECT — ongoing work & state (26)

### Infra / data / engine
| Note | State it holds |
|------|----------------|
| active_work_state | 🤝 HANDSHAKE ANCHOR — read first. Current P0/next-steps pointer. |
| arctic_tick_store | Canonical tick store = ArcticDB (511M ticks, sorted+sealed); read via `arctic_io.py`. Parquet deleted. |
| execution_db_design | execution.db 2-DB design (12 tables) — spec locked 2026-06-11, not built yet. |
| deployment_dgate_sequence | ORB-001 deploy ladder: Gates 0-6 → Gate 7 FIDELITY → FORWARD (demo→live). |
| project_engine_design | Engine architecture LOCKED: ENGINE_BLUEPRINT.md canonical, Engine/Strategy split, validate-first. |
| framework_metric_flexibility | Framework is multi-asset, idea-agnostic, tri-purpose; metric matches idea type (not always IC). |
| framework_schema_locked | Profile/manifest/N_trials-family schema locked 2026-05-24. |
| ai_execution_architecture | Delegation pattern: Claude orchestrates, Gemma executes. |
| ideas_log_db_husk_root_cause | The ideas_log.db "husk" bug — root-caused + fixed; what to check if it reappears. |
| lean_cli_runnability_status | LEAN CLI installed but Docker runtime + XAUUSD data UNVERIFIED; confirm before any run. |

### ORB strategy line
| Note | State it holds |
|------|----------------|
| orb001_validated | ⚠️ FALSIFIED 2026-06-12 — ORB-001 G0-6 edge was a look-ahead artifact of unsorted ticks. |
| orb_entry_timing_immediate | ORB-001 edge is the immediate 08:05 breakout; M15-confirm & entry-delay both FALSIFIED. |
| orb_dd_structural_floor | ORB-001 ~33% DD at $50 is a structural min-lot floor, not tunable; sub-10% needs ~$250+. |
| orb_trend_beta_fault_line | ORB-001 base symmetric edge is trend-beta — FALSIFIED (positive+sig in down-trend). |
| orb_ea_deployment_conventions | ORB EAs are standalone (orb_system namespace); naming↔magic, headless compile, tester UTC offset. |
| orb002_anchor_decision | ORB-002 (NY ORB) anchor = NYSE 09:30 ET DST-aware; alternatives rejected — don't re-litigate. |
| orb002_validated | ⚠️ ABANDONED-UNPROVEN — shares unsorted-tick engine; will not re-validate. |
| orb003_noon_validated | ⚠️ ABANDONED-UNPROVEN — same; was benched on 55% spread drag. |
| d0_feed_drift_reframe | D0 live JM "block" = normal B-book feed drift (~$28), not a bug; parity moved to D1. |

### B2B / HMM / IB lines
| Note | State it holds |
|------|----------------|
| project_b2b_python_parity | B2B engine ported to `b2b/sigma_core`, 17 tests; verifying via zone diff vs EA. |
| b2b_h1_phase_b_naive_finding | B2B H1 XAUUSD: honest positive edge over 1k+ trades, strongly significant — signal IS real (figures + cite live in the note itself). |
| hmm001_open_variables | HMM-001 passed Gates 0-4; W=20 frozen; open: calibration choice, NIG emission. |
| project_ib001_hypothesis | ⚠️ SUPERSEDED by ib001_reversion_finding (momentum/confluence framing was falsified). |
| ib001_reversion_finding | IB-001 KILLED @ cost: reversion real but ~40-200× too small for 2-pip spread → pivot to order-flow. |
| project_kronos_integration | Kronos (AAAI 2026) = primary ML integration for B2B zone-survival prediction. |
| project_micro_tab_architecture | MICRO tab: Bloomberg-ASKB equivalent for APAC equities; architecture finalized, Phase 1 ready. |

---

### Note on health
As of this snapshot the index (`MEMORY.md`) and the folder are in **exact sync — 58 = 58, 0 orphans, 0 broken links**.
Recently retired (not in this list): 4 dead job-hunt notes (hard-deleted) + 1 parked note (`project_vector_context_deployment`, now in `_stale/`).
