# Research Protocol 3.2 — Generic, Idea-Kind-Branched Gating

_Spec / ADR · 2026-06-15 · supersedes the HMM-coded front half of 3.1 ([research_protocol.md](../reference/research_protocol.md))_

## Problem

The protocol is **HMM-coded at the front**. Gate 2's 4 checks
(occupancy / stochastic-matrix / ergodicity / persistence) are Markov-only;
ORB / STRUCT silently hand-rolled their own `gate2_sanity.py`. `pipeline.py`
enforces only sequencing + Gate 6/7 evidence + the kill-rule; Gates 0–5 pass on
free-text `gate_answer` (honor-system). The lived symptom: **systematic
price-action strategies die at Gate 2/3 for the wrong reason** — Gate 2 applies
Markov checks that don't fit, and Gate 3 tests a *context-stripped symmetric base
rule* that washes out the conditional edge the strategy actually trades.

Pure price-action is the house style (no geometric chart patterns — statistical
breakout / trend / mean-reversion). The pipeline must test *that*, and must tell
a real conditional edge from selective memory without strangling it early.

## Decision

One pipeline; an **idea-kind tag picks the gate variant**. Significance-test type
is a **deterministic function of declared metadata, resolved by code, delivered
by the driver, validated at the gate** — never an agent's free choice (rule:
[enforcement_code_not_prose] — rules lost across sessions must be executable).

### 0 · Keystone — idea-kind + output-type (new declared metadata)

- `step1_ideas.idea_kind` ENUM (CHECK): `strategy` | `primitive` | `overlay` | `classifier`.
- `step1_ideas.output_type` ENUM (CHECK): `pnl_stream` | `classifier_score` | `primitive_output`.
- `protocol.GATE_APPLICABILITY[idea_kind]` → which gates apply (a `primitive`
  legally skips Gates 3–5, judged on correctness only).
- `protocol.significance_test_for(idea_kind, output_type)` → the mandated test:
  `pnl_stream → PSR/DSR` · `classifier_score → IC t-stat / AUC CI` ·
  `primitive_output → correctness`. **Single source of truth in code.**

### Per-gate changes

| Gate | From | To |
|------|------|----|
| **0 Understand** | math/papers first | **concept/mechanism first** (plain-English "why does this edge exist?"), then math. Conditioning is *born here* so it's mechanism-justified, not fitted. |
| **1 Frame** | spec = rule + null | spec also declares **conditioning** + **management** as first-class fields, plus `output_type` + resolved significance test. |
| **2 Foundation** | 4 Markov checks, "no human visual" | **3 method-free categories**: validity · non-degeneracy · **causal-cleanliness** (look-ahead / fill-realism guard lives here). Markov-4 demoted to the `classifier` instance. Trader's-eye → **per-idea optional** supplementary evidence. |
| **3 Baseline** | tests context-stripped symmetric base; t<1.0 = kill | tests the **declared-conditioned rule**; base-symmetric is a **diagnostic**, not the kill trigger. Kill stays gated by **≥2 falsified** (rule 8b, already code-enforced). Keep realistic fills + t>1.0 backstop on the conditioned rule. |
| **4 Model** | assumes a sophisticated model (HMM) | **"optional overlay / conditioning layer."** Overlay present → tests conditional improvement; none → **collapses into Gate 5**. `classifier` kind keeps it as a model gate. |
| **5 Signal** | always Sharpe-t / PSR | **significance test branches on `output_type`** (resolved by code). Adopt **QuantStats** tearsheet; **pre-commit 3–4 pass metrics before viewing** (no eyeball-gating). |
| **6 Validate** | walk-forward / OOS / MC | unchanged (universal). |
| **7 Fidelity** | MQL5 port diff | unchanged (Python→MQL5 deploy path). |

### How the agent "knows" the test (the enforcement chain)

1. **Declare** `output_type` (constrained ENUM) at Gate 1 — a fact, not a rule choice.
2. **Resolve** via `protocol.significance_test_for(...)` — one function, no prose.
3. **Deliver** — `idea_cli.py next` reports the resolved test at Gate 5.
4. **Validate** — `pipeline.pass_gate(5)` requires the `step4_results` metric_key to
   match the resolved test (e.g. `pnl_stream` requires a `psr` row, rejects `auc`);
   mismatch → blocked.
5. **Surface** — `idea_cli.py prebrief` + SessionStart write-contract brief carry the
   resolved test per idea, so the QR brief already contains it.

The doc is for humans; **driver + DB constraints + gate validation are what the
agent obeys.** No judgment call survives the chain.

## Alternatives considered

- **Lower the Gate 3 t-bar** — rejected: ships overfit noise; the bar isn't the
  problem, the *strawman object* (context-stripped base) is.
- **Per-idea bespoke gate scripts** (status quo, hand-rolled `gate2_sanity.py`) —
  rejected: drift, no enforcement, the exact failure 3.1 spent a session undoing.
- **Free-text "agent picks the test"** — rejected: drifts across sessions
  ([enforcement_code_not_prose]).

## Trigger conditions to revisit

- A new idea-kind appears that none of the 4 tags fit (e.g. a portfolio/allocation
  overlay) → extend the ENUM + applicability map, don't special-case.
- A `strategy` whose edge is genuinely symmetric (no conditioning) → Gate 3
  base-rule *is* the test; conditioning fields may be empty (allowed).

## Implementation tasks (tracked in log_tasks)

1. Schema migration: `idea_kind` + `output_type` ENUMs + backfill existing ideas.
2. `protocol.py`: `GATE_APPLICABILITY` + `significance_test_for` + wire into `next_step`.
3. `pipeline.py`: enforce kind→gate applicability (legal skip) + `pass_gate(5)` test-match validation.
4. Gate 0/1: concept-first + spec-birth fields (conditioning / management / output_type).
5. Gate 2: generic 3-category sanity checker; demote Markov-4 to `classifier`.
6. Gate 5: QuantStats tearsheet + pre-commit metric bars.
7. Doc regen: `research_protocol.md` + `research_db_schema.md`; single-source gate questions.
