# research/models/fob/ — FOB exploratory screens (not a pipeline)

One job: run one-off statistical screens against a specific EMIT run's payload to
answer one question, then log the result. This folder is a workbench, not a system
a loop should call unattended — each script is independent and disposable.

## Inputs
- Working (this run): `research/data/fob_payload/run_<n>/{zones,events,cycles}.parquet`
  — the run is picked explicitly (an `R_DIR` constant at the top of each script).
  Never assume "latest run" without checking.
- Reference: [excursion/](excursion/) CSVs — task-202 excursion outputs, per
  version/timeframe/cf.

## Process
1. Each script (`room_r_screen.py`, [alignment/](alignment/)`*.py`) guards against a
   specific contamination — read its own module docstring before trusting its output
   (e.g. `room_r_screen` v2 fixes `confirm_time` being future-conditioned).
2. Causal filters (e.g. `vr_time < bar_time`) are re-derived per script, not shared —
   confirm the script you're reading actually applies one before citing its number.
3. A finding gets logged via `research/code/gates/pipeline.py`'s `log_result` or
   `research/code/lineage/strategy_log.py`'s `log_change` — a `print()` statement is
   scratch work, not evidence, until it has a `result_id`.

## Outputs
- Printed findings → logged to `research.db` (as a `result_id`). This folder does not
  accumulate output files of its own beyond the `excursion/` CSVs.

## Human check
Before citing a number from here, confirm it has a `result_id` — an unlogged print
in this folder is a scratch calculation. Before running a script, confirm `R_DIR`
points at the run you think it does, not whatever was last edited into the constant.
