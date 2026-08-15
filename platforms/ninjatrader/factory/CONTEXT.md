# factory/ — Baysix venue-agnostic autonomous strategy factory (NT8/futures, Phase 0)

One job: run one pre-registered barrier-search cycle — spec → compile → test →
adjudicate → ledger — through a Venue adapter, without ever writing into `research.db`.
Futures is a separate namespace from the MT5 $20 mission (CLAUDE.md); this factory's
ledger is its own DB.

## Inputs
- Working (this run): a `StrategySpec` JSON ([spec.py](spec.py)) — the four axes
  (entry / filters / exit / risk), `mechanism` field mandatory.
- Reference (every run): a registered `prereg.json` ([prereg.py](prereg.py)) — refuses
  to overwrite an existing one; a changed threshold opens a new batch id instead.
- A `Venue` adapter implementing the six verbs ([venue.py](venue.py)): `write_source`
  / `compile` / `run_test` / `read_fitness` / `read_results` / `selfcheck`.

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
5. [ledger.py](ledger.py) writes the verdict to `factory.db` — one DDL home in this
   module; never duplicate the schema elsewhere.

## Outputs
- `factory.db` rows only. Never `research.db` — separate namespace, same discipline
  as the MT5/futures split in CLAUDE.md.

## Human check
Before running a new batch, confirm a `prereg.json` for this threshold doesn't already
exist — if it does, that's the rule working: open a new batch, don't move the old bar.
If `venue.selfcheck()` fails, stop; don't fall back to reading a raw NT8 log by hand
to "confirm it's probably fine."
