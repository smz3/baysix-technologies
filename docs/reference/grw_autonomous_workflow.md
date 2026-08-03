# GRW-001 Autonomous Workflow

The operating loop for the compounding-strategy factory, and the self-correction
machinery that lets it run without Syafiq in the loop.

Same convention as [RESEARCH_CODE_PROTOCOL.md](../../research/RESEARCH_CODE_PROTOCOL.md):
**every rule here exists because a real failure happened.** No rule is hypothetical.
The audit that produced them is in the Changelog at the bottom.

---

## 0. What this document is for

Autonomy fails in exactly one way: **the agent asserts something false, logs it,
and then builds on it.** Errors don't stay local — they compound into the next
night's work. Everything below exists to make that specific failure expensive and
detectable rather than silent.

There are three loops:

| Loop | Question it answers | Runs |
|---|---|---|
| **A — Claim Verification** | Is what the agent just said *true*? | Every claim, always |
| **B — Promotion Ladder** | Is what the factory just found *real*? | Every batch |
| **C — Session Driver** | What is the ONE next legal action? | Every cycle, **supervised** |

**Autonomy here means "Claude sequences the work without being told each step."
It does NOT mean unattended.** CLAUDE.md rule 12 stands: runs go in a visible
PowerShell window, never backgrounded, because Syafiq needs live output. There is
no cron, no overnight batch, no nightly loop.

Loop A guards the agent. Loop B guards the research. Loop C sequences both.

---

## 1. LOOP A — Claim Verification

### 1.1 The origin failure

Audit of the 2026-08-03 planning session: **four substantive errors in six turns,
zero self-caught.** Three were asserted from memory. One was caught — and it was
caught *only* because a query was run instead of recalled.

That is the whole mechanism. Recall produces errors; execution catches them.

### 1.2 The rule

**Every claim carries a provenance class. `RECALLED` is banned.**

| Class | Means | Must cite |
|---|---|---|
| `MEASURED` | Output of a command run this session | the command |
| `DERIVED` | Arithmetic over MEASURED values | the formula, inline |
| `CITED` | Read from a file or URL this session | path or URL |
| `ASSUMED` | Not verified — stated deliberately | **what would falsify it** |
| ~~`RECALLED`~~ | From memory/habit/another project | **BANNED** |

Applies to: replies to Syafiq, `step4_results` rows, handover notes, commit
messages, and any input to a promotion decision.

### 1.3 The four classes of error this catches

Each maps to one of the audited failures:

1. **Uncomputed quantitative claim** — "$50 risks 4–10% per trade, no strategy
   survives." Numbers stated without running them.
   → *Guard:* a number that is not `MEASURED` or `DERIVED` does not ship.

2. **Silently-swapped objective function** — recommending a cent account, which
   optimizes drawdown when the stated objective was growth.
   → *Guard:* the objective is a **declared, versioned artifact**
   (`grw_fitness.json`). Every recommendation names which objective it serves.
   A recommendation that cannot name one is not a recommendation.

3. **Component imported from another context** — ArcticDB and the dual compiler,
   carried over from FOB where they earned their place.
   → *Guard:* every proposed component declares `what_it_buys` **for this
   objective**, plus the simpler alternative that was rejected and why.
   Cross-system imports are `ASSUMED` until re-justified here.

4. **Unverified repo/schema state** — asserting `is_runs` and `trial_family_id`
   existed. They did not.
   → *Guard:* fully automatable, and therefore automated. See 1.4.

### 1.4 Executable guard — `claim_lint.py`

Extends the proven [handover_lint.py](../../research/code/infra/handover_lint.py)
pattern (handover numbers must cite a `result_id` in-section, enforced pre-commit).

Checks, in order of cheapness:

- **Schema claims** — any `table.column` named in the text is verified against
  live `PRAGMA table_info`. Unknown table or column → **hard fail**.
- **Path claims** — every markdown file link resolves on disk. → **hard fail**.
- **Bare numerals** in a findings section with no `result_id`, run id, or command
  citation within the same section → **hard fail**.
- **Banned hedge-free assertions** — "always", "never survives", "impossible",
  "no strategy" without an adjacent `DERIVED` formula → **warn**.

Wired at PreToolUse alongside
[protocol_guard.py](../../.claude/hooks/scripts/protocol_guard.py), which already
hard-blocks raw `sqlite3` writes. Same exit-2 deny convention.

### 1.5 The standing order

> **Check before you claim. Compute before you conclude. When the cost of
> checking is one command, there is no acceptable reason to recall instead.**

---

## 2. LOOP B — Promotion Ladder

