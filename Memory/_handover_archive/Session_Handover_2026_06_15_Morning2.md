# Handover — June 15, 2026 Morning2

## State
- **Protocol 3.2 keystone SHIPPED** (idea-kind branching). Spec/ADR: [docs/specs/2026-06-15-research-protocol-3.2-generic-gating.md](../docs/specs/2026-06-15-research-protocol-3.2-generic-gating.md).
- **Tasks 78/79 DONE:**
  - Migration 026: `step1_ideas.idea_kind` (strategy/primitive/overlay/classifier) + `output_type` (pnl_stream/classifier_score/primitive_output), CHECK-constrained. 7 in-flight ideas backfilled (STRUCT→primitive, HMM→classifier, ORB/BRK/MSM→strategy). Untagged ideas declare at Gate 1.
  - [protocol.py](../research/code/protocol.py): `GATE_APPLICABILITY` (legal skip — primitive→{0,1,2,7}, overlay→skip 3) + `significance_test_for()` resolver. `next_step()` now surfaces `idea_kind`, `applies`, `sig_test`. Verified: STRUCT→correctness, HMM→IC/AUC, strategy→PSR/DSR.
  - [pipeline.py](../research/code/pipeline.py): `update_idea` accepts idea_kind/output_type with enum validation (IDEA_KINDS / OUTPUT_TYPES).
- **Docs reconciled:** [research_db_schema.md](../docs/reference/research_db_schema.md) has the 2 new columns; [research_protocol.md](../docs/reference/research_protocol.md) carries a **3.2 transition banner** (ACTIVE vs PENDING-task) + the old chokehold lines (Gate 2 Markov-4-universal, Gate 3 kill-on-symmetric-base) are neutralized.
- **Design decisions locked this session** (in the spec): price-action is house style (statistical, no geometric patterns); B2B is a quant strategy with a measured raw edge that still owes a cost check (figures in [[b2b_h1_phase_b_naive_finding]]); STRUCT-001 = primitive family, sigma_core = B2B's separate primitive family. Gate 6 (OOS) is the real executioner, not 2-4.

## Next — EXECUTE tasks 80→84 (these BUILD the rest of 3.2; the real test is later: run breakout-pullback through the finished gates)

1. **Task 80 (P1) — `pass_gate(5)` enforcement backstop.** In [pipeline.py](../research/code/pipeline.py) `pass_gate()`: when `gate_number==5`, look up the idea's `output_type`, resolve via `protocol.significance_test_for`, and BLOCK the pass unless a matching `step4_results` metric_key exists for this idea at gate 5 (pnl_stream→requires a `psr` row; classifier_score→`ic_t`/`auc`; primitive_output→n/a, gate 5 not applicable). Mirror the existing `_gate7_has_pass_evidence` pattern (pipeline.py ~line 127). Add a helper `_gate5_has_matching_sigtest(idea_id)`. Raise a clear blocked error naming the required metric.

2. **Task 81 (P2) — Gate 0/1 spec fields.** Add concept-first sub-step to Gate 0 (doc, already ACTIVE in banner). At Gate 1 spec-birth, capture `conditioning` + `management` as first-class — extend strategy_log spec-birth or add idea fields; ensure `output_type` is set at Gate 1 (it gates task-80 enforcement). Wire a check into `next_step` that warns if a `strategy` reaches Gate 3 with no conditioning declared.

3. **Task 82 (P2) — Gate 2 generic checker.** Write the 3-category sanity (validity / non-degeneracy / causal-cleanliness) as a reusable function (new module e.g. `research/code/gate2_sanity.py` — consolidate the hand-rolled ORB/STRUCT ones). Demote Markov-4 to the `classifier` branch. Causal-cleanliness = look-ahead/fill-realism guard (the ORB unsorted-tick lesson).

4. **Task 83 (P2) — Gate 5 QuantStats.** Adopt QuantStats tearsheet as the reporting layer; pre-commit 3-4 pass metrics BEFORE viewing (no eyeball-gating). Branch on output_type per task 80.

5. **Task 84 (P2) — doc rewrite.** Finish [research_protocol.md](../docs/reference/research_protocol.md) prose to fully match 3.2 (banner is interim). Single-source the gate questions (kill doc↔code dup); `protocol.py` is source of truth.

## Blockers
None. Driver is live: `python research/code/idea_cli.py next <idea_id>` shows kind + applicable gates + resolved sig-test. Start with task 80 (it's P1 and the hard guardrail). Keystone is infra — no result-numbers produced this session.
