# grw_system — GRW-001 barrier-mandate meta-EA (MQL5)

One job: run the pre-registered barrier search (4 axes × fitness) for the $20
non-reloadable GRW mandate. This folder never decides the objective — it only
scores against it.

## Inputs
- Working (this run): a `.set` preset from [../../presets/grw_system/](../../presets/grw_system/)
  — one point in the 4-axis space (InpEntryType / InpFilterMask / InpExitType / InpRiskFrac).
- Reference (every run): [research/config/grw_fitness.json](../../../../research/config/grw_fitness.json)
  — the versioned barrier objective (stake/target/floor). A version bump = a new trial
  family; never edit it from in here.
- Reference (every run): `docs/private/mandate.md` (gitignored) — account size/target.
  Read before any sizing change.
- Sibling code, not duplicated here: [../../Include/grw_system/](../../Include/grw_system/)
  (`grw_types`/`grw_sizing`/`grw_entry`/`grw_filter`/`grw_exit`/`grw_trade`/`grw_fitness`/`grw_ledger`)
  and [../../Scripts/grw_system/](../../Scripts/grw_system/).

## Process
1. Run `gen_version.py grw` (regenerates `grw_version.mqh` — auto-gen, never hand-edited),
   then compile `grw_meta.mq5` via the MetaEditor CLI.
2. Run the MT5 Strategy Tester on **REAL TICKS (Model=4) only** — open-prices is banned
   for this system.
3. `OnTester()` scores the barrier outcome per `grw_fitness.json` (1.0 target-first /
   0.0 floor-first / UNRANKABLE censored). The `.mqh` files implement the objective;
   they don't define it — that lives one level up, in `research/config/`.
4. On barrier resolution the EA flattens the book and stops trading for the rest of
   the window. One pass = one Bernoulli draw — never averaged inside a pass.
5. Ingest results via `research/code/io/ingest_grw.py` → `research.db` (`grw_passes`).
   Never hand-write that table.

## Outputs
- `compile.log`, `grw_meta.ex5` → this folder (build artifacts).
- Tester CSV/report → `platforms/mt5/tester/` → ingested to `grw_passes` via `ingest_grw.py`.

## Human check
Before touching this folder, confirm which `grw_fitness.json` version is live — a
config scored under one version can't be pooled with another. Never add a variant EA
file here; extend an enum branch in the existing one (ONE FILE, forever — duplicating
it breaks the tester sweep and the git lineage in one move).
