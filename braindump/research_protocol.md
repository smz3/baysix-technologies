# Baysix Research Protocol
_Last updated: 2026-06-11 (added Gate 7 — FIDELITY, the port-fidelity bridge to deployment)_

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

Every idea must pass gates in order: **0 → 1 → 2 → 3 → 4 → 5 → 6**, then — only if it is re-implemented in another language for deployment — **7**.

**Gates 0–6 validate the *edge*** (does the signal exist and survive OOS?). Passing Gate 6 sets `step1_ideas.status='graduated'` — the research is complete. **Gate 7 validates the *port*** (did the deployed artifact faithfully reproduce the validated code?). It is a different *kind* of gate — about the artifact, not the edge — and it is the bridge between `research.db` and `execution.db` (a `deployments` row cannot be registered until Gate 7 is `passed`). See [execution_protocol.md](execution_protocol.md) §3.

A gate cannot be marked `passed` unless the previous gate is `passed`.
An idea can be `killed` at any gate. The kill reason must be logged.

---

### Gate 0 — Understand

**Question:** Do we know the model's mathematical truth from the literature?

**What this means:**
- Read and DISSECT the foundational papers for this model
- Know: how it works, under what conditions it works, what the failure modes are, what correct output looks like on financial data
- You must be able to describe what "working correctly" looks like before writing a single line of code

**Pass looks like:**
- At least one paper dissected in `step2_papers` (dissected=1)
- `papers_queue` view is empty for this idea
- Agent or human can answer: "On XAUUSD, this model working correctly would show X"

**Blocked looks like:**
- Papers added but not dissected
- Cannot describe correct output from first principles

**DB log:**
- `step2_papers` — one row per paper, dissected=1 with all fields filled
- `step3_gates` — gate_number=0, status=passed, gate_answer = summary of what working correctly looks like
- `step5_agent_log` — DISSECT gear entry per paper

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

**DB log:**
- `step3_gates` — gate_number=1, gate_answer = simple rule + null hypothesis

---

### Gate 2 — Foundation

**Question:** Does the simplest possible implementation produce sane output?

**What this means:**
- Build the simplest version of the idea — the **rule-based** dumb version from Gate 1, NOT the sophisticated model
- For HMM-001 this is the 5%/20-day Markov chain: label states by the fixed 5% threshold, count transitions into a 3×3 matrix
- The sophisticated model (HMM, etc.) is NOT built here — it lives at Gate 4. The 5% threshold is fixed; Gate 4 is where it gets cross-examined
- Run it on real XAUUSD data
- Pass 4 objective sanity checks (defined below) — no human visual confirmation
- Chart is generated as supplementary evidence, not the gating criterion

**Pass looks like (all 4 must pass):**

| Check | Criterion | Why |
|-------|-----------|-----|
| State occupancy | Every state ≥ 30 observations | Estimability floor — each transition row needs enough samples. A %-cutoff would wrongly reject genuinely rare regimes (e.g. bear states in a secular uptrend) |
| Stochastic matrix | Every populated row of M sums to 1.0 (±1e-9) | A valid transition matrix |
| Ergodicity | Exactly one eigenvalue ≈ 1, all others \|λ\| < 1, and M^n row-deviation decreases monotonically | A unique stationary π exists and the chain converges to it. Convergence *speed* is a property of λ₂, not a sanity bar — a sticky chain converges slowly and that is fine |
| Persistence (inertia) | A_jj > π_j for every state | Being in a state today makes tomorrow more likely than its unconditional rate — i.e. real inertia, not noise. A fixed 0.85 floor is an HMM artifact and wrongly rejects short-lived-but-real regimes |

_The HMM-specific checks (EM convergence, volatility separation, fixed-persistence floors) belong at **Gate 4**, where the sophisticated model is actually built. These were originally mis-applied to the rule-based baseline at Gate 2 attempt 1–2; recalibrated 2026-05-29._

**Blocked looks like:**
- Any one of the 4 checks fails — specific check + value logged as blocker
- Implementation crashes

**DB log:**
- `step4_results` — stage=IS, metric_key=foundation_check, metric_value=1 (pass) or 0 (fail), notes = per-check results
- `step3_gates` — gate_number=2, gate_answer = PASS/FAIL + per-check values

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

**Blocked / Kill looks like:**
- Raw edge is negative or t-stat < 1.0 → the signal does not exist even before costs
- Kill the idea here. Do not proceed.

**DB log:**
- `step4_results` — two rows per metric: cost_adjusted=0 (raw) and cost_adjusted=1 (net)
- `step3_gates` — gate_number=3, gate_answer = raw edge + net edge + t-stat

**Required fields in step4_results:**
`n_obs`, `period`, `data_start`, `data_end`, `git_sha`, `code_path`

---

### Gate 4 — Model

**Question:** Does the sophisticated model confirm or challenge the baseline?

**What this means:**
- Now build the real model (the complex version from the papers)
- Compare its regime labels / signal against the Gate 1 simple rule
- Where do they agree? Where do they disagree?
- The disagreement is where the model adds value
- If the model output is identical to the simple rule → the model adds no value, question whether to proceed

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

**What this means:**
- Reduce model output to a directional signal (+1 long, -1 short, 0 flat)
- Measure: Sharpe, t-stat, win rate, net edge after costs
- Compute PSR (Probabilistic Sharpe Ratio) using n_obs and n_trials
- If multiple parameter sets were tested, log n_trials and trial_family_id — the deflated Sharpe applies
- Net edge must be positive. If not, kill here.

**Pass looks like:**
- t-stat > 2.0 on IS signal
- Net edge > 0 after realistic costs
- PSR computed and logged

**Blocked / Kill looks like:**
- Net edge ≤ 0 → signal does not survive costs, kill here
- t-stat < 2.0 → insufficient evidence, blocked until more data or different approach

**DB log:**
- `step4_results` — full metric suite: sharpe, t_stat, win_rate, net_edge (raw + net), PSR
- All `n_obs`, `n_trials`, `trial_family_id`, `period` fields mandatory
- `step3_gates` — gate_number=5, gate_answer = signal summary + PSR

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

**Question:** Does the deployed artifact reproduce the validated research backtest on the *same* data?

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

1. **Gates are sequential.** No skipping. Gate N requires Gate N-1 passed.
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

1. Before calling: read `step1_ideas` and `step5_agent_log` for this idea — know what has already been done
2. After every call: write to DB before responding to Syafiq. No exceptions.
3. DISSECT gear → update `step2_papers` (dissected=1, fill all fields) + `step5_agent_log`
4. VALIDATE gear → write `step4_results` + `step5_agent_log`
5. GENERATE gear → write `step1_ideas` (new idea row) + `step5_agent_log`
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
