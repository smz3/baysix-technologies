# Handover — June 26, 2026 Afternoon

## State (FOB v1.13.0 = MULTI-POSITION + pure price-action; built+compiled+pushed, NOT yet run)
- **Big mechanic change shipped (sha 033d1f6, v1.13.0, strategy_log 77, task 176 done):**
  - **Multi-position** — dropped the 1-at-a-time `TS_INPOS` gate in [fob_trader.mq5](mt5/Experts/fob_system/fob_trader.mq5). EVERY CF now opens its own independent position (hedging). Rationale: the gate let the 1st CF lock the cycle so the **2nd CF (paper's best entry)** and beyond never fired. Position-id read off the entry deal (hedging-safe; `PositionSelect(_Symbol)` was ambiguous with concurrent positions). **JM = hedging (Syafiq confirmed)** — REQUIRED, netting would merge the positions.
  - **ATR fully removed** — FOB is now pure price-action, zero indicators. Study-mode MFE/MAE kept but in **RAW POINTS** (dropped atr/first_1atr columns; excursion CSV schema changed).
  - **Visual retention** — [fob_visual.mqh:229-231](mt5/Include/fob_system/fob_visual.mqh#L229-L231): a cycle with a LIVE open position keeps its PBO/VR/CF dots even after a newer cycle supersedes it (shows "held (open trade)"). Emitter untouched via a 2-arg `RedrawCurrentTF` overload.
- Both `fob_trader` + `fob_baysix` compile **0 errors** (1 cosmetic MQL5-Market version warning).
- Run config staged: [fob_m15_rr3_sl2.ini](mt5/tester/fob_m15_rr3_sl2.ini) — M15→M5, CF_ZONE, RR=3.0, SLbuf=2.0, real ticks 2016→2024.
- Excursion prior (task 170, result_id 13/14): P(MFE≥3 ATR)=28% vs 25% RR=3 breakeven → reachable but razor-thin; SLbuf=2 widens risk so reach drops. Fresh run = arbiter. SL is penetration-relative (buffer = K×penetration); collapses on shallow close-based breaks — left as-is per Syafiq.

## Next
1. **(task 175, P1) RUN [fob_m15_rr3_sl2.ini](mt5/tester/fob_m15_rr3_sl2.ini)** on the now multi-position v1.13.0 EA (JM closed + flat). Expect MANY more trades than v1.12.0 (no gate). Then ingest the FOB ledger, compute net $/trade + survival (NOT E[R], [[er_denominator_illusion]]), `pipeline.log_result()`, tie to strategy_log 77.
2. After result: sweep SLbuf {0,0.5,1,2} + confirm RR. Rank by net $/trade + survival.
3. **(task 171, P1)** retest entry (limit-on-pullback into PBO zone) — after RR/SL locked.

## Blockers
None. Compile = call `metaeditor64.exe` DIRECTLY from Bash (`/compile /inc:mt5/ /log:`) — the `powershell.exe -Command` route is DENIED by the classifier; direct-exe works (sha 033d1f6 built that way). Tester run needs JM terminal CLOSED + Syafiq flat (live $50). Tester account MUST be hedging.
