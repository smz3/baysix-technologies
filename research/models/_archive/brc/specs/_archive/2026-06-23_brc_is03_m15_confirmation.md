# BRC IS-03 — M15-BRC Confirmation Trigger (task #143)

**Status:** DESIGN SIMPLIFIED + LOCKED 2026-06-24 (strategy_log #62 supersedes #61, human_decision #85). Build pending.
**Idea:** BRC-001 · Gate 2 · **Control = IS-01** (blind H1 passive limit) · Real-tick model.
**Role:** zone-**SCREEN #1 (timing)** — does a LTF reaction confirm the H1 zone? Complements TPO (screen #2, location/quality). NOT a new strategy — a robustness filter on *which* H1 zones we trust.

## Thesis
Depth (T1/T2/T3, #132) and stop-width (buffer, #132) both **failed** — they only move
*where* we sit relative to invalidation. The depth sweep was a process-of-elimination:
it confirmed BRC zones are **mechanically sound** (price respects them) but that
**entry-depth is not the lever — selection is**. The loss concentrates in a *removable*
never-green / bulldozed cohort (~42% of trades, 85% of loss). IS-03 changes *which*
trades we take: require a **fresh M15 BRC** to confirm the H1 reaction — a straight
bulldoze through the H1 zone never forms a confirming M15, so it is auto-skipped.

## The 3 rules (simplified — was 9, see Audit below)

**Rule A — The gate (selection).** An H1 zone that has been **retested** (`t1` fires)
gets a **fresh, same-direction M15 BRC** that arms *after* the retest
(`M15.confirm_time > H1.t1_time`). **Spatial location ignored** — inside / outside /
overlapping the H1 band all qualify. Temporal freshness is the only gate.

**Rule B — The entry (reused IS-01 plan).** Trade the confirming M15 zone with the
standard entry plan: limit at **`M15.l1`**, stop at **`M15.l2 + InpSlBufferK·|M15.l1−M15.l2|`**
(k default 0.20). No new logic — `BrcBuildEntryPlan` pointed at the M15 zone.

**Rule C — Lifecycle (one-at-a-time).** Take the **first complete
(retested-H1 → fresh-M15) pair**. Hold **one at a time**; ignore further H1s and M15s
until it resolves (fills, or the H1 invalidates). **No supersede.**

## Scoring (pre-committed)
Report **R-tail distribution (min, p1, p5, count worse than −1R) + n + never-green %**
*first*; read $/trade *last* ([[er_denominator_illusion]] / result_id 6 lesson —
the −$0.413 looked survivable while E[R] was −1.26). Success = beat IS-01 on net edge
(E[R] **and** net $/trade) AND cut never-green %.

## Rule audit (9 → 3, 2026-06-24)
- R3 (bind / `parent_h1_key`) = bookkeeping, not a decision → folded into Rule A/C.
- R6 (same direction) = restatement of Rule A's gate → folded in.
- R4 + R5 (entry L1 / stop L2+buf) = the existing IS-01 entry plan → **Rule B (reused code)**.
- R7 + R8 + R9 (validity / supersede / first-come) → **Rule C**. R8 (supersede) **deleted**:
  it forced mid-flight churn in the state machine and tie-broke *opposite* to R9
  (newer-wins vs older-wins). Replaced by "first complete pair, one at a time."
- Net: only **Rule A** touches selection logic. Principle — an edge that needs 9 rules
  to appear is suspect; if it shows in 3 it is real. Strip first, let data earn rules back.

## Identity / binding (fields already in `tester_zones`)
- `zone_key` = `TF|DIR|epoch` — stable zone ID (e.g. `M15|BUY|1465849800`).
- `confirm_time` = BRC arm time ("fresh detection").
- `t1_time` = first touch (the "retest").
- `invalidation_time` = zone death (window end).
- New field to add: **`parent_h1_key`** on the entered M15 (M15→H1 lineage).

## Architecture
- **Emitter stays pristine** — already emits H1 + M15 zones with `zone_key` + `confirm_time`.
- **Trader-side build** (`brc_entry.mqh`): consume **both** H1 + M15 zone streams + run
  the (simplified) bind state-machine:
  - track live H1 zones that have been retested (`t1` fired, not yet invalidated),
  - when **no pair is active**, on the first new same-dir M15 BRC arm bind it to its
    retested H1 (Rule A) and place the entry (Rule B),
  - **one pair at a time** — while a pair is active, ignore further H1s and M15s,
  - drop the pending pair only when it resolves (fills, or the H1 invalidates). **No supersede.**

## Risk flags
- ⚠️ **Tight-stop / denominator trap (T3 lesson):** `M15.l2` stops are small → micro
  `r_unit` → fat −R tails on real ticks (killed T3, result_id 6). Mitigation = the
  pre-committed **R-tail-first scoring** above (read tails + n before $/trade). An
  `r_unit` floor or H1-stop variant is the A/B fallback if tails dominate (deferred).
- Sample-size: two-stage gate (H1 retest → fresh M15) + one-at-a-time will cut trade
  count — watch n.

## Success criterion
Beat IS-01 (blind H1 limit) on **net edge** (E[R] and net $/trade) AND reduce never-green %.
Frozen-then-OOS (#126) only after an IS variant shows edge.