### 2.1 The origin failure

A genetic optimizer *will* find noise. Run 4,800 passes and the top of the
distribution is the luckiest configuration, not the best one. Autonomously, that
false winner gets logged as a result and becomes next night's foundation.

The fix is not better statistics after the fact. It is **pre-registration**: the
rule that decides promotion is written *before* the run and the run cannot
change it.

### 2.2 Pre-registration

Before any batch, write `data/grw_runs/<batch_id>/prereg.json`, hash it, commit it:

```json
{
  "batch_id": "grw-2026-08-04-001",
  "hypothesis": "one sentence, falsifiable",
  "fitness": "grw_fitness.json@<sha>",
  "is_window":  ["2016-01-01", "2023-12-31"],
  "oos_window": ["2024-01-01", "2026-06-30"],
  "n_trials_budget": 5000,
  "promote_if": "oos_growth >= 0.5 * is_growth AND oos_n_trades >= 100",
  "kill_if":    "oos_growth <= 0",
  "prereg_sha": "<sha256 of this file minus this field>"
}
```

**The OOS window is never passed to the optimizer.** Not as a filter, not as a
sanity check, not "just to look". Looking is spending it.

Changing a threshold does not edit the file. It opens a **new batch** with a new
`batch_id`. The old one stays on the record, including its failure. This is what
makes the trial count honest.

### 2.3 The ladder

| Stage | Action | Writes to |
|---|---|---|
| **S0 GENERATE** | Optimizer runs N passes on IS window only | `grw_passes` (raw material, *not* results) |
| **S1 SCREEN** | Rank by fitness. Record `n_trials` = passes actually run | `grw_passes.rank` |
| **S2 HOLDOUT** | Top-K re-run on the untouched OOS window | `grw_passes.oos_*` |
| **S3 ADJUDICATE** | Apply `promote_if` / `kill_if` **mechanically** | verdict column |
| **S4 LOG** | Survivors → `step4_results`. Failures → FALSIFIED | `step4_results`, `log_strategy` |
| **S5 RECOMPUTE** | `protocol.next_step()` decides what happens next | — |

Rules:

- **Nothing becomes a `step4_results` row before S3.** Passes are raw material.
  Conflating the two is how a trial count of 5,000 gets reported as one result.
- **S3 is mechanical.** The adjudicator reads `prereg.json` and applies it. The
  agent does not get a vote. If the agent disagrees with a verdict, the remedy is
  a new pre-registered batch, never an override.
- **Failures are logged, not discarded.** A FALSIFIED row is an asset — it feeds
  the ≥2-falsified requirement in CLAUDE.md rule 8b and it keeps the denominator
  honest.
- **`n_trials` travels with every result.** A growth rate without its trial count
  is not a finding.

### 2.4 The self-correction property

Each cycle can invalidate the previous one, because:

- OOS is spent per batch and cannot be reused to rescue a dead idea.
- Promotion thresholds are fixed in advance, so a disappointing result cannot be
  re-described as a good one.
- Trial counts accumulate across batches within a `trial_family_id`, so the bar
  rises as the search widens.

This is the systematic part. Not "the agent is careful" — **the agent is unable
to grade its own homework.**

---

## 3. LOOP C — Session Driver

### 3.0 Scale: small-n, hypothesis-driven — NOT a genetic sweep

One 8-year real-tick backtest is **5–8 minutes** (`CITED`: Syafiq, 2026-08-03).
A batch is therefore **10–20 pre-registered configs — about 1–2 hours, supervised.**

Rejected: the ~5,000-pass/night genetic sweep proposed earlier. It manufactured a
multiplicity problem in order to justify machinery to defend against it. Small-n
does not make pre-registration less important — it makes it **cheaper**, and you
can still fool yourself with 20 trials. The trial counter stays; the brute force
goes.

