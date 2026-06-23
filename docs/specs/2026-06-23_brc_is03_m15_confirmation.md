# BRC IS-03 — M15-BRC Confirmation Trigger (task #143)

**Status:** DESIGN LOCKED 2026-06-23 (strategy_log #61 PROPOSED, human_decision #85). Build pending.
**Idea:** BRC-001 · Gate 2 · **Control = IS-01** (blind H1 passive limit) · Real-tick model.

## Thesis
Depth (T1/T2/T3, #132) and stop-width (buffer, #132) both **failed** to rescue the
never-green / same-bar-SL cohort (~42% of trades, 85% of loss). Both only move *where*
we sit relative to invalidation. IS-03 changes *which* trades we take: require a
**fresh M15 BRC** to confirm the H1 reaction before entering — a straight bulldoze
through the H1 zone never forms a confirming M15, so it is auto-skipped.

## Gate logic (BUY example; SELL mirrored)
1. H1 BUY zone gets **retested** → `H1.t1_time` fires (price returns to H1 L1).
2. Search for an **M15 BUY** zone with **`M15.confirm_time > H1.t1_time`** ("fresh" —
   armed *after* the H1 retest). **Spatial location ignored** — inside / outside /
   overlapping the H1 band all qualify. Temporal freshness is the only gate.
3. **Bind** that M15 zone to the H1 zone (`parent_h1_key = H1.zone_key`).
4. **Entry:** limit at **`M15.l1`** (fills on pullback to the M15 near-edge).
5. **Stop:** **`M15.l2 + InpSlBufferK · |M15.l1 − M15.l2|`** (buffered, k default 0.20).

## Locked parameters (2026-06-23)
| # | Knob | Decision |
|---|------|----------|
| 1 | Direction | M15 **same direction** as H1 |
| 2 | Validity window | While H1 zone is **alive** (`H1.t1_time → H1.invalidation_time`); no separate timer |
| 3 | Override | A **newer same-direction H1** retest **supersedes** the stale pending M15 |
| 4 | Multiple M15s | **First fresh** one (first-come) |

## Identity / binding (fields already in `tester_zones`)
- `zone_key` = `TF|DIR|epoch` — stable zone ID (e.g. `M15|BUY|1465849800`).
- `confirm_time` = BRC arm time ("fresh detection").
- `t1_time` = first touch (the "retest").
- `invalidation_time` = zone death (window end).
- New field to add: **`parent_h1_key`** on the entered M15 (M15→H1 lineage).

## Architecture
- **Emitter stays pristine** — already emits H1 + M15 zones with `zone_key` + `confirm_time`.
- **Trader-side build** (`brc_entry.mqh`): consume **both** H1 + M15 zone streams + run
  the bind state-machine:
  - track live H1 zones that have been retested (`t1` fired, not yet invalidated),
  - on each new M15 BRC arm, bind to the oldest unfilled same-dir retested H1 (first-come),
  - place limit at `M15.l1`, stop at `M15.l2 + buffer`,
  - drop the pending M15 if a newer same-dir H1 supersedes or the H1 invalidates.

## Risk flags
- ⚠️ **Tight-stop / denominator trap (T3 lesson):** `M15.l2` stops are small → micro
  `r_unit` → fat −R tails on real ticks (killed T3, result_id 6). Report the **R-tail
  distribution**, not just $/trade. Consider an `r_unit` floor if tails dominate.
- Sample-size: two-stage gate (H1 retest → fresh M15) will cut trade count — watch n.

## Success criterion
Beat IS-01 (blind H1 limit) on **net edge** (E[R] and net $/trade) AND reduce never-green %.
Frozen-then-OOS (#126) only after an IS variant shows edge.
