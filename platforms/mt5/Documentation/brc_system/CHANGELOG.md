# BRC System — Changelog

Versions are git-sha + `.set` + `BRC_VERSION`, not file copies. Each entry links the
research lineage (`strategy_log`) where relevant. See CLAUDE.md → MT5 / EA Workflow.

## brc_trader v1.0.0 — IS-01 (2026-06-23)
- **New: `brc_trader.mq5`** — strategy EA, sibling of the emitter. Reuses the emitter's
  detection pipeline (swing→break→zone→advance) on a single TF; trades via swappable modules.
- **New modules:**
  - `brc_entry.mqh` — `BRC_ENTRY_TOUCH {L1,MID,L2}` × `BRC_ENTRY_SIDE {CONTINUATION,FADE}`;
    builds a level-based limit-entry plan (SL = invalidation L2, R from actual entry). Fade unspecified (task 131).
  - `brc_exit.mqh` — `BRC_EXIT_MODE {TIME,TIME_TP}` + `max_hold` + `tp_mult`; native SL, clock exit, optional TP.
  - `brc_sizing.mqh` — `BRC_SIZE_MODE {FIXED_LOT,FIXED_FRAC}`; rounds DOWN to broker step, floors to min-lot.
- **New: `brc_version.mqh`** (auto-gen via `research/code/infra/gen_brc_version.py`) — git sha/branch/dirty/build,
  printed on init. DIRTY-tree runs = exploratory, not reproducible.
- **IS-01 atom** (strategy_log #55, PROPOSED): H1 · enter T1=L1 first-retest continuation ·
  SL=invalidation(L2) · close at 6 H1 bars · no TP · one position · fixed 0.01 lot.
  Preset: `mt5/presets/brc_system/brc_trader-v1.0.0-IS01.set`.
- ⚠️ COMPILE/RUN status tracked in the handover; verify fills under Open-prices before trusting any number.
