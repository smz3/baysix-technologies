# Handover — June 15, 2026 Morning

## State
- **Focus this session: research-protocol redesign discussion (no strategy work).**
- **3.1 DONE + pushed (commit ada5578)** — reconciled stale docs to live research.db:
  - [docs/reference/research_db_schema.md](docs/reference/research_db_schema.md) regenerated from live PRAGMA: 9 tables + 4 views (was 5 tables, ~6 migrations stale). Added log_strategy/log_tasks/tester_runs/tester_trades; step5_agent_log→log_agent; gate 0-6→0-7; real CHECK/UNIQUE/FK; open_backlog view.
  - [docs/reference/research_protocol.md](docs/reference/research_protocol.md): step5_agent_log→log_agent refs only. Faithful mirror; ZERO semantic change.
- **Audit finding (the spine of 3.2):** the protocol is HMM-coded at the front. Gate 2's 4 checks (occupancy/stochastic/ergodicity/persistence) are Markov-only; ORB/STRUCT silently hand-rolled their own gate2_sanity.py. pipeline.py enforces only sequencing + Gate 6/7 evidence + kill-rule; Gates 0-5 pass on free-text gate_answer (honor-system). protocol.py already classifies gates generically (evidence 3/5/6 · fidelity 7 · sense 0/1/2/4).
- **Memory check done:** no hidden protocol doc/script in ~/.claude memory — canonical lives only in workspace (protocol.md + pipeline.py + protocol.py).

## Next (3.2 — make it generic + robust; NOTHING written yet, discuss-first)
1. **Idea-kind branching** (the root fix): tag each idea `strategy` vs `primitive/component` vs `overlay` → decides WHICH gates apply. Fixes STRUCT forced through trading gates + vacuous Gate 4.
2. **Gate 0 reframe** (Syafiq-approved): concept/mechanism FIRST ("why does this edge exist?" plain English), THEN math/papers.
3. **Gate 2 generic** (Syafiq-approved): replace 4 Markov checks with 3 method-free categories — validity / non-degeneracy / causal-cleanliness — declared per idea. "No human visual" → optional per-idea.
4. **Gate 3 t-stat** (Syafiq-resolved): KEEP t-stat as the "is it real vs luck" backstop; ADD equity-smoothness + DD (account-size-aware, see [[orb_dd_structural_floor]]) as a SEPARATE path-quality check — do NOT swap. Gate 3 bar stays soft (t>1.0).
5. **Gate 5** (Syafiq-resolved): adopt QuantStats as the tearsheet/reporting layer; pre-commit 3-4 metrics as pass bars BEFORE viewing (no eyeball-gating). PSR+t-stat are ONE question (PSR = skew/kurtosis-aware t-stat), and only valid for P&L-stream ideas → significance test must branch on output type (return→PSR/DSR, classifier→IC t-stat/AUC CI, primitive→correctness).
6. Line 13: trader's-eye → optional per-idea, not baked. Single-source the gate questions (kill doc↔code dup).

## Blockers
None. 3.2 is a design discussion — get Syafiq's pick on which thread (likely #1 idea-kind branching, it unlocks the rest) before writing anything.
