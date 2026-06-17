# Handover — June 17, 2026 Morning2

## State
- **BRC detection spec FULLY LOCKED this session (discussion-only, no code written).** Resolves the 06-17 Morning blocker (DISPUTED detection). Decision logged: human call_id 76, strategy_log #48 (ADOPTED, component=entry).
- **Method = Path B: rawbreakout-derived.** BRC zones pair same-direction `struct.rawbreakout` events — 1st break = P2 (=L1 entry), 2nd break = P5 (confirm) — layered on swings (swings still give P1=L2 and P3=gate). NOT a swing-scan.
- **Mapping confirmed vs live EA** [B2BDetector.mqh:381-425](mt5/Include/Sigma_System/V5.0/Detection/B2BDetector.mqh#L381-L425): **L1 = P2, L2 = P1** (always, both dirs), fifty = mid(L1,L2), first_barrier=P2, second_barrier=P5. Visualizer touch states T1→T2→T3 (L1→50%→L2) = Syafiq's pullback thesis, already native.
- **P3<P1 gate RESTORED** (Syafiq yes). Makes L2=MAX(P1,P3)=P1 fall out, kills doc self-contradiction.
- **P4 = same-bar OR sequential** — one impulse bar breaks P2+P5, OR P2 then P5 on later bar. Both valid; native to struct's two-pass shared-L2. The same-bar/sequential label is the H_alt-2 (is-2nd-break-load-bearing) input for the Gate-3 edge test (task 110).
- **KEY FINDING:** the live EA does NOT derive zones from rawbreakouts — it is a swing-scan + plain `close < P5` P4 scan ([B2BDetector.mqh:588-628](mt5/Include/Sigma_System/V5.0/Detection/B2BDetector.mqh#L588-L628)); rawbreakouts are drawn but never consumed. So Path B is a **deliberate departure → EA is no longer a zone-for-zone oracle.** Validation = eyeball Gate 2 + the edge test.
- **BUY visual in [5PointB2BDetection.md](mt5/Include/Sigma_System/V5.0/Docs/5PointB2BDetection.md) is WRONG** (P1/LOW drawn far-right instead of left after P5). SELL diagram + both point tables are correct. Logic everywhere else is correct.
- Current [zones.py](research/models/brc/brc001/zones.py) is still the OLD Path-A swing-scan (close-scan P4, gate dropped) — to be rewritten next session. Nothing committed/changed this session except DB logs.

## Next (tasks 111-114 added this session, all under BRC-001)
1. **Task 111 (P1)** — fix BUY ASCII in 5PointB2BDetection.md as a true mirror of SELL (P5 high-left → P1 LOW/L2 → P2 HIGH/L1 → P3 higher-low → P4 above P5 right).
2. **Task 112 (P1)** — rewrite [zones.py](research/models/brc/brc001/zones.py) Path B: consume struct.rawbreakout, pair same-dir breaks (P2 then P5; P5 more extreme + older than P1), swings → P1(L2)+P3(gate), label same-bar vs sequential. Trace P1/L2 source vs EA first_barrier/L2_price.
3. **Task 113 (P1)** — port EA accuracy fixes: freshness (no swing between P3,P4), gap-validation (L2 not closed-through pre-P4), one-zone-per-P5 dedup (freshest P1). These fix the stale/duplicate zones = the real "inaccuracy". Needed regardless of A/B.
4. **Task 114 (P2)** — re-render Gate-2 visualizer → Syafiq eyeballs → open_gate(2)+pass_gate(2).
5. Downstream (already open): task 108 retest+continuation, task 110 Gate-3 edge test (H_base continuation vs H_alt-1 fade vs H_alt-2 single-vs-two-break).

## Blockers
None — spec locked, build greenlit. Path B accepted with its cost (EA no longer the validation oracle). Handover triggered by context soft-threshold (~104k), not a blocker.
