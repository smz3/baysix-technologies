# Handover — June 23, 2026 Morning3

## State
- **BRC-001 G2 unchanged: IS-01 baseline still NO edge** — net **−$0.33/trade** (result_id 2, full 8.5yr IS, ~1448 trades, no ruin at $10k). We will NOT freeze it; the reframe is the variant program.
- **Exit rules confirmed by code re-read (not memory).** Filled position exits two ways, first to hit: (1) **native SL = L2** zone-invalidation edge ([brc_entry.mqh:93](../mt5/Include/brc_system/brc_entry.mqh#L93)), defines 1R; broker-enforced. (2) **time exit = 6 closed H1 bars** after fill ([brc_trader.mq5:547](../mt5/Experts/brc_system/brc_trader.mq5#L547), `BrcTimeExitDue`/`BarsSince`). **No TP, no trail, no break-even** (IS-01 = `BRC_EXIT_TIME`, `InpTpMult=0`). Symmetric exit + cost = the ~spread bleed. Stop is intrabar (broker); time exit is bar-boundary.
- **Shipped + pushed this session (3, commit on master):**
- — **brc_trader zone visuals** — wired shared `CBrcVisual` (zones/swings/breaks) + new trade markers (entry arrow, gold fill-price label, SL/TP/entry level lines, exit X) under `InpVisualize`+`InpBrcShowTrades`. Own `BRC_TR_` object prefix. **Compiles 0 errors/0 warnings; Syafiq confirmed visuals render.** Needs tester **Visual Mode** (not Open-prices) to view.
- — **/handover Step 2.6 (BLOCKING)** — every handover must sync `log_tasks` (resolve done + open a task per `## Next`) via [backlog.py](../research/code/lineage/backlog.py). [handover.md](../.claude/commands/handover.md).
- — **Migration 034** — `log_tasks.priority` reordered to sit right after `status` (table + `open_backlog` view); filter-by-priority now works (37 rows, fk_ok).

## Next
1. **Task 134 (P1):** GET Syafiq's eyeballed **logic error** in [brc_trader.mq5](../mt5/Experts/brc_system/brc_trader.mq5) → fix → re-run IS-01 → compare to result_id 2. Do FIRST — may change the baseline before any sweep. (Base continuation = 1 falsified framing, not a kill; need ≥2.)
2. **Task 133 (P1, bumped):** exit-robustness sweep — max-hold 6/12/24 H1 bars + optional TP (+1R/+2R). The direct execution-logic lever; cheapest to sweep. Frozen→OOS, rank by $/trade + survival NOT E[R] ([[er_denominator_illusion]]).
3. **Task 136 (P2):** settle modelling fidelity (1-min OHLC for iteration vs real-tick final gate) BEFORE trusting any variant delta.

## Blockers
- None hard. OOS #126 stays blocked until an IS config is FROZEN — freeze comes from a variant that beats baseline, not from IS-01.
- Open methodology debate (now task 136): tick vs 1-min OHLC — unresolved, must settle before trusting deltas.
