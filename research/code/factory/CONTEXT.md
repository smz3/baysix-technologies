# factory/ — the venue-agnostic autonomous strategy factory (shared, all platforms)

One job: run one pre-registered barrier-search cycle — spec → compile → test →
adjudicate → ledger — through a Venue adapter.

Lifted out of `platforms/ninjatrader/` on 2026-08-16 (Syafiq's call, task 364 call 1).
It never contained an NT8 detail: a venue is six verbs, and the search, the objective,
the pre-registration and the adjudication never know which one is running. Living under
one platform meant MT5 would have had to re-implement pre-registration, the trial budget
and the one-way holdout, and the second copy is the one that drifts.

## The two-layer split (task 360, extended to every platform 2026-08-16)

| `platforms/<platform>/db/factory.db` — the workshop | `db/baysix.db` — the notebook |
|---|---|
| `batches`, `candidates` | `step1_ideas`, `step2_papers` |
| `sweep_runs`, `trades`, `agreements` | `step3_gates`, `step4_results` |
| `sweep_verdicts`, `sweep_claims` | `runs`, `log_tasks`, `log_agent`, `log_strategy` |
| every candidate tried, including the 50,000 that lost | the ones that earned a verdict |

Two rules, both from task 360:
1. **Promotion is one-way.** A row goes up only once it has earned a verdict. Nothing
   flows back down, and `step1_ideas`–`step4_results` are NEVER copied into a factory.db —
   `db_path.assert_not_spine()` refuses a file that has grown one.
2. **A platform sends its trial COUNT up, not its trial ROWS.** A 50k sweep costs the
   spine one number. Two ledgers holding two answers to "how much have we tested" is
   what silently lowers the bar for calling something real.

## Why one file per platform, not one shared factory.db
SQLite write-locks the whole file. The MT5 loop and the NT8 loop run at the same time —
one file means they queue behind each other for hours. Nothing in this layer ever joins
across platforms, so the split costs nothing. See [db_path.py](db_path.py).

## Inputs
- Working (this run): a `StrategySpec` JSON ([spec.py](spec.py)) — the four axes
  (entry / filters / exit / risk), `mechanism` field mandatory.
- Reference (every run): a registered `prereg.json` ([prereg.py](prereg.py)) — refuses
  to overwrite an existing one; a changed threshold opens a new batch id instead.
- A `Venue` adapter implementing the six verbs ([venue.py](venue.py)): `write_source`
  / `compile` / `run_test` / `read_fitness` / `read_results` / `selfcheck`.
- Objective configs live in [research/config/objective/](../../config/objective/).

## Process
1. `venue.selfcheck()` proves the adapter against a KNOWN strategy/result before any
   real run. NT8's headless backtest switches are undocumented and unsupported by the
   vendor — never trust them silently.
2. [objective.py](objective.py) scores the run as one Bernoulli draw of a barrier
   problem (`barrier_fixed`, ported from the MT5 GRW objective, or `barrier_prop`
   where the floor moves) — never blended with anything else.
3. [adjudicate.py](adjudicate.py) applies the pre-registered rule via AST-vetted
   parsing, not `eval()`. An unknown name raises; it never fails open to False.
4. [provenance.py](provenance.py) tags every reported number MEASURED / DERIVED /
   CITED / ASSUMED. RECALLED is banned.
5. [ledger.py](ledger.py) writes the verdict to that platform's `factory.db` — one DDL
   home in this module; never duplicate the schema elsewhere.

## Opening a ledger
```python
Ledger("mt5")          # platforms/mt5/db/factory.db
Ledger("ninjatrader")  # platforms/ninjatrader/db/factory.db
Ledger(path=tmp)       # tests ONLY — a hand-built path is how a worktree
                       # ends up counting its trials in a second file
```

## Human check
Before running a new batch, confirm a `prereg.json` for this threshold doesn't already
exist — if it does, that's the rule working: open a new batch, don't move the old bar.
If `venue.selfcheck()` fails, stop; don't fall back to reading a raw NT8 log by hand
to "confirm it's probably fine."

## Not built yet
- **No Venue adapter exists for either platform.** `venue.py` is the contract only.
  MT5 and NT8 each still need one before a batch can run.
- **The promotion function is unspecified** (task 364 call 2). Nothing yet carries a
  verdict from a factory.db up to `step4_results`, and nothing yet stamps the trial
  count on the spine's `runs.n_trials` (task 365).
