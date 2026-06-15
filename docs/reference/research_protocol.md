# Baysix Research Protocol
_Last updated: 2026-06-15 — **Protocol 3.2 fully shipped** (tasks 78–84): idea-kind branching, generic Gate 2, conditioned Gate 3, output-type-resolved Gate 5, code-enforced metric wall. Prose below reconciled to 3.2._
_Prior: 2026-06-11 — added Gate 7 (FIDELITY, the port-fidelity bridge to deployment)._

> ## Protocol 3.2 — one pipeline, idea-kind picks the variant
> Full design + rationale: [docs/specs/2026-06-15-research-protocol-3.2-generic-gating.md](../specs/2026-06-15-research-protocol-3.2-generic-gating.md).
> **Tag every idea** with `idea_kind` (`strategy` / `primitive` / `overlay` /
> `classifier`) + `output_type` (`pnl_stream` / `classifier_score` /
> `primitive_output`). The driver `idea_cli.py next` reads them and reports the
> **applicable gates + the resolved significance test** — read it, don't recall the
> ladder. Every row below is live in code:
>
> | 3.2 change | Live in |
> |---|---|
> | idea-kind branching — primitives skip Gates 3–6; applicability map | `protocol.GATE_APPLICABILITY`, `pipeline.open_gate` (refuses non-applicable gates) |
> | significance test resolved from `output_type`, never chosen | `protocol.significance_test_for`, surfaced by `next` |
> | `pass_gate(5)` blocks unless logged metric_key matches the resolved test | `pipeline._gate5_has_matching_sigtest` (task 80) |
> | Gate 0 concept/mechanism-first | doc-enforced — see Gate 0 |
> | Gate 1 declares conditioning + management + output_type | `strategy_log` components + `next` advisories (task 81) |
> | Gate 2 generic 3-category checker (validity / non-degeneracy / causal-cleanliness) | `research/code/gate2_sanity.py`; Markov-4 = classifier-only `markov4()` (task 82) |
> | Gate 3 tests the *conditioned* rule; base-symmetric = diagnostic, not kill | doc-enforced — see Gate 3 |
> | Gate 4 = optional overlay; collapses into Gate 5 if none | applicability map |
> | Gate 5 QuantStats tearsheet + pre-committed metrics, branched on output_type | `research/code/gate5_report.py` (task 83) |
>
> **Canonical source of truth is code, not this doc.** Gate questions live in
> `pipeline.GATE_QUESTIONS`; applicability in `protocol.GATE_APPLICABILITY`; the
> significance test in `protocol.significance_test_for`. The prose below is the
> loss-free human mirror — on any conflict, code wins and the doc is the bug.

---

## Goal Statement Requirement

Every engine, foundation model, or strategy built at Baysix must open with a locked Goal Statement before Gate 1 is passed. Format:

