# Handover — June 17, 2026 Afternoon

## State
- **BRC-001 at Gate 1 passed; Gate 2 NOT yet opened/passed** (`idea_cli next BRC-001` → OPEN Gate 2). Detector (Path B) + accuracy gates built last session (tasks 111/112/113). No edge measured yet → no result_id applies anywhere in this handover.
- **Task 115 DONE (code), Gate-2 eyeball PASSED verbally.** [visual.py](research/models/brc/brc001/visual.py) got a `direction` arg (buy/sell/both) + `overview3` batch mode + 500-bar default. Rendered [overview_buy/sell/both.png](research/outputs/brc001/) (BUY 23 / SELL 13 / both 36 zones, last 500 D1 bars). **Syafiq eyeballed all three: "the three charts are ok."** Committed `118afbb`, pushed.
- **Gate 2 pass NOT yet executed** — I have his verbal OK but did not run `open_gate`/`pass_gate` yet. That is the immediate first action below.
- **Touch model CONFIRMED with Syafiq (matches code + EA):** T1=L1=P2 (Layer1), T2=50%=mid(L1,L2) (Layer2), T3=L2=P1 (Layer3). Under restored P3<P1 gate L2 collapses to exactly P1.
- **Key gap surfaced:** BRC has **NO post-confirmation invalidation** — [zones.py](research/models/brc/brc001/zones.py) only has the PRE-confirmation `_passes_gap`. Once a zone is born at P4, nothing kills it. Must build (task 116).
- **Continuation anchor DECIDED = Option A** (measure forward return FROM the retest touch bar, not from P4). Thesis = Break→Retest→Continuation (price-action memory).
- **Architecture DECISION:** do NOT rebuild MT5's live state-event engine in Python. Batch is correct for research; "live watch" returns as a frozen per-zone lifecycle panel (task 117) after 116/108; true live-watch belongs at deployment via Gate-7 Python↔MT5 fidelity.

## Next
1. **Execute Gate 2 pass** (verbal OK already given): `pipeline.open_gate('BRC-001',2,pass_criteria=...)` then `pass_gate(2)`; then `backlog.resolve_task(115,...)` + `resolve_task(114,...)` (114 subsumed by 115).
2. **Task 116 (P1, infra) — build invalidation FIRST.** Forward-walk each confirmed zone from P4; mark DEAD at first bar CLOSING beyond L2(=P1): close>L2 SELL / close<L2 BUY. Mirrors EA [B2BZoneStatus.mqh:169-197](mt5/Include/Sigma_System/V5.0/Detection/B2BZoneStatus.mqh#L169-L197). Death boundary for all later measurement.
3. **Task 108 (P1, variant) — retest ladder + continuation.** Wick-based (D1 high/low) ordered T1→T2→T3; record deepest-T (T0/T1/T2/T3); Option-A continuation from each touch bar (horizon H + to-invalidation). Emit per-zone dataset (zone_id, dir, break_kind, deepest_T, touch_times, cont@T1/@T2/@T3, invalidated) → feeds Gate-3 edge test (task 110).
4. **Task 117 (P2)** lifecycle visual panel — AFTER 116/108. **Task 110 (P2)** Gate-3 edge test — consumes 108 dataset.

## Blockers
None. Detection diverges from EA by design (Path B; EA no longer the zone-for-zone oracle) — validation = Gate-2 eyeball (done) + Gate-3 edge test. Nuance to carry: T3 = WICK poke of L2 (zone still alive); invalidation = CLOSE beyond L2 (dead) — same level, two rules. Context hit ~102k soft threshold → this handover. No result-numbers cited because no edge has been measured yet (pre-Gate-3).