**The generator is Claude, mechanism-first** (set 2026-08-03 — Syafiq explicitly
declined to supply hypotheses: "let you loose... figure shit out for the
mission"). This is not a licence to sweep blindly. Every pre-registered config
must state **why the edge should exist** before it runs — a microstructure or
behavioural mechanism, in one sentence. A candidate with no mechanism is a
lottery ticket and does not get a slot in the batch. Mechanism-first is what
keeps small-n honest once the human hypothesis is removed from the loop: it makes
a failure *informative* rather than merely disappointing.

### 3.1 Built on what already exists

`protocol.next_step(idea_id)` already returns the ONE next legal action from DB
state (`next`, `why`, `warnings`), surfaced by
[idea_cli.py](../../research/code/gates/idea_cli.py) `next`. That is already a
state machine. **The autonomous loop is that state machine on a timer** — not a
parallel system.

### 3.2 The cycle

```
  preflight  →  next_step()  →  execute  →  log  →  adjudicate  →  brief
      ↑                                                              │
      └──────────────────────────────────────────────────────────────┘
```

1. **PREFLIGHT** — cheap assertions, abort loudly on any failure:
   - `research.db` reachable; `grw_*` schema matches expectation
   - JM terminal reachable; `account_info().leverage` read fresh (never assumed —
     it is tiered by equity and *changes as the account grows*)
   - symbol tick history covers the pre-registered IS window
   - no `terminal64.exe` already running (headless tester will not fire otherwise)
   - git clean or `git_dirty` recorded on every row
2. **NEXT** — `protocol.next_step()`. If it returns a human-only action, stop and
   brief. Do not improvise around a wall.
3. **EXECUTE** — launch via [run_tracked.py](../../research/code/infra/run_tracked.py).
   Wait on the **DONE-sentinel's existence**, never on output mtime.
4. **LOG** — via the code layer only (`pipeline.log_result`,
   `strategy_log.log_change`, `backlog`). Raw `sqlite3` is hook-blocked.
5. **ADJUDICATE** — S3 above, mechanical.
6. **BRIEF** — write the morning report. Every number carries its provenance class.

### 3.3 Hard stops — the loop halts and waits for a human

Autonomy is bounded. The loop stops on:

- any preflight assertion failure
- `next_step()` returning a `kill_idea` (rule 8b needs ≥2 falsified — never automatic)
- promotion to **G4 / live** — nothing touches the live account unattended
- adjudicator disagreeing with the agent's expectation (log both, stop, brief)
- three consecutive batches with no promotion — the search space is wrong, and
  that is a design question, not a compute question

### 3.4 What is never automated

- Deploying to the live account
- Killing an idea
- Changing the fitness function
- Editing a `prereg.json`
- Widening the trial budget after seeing results

---

## 4. Storage

Decided 2026-08-03 — **no separate database.**

- **`research.db`** — the ledger. `step1_ideas` / `step3_gates` / `step4_results`,
  the shared tester spine (`tester_runs` / `tester_trades` / `tester_run_summary`),
  plus new `grw_passes`. Currently 0.5 MB; ~1.25 MB/night of passes is trivial.
- **`data/grw_runs/*.parquet`** — full trade lists, **survivors only**. Mirrors the
  [fob_payload.py](../../research/code/io/fob_payload.py) pattern that took FOB
  from 598 MB to 0.4 MB.
- **`execution.db`** — untouched; the live-deployment twin if GRW ever reaches G4.

Rationale: the 2-DB design is a logged decision, `tester_runs` already carries
`leverage` / `initial_deposit` / `params` / `run_role` / `git_sha`, and namespace
isolation is achieved by `grw_*` prefixes per CLAUDE.md rule 4a — not by a new file.

---

## 5. Known gaps (blocking full autonomy)

Verified absent 2026-08-03, `MEASURED` by `PRAGMA table_info` + `sqlite_master`:

- `is_runs` table does not exist, though CLAUDE.md references it
- no `trial_family_id` column anywhere — the multiplicity ledger is unbuilt
- `tester_runs` DDL drift between [db_init.py](../../research/code/infra/db_init.py)
  and `tester.py` (open task 287) — a rebuild from stale DDL silently drops `run_role`
- `claim_lint.py` not written
- `prereg.json` schema + adjudicator not written

**The loop must not run autonomously until the trial-family key and the
adjudicator exist.** Without them Loop B has no teeth and the factory grades its
own homework.

---

## Changelog

| Date | Rule | Failure that caused it |
|---|---|---|
| 2026-08-03 | Loop A, all | 4 substantive errors in 6 turns, 0 self-caught |
| 2026-08-03 | A §1.3(1) | "$50 risks 4–10%/trade, no strategy survives" — intraday stops applied to a scalping mandate, never computed |
| 2026-08-03 | A §1.3(2) | Cent-account recommendation — drawdown objective silently substituted for growth objective |
| 2026-08-03 | A §1.3(3) | ArcticDB + dual compiler proposed — imported from FOB, earned nothing here |
| 2026-08-03 | A §1.3(4) | Asserted `is_runs` / `trial_family_id` existed; both absent |
| 2026-08-03 | B, all | Genetic optimizer over ~5k passes/night will surface noise as the top rank |
| 2026-08-03 | C §3.2(1) | JM leverage is equity-tiered and falls as the account grows — must be re-read, never cached |