**Goal:** [What the tool/model/strategy does in one sentence]
**What it detects/measures:** [Specific output — regime, signal, metric]
**Accuracy definition:** [What "working correctly" looks like — trader's eye test first, then statistical]
**Deployment:** [How it connects to downstream strategies — strategy-agnostic where possible]

The Goal Statement is logged in Gate 1's `gate_answer`. It cannot be vague. If you cannot write it in four lines, the idea is not ready for Gate 1.

---

## Philosophy

We are a quant fund. We apply proven, peer-reviewed models with the precision of a Michelin chef — not the guesswork of a home cook. The same ingredients (HMM, CUSUM, Markov chains) produce different outcomes based entirely on the quality of the process.

**Three principles that govern everything:**

1. **Simple first.** Build the dumbest possible version. Verify it works. Earn the right to add complexity.
2. **Foundation before sophistication.** The sophisticated model exists to challenge a simple baseline — not to replace one that was never built.
3. **Falsification over confirmation.** We are looking for reasons to kill an idea, not reasons to keep it alive. The kill reason is our research IP.

---

## The Gates (0 → 6 validate the edge; 7 validates the port)

Every idea passes its **applicable** gates in order: **0 → 1 → 2 → 3 → 4 → 5 → 6**,
then — only if it is re-implemented in another language for deployment — **7**.
**Which gates apply is set by `idea_kind` (3.2)**: a `primitive` legally skips 3–6
(judged on correctness + port fidelity only → {0,1,2,7}); an `overlay` skips the
standalone baseline (3); `strategy` / `classifier` run the full ladder. The
applicable set is `protocol.GATE_APPLICABILITY` and `pipeline.open_gate` refuses a
gate that does not apply. Sequencing then means "the previous **applicable** gate is
passed" — for a primitive, Gate 7's predecessor is Gate 2.

**Gates 0–6 validate the *edge*** (does the signal exist and survive OOS?). Passing Gate 6 sets `step1_ideas.status='graduated'` — the research is complete. **Gate 7 validates the *port*** (did the deployed artifact faithfully reproduce the validated code?). It is a different *kind* of gate — about the artifact, not the edge — and it is the bridge between `research.db` and `execution.db` (a `deployments` row cannot be registered until Gate 7 is `passed`). See [execution_protocol.md](execution_protocol.md) §3.

A gate cannot be marked `passed` unless the previous **applicable** gate is `passed`.
An idea can be `killed` at any gate. The kill reason must be logged.

---

### Gate 0 — Understand

**Question:** Do we know the model's mathematical truth from the literature?

**Concept-first (3.2).** Before any math or paper, answer in plain English: **why
should this edge exist?** Name the mechanism (who is on the other side, what
structural reason makes the move persist or revert). The idea's **conditioning** is
*born here* — the context the edge lives in is a consequence of the mechanism, not a
filter fitted later after a flat base disappointed. Only once the mechanism is
stated do you go to the math to confirm/refute it. This ordering is what stops
Gate 3 from testing a conditioning that was reverse-engineered from the data.

**What this means:**
- State the economic mechanism first (one paragraph, no equations).
- Then read and DISSECT the foundational papers for this model.
- Know: how it works, under what conditions it works, what the failure modes are, what correct output looks like on financial data.
- You must be able to describe what "working correctly" looks like before writing a single line of code.

**Pass looks like:**
- A stated mechanism ("why this edge exists") + the conditioning it implies.
- At least one paper dissected in `step2_papers` (dissected=1).
- `papers_queue` view is empty for this idea.
- Agent or human can answer: "This model working correctly would show X" (multi-asset; XAUUSD is one instance, not the frame).

**Blocked looks like:**
- Papers added but not dissected
- Cannot describe correct output from first principles

**DB log:**
- `step2_papers` — one row per paper, dissected=1 with all fields filled
- `step3_gates` — gate_number=0, status=passed, gate_answer = summary of what working correctly looks like
- `log_agent` — DISSECT gear entry per paper

---

### Gate 1 — Frame

**Question:** What is the simple human-readable rule and null hypothesis?

**What this means:**
- Define the dumbest possible version of this idea (the "5%/20-day equivalent")
- This rule must be explainable to anyone in one sentence
- State the null hypothesis: what would falsify this idea completely?
- No code at this gate — this is thinking only

**Pass looks like:**
- Simple rule defined and written down (e.g. "high-vol day = |return| > 0.8%")
- Null hypothesis stated clearly (e.g. "regime labels have no predictive power on next-day returns")
- Both logged in gate_answer

**Blocked looks like:**
- Cannot define a simple rule without referencing the complex model
- Null hypothesis is vague or unstated

**Declare `output_type` here (3.2).** Set `idea_kind` + `output_type` via
`pipeline.update_idea` at Gate 1 — they are *facts about the idea*, not test choices.
`output_type` resolves the mandated Gate-5 significance test (`pnl_stream` → PSR/DSR,
`classifier_score` → IC-t / AUC, `primitive_output` → correctness). Until it is set,
the Gate-5 metric wall is silently OFF — `idea_cli.py next` warns, and `pass_gate(1)`
prints a nudge.

**Spec-birth (mandatory):** Passing Gate 1 also births the strategy's spec — one
`CREATED` row per design component in `log_strategy`, each carrying its proposed
knobs in `params_json`. The components are **entry · anchor · exit · sizing · filter ·
conditioning · management** (3.2 made the last two first-class); emit a row for every
one the idea touches (omit the rest). **conditioning** = the regime/state that gives
the *conditional* edge (born at Gate 0, mechanism-justified — not fitted);
**management** = trade management (trail / partial / breakeven / time-stop). This is
the structured form of the simple rule, and it is what `strategy_log.get_spec(idea_id)`
renders as the spec card (each component tagged live / proposed / dead as the lineage
evolves). No spec-birth, no Gate 1 pass.

```python
from research.code import strategy_log
strategy_log.log_change(idea_id, "spec-birth", "CREATED", component="conditioning",
                        to_value="HTF_trend_up_200d",
                        params_json={"mechanism": "breakouts persist with higher-TF trend"})
strategy_log.log_change(idea_id, "spec-birth", "CREATED", component="entry",
                        to_value="immediate_breakout",
                        params_json={"trigger": "first_touch_of_OR_boundary", "confirm": False})
# ...repeat per component the idea defines
```

A `strategy` that reaches Gate 3 with **no conditioning** declared is flagged by
`idea_cli.py next` (declare it, or confirm the edge is genuinely symmetric — allowed).

**Pass looks like (DB):**
- `step1_ideas` — `idea_kind` + `output_type` set.
- `step3_gates` — gate_number=1, gate_answer = simple rule + null hypothesis.
- `log_strategy` — one `CREATED` spec-birth row per component (incl. conditioning where it applies), each with `params_json`.

---

### Gate 2 — Foundation

**Question:** Does the simplest possible implementation produce sane output?

**What this means:**
- Build the simplest version of the idea — the **rule-based** dumb version from Gate 1, NOT the sophisticated model.
- The sophisticated model (HMM, etc.) is NOT built here — it lives at Gate 4.
- Run it on real data and pass the **3 generic, method-free categories** (3.2).
- Trader's-eye is **per-idea optional** supplementary evidence, not a banned input; a chart is supplementary, never the gating criterion.

**The 3 categories (all must be covered AND pass).** Reusable checker:
[research/code/gate2_sanity.py](../../research/code/gate2_sanity.py) (`Gate2Sanity` —
`verdict()` requires all three categories covered + every check passing):

| Category | Asks | Examples |
|----------|------|----------|
| **validity** | is the output well-formed? | finite (no NaN/Inf), right shape/count, in a plausible range (gold $, a probability in [0,1]) |
| **non-degeneracy** | is the output non-trivial? | not constant, both directions / classes present, variance > 0 (a model that always says "flat" passes nothing) |
| **causal-cleanliness** | no look-ahead, realistic fills? | timestamps strictly monotonic *before any tick sim* (the ORB unsorted-tick lesson — `assert_monotonic_time`), entry strictly **after** the signal window closes |

**Markov-4 is the `classifier` instance, not the universal gate (3.2).** For a
`classifier` idea, run `gate2_sanity.markov4(states, transition_matrix)`, which maps
the four legacy checks onto the three categories:

| Legacy Markov check | Maps to | Criterion |
|-------|---------|-----------|
| Stochastic matrix | validity | every populated row of M sums to 1.0 (±1e-6) |
| State occupancy | non-degeneracy | every state occupied above a floor (no dead regime) |
| Persistence (inertia) | non-degeneracy | A_jj ≥ floor — being in a state today makes tomorrow more likely than its unconditional rate |
| Ergodicity / sequential path | causal-cleanliness | decoded path is time-ordered (fit on past only) |

_HMM-specific checks (EM convergence, volatility separation) belong at **Gate 4**,
where the sophisticated model is built — not on the rule-based baseline here._

**Blocked looks like:**
- Any check fails, or a category was never tested (an untested causal-cleanliness category does NOT pass Gate 2) — specific check + value logged as blocker.
- Implementation crashes.

**DB log:**
- `step4_results` — stage=IS, metric_key=foundation_check, metric_value=1 (pass) or 0 (fail), notes = per-check results.
- `step3_gates` — gate_number=2, gate_answer = PASS/FAIL + per-check values.

---

### Gate 3 — Baseline

**Question:** Does the dumb rule from Gate 1 have any edge, raw and after costs?

**What this means:**
- Implement the simple rule from Gate 1 as a trading signal
- Measure its edge in-sample: raw first, then after realistic costs (spread + commission)
- This becomes the benchmark. The sophisticated model at Gate 4 must beat this
- If the simple rule already has strong edge, question whether we need the complex model at all

**Realistic fills mandatory from Gate 3.** All path-dependent backtests (entries, exits, stops) MUST fill via [research/code/fills.py](../research/code/fills.py) (venue-aware bid/ask, MT5-faithful) — never an idealized mid+tolerance model. The retired idealized path (`anchor_oos._simulate_day`) is deprecated; do not reuse it. Classifier ideas that gate on AUC/IC (e.g. HMM-001) never simulate fills and are exempt. Guarded by `research/tests/test_fills.py::test_may2024_orb_parity_matches_fork_a`.

**Pass looks like:**
- Raw edge is positive and t-stat > 1.0 (signal exists, even if weak)
- Net edge logged separately (cost_adjusted=1)
- Both numbers in `step4_results`

**Test the *conditioned* rule, not a context-stripped strawman (3.2).** The Gate-1
spec declares the idea's conditioning (the mechanism-justified context it trades);
Gate 3 measures *that*. The bare symmetric base rule is a **diagnostic**, not the
kill trigger — a flat base with the conditioning declared at Gate 0 is **one
FALSIFIED hypothesis**, not a death. Conditioning must be born at Gate 0 (not fitted
after the base failed). `idea_cli.py next` flags a `strategy` that reaches this gate
with no conditioning declared.

**Blocked / Kill looks like:**
- The **conditioned** rule's raw edge is negative or t-stat < 1.0 → signal absent even before costs → **one FALSIFIED hypothesis** (reframe/variant). Kill needs **≥2 FALSIFIED** (rule 8b, code-enforced) — do **not** kill on the base rule alone.

**DB log:**
- `step4_results` — two rows per metric: cost_adjusted=0 (raw) and cost_adjusted=1 (net)
- `step3_gates` — gate_number=3, gate_answer = raw edge + net edge + t-stat

**Required fields in step4_results:**
`n_obs`, `period`, `data_start`, `data_end`, `git_sha`, `code_path`

---

### Gate 4 — Model

**Question:** Does the sophisticated model confirm or challenge the baseline?

**Optional overlay / conditioning layer (3.2).** Gate 4 is the *sophisticated model
or conditioning overlay* — and it is **optional**. If the idea has no overlay (a pure
rule strategy), Gate 4 **collapses into Gate 5** (the applicability map skips it for
an `overlay`-less path; a `classifier` keeps it as a real model gate). When an overlay
is present, the test is **conditional improvement** over the Gate-3 conditioned rule —
not standalone edge.

**What this means (when an overlay exists):**
- Build the real model / overlay (the complex version from the papers).
- Compare its regime labels / signal against the Gate 1 simple rule.
- Where do they agree? Where do they disagree? The disagreement is where the model adds value.
- If the model output is identical to the simple rule → the model adds no value, question whether to proceed.

**Pass looks like:**
- Model converges cleanly (no degenerate states)
- Model output has meaningful difference from simple baseline (not identical, not random)
- The disagreement can be explained from the literature (Gate 0 knowledge)

**Blocked looks like:**
- Model does not converge
- Model output is identical to baseline → no value added
- Model output cannot be explained → implementation likely broken

**DB log:**
- `step4_results` — model metrics logged with parameters JSON
- `step3_gates` — gate_number=4, gate_answer = where model agrees/disagrees with baseline and why

---

### Gate 5 — Signal

**Question:** Is there a tradeable signal with positive net edge?

**The significance test branches on `output_type`, resolved by code (3.2).** It is
*not* a free choice — `protocol.significance_test_for(idea_kind, output_type)` returns
the mandated test, and `pipeline.pass_gate(5)` **blocks the pass** unless a logged
`step4_results` metric_key matches it:

| output_type | mandated test | metric_key must match |
|---|---|---|
| `pnl_stream` | PSR / DSR (deflated Sharpe) | contains `psr` / `dsr` |
| `classifier_score` | IC t-stat / AUC CI | contains `ic_t` / `auc` |
| `primitive_output` | correctness (oracle / parity) | Gate 5 not applicable (primitive skips it) |

**Pre-commit the pass metrics BEFORE viewing — no eyeball-gating (3.2).** Producer:
[research/code/gate5_report.py](../../research/code/gate5_report.py) (`Gate5Report`).
Declare 3–4 numeric bars up front (`commit_bars(...)`), `evaluate_pnl` /
`evaluate_classifier` to compute + score, and only **then** render the QuantStats
tearsheet — the verdict is already decided by the committed bars. PSR/DSR use the
**per-period** convention: per-period Sharpe + T = observation count (never
annualised), kurtosis term `(kurt − 1)/4` with Pearson kurtosis.

**What this means:**
- Reduce model output to a directional signal (+1 long, −1 short, 0 flat) — or a classifier score.
- Compute the resolved test (PSR/DSR for pnl, IC-t / AUC-CI for classifier); if multiple parameter sets were tested, the **deflated** Sharpe (DSR) applies — log `n_trials` + `trial_family_id`.
- Net edge must be positive. If not, kill here.

**Pass looks like:**
- All pre-committed bars met (e.g. PSR ≥ 0.95, sharpe_t > 2.0, net_mean > 0), and the **matching** metric_key is logged so `pass_gate(5)` clears.

**Blocked / Kill looks like:**
- Net edge ≤ 0 → signal does not survive costs, kill here.
- A committed bar is missed → insufficient evidence, blocked.

**DB log:**
- `step4_results` — the resolved-test metric (a `psr`/`dsr` row for pnl_stream, `ic_t`/`auc` for classifier) **plus** the supporting suite; `n_obs`, `n_trials`, `trial_family_id`, `period` mandatory.
- `step3_gates` — gate_number=5, gate_answer = signal summary + the resolved-test value.

---

### Gate 6 — Validate

**Question:** Does the edge survive walk-forward and out-of-sample?

**What this means:**
- Walk-forward: roll window forward, refit model, measure signal on unseen data
- OOS: run on sealed OOS data (post 2024-05-02). One shot. No refitting after seeing OOS.
- Monte Carlo: simulate distribution of Sharpe outcomes, confirm edge is not luck
- The OOS run is final. If it fails here, the idea is killed — not adjusted, not re-optimised.

**Pass looks like:**
- Walk-forward Sharpe ≥ 50% of IS Sharpe (no severe degradation)
- OOS net edge > 0
- Monte Carlo 5th percentile Sharpe > 0

**Kill looks like:**
- OOS net edge ≤ 0 → idea killed, no exceptions
- Walk-forward Sharpe < 50% of IS → severe overfitting, kill

**DB log:**
- `step4_results` — three sets of rows: stage=walkforward, stage=montecarlo, stage=OOS
- `data_hash` mandatory on OOS run — proves data seal was respected
- `step3_gates` — gate_number=6, gate_answer = walk-forward + OOS + MC summary
- Update `step1_ideas` status to `graduated` (pass) or `killed` (fail)

---

### Gate 7 — Fidelity  (the port-fidelity bridge to deployment)

**Question:** Does the deployed artifact reproduce the validated backtest on the same data?

**What this means:**
- Applies **only when the strategy is re-implemented in another language** to run live — for us, the MQL5 Expert Advisor (the EA) that ports the Python research code. A Python→Python deployment (e.g. IBKR via `ib_insync`) runs the *same* validated code, has no port, and **skips Gate 7 entirely.**
- This gate isolates **port bugs**: it changes the *code* (Python → MQL5) while holding the *data* fixed (Dukascopy). Anything that drifts is a translation error, not an edge failure — the edge already passed Gate 6.
- Run the compiled `.ex5` in the **MT5 Strategy Tester** on the **research feed** (Dukascopy custom symbol, 100% real ticks), same OOS window, at a **fair deposit** (large enough that the risk cap never binds — too small biases the tester to a quiet-day subsample).
- Diff the tester trade-list against the Python research trade-list, per-trade **and** aggregate. The tester runs *identical data*, so it should **not** drift; a material gap is a port bug to fix in the EA.

**Pass looks like (statistical-equivalence, pre-committed before results seen):**
- Trade-set overlap (same `session_date` + `direction`) ≥ 95%
- E[R], win-rate, and $/trade each inside the research 95% CI
- Per-trade R correlation high

**Blocked / Kill looks like:**
- Material divergence → the deployed code is **not** the validated strategy. Fix the EA; nothing goes near a broker account. *(ORB-001 sits here now — FAILED: win-rate 56.7%→33.2%, a trailing-exit port bug.)*

**Hard rule:** FIDELITY **must** use the research data source (Dukascopy), never the broker's native history — that would conflate a port bug with a feed difference. The broker feed is introduced for the first time downstream at FORWARD (execution.db), on purpose.

**DB log:**
- `tester_runs` — one row per Strategy-Tester run (config + summary + the diff verdict)
- `tester_trades` — per-trade tester ledger (join key = `session_date`)
- `step3_gates` — gate_number=7, gate_answer = overlap % + E[R]/win/$per-t diff + verdict
- `log_agent` — if an agent ran the diff

*(Gate 7 lives in research.db because the tester is a workstation/batch activity on research data. Its pass is the precondition the execution layer checks before registering a deployment — see [execution_schema.md](execution_schema.md).)*

---

## Non-Negotiable Rules

1. **Gates are sequential within the applicable set.** No *ad hoc* skipping — but `idea_kind` legally removes vacuous gates (`protocol.GATE_APPLICABILITY`). Gate N requires the previous **applicable** gate passed; `pipeline.open_gate` enforces both.
2. **Kill reasons are mandatory.** If status=killed, `kill_gate` and `kill_reason` must be filled. No silent deaths.
3. **Results require reproducibility fields.** `git_sha`, `data_hash`, `n_obs` are mandatory on every step4_results row. A result without these is not a valid result.
4. **Raw and net must both be logged.** Gates 3 and 5 require `cost_adjusted=0` AND `cost_adjusted=1` rows for every metric.
5. **Period must be explicit.** Every metric must declare `period` (per_trade / daily / annualised). Ambiguity is not allowed.
6. **OOS is one shot.** Once OOS data is touched, the idea is either graduated or killed. No re-optimisation after seeing OOS.
7. **Simple before complex.** If the simple version (Gate 2) does not make intuitive sense, do not build the complex version (Gate 4). Fix the foundation first.
8. **Discuss before build.** "Discuss / dissect / dig into" = talk only. No files, no code until explicit build order.

---

## Agent Instructions

When a QR agent (GENERATE / DISSECT / VALIDATE gear) is called:

1. Before calling: read `step1_ideas` and `log_agent` for this idea — know what has already been done
2. After every call: write to DB before responding to Syafiq. No exceptions.
3. DISSECT gear → update `step2_papers` (dissected=1, fill all fields) + `log_agent`
4. VALIDATE gear → write `step4_results` + `log_agent`
5. GENERATE gear → write `step1_ideas` (new idea row) + `log_agent`
6. Always state which model was used: "QR agent ran on Sonnet/Opus"
7. Default model: Sonnet for all gears. Opus only when Syafiq explicitly says "use Opus"

---

## Gate Status Reference

| Status | Meaning |
|--------|---------|
| open | Gate created, work in progress |
| passed | Gate question answered, criteria met, ready to advance |
| blocked | Gate question cannot be answered yet — specific blocker logged |
| killed | Idea falsified at this gate — kill_reason mandatory |

---

## What Data to Preserve

When nuking and rebuilding the DB, always preserve:
- `step1_ideas` — the idea catalog (research IP)
- `step2_papers` — dissected paper knowledge (saves re-reading)

Everything else can be rebuilt from scratch.
