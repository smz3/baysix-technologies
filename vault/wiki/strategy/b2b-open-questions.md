---
type: wiki
domain: strategy
status: draft
tags:
  - b2b
  - wip
  - decisions
related:
  - "[[b2b-invalidation]]"
  - "[[b2b-overview]]"
  - "[[mt5-ea-architecture]]"
source_files:
  - "workspace/sigma-mt5/Documentation/B2B_CLUSTER_FIX_PLAN.md"
  - "workspace/sigma-mt5/Documentation/B2B_STRATEGY_DECISIONS.md"
last_updated: 2026-04-14
maintained_by: ai
ai_summary: "Three open B2B questions: OQ-001 Cluster detection edge case (3 fix options A/B/C — awaiting decision), OQ-002 Cascade invalidation not yet implemented in V5.0, OQ-003 SAMTC slippage impact on OOS performance (HYP-001)."
---

# B2B Open Questions

> Decisions made here should be propagated to the relevant wiki page via `/vault-ingest`. Mark as **RESOLVED** with date when closed.

---

## OQ-001 — Cluster Detection Edge Case

**Status:** Open — awaiting CIO/Researcher decision  
**Priority:** High — affects zone deduplication accuracy in clustered swing areas  
**Source:** `workspace/sigma-mt5/Documentation/B2B_CLUSTER_FIX_PLAN.md`

### The Problem

In clustered breakout scenarios (3+ swing highs/lows forming within ~10 bars), the B2B detector picks an older L1 or L2 than expected. The root cause is in `B2BDetector.mqh` lines 470–482:

```mql5
// Current logic: selects the "best price" 1st breakout, not the nearest in time
if(direction == DIRECTION_BULLISH)
  is_better = (candidate_1st.broken_swing_price > best_1st.broken_swing_price);  // Prefers HIGHER
else
  is_better = (candidate_1st.broken_swing_price < best_1st.broken_swing_price);  // Prefers LOWER
```

**Example scenario:**
```
Time:  T1(SH_A=100) → T2(SH_B=102) → T3(SH_C=101) → T4(BO_1 breaks SH_B) → T5(BO_2)
Current: BO_2 pairs with BO_1 (broke 102 = highest) even if a closer, more recent pair exists
Expected: BO_2 should pair with the most recent valid breakout (temporal proximity)
```

**L2 also affected:** L2 is searched between `2nd_swing_time → breakout_bar_time`. If the 2nd breakout picks an old swing, L2 comes from an old time period too.

### The Three Fix Options

**Option A — Temporal Proximity (Recommended)**

Change the "is_better" selection from price-based to time-based:
```diff
-is_better = (candidate_1st.broken_swing_price > best_1st.broken_swing_price)
+is_closer_in_time = (candidate_1st.breakout_bar_time > best_1st.breakout_bar_time)
+if(is_closer_in_time): best_1st = candidate_1st
```
- Pro: Always pairs with the most recent valid breakout. Intuitive. Reduces cluster confusion.
- Con: May not always get the "optimal" entry by price

**Option B — Keep All Valid Pairs (Let Dedup Filter)**

Create a B2B zone for EVERY valid pair, then rely on `AddZone()` deduplication:
```diff
-// Only keep best_1st
+// Add every valid pair to the array
+first_bo_arr[pairs_found] = candidate_1st
+second_bo_arr[pairs_found] = candidate_2nd
+pairs_found++
```
- Pro: Never misses a valid B2B. No selection bias.
- Con: Many more zones initially (performance impact). Needs more aggressive dedup thresholds.

**Option C — Hybrid: Nearest + Price Filter**

Select nearest in time, but reject if price is not within X% of the "optimal" price candidate.

### Secondary Decision: L2 Window Extension

**Current:** L2 searched between `2nd_swing_time → breakout_bar_time`  
**Proposed:** L2 searched between `1st_swing_time → breakout_bar_time` (wider window, captures more context)

### Verification Plan

1. Find chart section with clustered swing highs/lows (3+ within 10 bars)
2. Enable `InpLog_B2B = true` in TradingParameters
3. Compare logged B2B pairs with visual breakouts
4. Verify L1 and L2 match the expected swings
5. Compare zone count before/after the fix

