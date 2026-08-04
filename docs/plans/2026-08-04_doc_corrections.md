# Document Corrections — 2026-08-04

Audit of `baysix-technologies` docs/config against the live repo + DB, run from a Cowork
session with full read access. Every item below is `MEASURED` (a command run this session)
or `CITED` (read from the file on disk). Nothing here is recalled.

**Scope:** documents and config only. No strategy content, no logic changes.

**Method:** `PRAGMA table_info` + row counts against [research.db](../../research/db/research.db),
`grep -n` against the named files, artifact CSVs read from `mt5/tester/artifacts/`.

---

## Section A — Wrong or unverifiable numbers

These corrupt hand-arithmetic downstream. Highest damage first.

### A1 — `margin_pct` contradicts its own comment `[P0]`

- **File:** [brokers/justmarkets.yaml:75](../../brokers/justmarkets.yaml#L75)
- **Text:** `margin_pct: 0.03              # = 1:3000`
- **Problem:** 3% margin is **1:33**. 1:3000 is `0.000333`. The value and the comment
  cannot both be true.
- **Why it matters:** if `0.03` is correct, one ounce of gold at ~$3,300 requires ~$99 of
  margin and a $20 account **cannot open 0.01 lot at all** — which contradicts the four
  runs on record (result_id 61-68). So one of the two is wrong, and every position-size
  or ruin calculation that reads this field inherits the error.
- **Fix:** measure it. `OrderCalcMargin()` or `SymbolInfoDouble(SYMBOL_MARGIN_INITIAL)` on
  `XAUUSD.s` in the live terminal. Record the measured value, delete the losing half of
  the contradiction, and note metals may carry an instrument-specific margin rate that
  overrides account leverage.
- **Do not** resolve this by reasoning about which is more likely. It is one command.

### A2 — Broker spec is written for a $50 account `[P0]`

- **File:** [brokers/justmarkets.yaml](../../brokers/justmarkets.yaml) lines **22, 46, 67**
- **Text:**
  - `:22` — `so it's unavailable on the $50 account. Pro is the right modelling basis.`
  - `:46` — `# min-lot risk floor on $50: a 5-pip stop on 0.01 lot risks $0.50 = 1% equity;`
  - `:67` — `finding: Raw is only ~15% cheaper AND needs $200 min deposit — unavailable at $50.`
- **Problem:** live mandate is **$20**. Every risk-floor figure in those comments is
  computed against the wrong denominator.
- **Fix:** re-derive at $20. Note that the `:46` comment is doubly stale — it reads as a
  reassurance ("1% equity") that is false at $20.

### A3 — `data_source` hardcoded to the wrong venue `[P0]`

- **File:** [research/code/io/ingest_grw.py:110](../../research/code/io/ingest_grw.py#L110)
- **Text:** `data_source="dukascopy",`
- **Problem:** `MEASURED` — `grw_run_XAUUSD.s_v0.2.0_20210401_jm_tight.csv` and
  `..._jm_wide.csv` ran on `XAUUSD.s` (Just Markets ticks). They are ingested as
  Dukascopy. Two of four GRW runs carry false provenance.
- **Why it matters:** the entire point of the 2026-08-03 pivot was that the wrong venue's
  cost was being charged. The ingest path still hardcodes the wrong venue's *label*, so
  the DB cannot distinguish the runs that fixed the bug from the ones that had it.
- **Fix:** derive `data_source` from the symbol (`XAUUSD.s` → `just_markets`,
  `XAUUSD_dukas` → `dukascopy`). Backfill the two affected `tester_runs` rows.

### A4 — TO_VERIFY fields are tracked inconsistently `[P2]`

- **File:** [brokers/justmarkets.yaml](../../brokers/justmarkets.yaml)
- **Problem:** `regulator: TO_VERIFY` (`:11`) and `news_pips: TO_VERIFY` (`:61`) are marked
  unverified but are **absent** from `to_verify_fields: [stress_pips, beta_stress]` (`:146`).
  Anything reading that list as the authoritative gap register misses two fields.
- **Also:** `last_verified: 2026-05-25` — the file is 10 weeks stale against a live account.
- **Fix:** make `to_verify_fields` complete, or drop it and rely on inline markers. One
  mechanism, not two.

### A5 — Pro account type unconfirmed against balance `[P2]`

- **File:** [brokers/justmarkets.yaml:25](../../brokers/justmarkets.yaml#L25) — `active: pro`
- **Problem:** public JM material lists **Pro minimum deposit at $200** with spreads quoted
  "from 0.0-0.1 pips"; the yaml models Pro at ~2.0 pips (`:58`, sourced to
  "Syafiq's live experience"). The account under discussion holds $20. Either the account
  is not Pro, JM restructured its tiers, or the MY entity differs.
- **Fix:** read account type + live spread from the terminal, record with date.
- **Note:** low urgency for *backtests* — since the 2026-08-03 pivot they run on `XAUUSD.s`
  real ticks and use recorded spread, not this constant. It still matters for the
  hand-arithmetic that cites
  [justmarkets.yaml:145](../../brokers/justmarkets.yaml#L145).

### A6 — CORRECTION TO THIS AUDIT

- An earlier pass in this session asserted `stop_out_level` was **missing** from the broker
  spec. That was wrong. `stop_out_level_pct: 20` exists at
  [justmarkets.yaml:99](../../brokers/justmarkets.yaml#L99), marked confirmed.
- Verbal margin-room arithmetic given earlier in the same session used **50%** as the
  stop-out level. The correct figure is **20%**. Any number derived from that pass is void.
- Logged here rather than silently dropped — this is precisely the Loop A §1.3(4) failure
  class (unverified repo state asserted as fact), and the failure is more useful on the
  record than off it.

---

## Section B — Stale mandate baked into live config

The 2026-08-03 handover records a scalping mandate. Syafiq's manual method, described
2026-08-04, is a **half-pot barrier method targeting ~2:1 over roughly 3 trades**. These
files still encode the former.

**Section B is a PROPOSAL, not a correction.** It contradicts a logged decision
(`ranking must come from survival time + log-growth at $20`, prior handover) and therefore
requires Syafiq's explicit call before any file is touched.

### B1 — `min_trades: 500` selects for the wrong shape `[OPEN DECISION]`

- **File:** [research/config/grw_fitness.json:23](../../research/config/grw_fitness.json#L23)
- **Problem:** an unrankable sentinel at 500 trades makes any configuration trading fewer
  than 500 times score `-1e9`. A ~3-trade method is unrankable by construction.
- **Fix (if B2 is accepted):** replace the floor with a `max_trades` cap.
- **Constraint:** `grw_passes` is `MEASURED` at **0 rows**, so a change is still free —
  no pass has ever been judged against v1.1.0. That window closes on the first batch.

### B2 — Objective is Kelly; mandate is a barrier problem `[OPEN DECISION]`

- **File:** [research/config/grw_fitness.json:3-4](../../research/config/grw_fitness.json#L3-L4)
- **Text:** `"name": "log_growth"`, `"objective": "log(final_equity / initial_deposit)"`
- **Problem:** log-growth maximises terminal wealth over an unbounded horizon with ruin
  treated as catastrophic. The stated mandate is fixed stake, fixed target, ruin accepted,
  small trade count. Different problem class.
- **Candidate replacement:** `P(equity >= target before equity < min_viable)`.
- **Tension to resolve:** the prior handover states ranking must come from *survival time +
  log-growth at $20*. That is a logged decision and it conflicts with the above. **Syafiq
  decides.** Do not change the file on the strength of this document.
- **If accepted:** version bump starts a new trial family per the file's own
  `change_policy`; v1.x passes cannot be pooled.

### B3 — `sizing_valid` treats deliberate clamping as invalidity `[OPEN DECISION]`

- **File:** [research/config/grw_fitness.json:46](../../research/config/grw_fitness.json#L46)
- **Text:** `"rule": "clamp_up_frac <= 0.20"`
- **Problem:** the flag exists to catch a run that *accidentally* measured a fixed-lot
  strategy. Under deliberate half-potting, sizing at or near the lot floor is the intent,
  not a defect. `MEASURED`: all four runs on record carry `sizing_valid=0`.
- **Fix (if B2 accepted):** redefine against the *declared* bet fraction, or demote to
  reported-only.

### B4 — `CLAUDE.md` goal line predates the mandate `[P1]`

- **File:** [CLAUDE.md:11](../../CLAUDE.md#L11)
- **Text:** `Goal: a research process that survives out-of-sample, scaled up over time.`
- **Problem:** describes the research-process mandate. Does not mention the $20 deployment
  mandate. A fresh agent reads only this.
- **Fix:** state both, and state their relationship, in the file every session loads first.

### B5 — Scalp framing in MQL5 headers `[P1]`

- **File:** [mt5/Include/grw_system/grw_types.mqh](../../mt5/Include/grw_system/grw_types.mqh)
- **Text:** header comment `STOP-DISTANCE mode — the axis the $20 scalp mandate needs`;
  `GRW_SL_ABS_PIPS = 1, // ... THE SCALP MODE`
- **Fix:** correct the framing or mark the block superseded. Source comments are read as
  current by every agent that opens the file.

### B6 — Superseded changelog entry reads as live `[P1]`

- **File:** [research/config/grw_fitness.json:8](../../research/config/grw_fitness.json#L8)
- **Text:** `1.1.0 (2026-08-03) — min_trades 30 -> 500 for the SCALP mandate (task 294)`
- **Fix:** if B1/B2 land, supersede in place with the reason. Do not delete — the file's own
  change_policy makes the history the audit trail.

### B7 — `step1_ideas` GRW-001 name conflates idea with deployment `[P2]`

- `MEASURED`: `name = 'Compounding strategy factory ($20 JM live)'`, `status = 'ideation'`.
- The mechanism and the account it is deployed on are different objects. Splitting them is
  what lets the same mechanism be evaluated at a different stake without renaming the idea.

### B8 — Mandate doc lives outside the repo `[P1]`

- **Path:** `~/.claude/projects/c--Users-User-Desktop-baysix-technologies/memory/grw_20usd_scalp_mandate.md`
- **Problem:** referenced from the repo handover as `[[grw_20usd_scalp_mandate]]`, but the
  file is **not in the repo** — `MEASURED`: `memory/` contains only two handovers and
  `_handover_archive/`. It is outside version control, outside `handover_lint`, and still
  readable by Claude Code as authoritative.
- **Fix:** move into the repo or delete. A canonical mandate that git cannot see is the
  single most dangerous document in the system.

---

## Section C — Design errors in the specs

### C1 — OOS holdout leaks across batches `[P0]`

- **File:** [docs/reference/grw_autonomous_workflow.md](../../docs/reference/grw_autonomous_workflow.md) §2.2
- **Code:** [research/code/gates/grw.py](../../research/code/gates/grw.py) `record_oos()`
- **Problem:** `grw_batches.oos_spent` latches to 1 **per batch**. Nothing checks whether
  the same `oos_window` was already used by a previous batch. `register_batch()` validates
  only that IS ends before OOS starts.
- **Consequence:** batch 2 re-registers the same held-out window and gets a clean look at
  it. After N batches the holdout is fully burned and no code notices. The spec's own
  standard — *"Looking is spending it"* — is enforced within a batch and silently violated
  across them.
- **Fix:** a global look-counter keyed `(symbol, oos_start, oos_end)`, incremented on every
  `record_oos`, surfaced in the batch scoreboard. Plus a sealed vault window that no batch
  may register until G4.
- **Severity:** this is the guard the whole promotion ladder rests on.

### C2 — Risk fraction and stop distance modelled as independent axes `[P1]`

- **File:** [mt5/Experts/grw_system/grw_meta.mq5](../../mt5/Experts/grw_system/grw_meta.mq5)
  — `InpRiskFrac` (AXIS 4) and `InpSlMode`/`InpSlPips` (AXIS 1)
- **Problem:** at high leverage on a small account these are **one parameter**. Position
  size sets pip value and margin consumption simultaneously; the margin-call level then
  determines maximum adverse excursion. Beyond a size threshold the broker sets the stop,
  not `InpSlPips`.
- **Fix:** add the margin-level constraint to the sizing module so an infeasible
  (risk_frac, stop) pair is rejected at config time rather than discovered as a stop-out.
- **Note:** requires A1 resolved first — the constraint cannot be computed while the
  margin rate is contradictory.

### C3 — G1 paper wall blocks a codification-shaped idea `[P1]`

- **File:** [docs/reference/research_protocol.md:15](../../docs/reference/research_protocol.md#L15)
- **Text:** G1 requires `>=1 step2_papers row`, code-enforced by
  `pipeline._enforce_gate_walls`.
- **Problem:** an idea that codifies an operator's existing discretionary method has no
  originating paper. The wall blocks it at G1 regardless of merit.
- **Fix:** either an `idea_kind` that exempts the paper requirement (the protocol already
  varies gates by `idea_kind` — primitives are correctness-only `{1,2}`), or use the
  existing `allow_incomplete=True` waiver with a logged reason. Decide which, once.

### C4 — Loop A §1.3(2) logs a correct conclusion with wrong reasoning `[P2]`

- **File:** [docs/reference/grw_autonomous_workflow.md:70-74](../../docs/reference/grw_autonomous_workflow.md#L70-L74)
- **Text:** `Cent-account recommendation — drawdown objective silently substituted for
  growth objective`
- **Problem:** the conclusion (no cent account) stands on Syafiq's 2026-08-04 decision. The
  logged *reason* conflates two distinct arguments: a cent account changes lot
  **resolution**, which is a feasibility property, not a risk preference. Agents inherit
  the reasoning, not the conclusion.
- **Fix:** correct in place. Record that the rejection now rests on an operator decision,
  and separate the resolution argument from the objective-substitution argument so the
  latter stays a valid Loop A example.

### C5 — `claim_lint.py` remains unwritten `[P1]`

- **File:** [docs/reference/grw_autonomous_workflow.md](../../docs/reference/grw_autonomous_workflow.md) §5, task 291
- **Status:** unchanged. The doc's own standing order — *"The loop must not run
  autonomously until `claim_lint.py` exists"* — is still binding.
- **Evidence it is needed:** Section A6 of this document is exactly the failure class
  `claim_lint` was specified to catch, committed inside an audit whose purpose was
  catching it.

---

## Section D — Rules that exist but are not enforced

### D1 — `git_dirty` provenance rule is decorative `[P1]`

- **File:** [research/code/gates/grw.py](../../research/code/gates/grw.py) `_git()`
- **Text:** *"Provenance travels with every row — a DIRTY tree means the run is exploratory
  and cannot be cited as evidence."*
- **`MEASURED`:** all four `tester_runs` rows carry `git_dirty=1`. All four GRW artifact
  CSVs carry `git_dirty,1`. The numbers were cited as evidence anyway.
- **Fix:** pick one. Either `log_result` refuses a dirty-tree row (or flags it visibly in
  every downstream read), or the docstring drops the claim. A rule that is stated and not
  enforced is worse than no rule — it produces false confidence in the reader.

### D2 — Trade spine not populated `[P2]`

- **`MEASURED`:** `tester_runs` = 4 rows, `tester_trades` = **0 rows**.
- The per-trade ledger the artifacts contain (`grw_trades_*.csv` exist on disk) never
  reaches the DB. Forensics on any promoted config are impossible from `research.db` alone.

### D3 — README overstates the arbiter `[P3]`

- **File:** [README.md:41](../../README.md#L41)
- **Text:** *"the MetaTrader 5 Strategy Tester on real dukascopy ticks (2016→2026) is the
  ground-truth arbiter"*
- **Problem:** execution is on Just Markets. The yaml carries the caveat
  (`model_on_dukascopy_execute_on_jm`); the README states it unqualified, and since the
  2026-08-03 pivot the JM runs use `XAUUSD.s`, not Dukascopy.

---

## Section E — Housekeeping

- **Backlog triage.** `MEASURED`: 62 open tasks, of which ~48 are FOB P1s, while FOB sits
  at `gate_1` and BRC is parked at `gate_2`. The SessionStart hook surfaces all of them as
  live priority every session. Bulk-park the FOB P1s or accept that the brief is noise.
- **`PARKED` headers.** Any doc encoding the log-growth/Kelly framing needs a loud PARKED
  banner at the top if B2 is accepted. Agent confusion comes from stale documents that
  still read as current — not from directory layout. This is the cheap fix and it is the
  one that actually works.

---

## Suggested order

| Step | Items | Why first |
|---|---|---|
| 1 | **A1** | Every sizing and ruin number depends on it. One terminal command. |
| 2 | **A2, A3** | Wrong constants and false provenance, both mechanical fixes. |
| 3 | **C1** | The holdout guard the promotion ladder rests on. |
| 4 | **B2 decision** | Gates B1/B3/B6. Syafiq's call, not the agent's. |
| 5 | **B4, B5, B8, E** | Stale mandate text — cheap, and it stops the rework loop. |
| 6 | **D1, D2** | Enforce or delete. |
| 7 | **C2, C3, C5, A4, A5, D3** | The rest. |

---

## Changelog

| Date | Entry |
|---|---|
| 2026-08-04 | Created. Cowork audit session. A6 records an error made and corrected inside this same audit. |
