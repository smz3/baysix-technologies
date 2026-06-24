# Handover — June 24, 2026 Afternoon

> BRC-zone entry is PARKED. Both directions lose ~identically → no directional edge. Pivot = revive original B2B and compare. Don't re-litigate the fade.

## State
- **FADE tested + dead (task 131 done).** Built mirror-R fade in v1.3.0 (`BRC_FADE`: STOP entry at the level, stop mirrored across entry so |risk| = continuation). Same IS-01 atom (SINGLE/L1/k0.20), only direction flipped.
- **Verdict — both sides bleed the cost floor:**
  - CONT re-baseline (v1.3.0, real ticks): E[R]=−0.213, net −0.672/trade, t=−4.78, n=1459 — **result_id 9**.
  - FADE: E[R]=−0.220, net −0.569/trade, t=−4.84, n=1546 — **result_id 10**.
  - Identical loss ⇒ the BRC level has **no directional content**; −0.22R is just cost/drag. A real edge would be asymmetric (mirror would win). It doesn't.
- **BRC PARKED, not killed** (Syafiq's call): 2 falsifications on record (rule 8b met) but reopenable. strategy_log #67 (REJECTED→PARKED), human_decision 86.
- Code: fade in [brc_entry.mqh](../mt5/Include/brc_system/brc_entry.mqh#L118), `is_long` widened for BUY_STOP [brc_trader.mq5:521](../mt5/Experts/brc_system/brc_trader.mq5#L521), readable tester input labels. Presets [CONT](../mt5/presets/brc_system/brc_trader-v1.3.0-IS01-CONT.set) / [FADE](../mt5/presets/brc_system/brc_trader-v1.3.0-Halt1-FADE.set). Compiles clean (0/0), shas ecafc29→69467ef.
- **Tester .set loading learned:** dialog reads `MQL5\Profiles\Tester\` (NOT `Presets\`). Both v1.3.0 .sets copied there. Load via Inputs tab → Load; row "3) ENTRY SIDE" must read CONTINUATION/FADE.

## Next
1. **Revive ORIGINAL B2B → MT5 tester (task 149, P1).** Untangle the bloated last-yr B2B AI code, get it MT5-testable on IDENTICAL `XAUUSD_dukas`, same span (2016.06–2024.06), same real-ticks/cost model, scored net $/trade + E[R]. (Fresh-context job — heavy.)
2. **Compare B2B-original vs BRC** (result_id 9 cont / result_id 10 fade). Q: did BRC reconstruction lose an edge the original had, or was the zone premise always edgeless?
3. **If B2B-original also loses** → zone-entry premise dead; formalize BRC kill + close the family. If it wins → BRC broke something in translation.

## Blockers
None. OOS #126 stays blocked (no positive frozen IS edge). B2B code is bloated/spaghetti — untangling is the task-149 cost, not a blocker.
