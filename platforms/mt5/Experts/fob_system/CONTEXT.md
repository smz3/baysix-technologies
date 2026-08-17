# fob_system — FOB (First Opposite Breakout) single EA

One job: run FOB's three modes (EMIT / TRADE / STUDY) off one causal accumulator.
EMIT must stay a parameter-free, byte-identical oracle — the other two modes build
on it but never leak logic back into it.

## Inputs
- Working (this run): `InpMode` (EMIT/TRADE/STUDY) + a `.set` preset from
  [../../presets/fob_system/](../../presets/fob_system/).
- Reference: [../../Include/fob_system/](../../Include/fob_system/) (`fob_types` ·
  `fob_engine` · `fob_sequence` · `fob_lifecycle` · `fob_entry` · `fob_ledger` ·
  `fob_study` · `fob_csv` · `fob_visual*`) — FOB owns everything here; nothing is
  shared with `brc_system` or `grw_system` (CLAUDE.md rule 4a — namespace discipline).

## Process
1. Run `gen_version.py fob` (regenerates `fob_version.mqh` — auto-gen), then compile
   `fob_baysix.mq5`.
2. Run on **REAL TICKS (Model=4) only** — open-prices is banned, it roughly doubles
   the apparent edge.
3. **EMIT** (default): read-only oracle, writes the lifecycle CSV for Python/OOS.
   Never add strategy parameters or conditional logic to this mode.
4. **TRADE**: opens a market position per CF on the setup TF, SL beyond zone L2 by
   `k*band`, TP = `RR*risk`. Higher-TF alignment is awareness, never a gate.
5. **STUDY**: T-170 forward-excursion (MFE/MAE/terminal) per CF, no orders.
6. Ingest via `core/io/ingest_fob.py` / `ingest_fob_phase2.py` → `research.db`
   `fob_*` tables. Never hand-write those tables.

## Outputs
- `fob_baysix.ex5`, compile logs → this folder.
- EMIT lifecycle CSV → `research/data/fob_payload/run_<n>/` (Parquet-per-run, not
  written to `research.db` directly).

## Human check
Before editing, confirm which mode the change actually touches — an EMIT change
propagates into every OOS re-emit downstream, so accidentally scoping a TRADE/STUDY
fix onto EMIT is the one mistake this contract exists to catch. FOB's exits are
settled (H4 is tail-carried; early-exit rules truncate more right tail than they
save) — entry timing is the only lever open for change without an explicit go-ahead.