### Decision Needed

- [ ] Which option: **A** (temporal), **B** (all pairs), or **C** (hybrid)?
- [ ] Extend L2 window: **Yes** or **No**?
- [ ] Add minimum zone width filter (reject if `|L1 - L2| < X points`)? **Yes** or **No**?

---

## OQ-002 — Cascade Invalidation Not Implemented

**Status:** Open — known implementation gap in V5.0  
**Priority:** Medium — ghost child zones may appear after parent invalidation  
**Source:** `workspace/sigma-mt5/Documentation/B2B_STRATEGY_DECISIONS.md` — Decision #3

### The Problem

The decision is clear (see [[b2b-invalidation]]): when a parent zone invalidates, all child zones within it auto-invalidate simultaneously.

**Current V5.0 behavior:** This cascade is NOT implemented. Child zones may remain ACTIVE on chart after their parent zone is invalidated. A D1 zone could close beyond L2, but its H4 and M5 children remain visible as valid trade zones.

**Risk:** Traders may see and act on orphaned child zones that no longer have structural support.

### Implementation Target

`CB2BZoneStatus::UpdateZoneStatus()` in `B2BZoneStatus.mqh`:

When a zone transitions to INVALIDATED:
1. Query `B2BZoneManager` for all zones with `parent_id == this_zone.id`
2. For each child zone: set status = INVALIDATED, fire `ZONE_CHANGE_STRUCTURAL` event
3. Log cascade event to `QuantLogger`

**Decision:** Implementation agreed — just needs to be built. No decision required, just scheduling.

---

## OQ-003 — SAMTC Slippage Impact on OOS Performance

**Status:** Open research question — production gate blocker  
**Priority:** High — must resolve before Test 13A gets CIO approval  
**Tracked as:** HYP-001 on the [[hypothesis-board]] (stub — create when building hypothesis-board page)

### The Question

Test 13A OOS shows Sharpe 1.16 / Payoff 1.65 / Skew 3.43 using clean backtest fills.

Does this edge hold when realistic slippage is applied? The concern:
- SAMTC entries are at L1 (zone boundary) — price often moves quickly at this level
- Clean fills assume instant execution at exact L1 price
- Live trading on Binance Futures has ~0.5–2bp slippage on market orders

### What's Needed

1. **Slippage sensitivity test:** Re-run 13A backtest with simulated slippage of 0bp, 5bp, 10bp, 20bp
2. **Break-even slippage:** Find the slippage level at which Sharpe drops below 1.0
3. **Limit order alternative:** Test entering via limit orders at L1 rather than market — eliminates slippage but reduces fill rate

### Resolution Path

Run slippage sensitivity in `scripts/run_phase_4_simulation.py` with slippage parameter sweep. Report Sharpe at each level. If Sharpe ≥ 1.0 at 10bp, edge is confirmed robust.

---

## Resolved Questions (Archive)

| ID | Question | Resolution | Date |
|----|---------|------------|------|
| OQ-004 | L1 selection direction (BUY = highest or lowest?) | Corrected: BUY = HIGHEST L1, SELL = LOWEST L1 | Dec 18, 2025 |
| OQ-005 | M15/M30 layer placement (Sniper or Control?) | CONTROL layer. Sniper = M5/M1 only | Dec 18, 2025 |
| OQ-006 | T3 wick to L2 — invalidation or not? | NOT invalidation. T3 = intelligence. Close beyond L2 = invalidation | Dec 18, 2025 |
| OQ-007 | Zone aging — do zones expire? | No. Old zones are 100% valid regardless of age | Dec 18, 2025 |
| OQ-008 | Opposite direction child zones — show or hide? | Show both. Let market decide. No trap labels | Dec 18, 2025 |

---

## Related Pages

- [[b2b-invalidation]] — Cascade rules (OQ-002 background)
- [[b2b-overview]] — L1 selection rules (OQ-004 context)
- [[mt5-ea-architecture]] — Cluster fix implementation target (OQ-001)
- [[backtest-results]] — Test 13A (OQ-003 context)
