# Handover — June 13, 2026 Morning

## State
**ORB-001 CLOSED — falsified clean.** Fork A ([fork_a_ea_emulation.py](research/models/orb/orb001/fork_a_ea_emulation.py)) ran EA-faithful realistic bid/ask fills AND Python idealized on the SAME sorted Arctic ticks, 25mo OOS, 526 trades: both negative (realistic E_R −0.0857 / t −1.67 / net −$2.99, idealized E_R −0.0775), divergence only −4.28 sumR → the old +67.4R was pure unsorted-tick look-ahead, NOT the fill model. **result_id 122, strategy_log #24 FALSIFIED, tasks 47+53 DONE.** Fill-realism plumbing validated end-to-end off sorted Arctic. ORB-002/003 stay abandoned-unproven (same engine/family). The rest of the session was DESIGN (discuss-only, nothing built) — see below.

## Decisions locked this session (all discuss-only — BUILD is the Next list)
- **Task 49 = Fill Primitive** `research/code/fills.py`: shared bid/ask fill model, idea-agnostic, reads venue from [brokers/justmarkets.yaml](brokers/justmarkets.yaml) (JM-Pro = spread-only, $0.10 half-spread, no commission). **(A)** lightweight Python dataclass, NOT a YAML DSL. **(B)** hand-write entry/exit per strategy calling the primitive; extract a library only on 2nd reuse. **(C)** realistic fills mandatory from Gate 3+; classifier ideas (HMM AUC/IC) exempt. Delete the idealized `_simulate_day` path (no toggle). Pin to MT5-tester ground truth (May-2024 ORB) as a permanent parity regression test. Do NOT retrofit the 18 dead ORB scripts.
- **Strategy Spec workflow** = the missing foundational step after Ideation+Papers, born at **Gate 1**. NOT a new table — `log_strategy` already separates entry/exit/sizing/anchor/filter/config **by row** (`component` col) and `get_live_config()` replays them. Birth spec = one `CREATED` row per component at Gate 1 (currently logged retroactively — that was the gap). Lifecycle: CREATED→VALIDATED/ADOPTED→FALSIFIED/REJECTED.
- **Schema delta = ONE column:** add `params_json` (TEXT) to `log_strategy` to carry each component's structured knobs (to_value stays the human label). Via numbered migration in [research/migrations/](research/migrations/), not a rebuild.
- **`get_spec(idea_id)`** (sibling of get_live_config) assembles rows into a readable spec card (entry/exit/sizing/filters, each tagged proposed/live/dead); render in Streamlit dashboard.
- **NO DB reset** (Syafiq agreed). Contaminated old ORB results = falsification IP, already labeled void via FALSIFIED rows + notes. execution.db has zero live data anyway. Version forward, never wipe the lab notebook.

## Next
1. **Build task 49** — write [research/code/fills.py](research/code/fills.py) (extract broker mechanics from `_simulate_day_ea`), + May-2024 parity regression test pinned to MT5 tester. Then protocol rule into [braindump/research_protocol.md](braindump/research_protocol.md).
2. **Build strategy-spec workflow (task 57, new)** — migration adding `params_json` to log_strategy; `get_spec(idea_id)` + spec-card render; backfill ORB-001's spec as the worked example; document Gate-1 spec-birth step in research_protocol.md.
3. **Task 56** — backup `data/arctic/` (SOLE copy of 10yr ticks) — Syafiq wants this AFTER 49.
4. Log the A/B/C + spec-workflow architecture decision via `log_human_decision` (deferred from this session — now locked).

## Blockers
None. All Next items are build orders on locked decisions.
